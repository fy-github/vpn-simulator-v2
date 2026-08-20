"""Integration tests: L2TP 握手后数据面往返（真实 RFC 2661 数据消息）。"""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.l2tp.control import generate_shared_secret
from vpn_simulator.services.l2tp_data_transport import L2TPDataTransport
from vpn_simulator.services.l2tp_handshake import (
    CLIENT_SESSION_ID,
    CLIENT_TUNNEL_ID,
    SERVER_SESSION_ID,
    SERVER_TUNNEL_ID,
    L2TPHandshake,
)


@pytest.mark.asyncio
async def test_l2tp_handshake_then_data_roundtrip() -> None:
    secret = generate_shared_secret()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        client_addr = client_sock.local_address
        assert server_addr is not None and client_addr is not None

        client_hs = L2TPHandshake(secret, client_sock)
        server_hs = L2TPHandshake(secret, server_sock)
        await asyncio.gather(
            client_hs.initiate(server_addr),
            server_hs.respond(),
        )

        client_t = L2TPDataTransport(
            client_sock, CLIENT_TUNNEL_ID, CLIENT_SESSION_ID, SERVER_TUNNEL_ID, SERVER_SESSION_ID
        )
        server_t = L2TPDataTransport(
            server_sock, SERVER_TUNNEL_ID, SERVER_SESSION_ID, CLIENT_TUNNEL_ID, CLIENT_SESSION_ID
        )

        payload = b"L2TP data-plane payload"
        await client_t.send_data(server_addr, payload)
        assert await server_t.recv_data() == payload
        await server_t.send_data(client_addr, payload)
        assert await client_t.recv_data() == payload


@pytest.mark.asyncio
async def test_l2tp_wrong_session_rejected() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        # 服务端期望 session=2，但客户端错误地以 session=9 封装
        client_t = L2TPDataTransport(client_sock, 1, 1, 2, 9)
        server_t = L2TPDataTransport(server_sock, 2, 2, 1, 1)

        await client_t.send_data(server_addr, b"data")
        with pytest.raises(ValueError, match="id mismatch"):
            await server_t.recv_data()
