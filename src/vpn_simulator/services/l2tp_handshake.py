"""L2TP 真实握手编排：packetio + control + 状态机。

在一次 UDP 套接字上执行真实的 L2TP 控制面握手：

- 客户端 `initiate()`：SCCRQ → SCCRP（校验隧道认证）→ SCCCN → ICRQ → ICRP → ICCN，
  返回 ``(client_tunnel_id, server_tunnel_id)``。
- 服务端 `respond()`：接收并回复上述消息，驱动 `L2TPStateMachine`（服务器视角）
  INITIAL → CONNECTED，返回 ``(client_tunnel_id, server_tunnel_id)``。

本模块只做控制面握手与隧道认证（HMAC challenge-response），不实现 PPP 加密。
"""

from __future__ import annotations

import hmac as hmac_mod
from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.l2tp.control import (
    MSG_ICCN,
    MSG_SCCCN,
    build_empty,
    build_icrp,
    build_icrq,
    build_sccrp,
    build_sccrq,
    compute_challenge_response,
    generate_challenge,
    parse_empty,
    parse_icrp,
    parse_icrq,
    parse_sccrp,
    parse_sccrq,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0
CLIENT_TUNNEL_ID = 1
SERVER_TUNNEL_ID = 2
CLIENT_SESSION_ID = 1
SERVER_SESSION_ID = 2


class L2TPHandshake:
    """在 UDP 套接字上执行一次真实 L2TP 握手。"""

    def __init__(
        self,
        secret: bytes,
        socket: UdpSocket,
        state_machine: ProtocolStateMachine | None = None,
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._secret = secret
        self._socket = socket
        self._state_machine = state_machine
        self._on_packet = on_packet

    async def initiate(
        self,
        peer_addr: tuple[str, int],
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """客户端执行握手，返回 ``(client_tunnel_id, server_tunnel_id)``。"""
        local_addr = self._socket.local_address
        challenge = generate_challenge()

        sccrq = build_sccrq(CLIENT_TUNNEL_ID, challenge)
        await self._socket.sendto(sccrq, peer_addr)
        self._record(PacketDirection.OUTGOING, "SCCRQ", sccrq, local_addr, peer_addr)

        sccrp, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "SCCRP", sccrp, _peer, local_addr)
        _, response, server_tunnel_id = parse_sccrp(sccrp)
        expected = compute_challenge_response(self._secret, challenge, CLIENT_TUNNEL_ID)
        if not hmac_mod.compare_digest(response, expected):
            raise ValueError("L2TP 隧道认证失败")
        logger.info("l2tp_tunnel_authenticated", server_tunnel_id=server_tunnel_id)

        scccn = build_empty(CLIENT_TUNNEL_ID, 0, MSG_SCCCN)
        await self._socket.sendto(scccn, peer_addr)
        self._record(PacketDirection.OUTGOING, "SCCCN", scccn, local_addr, peer_addr)

        icrq = build_icrq(CLIENT_SESSION_ID)
        await self._socket.sendto(icrq, peer_addr)
        self._record(PacketDirection.OUTGOING, "ICRQ", icrq, local_addr, peer_addr)

        icrp, _peer = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "ICRP", icrp, _peer, local_addr)
        _, server_session_id = parse_icrp(icrp)
        logger.info("l2tp_session_replied", server_session_id=server_session_id)

        iccn = build_empty(CLIENT_TUNNEL_ID, CLIENT_SESSION_ID, MSG_ICCN)
        await self._socket.sendto(iccn, peer_addr)
        self._record(PacketDirection.OUTGOING, "ICCN", iccn, local_addr, peer_addr)
        return CLIENT_TUNNEL_ID, server_tunnel_id

    async def respond(
        self,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """服务端执行握手，返回 ``(client_tunnel_id, server_tunnel_id)``。"""
        local_addr = self._socket.local_address
        await self._trigger("START")

        sccrq, client_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "SCCRQ", sccrq, client_addr, local_addr)
        _, challenge, client_tunnel_id = parse_sccrq(sccrq)
        response = compute_challenge_response(self._secret, challenge, client_tunnel_id)
        await self._trigger("RECEIVE_SCCRQ")

        sccrp = build_sccrp(SERVER_TUNNEL_ID, response)
        await self._socket.sendto(sccrp, client_addr)
        self._record(PacketDirection.OUTGOING, "SCCRP", sccrp, local_addr, client_addr)

        scccn, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "SCCCN", scccn, client_addr, local_addr)
        parse_empty(scccn, MSG_SCCCN)
        await self._trigger("RECEIVE_SCCCN")

        icrq, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "ICRQ", icrq, client_addr, local_addr)
        _, client_session_id = parse_icrq(icrq)
        await self._trigger("RECEIVE_ICRQ")

        icrp = build_icrp(SERVER_SESSION_ID)
        await self._socket.sendto(icrp, client_addr)
        self._record(PacketDirection.OUTGOING, "ICRP", icrp, local_addr, client_addr)
        logger.info("l2tp_session_established", client_session_id=client_session_id)

        iccn, _ = await self._socket.recvfrom(timeout=timeout)
        self._record(PacketDirection.INCOMING, "ICCN", iccn, client_addr, local_addr)
        parse_empty(iccn, MSG_ICCN)
        await self._trigger("RECEIVE_ICCN")

        await self._trigger("START_PPP")
        await self._trigger("PPP_COMPLETE")
        return client_tunnel_id, SERVER_TUNNEL_ID

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
            protocol="l2tp",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
