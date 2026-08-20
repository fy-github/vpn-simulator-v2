"""Unit tests for L2TP control framing + tunnel auth (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.l2tp.control import (
    MSG_ICCN,
    MSG_SCCCN,
    MSG_SCCRP,
    MSG_SCCRQ,
    build_control_message,
    build_empty,
    build_icrp,
    build_icrq,
    build_sccrp,
    build_sccrq,
    compute_challenge_response,
    generate_challenge,
    parse_control_message,
    parse_empty,
    parse_icrp,
    parse_icrq,
    parse_sccrp,
    parse_sccrq,
)

SECRET = b"s" * 32


class TestTunnelAuth:
    def test_challenge_response(self) -> None:
        challenge = generate_challenge()
        resp = compute_challenge_response(SECRET, challenge, 1)
        assert len(resp) == 32
        assert resp == compute_challenge_response(SECRET, challenge, 1)
        # tunnel_id 参与认证，不同 tunnel_id 响应不同
        assert resp != compute_challenge_response(SECRET, challenge, 2)


class TestControlMessages:
    def test_sccrq_round_trip(self) -> None:
        challenge = generate_challenge()
        raw = build_sccrq(1, challenge)
        msg, ch, tid = parse_sccrq(raw)
        assert msg.message_type == MSG_SCCRQ
        assert ch == challenge and tid == 1

    def test_sccrp_round_trip(self) -> None:
        challenge = generate_challenge()
        resp = compute_challenge_response(SECRET, challenge, 1)
        raw = build_sccrp(2, resp)
        msg, r, tid = parse_sccrp(raw)
        assert msg.message_type == MSG_SCCRP
        assert r == resp and tid == 2

    def test_icrq_icrp_round_trip(self) -> None:
        _, sid = parse_icrq(build_icrq(1))
        assert sid == 1
        _, sid = parse_icrp(build_icrp(2))
        assert sid == 2

    def test_empty_messages(self) -> None:
        parse_empty(build_empty(1, 0, MSG_SCCCN), MSG_SCCCN)
        parse_empty(build_empty(1, 1, MSG_ICCN), MSG_ICCN)

    def test_wrong_type_rejected(self) -> None:
        raw = build_sccrq(1, generate_challenge())
        with pytest.raises(ValueError):
            parse_sccrp(raw)

    def test_bad_length(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_control_message(b"\x00" * 5)
        raw = build_control_message(1, 0, 0, 0, MSG_SCCRQ, b"short")
        with pytest.raises(ValueError):
            parse_sccrq(raw)
