"""Integration tests: SSTP 真实 TLS 握手 + CALL_CONNECT 端到端。"""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.plugins.protocols.sstp.state_machine import SSTPStateMachine
from vpn_simulator.plugins.protocols.sstp.tls import create_tls_contexts
from vpn_simulator.services.sstp_handshake import SSTPHandshake


@pytest.mark.asyncio
async def test_sstp_tls_handshake_end_to_end() -> None:
    queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Queue()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await queue.put((reader, writer))

    contexts = create_tls_contexts()
    server = await asyncio.start_server(handle_client, "127.0.0.1", 0, ssl=contexts.server)
    client_writer: asyncio.StreamWriter | None = None
    server_writer: asyncio.StreamWriter | None = None
    try:
        port = server.sockets[0].getsockname()[1]
        client_reader, client_writer = await asyncio.open_connection(
            "127.0.0.1", port, ssl=contexts.client
        )
        server_reader, server_writer = await queue.get()

        server_sm = SSTPStateMachine()
        client_hs = SSTPHandshake(client_reader, client_writer)
        server_hs = SSTPHandshake(server_reader, server_writer, state_machine=server_sm)

        await asyncio.gather(
            client_hs.initiate(),
            server_hs.respond(),
        )

        assert server_sm.current_state == "CONNECTED"
    finally:
        if client_writer is not None:
            client_writer.close()
        if server_writer is not None:
            server_writer.close()
        server.close()
        await server.wait_closed()
