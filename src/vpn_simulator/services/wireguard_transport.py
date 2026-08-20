"""WireGuard 数据面真实往返编排：packetio + transport 会话。

在一次 UDP 套接字上发送/接收真实加密的 WireGuard 数据报文：

- `send_data()`：用 `WireGuardTransportSession.seal()` 加密明文并发送。
- `recv_data()`：接收、解密、做重放防护，并校验 `receiver_index` 匹配本端索引。

与 `services/wireguard_handshake.py`（控制面握手）配合，构成 WireGuard 的
完整真实报文闭环：握手派生密钥 → 数据面加解密往返。
"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.wireguard.transport import WireGuardTransportSession

logger = structlog.get_logger(__name__)

DEFAULT_DATA_TIMEOUT = 5.0


class WireGuardTransport:
    """在一个 UDP 套接字上收发真实加密的 WireGuard 数据报文。"""

    def __init__(
        self,
        socket: UdpSocket,
        session: WireGuardTransportSession,
        local_index: int,
        peer_index: int,
    ) -> None:
        self._socket = socket
        self._session = session
        self._local_index = local_index
        self._peer_index = peer_index

    async def send_data(self, peer_addr: tuple[str, int], plaintext: bytes) -> int:
        """加密并发送一段明文，返回发送的报文字节数。"""
        packet = self._session.seal(self._peer_index, plaintext)
        await self._socket.sendto(packet, peer_addr)
        logger.info("wireguard_data_sent", bytes=len(packet), to=peer_addr)
        return len(packet)

    async def recv_data(self, timeout: float = DEFAULT_DATA_TIMEOUT) -> bytes:
        """接收并解密一段数据报文，返回明文。

        Raises:
            ValueError: 解密/重放校验失败，或 `receiver_index` 与本端索引不符。
        """
        raw, peer_addr = await self._socket.recvfrom(timeout=timeout)
        receiver_index, plaintext = self._session.open(raw)
        if receiver_index != self._local_index:
            raise ValueError(f"unexpected receiver_index: {receiver_index} != {self._local_index}")
        logger.info("wireguard_data_received", bytes=len(raw), from_=peer_addr)
        return plaintext
