"""Unit tests for OpenVPN data channel framing + AES-256-GCM (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.openvpn.control_channel import P_DATA_V2
from vpn_simulator.plugins.protocols.openvpn.data_channel import (
    OpenVPNDataSession,
    build_data_packet,
    derive_data_key,
    parse_data_packet,
)

KEY = b"d" * 32


class TestDataChannelCrypto:
    """P1 — data message framing + AES-256-GCM."""

    def test_build_and_parse_round_trip(self) -> None:
        raw = build_data_packet(KEY, peer_id=7, packet_id=0, plaintext=b"hello")
        peer_id, packet_id, plaintext = parse_data_packet(KEY, raw)
        assert peer_id == 7
        assert packet_id == 0
        assert plaintext == b"hello"

    def test_header_layout(self) -> None:
        raw = build_data_packet(KEY, peer_id=7, packet_id=5, plaintext=b"x")
        assert raw[0] == P_DATA_V2
        assert int.from_bytes(raw[1:9], "big") == 7
        assert int.from_bytes(raw[9:13], "big") == 5

    def test_tamper_detected(self) -> None:
        raw = bytearray(build_data_packet(KEY, 1, 0, b"secret"))
        raw[-1] ^= 0xFF
        with pytest.raises(ValueError):
            parse_data_packet(KEY, bytes(raw))

    def test_wrong_key_fails(self) -> None:
        raw = build_data_packet(b"a" * 32, 1, 0, b"secret")
        with pytest.raises(ValueError):
            parse_data_packet(b"b" * 32, raw)

    def test_short_packet(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_data_packet(KEY, b"\x09\x00\x00\x00")

    def test_bad_opcode(self) -> None:
        raw = b"\x07" + b"\x00" * 12 + b"\x00" * 32
        with pytest.raises(ValueError, match="opcode"):
            parse_data_packet(KEY, raw)

    def test_derive_data_key(self) -> None:
        k1 = derive_data_key(b"k" * 32, client_session_id=1, server_session_id=2)
        k2 = derive_data_key(b"k" * 32, client_session_id=1, server_session_id=3)
        assert len(k1) == 32
        assert k1 == derive_data_key(b"k" * 32, client_session_id=1, server_session_id=2)
        assert k1 != k2


class TestDataSession:
    """P1 — session seal/open with replay protection."""

    def test_seal_increments_packet_id(self) -> None:
        session = OpenVPNDataSession(data_key=KEY)
        first = session.seal(1, b"a")
        second = session.seal(1, b"b")
        assert int.from_bytes(first[9:13], "big") == 0
        assert int.from_bytes(second[9:13], "big") == 1

    def test_open_round_trip(self) -> None:
        sender = OpenVPNDataSession(data_key=KEY)
        receiver = OpenVPNDataSession(data_key=KEY)
        peer_id, plaintext = receiver.open(sender.seal(2, b"payload"))
        assert peer_id == 2
        assert plaintext == b"payload"

    def test_replay_rejected(self) -> None:
        sender = OpenVPNDataSession(data_key=KEY)
        receiver = OpenVPNDataSession(data_key=KEY)
        packet = sender.seal(1, b"m")
        receiver.open(packet)
        with pytest.raises(ValueError, match="replay"):
            receiver.open(packet)
