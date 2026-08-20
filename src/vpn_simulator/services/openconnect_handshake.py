"""OpenConnect 真实握手编排：TLS 流 + CSTP CONNECT + 状态机。

协议栈：TCP(443) → TLS → CSTP（HTTP CONNECT + X-CSTP-*）→ PPP。本模块在已建立 TLS
的 asyncio 流上执行 CSTP 隧道协商：

- 客户端 `initiate()`：发 CSTP CONNECT 请求 → 校验 200 响应。
- 服务端 `respond()`：校验 CONNECT 请求 → 发 200 响应，驱动 `OpenConnectStateMachine`
  INITIAL → CONNECTED（DTLS 走 DTLS_SKIPPED，PPP LCP/IPCP/MSCHAPv2 不实现，明示）。

TLS 握手在连接建立阶段由 `ssl` 完成（复用 `sstp/tls.py` 的自签名证书助手）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import structlog

from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.openconnect.cstp import (
    HEADER_END,
    build_connect_request,
    build_connect_response,
    parse_connect_request,
    parse_connect_response,
)

logger = structlog.get_logger(__name__)


class OpenConnectHandshake:
    """在已建 TLS 的 asyncio 流上执行一次真实 OpenConnect CSTP 握手。"""

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
        """客户端执行 CSTP CONNECT 握手。"""
        await self._send(build_connect_request(), "CSTP_CONNECT_REQUEST")
        raw = await self._recv_headers_and_record("CSTP_CONNECT_RESPONSE")
        parse_connect_response(raw)
        logger.info("openconnect_connected")

    async def respond(self) -> None:
        """服务端执行 CSTP CONNECT 握手，驱动状态机到 CONNECTED。"""
        await self._trigger("TCP_CONNECTED")
        await self._trigger("TLS_HANDSHAKE_COMPLETE")

        raw = await self._recv_headers_and_record("CSTP_CONNECT_REQUEST")
        parse_connect_request(raw)

        await self._send(build_connect_response(), "CSTP_CONNECT_RESPONSE")
        await self._trigger("CSTP_NEGOTIATION_COMPLETE")
        # DTLS 数据通道与 PPP LCP/IPCP/MSCHAPv2 不实现，教学简化驱动状态机
        await self._trigger("DTLS_SKIPPED")
        await self._trigger("LCP_NEGOTIATION_COMPLETE")
        await self._trigger("AUTHENTICATION_SUCCESS")
        await self._trigger("IPCP_NEGOTIATION_COMPLETE")
        logger.info("openconnect_tunnel_established")

    async def _send(self, data: bytes, message_type: str) -> None:
        self._writer.write(data)
        await self._writer.drain()
        self._record(PacketDirection.OUTGOING, message_type, data)

    async def _recv_headers_and_record(self, message_type: str) -> bytes:
        raw = await self._reader.readuntil(HEADER_END)
        self._record(PacketDirection.INCOMING, message_type, raw)
        return raw

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
            protocol="openconnect",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
