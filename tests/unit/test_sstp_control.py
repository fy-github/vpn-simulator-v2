"""Unit tests for SSTP control framing (MS-SSTP 教学简化) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.sstp.control import (
    CTL_CALL_CONNECT_ACK,
    CTL_CALL_CONNECT_REQUEST,
    build_sstp_message,
    parse_call_connect_ack,
    parse_call_connect_request,
    parse_sstp_message,
)


class TestSSTPControl:
    def test_round_trip(self) -> None:
        raw = build_sstp_message(CTL_CALL_CONNECT_REQUEST)
        msg = parse_sstp_message(raw)
        assert msg.message_type == CTL_CALL_CONNECT_REQUEST
        assert msg.payload == b""

    def test_request_ack_parse(self) -> None:
        parse_call_connect_request(build_sstp_message(CTL_CALL_CONNECT_REQUEST))
        parse_call_connect_ack(build_sstp_message(CTL_CALL_CONNECT_ACK))

    def test_wrong_type_rejected(self) -> None:
        raw = build_sstp_message(CTL_CALL_CONNECT_ACK)
        with pytest.raises(ValueError, match="unexpected"):
            parse_call_connect_request(raw)

    def test_bad_version_rejected(self) -> None:
        raw = bytearray(build_sstp_message(CTL_CALL_CONNECT_REQUEST))
        raw[0] = 0x21  # version 2
        with pytest.raises(ValueError, match="version"):
            parse_sstp_message(bytes(raw))

    def test_c_bit_missing_rejected(self) -> None:
        raw = bytearray(build_sstp_message(CTL_CALL_CONNECT_REQUEST))
        raw[0] = 0x10  # 清除 C 位
        with pytest.raises(ValueError, match="C bit"):
            parse_sstp_message(bytes(raw))

    def test_length_mismatch_rejected(self) -> None:
        raw = build_sstp_message(CTL_CALL_CONNECT_REQUEST) + b"extra"
        with pytest.raises(ValueError, match="mismatch"):
            parse_sstp_message(raw)

    def test_short_packet_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_sstp_message(b"\x11\x00\x01")
