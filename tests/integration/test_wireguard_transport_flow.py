"""Integration tests: WireGuard handshake → data-plane encrypted round-trip."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.wireguard.crypto import WireGuardIdentity
from vpn_simulator.plugins.protocols.wireguard.transport import (
    WireGuardTransportSession,
    build_data_packet,
)
from vpn_simulator.services.wireguard_handshake import WireGuardHandshake
from vpn_simulator.services.wireguard_transport import WireGuardTransport


@pytest.mark.asyncio
async def test_handshake_then_data_roundtrip() -> None:
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(initiator, initiator_sock)
        responder_hs = WireGuardHandshake(responder, responder_sock)
        initiator_keys, responder_keys = await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder.public_bytes, 1),
            responder_hs.respond(sender_index=2),
        )

        initiator_transport = WireGuardTransport(
            initiator_sock,
            WireGuardTransportSession(send_key=initiator_keys[0], recv_key=initiator_keys[1]),
            local_index=1,
            peer_index=2,
        )
        responder_transport = WireGuardTransport(
            responder_sock,
            WireGuardTransportSession(send_key=responder_keys[1], recv_key=responder_keys[0]),
            local_index=2,
            peer_index=1,
        )

        payload = b"hello wireguard data plane"
        await initiator_transport.send_data(responder_addr, payload)
        assert await responder_transport.recv_data() == payload

        initiator_addr = initiator_sock.local_address
        assert initiator_addr is not None
        await responder_transport.send_data(initiator_addr, b"ack")
        assert await initiator_transport.recv_data() == b"ack"


@pytest.mark.asyncio
async def test_data_replay_rejected_across_sockets() -> None:
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(initiator, initiator_sock)
        responder_hs = WireGuardHandshake(responder, responder_sock)
        initiator_keys, responder_keys = await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder.public_bytes, 1),
            responder_hs.respond(sender_index=2),
        )

        initiator_transport = WireGuardTransport(
            initiator_sock,
            WireGuardTransportSession(send_key=initiator_keys[0], recv_key=initiator_keys[1]),
            local_index=1,
            peer_index=2,
        )
        responder_transport = WireGuardTransport(
            responder_sock,
            WireGuardTransportSession(send_key=responder_keys[1], recv_key=responder_keys[0]),
            local_index=2,
            peer_index=1,
        )

        await initiator_transport.send_data(responder_addr, b"dup")
        assert await responder_transport.recv_data() == b"dup"

        # 重放同一 counter=0 的密文应被响应方拒绝。
        replay = build_data_packet(initiator_keys[0], receiver_index=2, counter=0, plaintext=b"dup")
        await initiator_sock.sendto(replay, responder_addr)
        with pytest.raises(ValueError, match="replay"):
            await responder_transport.recv_data()
