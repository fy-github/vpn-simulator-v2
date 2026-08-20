"""Unit tests for VXLAN data-plane encapsulation (RFC 7348) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.vxlan.encap import (
    build_vxlan_packet,
    parse_vxlan_packet,
)


class TestVXLANEncap:
    def test_round_trip(self) -> None:
        payload = b"inner ethernet frame"
        raw = build_vxlan_packet(100, payload)
        vni, plaintext = parse_vxlan_packet(raw)
        assert (vni, plaintext) == (100, payload)

    def test_i_flag_missing(self) -> None:
        raw = bytearray(build_vxlan_packet(100, b"data"))
        raw[0] = 0x00  # 清除 I 位
        with pytest.raises(ValueError, match="I flag"):
            parse_vxlan_packet(bytes(raw))

    def test_short_packet_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_vxlan_packet(b"\x08\x00\x00\x00")

    def test_vni_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="VNI out of range"):
            build_vxlan_packet(0xFFFFFF + 1, b"data")
