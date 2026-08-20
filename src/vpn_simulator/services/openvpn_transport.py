"""OpenVPN 数据面真实往返编排：packetio + 数据信道会话。

在一次 UDP 套接字上发送/接收真实加密的 OpenVPN 数据报文：

- `send_data()`：用 `OpenVPNDataSession.seal()` 加密明文并发送。
- `recv_data()`：接收、解密、做重放防护，并校验 `peer_id` 匹配本端 session_id。

与 `services/openvpn_handshake.py`（控制信道 Hard Reset）配合，构成 OpenVPN
的真实报文闭环：控制信道建立 → 派生数据密钥 → 数据面 AES-256-GCM 加解密往返。
"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.openvpn.data_channel import OpenVPNDataSession

logger = structlog.get_logger(__name__)

DEFAULT_DATA_TIMEOUT = 5.0


class OpenVPNTransport:
    """在一个 UDP 套接字上收发真实加密的 OpenVPN 数据报文。"""

    def __init__(
        self,
        socket: UdpSocket,
        session: OpenVPNDataSession,
        local_id: int,
        peer_id: int,
    ) -> None:
        self._socket = socket
        self._session = session
        self._local_id = local_id
        self._peer_id = peer_id

    async def send_data(self, peer_addr: tuple[str, int], plaintext: bytes) -> int:
        """加密并发送一段明文，返回发送的报文字节数。"""
        packet = self._session.seal(self._peer_id, plaintext)
        await self._socket.sendto(packet, peer_addr)
        logger.info("openvpn_data_sent", bytes=len(packet), to=peer_addr)
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_DATA_TIMEOUT) -> bytes:
        """接收并解密一段数据报文，返回明文。

        Raises:
            ValueError: 解密/重放校验失败，或 `peer_id` 与本端 session_id 不符。
        """
        raw, peer_addr = await self._socket.recvfrom(timeout=timeout)
        peer_id, plaintext = self._session.open(raw)
        if peer_id != self._local_id:
            raise ValueError(f"unexpected peer_id: {peer_id} != {self._local_id}")
        logger.info("openvpn_data_received", bytes=len(raw), from_=peer_addr)
        return plaintext
