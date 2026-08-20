"""SSTP 真实握手编排：TLS 流 + SSTP 控制协商 + 状态机。

SSTP 协议栈：TCP(443) → TLS → SSTP 控制 → PPP。本模块在已建立 TLS 的 asyncio 流上
执行 SSTP 控制协商（CALL_CONNECT_REQUEST/ACK）：

- 客户端 `initiate()`：发 CALL_CONNECT_REQUEST → 收 CALL_CONNECT_ACK。
- 服务端 `respond()`：收 CALL_CONNECT_REQUEST → 发 CALL_CONNECT_ACK，驱动
  `SSTPStateMachine`（服务器视角）INITIAL → CONNECTED。

TLS 握手在连接建立阶段由 `ssl` 完成（见 `plugins/protocols/sstp/tls.py`）；
本模块只处理 TLS 之上的 SSTP 控制消息，PPP LCP/IPCP/MSCHAPv2 不实现（明示）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import structlog

from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.ppp.control import (
    CONFIGURE_ACK,
    CONFIGURE_REQUEST,
    build_configure_ack,
    build_configure_request,
    build_ipcp_ip_option,
    build_lcp_mru_option,
    parse_frame,
)
from vpn_simulator.plugins.protocols.ppp.control import (
    HEADER_LEN as PPP_HEADER_LEN,
)
from vpn_simulator.plugins.protocols.sstp.control import (
    CTL_CALL_CONNECT_ACK,
    CTL_CALL_CONNECT_REQUEST,
    HEADER_LEN,
    build_sstp_message,
    parse_call_connect_ack,
    parse_call_connect_request,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0


class SSTPHandshake:
    """在已建 TLS 的 asyncio 流上执行一次真实 SSTP 控制握手。"""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        state_machine: ProtocolStateMachine | None = None,
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._state_machine = state_machine
        self._on_packet = on_packet

    async def initiate(self) -> None:
        """客户端执行 SSTP 控制握手 + PPP LCP/IPCP 协商。"""
        await self._send(build_sstp_message(CTL_CALL_CONNECT_REQUEST), "CALL_CONNECT_REQUEST")
        raw = await self._recv_and_record("CALL_CONNECT_ACK")
        parse_call_connect_ack(raw)
        await self._negotiate_ppp()
        logger.info("sstp_connected")

    async def respond(self) -> None:
        """服务端执行 SSTP 控制握手，驱动状态机到 CONNECTED。"""
        await self._trigger("TCP_CONNECTED")
        await self._trigger("TLS_HANDSHAKE_COMPLETE")

        raw = await self._recv_and_record("CALL_CONNECT_REQUEST")
        parse_call_connect_request(raw)

        await self._send(build_sstp_message(CTL_CALL_CONNECT_ACK), "CALL_CONNECT_ACK")
        await self._trigger("SSTP_CALL_CONNECTED")

        # PPP LCP 协商（真实 Configure-Request/Ack）
        code, identifier, options = parse_frame(await self._recv_ppp("LCP_CONFIGURE_REQUEST"))
        if code != CONFIGURE_REQUEST:
            raise ValueError(f"expected LCP Configure-Request, got code {code}")
        await self._send_ppp(build_configure_ack(identifier, options), "LCP_CONFIGURE_ACK")
        await self._trigger("LCP_NEGOTIATION_COMPLETE")
        # MS-CHAPv2 认证在 validation 层执行，此处合成触发
        await self._trigger("AUTHENTICATION_SUCCESS")

        # PPP IPCP 协商（真实 Configure-Request/Ack）
        code, identifier, options = parse_frame(await self._recv_ppp("IPCP_CONFIGURE_REQUEST"))
        if code != CONFIGURE_REQUEST:
            raise ValueError(f"expected IPCP Configure-Request, got code {code}")
        await self._send_ppp(build_configure_ack(identifier, options), "IPCP_CONFIGURE_ACK")
        await self._trigger("IPCP_NEGOTIATION_COMPLETE")
        logger.info("sstp_tunnel_established")

    async def _negotiate_ppp(self) -> None:
        """客户端执行 PPP LCP/IPCP 协商（真实 Configure-Request/Ack）。"""
        code, _id, _data = parse_frame(
            await self._send_ppp_and_recv(
                build_configure_request(1, build_lcp_mru_option()),
                "LCP_CONFIGURE_REQUEST",
                "LCP_CONFIGURE_ACK",
            )
        )
        if code != CONFIGURE_ACK:
            raise ValueError(f"expected LCP Configure-Ack, got code {code}")

        code, _id, _data = parse_frame(
            await self._send_ppp_and_recv(
                build_configure_request(2, build_ipcp_ip_option()),
                "IPCP_CONFIGURE_REQUEST",
                "IPCP_CONFIGURE_ACK",
            )
        )
        if code != CONFIGURE_ACK:
            raise ValueError(f"expected IPCP Configure-Ack, got code {code}")

    async def _send(self, data: bytes, message_type: str) -> None:
        self._writer.write(data)
        await self._writer.drain()
        self._record(PacketDirection.OUTGOING, message_type, data)

    async def _recv_and_record(self, message_type: str) -> bytes:
        header = await self._reader.readexactly(HEADER_LEN)
        length = int.from_bytes(header[3:5], "big")
        body = await self._reader.readexactly(length - HEADER_LEN)
        full = header + body
        self._record(PacketDirection.INCOMING, message_type, full)
        return full

    async def _send_ppp_and_recv(self, data: bytes, send_type: str, recv_type: str) -> bytes:
        """发送一条 PPP 控制帧并接收响应（客户端）。"""
        await self._send_ppp(data, send_type)
        return await self._recv_ppp(recv_type)

    async def _send_ppp(self, data: bytes, message_type: str) -> None:
        self._writer.write(data)
        await self._writer.drain()
        self._record(PacketDirection.OUTGOING, message_type, data)

    async def _recv_ppp(self, message_type: str) -> bytes:
        header = await self._reader.readexactly(PPP_HEADER_LEN)
        length = int.from_bytes(header[2:4], "big")
        if length < PPP_HEADER_LEN:
            raise ValueError(f"invalid PPP control length: {length}")
        body = await self._reader.readexactly(length - PPP_HEADER_LEN)
        full = header + body
        self._record(PacketDirection.INCOMING, message_type, full)
        return full

    async def _trigger(self, event: str) -> None:
        if self._state_machine is not None:
            await self._state_machine.trigger(event)

    def _record(self, direction: PacketDirection, message_type: str, data: bytes) -> None:
        if self._on_packet is None:
            return
        peer = self._writer.get_extra_info("peername") or ("127.0.0.1", 0)
        local = self._writer.get_extra_info("sockname") or ("127.0.0.1", 0)
        src = local if direction is PacketDirection.OUTGOING else peer
        dst = peer if direction is PacketDirection.OUTGOING else local
        src_ip, src_port = src
        dst_ip, dst_port = dst
        self._on_packet(
            protocol="sstp",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
