"""Unit tests for IPsec ESP data-plane (AES-256-GCM) framing (P1/P3)."""

from __future__ import annotations

import os

import pytest
from vpn_simulator.plugins.protocols.ipsec.esp import (
    ESP_HEADER_LEN,
    ESPSession,
    build_esp_packet,
    parse_esp_packet,
)

KEY = os.urandom(32)


class TestESPPacket:
    def test_round_trip(self) -> None:
        payload = b"hello esp"
        raw = build_esp_packet(0x1001, 0, KEY, payload)
        assert len(raw) == ESP_HEADER_LEN + len(payload) + 16  # + GCM tag
        spi, seq, plaintext = parse_esp_packet(KEY, raw)
        assert (spi, seq, plaintext) == (0x1001, 0, payload)

    def test_wrong_key_rejected(self) -> None:
        raw = build_esp_packet(0x1001, 0, KEY, b"secret")
        with pytest.raises(ValueError, match="authentication failed"):
            parse_esp_packet(os.urandom(32), raw)

    def test_tampered_ciphertext_rejected(self) -> None:
        raw = bytearray(build_esp_packet(0x1001, 0, KEY, b"secret"))
        raw[-1] ^= 0x01
        with pytest.raises(ValueError, match="authentication failed"):
            parse_esp_packet(KEY, bytes(raw))

    def test_short_packet_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_esp_packet(KEY, b"\x00" * 4)


class TestESPSession:
    def test_seal_open(self) -> None:
        session = ESPSession(KEY)
        raw = session.seal(0x1002, b"payload-1")
        spi, plaintext = session.open(raw)
        assert (spi, plaintext) == (0x1002, b"payload-1")
        # seq 递增
        raw2 = session.seal(0x1002, b"payload-2")
        assert int.from_bytes(raw2[4:8], "big") == 1

    def test_replay_rejected(self) -> None:
        session = ESPSession(KEY)
        raw = session.seal(0x1002, b"payload")
        session.open(raw)
        with pytest.raises(ValueError, match="replay"):
            session.open(raw)
