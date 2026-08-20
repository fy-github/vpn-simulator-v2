"""Unit tests for PPP LCP/IPCP control framing (RFC 1661 / RFC 1332) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.ppp.control import (
    CONFIGURE_ACK,
    CONFIGURE_REQUEST,
    build_configure_ack,
    build_configure_request,
    build_ipcp_ip_option,
    build_lcp_mru_option,
    parse_frame,
)


class TestPPPControl:
    def test_lcp_roundtrip(self) -> None:
        raw = build_configure_request(7, build_lcp_mru_option(1500))
        code, identifier, data = parse_frame(raw)
        assert (code, identifier) == (CONFIGURE_REQUEST, 7)
        assert data == bytes([1, 4, 0x05, 0xDC])  # MRU=1500

    def test_ipcp_roundtrip(self) -> None:
        raw = build_configure_request(9, build_ipcp_ip_option("192.168.1.10"))
        code, identifier, data = parse_frame(raw)
        assert (code, identifier) == (CONFIGURE_REQUEST, 9)
        assert data == bytes([3, 6, 192, 168, 1, 10])

    def test_ack_echoes_options(self) -> None:
        options = build_lcp_mru_option(1400)
        req = build_configure_request(3, options)
        _code, identifier, req_data = parse_frame(req)
        ack = build_configure_ack(identifier, req_data)
        code, ack_id, ack_data = parse_frame(ack)
        assert (code, ack_id) == (CONFIGURE_ACK, 3)
        assert ack_data == req_data

    def test_short_frame_rejected(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_frame(b"\x01\x01\x00")

    def test_length_mismatch_rejected(self) -> None:
        raw = build_configure_request(1, build_lcp_mru_option())
        with pytest.raises(ValueError, match="mismatch"):
            parse_frame(raw[:-1])

    def test_invalid_ip_rejected(self) -> None:
        with pytest.raises(ValueError, match="IPv4"):
            build_ipcp_ip_option("999.1.1.1")
