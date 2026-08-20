"""Unit tests for OpenConnect CSTP framing (AnyConnect 教学简化) (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.openconnect.cstp import (
    build_connect_request,
    build_connect_response,
    parse_connect_request,
    parse_connect_response,
)


class TestCSTP:
    def test_request_parse(self) -> None:
        parse_connect_request(build_connect_request())

    def test_response_parse(self) -> None:
        parse_connect_response(build_connect_response())

    def test_bad_request_line_rejected(self) -> None:
        raw = build_connect_request().replace(b"CONNECT", b"GET", 1)
        with pytest.raises(ValueError, match="request line"):
            parse_connect_request(raw)

    def test_bad_request_version_rejected(self) -> None:
        raw = build_connect_request().replace(b"X-CSTP-Version: 1", b"X-CSTP-Version: 9", 1)
        with pytest.raises(ValueError, match="Version"):
            parse_connect_request(raw)

    def test_bad_response_status_rejected(self) -> None:
        raw = build_connect_response().replace(b"200 CONNECTED", b"403 Forbidden", 1)
        with pytest.raises(ValueError, match="status"):
            parse_connect_response(raw)
