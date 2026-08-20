"""Integration tests: PPTP control handshake over TCP end-to-end."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.plugins.protocols.pptp.state_machine import PPTPStateMachine
from vpn_simulator.services.pptp_handshake import PPTPHandshake


@pytest.mark.asyncio
async def test_pptp_handshake_end_to_end() -> None:
    queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Queue()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await queue.put((reader, writer))

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    client_writer: asyncio.StreamWriter | None = None
    server_writer: asyncio.StreamWriter | None = None
    try:
        port = server.sockets[0].getsockname()[1]
        client_reader, client_writer = await asyncio.open_connection("127.0.0.1", port)
        server_reader, server_writer = await queue.get()

        server_sm = PPTPStateMachine()
        client_hs = PPTPHandshake(client_reader, client_writer)
        server_hs = PPTPHandshake(server_reader, server_writer, state_machine=server_sm)

        client_ids, server_ids = await asyncio.gather(
            client_hs.initiate(),
            server_hs.respond(),
        )

        assert client_ids == (1, 2)
        assert server_ids == (1, 2)
        assert server_sm.current_state == "CONNECTED"
    finally:
        if client_writer is not None:
            client_writer.close()
        if server_writer is not None:
            server_writer.close()
        server.close()
        await server.wait_closed()
