"""Unit tests for PPTP control framing (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.pptp.control import (
    build_ocrp,
    build_ocrq,
    build_sccrp,
    build_sccrq,
    parse_control_message,
    parse_ocrp,
    parse_ocrq,
    parse_sccrp,
    parse_sccrq,
)


class TestControlMessages:
    def test_sccrq_round_trip(self) -> None:
        msg = parse_sccrq(build_sccrq())
        assert msg.control_type == 1

    def test_sccrp_round_trip(self) -> None:
        parse_sccrp(build_sccrp())

    def test_ocrq_round_trip(self) -> None:
        _, call_id, call_serial = parse_ocrq(build_ocrq(1, 7))
        assert (call_id, call_serial) == (1, 7)

    def test_ocrp_round_trip(self) -> None:
        _, call_id, peer_call_id = parse_ocrp(build_ocrp(2, 1))
        assert (call_id, peer_call_id) == (2, 1)

    def test_bad_magic_cookie(self) -> None:
        raw = bytearray(build_sccrq())
        raw[4] ^= 0xFF
        with pytest.raises(ValueError, match="magic"):
            parse_control_message(bytes(raw))

    def test_length_mismatch(self) -> None:
        raw = build_sccrq() + b"extra"
        with pytest.raises(ValueError, match="mismatch"):
            parse_control_message(raw)

    def test_short_message(self) -> None:
        with pytest.raises(ValueError):
            parse_control_message(b"\x00\x05")

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_ocrq(build_sccrq())
