"""IKEv2/IPSec 真实握手编排：packetio + crypto + 状态机。

在一次 UDP 套接字上执行真实的 IKEv2 控制面握手：

- 发起方 `initiate()`：IKE_SA_INIT 请求 → 响应 → IKE_AUTH 请求 → 响应，
  驱动 `IKEv2StateMachine` INITIAL → CONNECTED，返回 ``(spi_i, spi_r)``。
- 响应方 `respond()`：接收 IKE_SA_INIT 请求、回复响应、接收并校验 IKE_AUTH、
  回复 IKE_AUTH，返回 ``(spi_i, spi_r)``。

本模块只做控制面握手（IKE SA 建立），不实现 ESP 数据面转发。
"""

from __future__ import annotations

from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.ikev2.crypto import (
    IKEv2KeySet,
    build_ike_auth,
    build_ike_sa_init,
    derive_key_set,
    dh,
    generate_ephemeral,
    generate_nonce,
    generate_spi,
    parse_ike_auth,
    parse_ike_sa_init,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0


class IKEv2Handshake:
    """在 UDP 套接字上执行一次真实 IKEv2 握手。"""

    def __init__(
        self,
        identity: bytes,
        socket: UdpSocket,
        state_machine: ProtocolStateMachine | None = None,
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._identity = identity
        self._socket = socket
        self._state_machine = state_machine
        self._on_packet = on_packet
        self._spi = generate_spi()
        self._private, self._public = generate_ephemeral()
        self._nonce = generate_nonce()
        self._keys: IKEv2KeySet | None = None

    async def initiate(
        self,
        responder_addr: tuple[str, int],
        responder_identity: bytes,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """发起方执行握手，返回 ``(spi_i, spi_r)``。"""
        local_addr = self._socket.local_address

        # 1. IKE_SA_INIT 请求
        request = build_ike_sa_init(self._spi, 0, self._public, self._nonce, is_initiator=True)
        await self._socket.sendto(request, responder_addr)
        self._record(PacketDirection.OUTGOING, "IKE_SA_INIT", request, local_addr, responder_addr)
        logger.info("ikev2_sa_init_sent", bytes=len(request), to=responder_addr)
        await self._trigger("SEND_IKE_SA_INIT")

        # 2. IKE_SA_INIT 响应
        response, _peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "IKE_SA_INIT", response, _peer_addr, local_addr)
        sa_resp = parse_ike_sa_init(response)
        self._keys = derive_key_set(
            dh(self._private, sa_resp.ke_public), self._nonce, sa_resp.nonce
        )
        logger.info("ikev2_sa_init_received", bytes=len(response), spi_r=sa_resp.spi_r)
        await self._trigger("RECEIVE_IKE_SA_INIT")

        # 3. IKE_AUTH 请求
        auth_req = build_ike_auth(
            self._keys.sk_ei,
            self._keys.sk_pi,
            self._spi,
            sa_resp.spi_r,
            msgid=1,
            identity=self._identity,
            is_initiator=True,
        )
        await self._socket.sendto(auth_req, responder_addr)
        self._record(PacketDirection.OUTGOING, "IKE_AUTH", auth_req, local_addr, responder_addr)
        await self._trigger("SEND_IKE_AUTH")

        # 4. IKE_AUTH 响应
        auth_resp, _peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "IKE_AUTH", auth_resp, _peer_addr, local_addr)
        parse_ike_auth(self._keys.sk_er, self._keys.sk_pi, auth_resp, responder_identity)
        await self._trigger("RECEIVE_IKE_AUTH")

        # 5-6. Child SA 与 ESP 隧道就绪（控制面握手完成）。
        await self._trigger("CHILD_SA_READY")
        await self._trigger("ESP_TUNNEL_READY")
        return self._spi, sa_resp.spi_r

    async def respond(
        self,
        initiator_identity: bytes,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """响应方执行握手，返回 ``(spi_i, spi_r)``。"""
        local_addr = self._socket.local_address

        # 1. 接收 IKE_SA_INIT 请求
        request, initiator_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "IKE_SA_INIT", request, initiator_addr, local_addr)
        sa_req = parse_ike_sa_init(request)
        self._keys = derive_key_set(dh(self._private, sa_req.ke_public), sa_req.nonce, self._nonce)
        logger.info("ikev2_sa_init_received", bytes=len(request), spi_i=sa_req.spi_i)

        # 2. 回复 IKE_SA_INIT 响应
        response = build_ike_sa_init(
            sa_req.spi_i, self._spi, self._public, self._nonce, is_initiator=False
        )
        await self._socket.sendto(response, initiator_addr)
        self._record(PacketDirection.OUTGOING, "IKE_SA_INIT", response, local_addr, initiator_addr)

        # 3. 接收并校验 IKE_AUTH 请求
        auth_req, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "IKE_AUTH", auth_req, initiator_addr, local_addr)
        parse_ike_auth(self._keys.sk_ei, self._keys.sk_pi, auth_req, initiator_identity)

        # 4. 回复 IKE_AUTH 响应
        auth_resp = build_ike_auth(
            self._keys.sk_er,
            self._keys.sk_pi,
            self._spi,
            sa_req.spi_i,
            msgid=1,
            identity=self._identity,
            is_initiator=False,
        )
        await self._socket.sendto(auth_resp, initiator_addr)
        self._record(PacketDirection.OUTGOING, "IKE_AUTH", auth_resp, local_addr, initiator_addr)
        return sa_req.spi_i, self._spi

    async def _trigger(self, event: str) -> None:
        if self._state_machine is not None:
            await self._state_machine.trigger(event)

    def _record(
        self,
        direction: PacketDirection,
        message_type: str,
        data: bytes,
        src: tuple[str, int] | None,
        dst: tuple[str, int] | None,
    ) -> None:
        if self._on_packet is None:
            return
        src_ip, src_port = src if src else ("", 0)
        dst_ip, dst_port = dst if dst else ("", 0)
        self._on_packet(
            protocol="ikev2",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
