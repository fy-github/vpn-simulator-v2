"""Unit tests for IKEv2 handshake crypto (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.ikev2.crypto import (
    IKEv2KeySet,
    build_ike_auth,
    build_ike_sa_init,
    derive_key_set,
    dh,
    generate_ephemeral,
    generate_nonce,
    generate_spi,
    parse_ike_auth,
    parse_ike_sa_init,
)

SHARED = b"s" * 32
NONCE_I = b"n" * 32
NONCE_R = b"m" * 32


class TestKeyDerivation:
    def test_derive_key_set_deterministic_and_sized(self) -> None:
        keys = derive_key_set(SHARED, NONCE_I, NONCE_R)
        assert keys == derive_key_set(SHARED, NONCE_I, NONCE_R)
        for k in (keys.sk_ei, keys.sk_er, keys.sk_ai, keys.sk_ar, keys.sk_pi):
            assert len(k) == 32

    def test_nonce_order_matters(self) -> None:
        assert derive_key_set(SHARED, NONCE_I, NONCE_R) != derive_key_set(SHARED, NONCE_R, NONCE_I)

    def test_directional_keys_differ(self) -> None:
        keys = derive_key_set(SHARED, NONCE_I, NONCE_R)
        assert keys.sk_ei != keys.sk_er
        assert keys.sk_ai != keys.sk_ar

    def test_dh_symmetric(self) -> None:
        priv_a, pub_a = generate_ephemeral()
        priv_b, pub_b = generate_ephemeral()
        assert dh(priv_a, pub_b) == dh(priv_b, pub_a)


class TestIkeSaInit:
    def test_build_and_parse_round_trip(self) -> None:
        spi_i = generate_spi()
        _, pub = generate_ephemeral()
        nonce = generate_nonce()
        raw = build_ike_sa_init(spi_i, 0, pub, nonce, is_initiator=True)
        msg = parse_ike_sa_init(raw)
        assert msg.spi_i == spi_i
        assert msg.spi_r == 0
        assert msg.ke_public == pub
        assert msg.nonce == nonce
        assert msg.is_initiator is True

    def test_response_flag(self) -> None:
        raw = build_ike_sa_init(1, 2, b"p" * 32, b"q" * 32, is_initiator=False)
        assert parse_ike_sa_init(raw).is_initiator is False

    def test_bad_length(self) -> None:
        with pytest.raises(ValueError, match="length"):
            parse_ike_sa_init(b"\x00" * 10)

    def test_bad_exchange_type(self) -> None:
        raw = bytearray(build_ike_sa_init(1, 0, b"p" * 32, b"q" * 32, is_initiator=True))
        raw[17] = 35  # change exchange type away from IKE_SA_INIT
        with pytest.raises(ValueError, match="exchange"):
            parse_ike_sa_init(bytes(raw))


class TestIkeAuth:
    def _keys(self) -> IKEv2KeySet:
        return derive_key_set(SHARED, NONCE_I, NONCE_R)

    def test_build_and_parse_round_trip(self) -> None:
        keys = self._keys()
        identity = b"initiator@test"
        raw = build_ike_auth(
            keys.sk_ei, keys.sk_pi, 1, 2, msgid=1, identity=identity, is_initiator=True
        )
        msg = parse_ike_auth(keys.sk_ei, keys.sk_pi, raw, expected_identity=identity)
        assert msg.identity == identity
        assert msg.spi_i == 1 and msg.spi_r == 2 and msg.msgid == 1

    def test_tamper_detected(self) -> None:
        keys = self._keys()
        identity = b"initiator@test"
        raw = bytearray(build_ike_auth(keys.sk_ei, keys.sk_pi, 1, 2, 1, identity, True))
        raw[-1] ^= 0xFF
        with pytest.raises(ValueError):
            parse_ike_auth(keys.sk_ei, keys.sk_pi, bytes(raw), identity)

    def test_wrong_key_fails(self) -> None:
        keys = self._keys()
        other = derive_key_set(b"t" * 32, NONCE_I, NONCE_R)
        identity = b"initiator@test"
        raw = build_ike_auth(keys.sk_ei, keys.sk_pi, 1, 2, 1, identity, True)
        with pytest.raises(ValueError):
            parse_ike_auth(other.sk_ei, other.sk_pi, raw, identity)

    def test_wrong_auth_key_rejected(self) -> None:
        keys = self._keys()
        identity = b"initiator@test"
        raw = build_ike_auth(keys.sk_ei, keys.sk_pi, 1, 2, 1, identity, True)
        forged = IKEv2KeySet(
            sk_ei=keys.sk_ei,
            sk_er=keys.sk_er,
            sk_ai=keys.sk_ai,
            sk_ar=keys.sk_ar,
            sk_pi=b"x" * 32,
        )
        with pytest.raises(ValueError, match="HMAC"):
            parse_ike_auth(forged.sk_ei, forged.sk_pi, raw, identity)

    def test_unexpected_identity_rejected(self) -> None:
        keys = self._keys()
        identity = b"initiator@test"
        raw = build_ike_auth(keys.sk_ei, keys.sk_pi, 1, 2, 1, identity, True)
        with pytest.raises(ValueError, match="identity"):
            parse_ike_auth(keys.sk_ei, keys.sk_pi, raw, b"someone-else@test")

    def test_bad_length(self) -> None:
        keys = self._keys()
        with pytest.raises(ValueError, match="length"):
            parse_ike_auth(keys.sk_ei, keys.sk_pi, b"\x00" * 10, b"x")
