"""Integration tests: PPTP 控制握手后 GRE 数据面往返（真实 RFC 2784）。"""

from __future__ import annotations

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.services.gre_transport import GRETransport


@pytest.mark.asyncio
async def test_gre_roundtrip() -> None:
    client_key, server_key = 1, 2

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        client_addr = client_sock.local_address
        assert server_addr is not None and client_addr is not None

        client_t = GRETransport(client_sock, client_key, server_key)
        server_t = GRETransport(server_sock, server_key, client_key)

        payload = b"GRE data-plane payload"
        await client_t.send_data(server_addr, payload)
        assert await server_t.recv_data() == payload
        await server_t.send_data(client_addr, payload)
        assert await client_t.recv_data() == payload


@pytest.mark.asyncio
async def test_gre_wrong_key_rejected() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        # 服务端期望 key=2，但客户端错误地以 key=3 封装
        client_t = GRETransport(client_sock, local_key=1, peer_key=3)
        server_t = GRETransport(server_sock, local_key=2, peer_key=1)

        await client_t.send_data(server_addr, b"data")
        with pytest.raises(ValueError, match="key mismatch"):
            await server_t.recv_data()
