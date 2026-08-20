"""Unit tests for L2TP data-plane framing (RFC 2661) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.l2tp.data_channel import (
    build_l2tp_data,
    parse_l2tp_data,
)


class TestL2TPData:
    def test_round_trip(self) -> None:
        payload = b"hello l2tp data"
        raw = build_l2tp_data(2, 2, payload)
        tunnel_id, session_id, plaintext = parse_l2tp_data(raw)
        assert (tunnel_id, session_id, plaintext) == (2, 2, payload)

    def test_control_bit_rejected(self) -> None:
        raw = bytearray(build_l2tp_data(2, 2, b"data"))
        raw[0] |= 0x80  # 置 T=1（控制消息）
        with pytest.raises(ValueError, match="not an L2TP data"):
            parse_l2tp_data(bytes(raw))

    def test_bad_version_rejected(self) -> None:
        raw = bytearray(build_l2tp_data(2, 2, b"data"))
        raw[1] = 0x03  # 版本 3
        with pytest.raises(ValueError, match="version"):
            parse_l2tp_data(bytes(raw))

    def test_short_packet_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_l2tp_data(b"\x00\x00\x00\x01")
