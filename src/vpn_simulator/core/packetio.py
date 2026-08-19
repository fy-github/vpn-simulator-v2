"""packetio — 真实 UDP 报文收发层。

基于 asyncio 的 UDP datagram 端点提供轻量、可复用的报文收发能力，
供协议握手（如 WireGuard）、故障注入、PCAP 回放等功能使用。

设计要点：
- 异步、非阻塞：`recvfrom` 基于 `asyncio.Queue`，支持超时。
- 只负责 UDP 字节流收发，不做协议解析（解析交给各协议插件）。
"""

from __future__ import annotations

import asyncio
from typing import cast


class _DatagramProtocol(asyncio.DatagramProtocol):
    """接收 datagram 并放入队列。"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue()
        self._transport: asyncio.DatagramTransport | None = None
        self._error: Exception | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._queue.put_nowait((data, addr))

    def error_received(self, exc: Exception) -> None:
        self._error = exc


class UdpSocket:
    """异步 UDP datagram 套接字。

    Example:
        >>> async with UdpSocket("127.0.0.1", 0) as sock:
        ...     await sock.sendto(b"ping", ("127.0.0.1", 9000))
        ...     data, addr = await sock.recvfrom(timeout=5.0)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._transport: asyncio.DatagramTransport | None = None
        self._protocol: _DatagramProtocol | None = None

    async def __aenter__(self) -> UdpSocket:
        await self.bind()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def bind(self) -> None:
        """绑定本地地址并开始监听。"""
        loop = asyncio.get_running_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            _DatagramProtocol, local_addr=(self._host, self._port)
        )

    @property
    def local_address(self) -> tuple[str, int] | None:
        """返回 (host, port) 的本地绑定地址。"""
        if self._transport is None:
            return None
        sockname = self._transport.get_extra_info("sockname")
        return (str(sockname[0]), int(sockname[1])) if sockname else None

    async def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
        """发送 datagram 到指定地址。"""
        if self._transport is None:
            raise RuntimeError("UdpSocket not bound; call bind() first")
        self._transport.sendto(data, addr)

    async def recvfrom(self, timeout: float | None = None) -> tuple[bytes, tuple[str, int]]:
        """接收一个 datagram，返回 (data, addr)。

        Args:
            timeout: 超时秒数；None 表示无限等待。超时抛 TimeoutError。

        Raises:
            TimeoutError: 等待超时。
            RuntimeError: 套接字未绑定。
        """
        if self._protocol is None:
            raise RuntimeError("UdpSocket not bound; call bind() first")
        if timeout is None:
            return await self._protocol._queue.get()
        return await asyncio.wait_for(self._protocol._queue.get(), timeout)

    async def close(self) -> None:
        """关闭套接字。"""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None
