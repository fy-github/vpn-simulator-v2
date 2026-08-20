"""L2TP 数据面收发编排（真实 L2TP 数据报文往返）。"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.l2tp.data_channel import build_l2tp_data, parse_l2tp_data

logger = structlog.get_logger(__name__)

DEFAULT_L2TP_TIMEOUT = 5.0


class L2TPDataTransport:
    """在 UDP 套接字上做 L2TP 数据面收发。"""

    def __init__(
        self,
        socket: UdpSocket,
        local_tunnel: int,
        local_session: int,
        peer_tunnel: int,
        peer_session: int,
    ) -> None:
        self._socket = socket
        self._local_tunnel = local_tunnel
        self._local_session = local_session
        self._peer_tunnel = peer_tunnel
        self._peer_session = peer_session

    async def send_data(self, peer_addr: tuple[str, int], payload: bytes) -> int:
        """封装并发送一条 L2TP 数据报文，返回字节数。"""
        packet = build_l2tp_data(self._peer_tunnel, self._peer_session, payload)
        await self._socket.sendto(packet, peer_addr)
        logger.info("l2tp_data_sent", bytes=len(packet))
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_L2TP_TIMEOUT) -> bytes:
        """接收并解封一条 L2TP 数据报文，返回 payload。"""
        raw, _peer = await self._socket.recvfrom(timeout)
        tunnel_id, session_id, payload = parse_l2tp_data(raw)
        if tunnel_id != self._local_tunnel or session_id != self._local_session:
            raise ValueError(
                f"L2TP id mismatch: got ({tunnel_id},{session_id}), "
                f"expected ({self._local_tunnel},{self._local_session})"
            )
        logger.info("l2tp_data_received", bytes=len(raw))
        return payload
