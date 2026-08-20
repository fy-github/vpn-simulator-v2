"""Unit tests for WireGuard data-plane transport (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.wireguard.transport import (
    MSG_TYPE_DATA,
    WireGuardTransportSession,
    build_data_packet,
    parse_data_packet,
)

KEY = b"k" * 32


class TestDataPacketCrypto:
    """P1 — data message framing + ChaCha20-Poly1305."""

    def test_build_and_parse_round_trip(self) -> None:
        raw = build_data_packet(KEY, receiver_index=2, counter=0, plaintext=b"hello")
        receiver_index, counter, plaintext = parse_data_packet(KEY, raw)
        assert receiver_index == 2
        assert counter == 0
        assert plaintext == b"hello"

    def test_header_layout(self) -> None:
        raw = build_data_packet(KEY, receiver_index=7, counter=5, plaintext=b"x")
        assert int.from_bytes(raw[0:4], "little") == MSG_TYPE_DATA
        assert int.from_bytes(raw[4:8], "little") == 7
        assert int.from_bytes(raw[8:16], "little") == 5

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
            parse_data_packet(KEY, b"\x04\x00\x00\x00")

    def test_bad_type(self) -> None:
        raw = b"\x01\x00\x00\x00" + b"\x00" * 12 + b"\x00" * 32
        with pytest.raises(ValueError, match="type"):
            parse_data_packet(KEY, raw)


class TestTransportSession:
    """P1 — session seal/open with replay protection."""

    def test_seal_increments_counter(self) -> None:
        session = WireGuardTransportSession(send_key=KEY, recv_key=KEY)
        first = session.seal(1, b"a")
        second = session.seal(1, b"b")
        assert int.from_bytes(first[8:16], "little") == 0
        assert int.from_bytes(second[8:16], "little") == 1

    def test_open_round_trip(self) -> None:
        sender = WireGuardTransportSession(send_key=KEY, recv_key=KEY)
        receiver = WireGuardTransportSession(send_key=KEY, recv_key=KEY)
        receiver_index, plaintext = receiver.open(sender.seal(2, b"payload"))
        assert receiver_index == 2
        assert plaintext == b"payload"

    def test_replay_rejected(self) -> None:
        sender = WireGuardTransportSession(send_key=KEY, recv_key=KEY)
        receiver = WireGuardTransportSession(send_key=KEY, recv_key=KEY)
        packet = sender.seal(1, b"m")
        receiver.open(packet)
        with pytest.raises(ValueError, match="replay"):
            receiver.open(packet)
