"""Integration tests: OpenVPN control handshake → data-plane encrypted round-trip."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.openvpn.control_channel import generate_tls_auth_key
from vpn_simulator.plugins.protocols.openvpn.data_channel import (
    OpenVPNDataSession,
    build_data_packet,
    derive_data_key,
)
from vpn_simulator.services.openvpn_handshake import OpenVPNHandshake
from vpn_simulator.services.openvpn_transport import OpenVPNTransport


@pytest.mark.asyncio
async def test_handshake_then_data_roundtrip() -> None:
    key = generate_tls_auth_key()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        client_hs = OpenVPNHandshake(key, client_sock)
        server_hs = OpenVPNHandshake(key, server_sock)
        client_result, _ = await asyncio.gather(
            client_hs.initiate(server_addr),
            server_hs.respond(),
        )
        client_session_id, server_session_id = client_result

        data_key = derive_data_key(key, client_session_id, server_session_id)
        client_transport = OpenVPNTransport(
            client_sock,
            OpenVPNDataSession(data_key=data_key),
            local_id=client_session_id,
            peer_id=server_session_id,
        )
        server_transport = OpenVPNTransport(
            server_sock,
            OpenVPNDataSession(data_key=data_key),
            local_id=server_session_id,
            peer_id=client_session_id,
        )

        payload = b"hello openvpn data plane"
        await client_transport.send_data(server_addr, payload)
        assert await server_transport.recv_data() == payload

        client_addr = client_sock.local_address
        assert client_addr is not None
        await server_transport.send_data(client_addr, b"ack")
        assert await client_transport.recv_data() == b"ack"


@pytest.mark.asyncio
async def test_data_replay_rejected_across_sockets() -> None:
    key = generate_tls_auth_key()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        client_hs = OpenVPNHandshake(key, client_sock)
        server_hs = OpenVPNHandshake(key, server_sock)
        client_result, _ = await asyncio.gather(
            client_hs.initiate(server_addr),
            server_hs.respond(),
        )
        client_session_id, server_session_id = client_result

        data_key = derive_data_key(key, client_session_id, server_session_id)
        client_transport = OpenVPNTransport(
            client_sock,
            OpenVPNDataSession(data_key=data_key),
            local_id=client_session_id,
            peer_id=server_session_id,
        )
        server_transport = OpenVPNTransport(
            server_sock,
            OpenVPNDataSession(data_key=data_key),
            local_id=server_session_id,
            peer_id=client_session_id,
        )

        await client_transport.send_data(server_addr, b"dup")
        assert await server_transport.recv_data() == b"dup"

        # 重放同一 packet_id=0 的密文应被服务端拒绝。
        replay = build_data_packet(
            data_key, peer_id=server_session_id, packet_id=0, plaintext=b"dup"
        )
        await client_sock.sendto(replay, server_addr)
        with pytest.raises(ValueError, match="replay"):
            await server_transport.recv_data()
