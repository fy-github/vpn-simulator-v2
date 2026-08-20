"""Unit tests for PPP MS-CHAPv2 (RFC 2759) — MD4 / SHA1 / DES (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.ppp.mschapv2 import (
    compute_challenge,
    compute_challenge_response,
    compute_nt_hash,
    generate_challenge,
    md4,
    verify_challenge_response,
)


class TestMD4:
    """RFC 1320 测试向量。"""

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"", "31d6cfe0d16ae931b73c59d7e0c089c0"),
            (b"a", "bde52cb31de33e46245e05fbdbd6fb24"),
            (b"abc", "a448017aaf21d8525fc10ae87aa6729d"),
            (b"message digest", "d9130a8164549fe818874806e1c7014b"),
        ],
    )
    def test_md4_rfc1320_vectors(self, data: bytes, expected: str) -> None:
        assert md4(data).hex() == expected


class TestMSCHAPv2:
    """RFC 2759 第 9.2 节测试向量（UserName=User, Password=clientPass）。"""

    SERVER_CHALLENGE = bytes.fromhex("5B5D7C7D7B3F2F3E3C2C602132262628")
    PEER_CHALLENGE = bytes.fromhex("21402324255E262A28295F2B3A337C7E")

    def test_nt_hash(self) -> None:
        assert compute_nt_hash("clientPass").hex().upper() == "44EBBA8D5312B8D611474411F56989AE"

    def test_challenge(self) -> None:
        assert (
            compute_challenge(self.PEER_CHALLENGE, self.SERVER_CHALLENGE, "User").hex().upper()
            == "D02E4386BCE91226"
        )

    def test_challenge_response(self) -> None:
        nt = compute_nt_hash("clientPass")
        resp = compute_challenge_response(nt, self.PEER_CHALLENGE, self.SERVER_CHALLENGE, "User")
        assert resp.hex().upper() == "82309ECD8D708B5EA08FAA3981CD83544233114A3D85D6DF"

    def test_verify_roundtrip(self) -> None:
        peer = generate_challenge()
        server = generate_challenge()
        username = "alice@vpn-simulator.local"
        response = compute_challenge_response(compute_nt_hash("s3cret"), peer, server, username)
        assert verify_challenge_response("s3cret", username, peer, server, response)

    def test_verify_wrong_password_rejected(self) -> None:
        peer = generate_challenge()
        server = generate_challenge()
        username = "alice@vpn-simulator.local"
        response = compute_challenge_response(compute_nt_hash("correct"), peer, server, username)
        assert not verify_challenge_response("wrong", username, peer, server, response)

    def test_verify_wrong_challenge_rejected(self) -> None:
        peer = generate_challenge()
        server = generate_challenge()
        username = "alice@vpn-simulator.local"
        response = compute_challenge_response(compute_nt_hash("s3cret"), peer, server, username)
        tampered = bytes([server[0] ^ 0xFF]) + server[1:]
        assert not verify_challenge_response("s3cret", username, peer, tampered, response)
