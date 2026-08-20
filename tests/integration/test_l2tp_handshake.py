"""Integration tests: L2TP control handshake + tunnel auth end-to-end."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.l2tp.control import generate_shared_secret
from vpn_simulator.plugins.protocols.l2tp.state_machine import L2TPStateMachine
from vpn_simulator.services.l2tp_handshake import L2TPHandshake


@pytest.mark.asyncio
async def test_l2tp_handshake_end_to_end() -> None:
    secret = generate_shared_secret()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        server_sm = L2TPStateMachine()
        client_hs = L2TPHandshake(secret, client_sock)
        server_hs = L2TPHandshake(secret, server_sock, state_machine=server_sm)

        client_ids, server_ids = await asyncio.gather(
            client_hs.initiate(server_addr),
            server_hs.respond(),
        )

        assert client_ids == (1, 2)
        assert server_ids == (1, 2)
        assert server_sm.current_state == "CONNECTED"


@pytest.mark.asyncio
async def test_l2tp_rejects_wrong_secret() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        client_hs = L2TPHandshake(generate_shared_secret(), client_sock)
        server_hs = L2TPHandshake(generate_shared_secret(), server_sock)

        results = await asyncio.gather(
            client_hs.initiate(server_addr, timeout=1.0),
            server_hs.respond(timeout=1.0),
            return_exceptions=True,
        )
        assert any(isinstance(r, ValueError) for r in results)
