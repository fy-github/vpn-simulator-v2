"""Tests for the WireGuard scapy wire-format layer."""

from __future__ import annotations

from vpn_simulator.plugins.protocols.wireguard.crypto import (
    WireGuardIdentity,
    build_initiation,
    build_response,
    parse_initiation,
)
from vpn_simulator.plugins.protocols.wireguard.wire_format import (
    WireGuardInitiation,
    WireGuardResponse,
    parse_wireguard_message,
)


def test_parse_initiation_message():
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    raw, _ = build_initiation(initiator, responder.public_bytes, sender_index=0xAABBCCDD)

    packet = parse_wireguard_message(raw)
    assert isinstance(packet, WireGuardInitiation)
    assert packet.msg_type == 1
    assert packet.sender_index == 0xAABBCCDD
    assert len(packet.ephemeral) == 32
    assert bytes(packet) == raw  # 重新序列化一致


def test_parse_response_message():
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    init_msg, _ = build_initiation(initiator, responder.public_bytes, 1)
    parsed = parse_initiation(responder, init_msg)
    resp_raw, _ = build_response(responder, parsed, sender_index=2, receiver_index=1)

    packet = parse_wireguard_message(resp_raw)
    assert isinstance(packet, WireGuardResponse)
    assert packet.msg_type == 2
    assert packet.sender_index == 2
    assert packet.receiver_index == 1
    assert bytes(packet) == resp_raw
