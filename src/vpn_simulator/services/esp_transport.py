"""IPsec ESP 数据面收发编排（真实 AES-256-GCM ESP 报文往返）。"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.ipsec.esp import ESPSession

logger = structlog.get_logger(__name__)

DEFAULT_ESP_TIMEOUT = 5.0


class ESPTransport:
    """在 UDP 套接字上做 ESP 加密数据面收发。"""

    def __init__(
        self,
        socket: UdpSocket,
        session: ESPSession,
        local_spi: int,
        peer_spi: int,
    ) -> None:
        self._socket = socket
        self._session = session
        self._local_spi = local_spi
        self._peer_spi = peer_spi

    async def send_data(self, peer_addr: tuple[str, int], plaintext: bytes) -> int:
        """加密并发送一条 ESP 数据报文，返回字节数。"""
        packet = self._session.seal(self._peer_spi, plaintext)
        await self._socket.sendto(packet, peer_addr)
        logger.info("esp_sent", bytes=len(packet))
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_ESP_TIMEOUT) -> bytes:
        """接收并解密一条 ESP 数据报文，返回明文。"""
        raw, _peer = await self._socket.recvfrom(timeout)
        spi, plaintext = self._session.open(raw)
        if spi != self._local_spi:
            raise ValueError(f"ESP SPI mismatch: got {spi}, expected {self._local_spi}")
        logger.info("esp_received", bytes=len(raw))
        return plaintext
