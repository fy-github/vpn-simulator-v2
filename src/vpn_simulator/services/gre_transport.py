"""PPTP GRE 数据面收发编排（真实 GRE 报文往返）。"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.pptp.gre import build_gre_packet, parse_gre_packet

logger = structlog.get_logger(__name__)

DEFAULT_GRE_TIMEOUT = 5.0


class GRETransport:
    """在 UDP 套接字上做 GRE 数据面收发。"""

    def __init__(
        self,
        socket: UdpSocket,
        local_key: int,
        peer_key: int,
    ) -> None:
        self._socket = socket
        self._local_key = local_key
        self._peer_key = peer_key

    async def send_data(self, peer_addr: tuple[str, int], payload: bytes) -> int:
        """封装并发送一条 GRE 数据报文，返回字节数。"""
        packet = build_gre_packet(self._peer_key, payload)
        await self._socket.sendto(packet, peer_addr)
        logger.info("gre_sent", bytes=len(packet))
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_GRE_TIMEOUT) -> bytes:
        """接收并解封一条 GRE 数据报文，返回 payload。"""
        raw, _peer = await self._socket.recvfrom(timeout)
        key, payload = parse_gre_packet(raw)
        if key != self._local_key:
            raise ValueError(f"GRE key mismatch: got {key}, expected {self._local_key}")
        logger.info("gre_received", bytes=len(raw))
        return payload
