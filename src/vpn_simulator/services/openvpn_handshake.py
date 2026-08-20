"""OpenVPN 控制信道真实握手编排：packetio + control_channel + 状态机。

在一次 UDP 套接字上执行真实的 OpenVPN 控制信道 Hard Reset 交换：

- 发起方 `initiate()`：发送 P_CONTROL_HARD_RESET_CLIENT_V2、接收
  P_CONTROL_HARD_RESET_SERVER_V2（均经 ``--tls-auth`` HMAC 认证），驱动
  状态机 INITIAL → HARD_RESET_SENT → HARD_RESET_RECEIVED → TLS_HANDSHAKE。
- 响应方 `respond()`：接收 HARD_RESET_CLIENT_V2、校验 HMAC、回送
  HARD_RESET_SERVER_V2。

本模块只做控制面握手（Hard Reset + 控制信道组帧/HMAC 认证），不实现完整
TLS 数据面密钥协商，也不转发数据面报文。
"""

from __future__ import annotations

from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.openvpn.control_channel import (
    P_CONTROL_HARD_RESET_CLIENT_V2,
    P_CONTROL_HARD_RESET_SERVER_V2,
    build_control_packet,
    generate_session_id,
    parse_control_packet,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0


class OpenVPNHandshake:
    """在 UDP 套接字上执行一次真实 OpenVPN 控制信道握手。"""

    def __init__(
        self,
        tls_auth_key: bytes,
        socket: UdpSocket,
        state_machine: ProtocolStateMachine | None = None,
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._tls_auth_key = tls_auth_key
        self._socket = socket
        self._state_machine = state_machine
        self._on_packet = on_packet

    async def initiate(
        self,
        server_addr: tuple[str, int],
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int]:
        """发起方执行握手，返回 (本端 session_id, 对端 session_id)。

        真实网络动作为每一步状态转换的前提：发送 HARD_RESET_CLIENT_V2 后才
        触发 SEND_HARD_RESET，收到 HARD_RESET_SERVER_V2 后才触发
        RECEIVE_HARD_RESET / START_TLS。
        """
        client_session_id = generate_session_id()
        reset_client = build_control_packet(
            P_CONTROL_HARD_RESET_CLIENT_V2, client_session_id, 0, b"", self._tls_auth_key
        )
        local_addr = self._socket.local_address
        await self._socket.sendto(reset_client, server_addr)
        self._record(
            PacketDirection.OUTGOING,
            "HARD_RESET_CLIENT_V2",
            reset_client,
            local_addr,
            server_addr,
        )
        logger.info("openvpn_hard_reset_client_sent", bytes=len(reset_client), to=server_addr)
        await self._trigger("SEND_HARD_RESET")

        reset_server, peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(
            PacketDirection.INCOMING,
            "HARD_RESET_SERVER_V2",
            reset_server,
            peer_addr,
            local_addr,
        )
        parsed = parse_control_packet(reset_server, self._tls_auth_key)
        if parsed.opcode != P_CONTROL_HARD_RESET_SERVER_V2:
            raise ValueError(f"unexpected opcode: {parsed.opcode_name}")
        logger.info("openvpn_hard_reset_server_received", bytes=len(reset_server))
        await self._trigger("RECEIVE_HARD_RESET")
        await self._trigger("START_TLS")

        return client_session_id, parsed.session_id

    async def respond(self, timeout: float = DEFAULT_HANDSHAKE_TIMEOUT) -> int:
        """响应方接收 HARD_RESET_CLIENT_V2、校验 HMAC、回送 HARD_RESET_SERVER_V2。

        Returns:
            发起方的 session_id。
        """
        reset_client, initiator_addr = await self._socket.recvfrom(timeout=timeout)
        local_addr = self._socket.local_address
        self._record(
            PacketDirection.INCOMING,
            "HARD_RESET_CLIENT_V2",
            reset_client,
            initiator_addr,
            local_addr,
        )
        parsed = parse_control_packet(reset_client, self._tls_auth_key)
        if parsed.opcode != P_CONTROL_HARD_RESET_CLIENT_V2:
            raise ValueError(f"unexpected opcode: {parsed.opcode_name}")
        logger.info("openvpn_hard_reset_client_received", bytes=len(reset_client))

        server_session_id = generate_session_id()
        reset_server = build_control_packet(
            P_CONTROL_HARD_RESET_SERVER_V2, server_session_id, 0, b"", self._tls_auth_key
        )
        await self._socket.sendto(reset_server, initiator_addr)
        self._record(
            PacketDirection.OUTGOING,
            "HARD_RESET_SERVER_V2",
            reset_server,
            local_addr,
            initiator_addr,
        )
        logger.info("openvpn_hard_reset_server_sent", bytes=len(reset_server), to=initiator_addr)

        return parsed.session_id

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
            protocol="openvpn",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
