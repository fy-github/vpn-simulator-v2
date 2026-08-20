"""VXLAN 数据面收发编排（真实 VXLAN 封装/解封装往返）。"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.vxlan.encap import build_vxlan_packet, parse_vxlan_packet

logger = structlog.get_logger(__name__)

DEFAULT_VXLAN_TIMEOUT = 5.0


class VXLANTransport:
    """在 UDP 套接字上做 VXLAN 封装/解封装收发。"""

    def __init__(
        self,
        socket: UdpSocket,
        local_vni: int,
        peer_vni: int,
    ) -> None:
        self._socket = socket
        self._local_vni = local_vni
        self._peer_vni = peer_vni

    async def send_data(self, peer_addr: tuple[str, int], payload: bytes) -> int:
        """封装并发送一条 VXLAN 报文，返回字节数。"""
        packet = build_vxlan_packet(self._peer_vni, payload)
        await self._socket.sendto(packet, peer_addr)
        logger.info("vxlan_sent", bytes=len(packet))
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_VXLAN_TIMEOUT) -> bytes:
        """接收并解封一条 VXLAN 报文，返回 payload。"""
        raw, _peer = await self._socket.recvfrom(timeout)
        vni, payload = parse_vxlan_packet(raw)
        if vni != self._local_vni:
            raise ValueError(f"VXLAN VNI mismatch: got {vni}, expected {self._local_vni}")
        logger.info("vxlan_received", bytes=len(raw))
        return payload
