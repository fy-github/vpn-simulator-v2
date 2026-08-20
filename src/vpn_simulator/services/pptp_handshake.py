"""PPTP 真实握手编排：asyncio TCP 流 + control + 状态机。

PPTP 控制信道走 TCP 1723（明文）。本模块在一条 TCP 连接上执行控制面握手：

- 客户端 `initiate()`：SCCRQ → SCCRP → OCRQ → OCRP，返回 ``(client_call_id, server_call_id)``。
- 服务端 `respond()`：SCCRQ → SCCRP → OCRQ → OCRP，驱动 `PPTPStateMachine`
  （服务器视角）INITIAL → CONNECTED，返回 ``(client_call_id, server_call_id)``。

本模块只做控制面握手，不实现 MS-CHAPv2 认证与 PPP LCP/IPCP 协商。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import structlog

from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.pptp.control import (
    build_ocrp,
    build_ocrq,
    build_sccrp,
    build_sccrq,
    parse_ocrp,
    parse_ocrq,
    parse_sccrp,
    parse_sccrq,
)

logger = structlog.get_logger(__name__)

CLIENT_CALL_ID = 1
SERVER_CALL_ID = 2


class PPTPHandshake:
    """在一条 TCP 连接上执行一次真实 PPTP 控制握手。"""

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

    async def initiate(self) -> tuple[int, int]:
        """客户端执行握手，返回 ``(client_call_id, server_call_id)``。"""
        await self._send(build_sccrq(), "SCCRQ")
        raw = await self._recv_and_record("SCCRP")
        parse_sccrp(raw)
        await self._send(build_ocrq(CLIENT_CALL_ID, call_serial=1), "OCRQ")
        raw = await self._recv_and_record("OCRP")
        _, server_call_id, peer_call_id = parse_ocrp(raw)
        logger.info("pptp_call_connected", server_call_id=server_call_id, peer_call_id=peer_call_id)
        return CLIENT_CALL_ID, server_call_id

    async def respond(self) -> tuple[int, int]:
        """服务端执行握手，返回 ``(client_call_id, server_call_id)``。"""
        await self._trigger("START")

        raw = await self._recv_and_record("SCCRQ")
        parse_sccrq(raw)
        await self._trigger("RECEIVE_SCCRQ")

        await self._send(build_sccrp(), "SCCRP")
        await self._trigger("SCCRP_SENT_OK")

        raw = await self._recv_and_record("OCRQ")
        _, client_call_id, _call_serial = parse_ocrq(raw)
        await self._trigger("RECEIVE_OCRQ")

        await self._send(build_ocrp(SERVER_CALL_ID, client_call_id), "OCRP")
        await self._trigger("GRE_READY")
        await self._trigger("START_LCP")
        await self._trigger("LCP_COMPLETE")
        await self._trigger("AUTH_SUCCESS")
        await self._trigger("IPCP_COMPLETE")
        return client_call_id, SERVER_CALL_ID

    async def _send(self, data: bytes, message_type: str) -> None:
        self._writer.write(data)
        await self._writer.drain()
        logger.info("pptp_sent", message_type=message_type, bytes=len(data))
        self._record(PacketDirection.OUTGOING, message_type, data)

    async def _recv_and_record(self, message_type: str) -> bytes:
        length = int.from_bytes(await self._reader.readexactly(2), "big")
        data = await self._reader.readexactly(length - 2)
        full = length.to_bytes(2, "big") + data
        logger.info("pptp_received", message_type=message_type, bytes=length)
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
            protocol="pptp",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
