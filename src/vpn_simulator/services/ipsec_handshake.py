"""IKEv1/IPSec 真实握手编排：packetio + crypto + 状态机。

在一次 UDP 套接字上执行真实的 IKEv1 Main Mode（Phase 1，6 消息）与
Quick Mode（Phase 2，3 消息）握手：

- 发起方 `initiate()`：驱动 `IPsecStateMachine` INITIAL → CONNECTED，
  返回 ``(cookie_i, cookie_r)``。
- 响应方 `respond()`：对应回复 9 条消息，返回 ``(cookie_i, cookie_r)``。

本模块只做控制面握手（ISAKMP/IPSec SA 建立），不实现 ESP 数据面转发。
"""

from __future__ import annotations

from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.ipsec.crypto import (
    IPsecKeySet,
    build_main_mode_auth,
    build_main_mode_ke,
    build_main_mode_sa,
    build_quick_mode_msg,
    derive_key_set,
    dh,
    generate_cookie,
    generate_ephemeral,
    generate_nonce,
    parse_main_mode_auth,
    parse_main_mode_ke,
    parse_main_mode_sa,
    parse_quick_mode_msg,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0


class IPsecHandshake:
    """在 UDP 套接字上执行一次真实 IKEv1 握手。"""

    def __init__(
        self,
        identity: bytes,
        psk: bytes,
        socket: UdpSocket,
        state_machine: ProtocolStateMachine | None = None,
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._identity = identity
        self._psk = psk
        self._socket = socket
        self._state_machine = state_machine
        self._on_packet = on_packet
        self._cookie = generate_cookie()
        self._private, self._public = generate_ephemeral()
        self._nonce = generate_nonce()
        self._keys: IPsecKeySet | None = None

    async def initiate(
        self,
        responder_addr: tuple[str, int],
        responder_identity: bytes,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """发起方执行握手，返回 ``(cookie_i, cookie_r)``。"""
        local_addr = self._socket.local_address

        # Phase 1 Main Mode
        msg1 = build_main_mode_sa(self._cookie, 0, is_initiator=True)
        await self._socket.sendto(msg1, responder_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_SA", msg1, local_addr, responder_addr)
        await self._trigger("SEND_PHASE1_SA")

        msg2, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_SA", msg2, _peer, local_addr)
        sa_resp = parse_main_mode_sa(msg2)
        await self._trigger("RECEIVE_PHASE1_SA")

        msg3 = build_main_mode_ke(self._cookie, sa_resp.cookie_r, self._public, self._nonce, True)
        await self._socket.sendto(msg3, responder_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_KE", msg3, local_addr, responder_addr)
        await self._trigger("SEND_PHASE1_KE")

        msg4, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_KE", msg4, _peer, local_addr)
        ke_resp = parse_main_mode_ke(msg4)
        shared = dh(self._private, ke_resp.ke)
        self._keys = derive_key_set(self._psk, self._nonce, ke_resp.nonce)
        logger.info("ipsec_phase1_keys_derived", shared_len=len(shared))
        await self._trigger("RECEIVE_PHASE1_KE")

        msg5 = build_main_mode_auth(
            self._cookie,
            sa_resp.cookie_r,
            self._keys.skeyid,
            self._keys.skeyid_e,
            self._public,
            ke_resp.ke,
            self._nonce,
            ke_resp.nonce,
            self._identity,
            True,
        )
        await self._socket.sendto(msg5, responder_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_AUTH", msg5, local_addr, responder_addr)
        await self._trigger("SEND_PHASE1_AUTH")

        msg6, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_AUTH", msg6, _peer, local_addr)
        parse_main_mode_auth(
            self._keys.skeyid,
            self._keys.skeyid_e,
            self._public,
            ke_resp.ke,
            self._nonce,
            ke_resp.nonce,
            msg6,
            responder_identity,
        )
        await self._trigger("RECEIVE_PHASE1_AUTH")

        # Phase 2 Quick Mode
        nonce2_i = generate_nonce()
        qm1 = build_quick_mode_msg(
            self._cookie, sa_resp.cookie_r, self._keys.skeyid_a, nonce2_i, True
        )
        await self._socket.sendto(qm1, responder_addr)
        self._record(PacketDirection.OUTGOING, "QUICK_MODE_HASH", qm1, local_addr, responder_addr)
        await self._trigger("SEND_PHASE2_HASH")

        qm2, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "QUICK_MODE_HASH", qm2, _peer, local_addr)
        parse_quick_mode_msg(self._keys.skeyid_a, qm2)
        await self._trigger("RECEIVE_PHASE2_HASH")

        qm3 = build_quick_mode_msg(
            self._cookie, sa_resp.cookie_r, self._keys.skeyid_a, b"", True, final_ack=True
        )
        await self._socket.sendto(qm3, responder_addr)
        self._record(PacketDirection.OUTGOING, "QUICK_MODE_ACK", qm3, local_addr, responder_addr)
        await self._trigger("SEND_PHASE2_ACK")

        await self._trigger("ESP_SA_READY")
        await self._trigger("TUNNEL_ESTABLISHED")
        return self._cookie, sa_resp.cookie_r

    async def respond(
        self,
        initiator_identity: bytes,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """响应方执行握手，返回 ``(cookie_i, cookie_r)``。"""
        local_addr = self._socket.local_address

        msg1, initiator_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_SA", msg1, initiator_addr, local_addr)
        sa_req = parse_main_mode_sa(msg1)

        msg2 = build_main_mode_sa(sa_req.cookie_i, self._cookie, is_initiator=False)
        await self._socket.sendto(msg2, initiator_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_SA", msg2, local_addr, initiator_addr)

        msg3, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_KE", msg3, initiator_addr, local_addr)
        ke_req = parse_main_mode_ke(msg3)

        msg4 = build_main_mode_ke(sa_req.cookie_i, self._cookie, self._public, self._nonce, False)
        await self._socket.sendto(msg4, initiator_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_KE", msg4, local_addr, initiator_addr)
        self._keys = derive_key_set(self._psk, ke_req.nonce, self._nonce)

        msg5, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "MAIN_MODE_AUTH", msg5, initiator_addr, local_addr)
        parse_main_mode_auth(
            self._keys.skeyid,
            self._keys.skeyid_e,
            ke_req.ke,
            self._public,
            ke_req.nonce,
            self._nonce,
            msg5,
            initiator_identity,
        )

        msg6 = build_main_mode_auth(
            sa_req.cookie_i,
            self._cookie,
            self._keys.skeyid,
            self._keys.skeyid_e,
            ke_req.ke,
            self._public,
            ke_req.nonce,
            self._nonce,
            self._identity,
            False,
        )
        await self._socket.sendto(msg6, initiator_addr)
        self._record(PacketDirection.OUTGOING, "MAIN_MODE_AUTH", msg6, local_addr, initiator_addr)

        qm1, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "QUICK_MODE_HASH", qm1, initiator_addr, local_addr)
        parse_quick_mode_msg(self._keys.skeyid_a, qm1)

        nonce2_r = generate_nonce()
        qm2 = build_quick_mode_msg(
            sa_req.cookie_i, self._cookie, self._keys.skeyid_a, nonce2_r, False
        )
        await self._socket.sendto(qm2, initiator_addr)
        self._record(PacketDirection.OUTGOING, "QUICK_MODE_HASH", qm2, local_addr, initiator_addr)

        qm3, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "QUICK_MODE_ACK", qm3, initiator_addr, local_addr)
        parse_quick_mode_msg(self._keys.skeyid_a, qm3, final_ack=True)
        return sa_req.cookie_i, self._cookie

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
            protocol="ipsec",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
