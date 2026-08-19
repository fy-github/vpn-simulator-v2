"""Integration tests: real handshake packets reach packets table + WS stream."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection, PacketType
from vpn_simulator.plugins.protocols.wireguard.crypto import WireGuardIdentity
from vpn_simulator.plugins.protocols.wireguard.state_machine import (
    WireGuardStateMachine,
)
from vpn_simulator.services.packet_parser import packet_parser
from vpn_simulator.services.packet_recorder import record_real_packet
from vpn_simulator.services.traffic import get_traffic_service
from vpn_simulator.services.wireguard_handshake import WireGuardHandshake


@pytest.mark.asyncio
async def test_real_handshake_packets_reach_packets_table_and_ws_stream():
    packet_parser.clear_packets()
    traffic = get_traffic_service()
    traffic_before = traffic.packet_count

    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    state_machine = WireGuardStateMachine()

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(
            initiator, initiator_sock, state_machine, on_packet=record_real_packet
        )
        responder_hs = WireGuardHandshake(responder, responder_sock)

        await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder.public_bytes, 0x11111111),
            responder_hs.respond(sender_index=0x22222222),
        )

    # packets 表（packet_parser）应记录两条 WireGuard 握手报文
    wg_packets = packet_parser.get_packets(protocol="wireguard")
    assert len(wg_packets) == 2

    directions = {p.direction for p in wg_packets}
    assert directions == {PacketDirection.OUTGOING, PacketDirection.INCOMING}
    assert all(p.parsed for p in wg_packets)  # 已按字段定义解析
    assert all(p.packet_type == PacketType.CONTROL for p in wg_packets)
    assert {len(p.raw_data) for p in wg_packets} == {148, 92}

    # WS 流（TrafficService）应注入同样两条报文
    assert traffic.packet_count == traffic_before + 2
    recent_sizes = [p["size"] for p in traffic.get_recent_packets(limit=10)]
    assert 148 in recent_sizes
    assert 92 in recent_sizes
