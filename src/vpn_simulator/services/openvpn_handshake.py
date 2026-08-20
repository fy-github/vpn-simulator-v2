"""OpenVPN 控制信道真实握手编排：Hard Reset + TLS + PUSH + 状态机。

在一次 UDP 套接字上执行真实的 OpenVPN 控制信道握手：

1. **Hard Reset**：交换 ``P_CONTROL_HARD_RESET_CLIENT_V2`` / ``_SERVER_V2``（均经
   ``--tls-auth`` HMAC 认证）。
2. **TLS 握手**：在控制信道（``P_CONTROL_V1`` 载荷）上用 ``ssl.MemoryBIO`` 驱动真实
   TLS 1.3 握手（服务端自签名证书，客户端 ``CERT_NONE`` 跳过验证，教学模拟器）。
3. **数据密钥**：真实 OpenVPN 用 TLS keying-material exporter 派生数据密钥；本环境
   Python ssl 未暴露 ``export_keying_material``，故在 TLS 加密信道内交换随机 32 字节
   数据密钥（见 ``plugins/protocols/openvpn/tls.py``）。
4. **PUSH**：客户端发 ``PUSH_REQUEST``、服务端回 ``PUSH_REPLY``（均 P_CONTROL_V1
   明文控制消息），驱动状态机到 ``CONNECTED``。

本模块不转发数据面报文（数据面见 ``services/openvpn_transport.py``）。
"""

from __future__ import annotations

import secrets
import ssl
from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.openvpn.control_channel import (
    P_CONTROL_HARD_RESET_CLIENT_V2,
    P_CONTROL_HARD_RESET_SERVER_V2,
    P_CONTROL_V1,
    build_control_packet,
    generate_session_id,
    parse_control_packet,
)
from vpn_simulator.plugins.protocols.openvpn.tls import DATA_KEY_LEN, TLSBIO, create_tls_contexts

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0

PUSH_REQUEST = b"PUSH_REQUEST"
PUSH_REPLY = b"PUSH_REPLY: ifconfig 10.8.0.2 10.8.0.1"


class OpenVPNHandshake:
    """在 UDP 套接字上执行一次真实 OpenVPN 控制信道握手（含 TLS + PUSH）。"""

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
        self._session_id = 0
        self._peer_addr: tuple[str, int] | None = None
        self._next_packet_id = 1  # Hard Reset 使用 packet_id=0

    async def initiate(
        self,
        server_addr: tuple[str, int],
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[int, int, bytes]:
        """发起方执行握手，返回 ``(本端 session_id, 对端 session_id, 数据密钥)``。"""
        self._session_id = generate_session_id()
        self._peer_addr = server_addr
        reset_client = build_control_packet(
            P_CONTROL_HARD_RESET_CLIENT_V2, self._session_id, 0, b"", self._tls_auth_key
        )
        local_addr = self._socket.local_address
        await self._socket.sendto(reset_client, server_addr)
        self._record(
            PacketDirection.OUTGOING, "HARD_RESET_CLIENT_V2", reset_client, local_addr, server_addr
        )
        logger.info("openvpn_hard_reset_client_sent", bytes=len(reset_client), to=server_addr)
        await self._trigger("SEND_HARD_RESET")

        reset_server, peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(
            PacketDirection.INCOMING, "HARD_RESET_SERVER_V2", reset_server, peer_addr, local_addr
        )
        parsed = parse_control_packet(reset_server, self._tls_auth_key)
        if parsed.opcode != P_CONTROL_HARD_RESET_SERVER_V2:
            raise ValueError(f"unexpected opcode: {parsed.opcode_name}")
        server_session_id = parsed.session_id
        logger.info("openvpn_hard_reset_server_received", bytes=len(reset_server))
        await self._trigger("RECEIVE_HARD_RESET")
        await self._trigger("START_TLS")

        data_key = await self._run_tls_and_push(client_side=True, timeout=timeout)
        return self._session_id, server_session_id, data_key

    async def respond(self, timeout: float = DEFAULT_HANDSHAKE_TIMEOUT) -> tuple[int, int, bytes]:
        """响应方执行握手，返回 ``(发起方 session_id, 本端 session_id, 数据密钥)``。"""
        reset_client, initiator_addr = await self._socket.recvfrom(timeout=timeout)
        local_addr = self._socket.local_address
        self._peer_addr = initiator_addr
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
        client_session_id = parsed.session_id
        logger.info("openvpn_hard_reset_client_received", bytes=len(reset_client))

        self._session_id = generate_session_id()
        reset_server = build_control_packet(
            P_CONTROL_HARD_RESET_SERVER_V2, self._session_id, 0, b"", self._tls_auth_key
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

        data_key = await self._run_tls_and_push(client_side=False, timeout=timeout)
        return client_session_id, self._session_id, data_key

    async def _run_tls_and_push(self, client_side: bool, timeout: float) -> bytes:
        """TLS 握手 + 数据密钥交换 + PUSH（均在 TLS 加密信道内），返回数据密钥。"""
        server_ctx, client_ctx = create_tls_contexts()
        tlsbio = TLSBIO(client_ctx if client_side else server_ctx, server_side=not client_side)

        await self._drive_tls_handshake(tlsbio, timeout)
        if client_side:
            data_key = secrets.token_bytes(DATA_KEY_LEN)
            tlsbio.write(data_key)
            tlsbio.write(PUSH_REQUEST)
            await self._flush_tls(tlsbio)
            await self._trigger("TLS_COMPLETE")
            await self._trigger("SEND_PUSH_REQUEST")
            reply = await self._recv_tls_app_data(tlsbio, len(PUSH_REPLY), timeout)
            if reply != PUSH_REPLY:
                raise ValueError(f"unexpected PUSH reply: {reply!r}")
            await self._trigger("RECEIVE_PUSH_REPLY")
        else:
            data_key = await self._recv_tls_app_data(tlsbio, DATA_KEY_LEN, timeout)
            request = await self._recv_tls_app_data(tlsbio, len(PUSH_REQUEST), timeout)
            if request != PUSH_REQUEST:
                raise ValueError(f"unexpected PUSH request: {request!r}")
            tlsbio.write(PUSH_REPLY)
            await self._flush_tls(tlsbio)
            await self._trigger("TLS_COMPLETE")
        logger.info("openvpn_tls_established", version=tlsbio.version)
        return data_key

    async def _drive_tls_handshake(self, tlsbio: TLSBIO, timeout: float) -> None:
        """非阻塞驱动 TLS 握手：``do_handshake`` 抛 WantRead/Write 时收发控制报文。"""
        while True:
            try:
                tlsbio.do_handshake()
                await self._flush_tls(tlsbio)
                return
            except ssl.SSLWantReadError:
                await self._flush_tls(tlsbio)
                tlsbio.feed_incoming(await self._recv_control_payload(timeout))
            except ssl.SSLWantWriteError:
                await self._flush_tls(tlsbio)

    async def _flush_tls(self, tlsbio: TLSBIO) -> None:
        """把 TLSBIO 待发送字节全部作为 P_CONTROL_V1 载荷发出。"""
        while tlsbio.has_outgoing():
            await self._send_control_payload(tlsbio.take_outgoing())

    async def _recv_tls_app_data(self, tlsbio: TLSBIO, n: int, timeout: float) -> bytes:
        """从 TLS 加密信道接收 ``n`` 字节明文（累计直到凑满）。"""
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = tlsbio.read(n - len(buf))
                if chunk:
                    buf.extend(chunk)
                else:
                    raise ValueError("TLS peer closed unexpectedly")
            except ssl.SSLWantReadError:
                tlsbio.feed_incoming(await self._recv_control_payload(timeout))
        return bytes(buf)

    async def _send_control_payload(self, payload: bytes) -> None:
        assert self._peer_addr is not None
        packet = build_control_packet(
            P_CONTROL_V1,
            self._session_id,
            self._next_packet_id,
            payload,
            self._tls_auth_key,
        )
        self._next_packet_id += 1
        await self._socket.sendto(packet, self._peer_addr)
        self._record(
            PacketDirection.OUTGOING,
            "P_CONTROL_V1",
            packet,
            self._socket.local_address,
            self._peer_addr,
        )

    async def _recv_control_payload(self, timeout: float) -> bytes:
        """接收一条 P_CONTROL_V1 报文并返回其载荷。"""
        raw, peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(
            PacketDirection.INCOMING,
            "P_CONTROL_V1",
            raw,
            peer_addr,
            self._socket.local_address,
        )
        parsed = parse_control_packet(raw, self._tls_auth_key)
        if parsed.opcode != P_CONTROL_V1:
            raise ValueError(f"unexpected opcode: {parsed.opcode_name}")
        return parsed.payload

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
