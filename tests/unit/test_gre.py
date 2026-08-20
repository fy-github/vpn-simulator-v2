"""Unit tests for PPTP GRE data-plane framing (RFC 2784) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.pptp.gre import (
    build_gre_packet,
    parse_gre_packet,
)


class TestGREPacket:
    def test_round_trip(self) -> None:
        payload = b"hello gre"
        raw = build_gre_packet(1, payload)
        key, plaintext = parse_gre_packet(raw)
        assert (key, plaintext) == (1, payload)

    def test_key_flag_missing(self) -> None:
        raw = build_gre_packet(1, b"data")
        raw = b"\x00\x00" + raw[2:]  # 清除 K 位
        with pytest.raises(ValueError, match="key flag"):
            parse_gre_packet(raw)

    def test_wrong_protocol(self) -> None:
        raw = bytearray(build_gre_packet(1, b"data"))
        raw[2:4] = (0x0800).to_bytes(2, "big")  # IPv4 而非 PPP
        with pytest.raises(ValueError, match="protocol"):
            parse_gre_packet(bytes(raw))

    def test_short_packet_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_gre_packet(b"\x00" * 4)
