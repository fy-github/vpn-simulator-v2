"""Unit tests for OpenVPN control-channel framing + --tls-auth HMAC (P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.openvpn.control_channel import (
    P_CONTROL_HARD_RESET_CLIENT_V2,
    P_CONTROL_HARD_RESET_SERVER_V2,
    ControlPacket,
    build_control_packet,
    generate_session_id,
    generate_tls_auth_key,
    parse_control_packet,
)


class TestControlChannel:
    """P3 — OpenVPN control channel framing."""

    def test_round_trip(self) -> None:
        key = generate_tls_auth_key()
        session_id = generate_session_id()
        payload = b"\x16\x03\x03\x00\x05\x00\x00\x00"  # minimal TLS record-ish
        raw = build_control_packet(P_CONTROL_HARD_RESET_CLIENT_V2, session_id, 0, payload, key)
        parsed = parse_control_packet(raw, key)
        assert parsed.opcode == P_CONTROL_HARD_RESET_CLIENT_V2
        assert parsed.session_id == session_id
        assert parsed.packet_id == 0
        assert parsed.payload == payload

    def test_packet_length(self) -> None:
        key = generate_tls_auth_key()
        raw = build_control_packet(P_CONTROL_HARD_RESET_CLIENT_V2, 1, 0, b"", key)
        assert len(raw) == 1 + 8 + 32 + 4

    def test_tamper_detection(self) -> None:
        key = generate_tls_auth_key()
        raw = bytearray(build_control_packet(P_CONTROL_HARD_RESET_CLIENT_V2, 7, 0, b"hi", key))
        raw[-1] ^= 0xFF  # flip the last payload byte
        with pytest.raises(ValueError):
            parse_control_packet(bytes(raw), key)

    def test_wrong_key(self) -> None:
        raw = build_control_packet(P_CONTROL_HARD_RESET_CLIENT_V2, 7, 0, b"hi", b"a" * 32)
        with pytest.raises(ValueError):
            parse_control_packet(raw, b"b" * 32)

    def test_short_packet(self) -> None:
        with pytest.raises(ValueError):
            parse_control_packet(b"\x07\x00\x00", b"a" * 32)

    def test_opcode_name(self) -> None:
        packet = ControlPacket(
            opcode=P_CONTROL_HARD_RESET_SERVER_V2, session_id=0, packet_id=0, payload=b""
        )
        assert packet.opcode_name == "P_CONTROL_HARD_RESET_SERVER_V2"
