"""Unit tests for IKEv1/IPSec handshake crypto (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.ipsec.crypto import (
    build_main_mode_auth,
    build_main_mode_ke,
    build_main_mode_sa,
    build_quick_mode_msg,
    derive_key_set,
    dh,
    generate_cookie,
    generate_ephemeral,
    generate_nonce,
    parse_main_mode_auth,
    parse_main_mode_ke,
    parse_main_mode_sa,
    parse_quick_mode_msg,
)

PSK = b"p" * 32
NONCE_I = b"n" * 32
NONCE_R = b"m" * 32
KE_I = b"a" * 32
KE_R = b"b" * 32


class TestKeyDerivation:
    def test_derive_key_set(self) -> None:
        keys = derive_key_set(PSK, NONCE_I, NONCE_R)
        assert keys == derive_key_set(PSK, NONCE_I, NONCE_R)
        for k in (keys.skeyid, keys.skeyid_a, keys.skeyid_e):
            assert len(k) == 32

    def test_nonce_order_matters(self) -> None:
        assert derive_key_set(PSK, NONCE_I, NONCE_R) != derive_key_set(PSK, NONCE_R, NONCE_I)

    def test_dh_symmetric(self) -> None:
        priv_a, pub_a = generate_ephemeral()
        priv_b, pub_b = generate_ephemeral()
        assert dh(priv_a, pub_b) == dh(priv_b, pub_a)


class TestMainMode:
    def test_sa_round_trip(self) -> None:
        cookie_i = generate_cookie()
        raw = build_main_mode_sa(cookie_i, 0, is_initiator=True)
        msg = parse_main_mode_sa(raw)
        assert msg.cookie_i == cookie_i
        assert msg.cookie_r == 0
        assert msg.is_initiator is True

    def test_ke_round_trip(self) -> None:
        raw = build_main_mode_ke(1, 2, KE_I, NONCE_I, is_initiator=True)
        msg = parse_main_mode_ke(raw)
        assert msg.cookie_i == 1 and msg.cookie_r == 2
        assert msg.ke == KE_I and msg.nonce == NONCE_I
        assert msg.is_initiator is True

    def _keys(self):
        return derive_key_set(PSK, NONCE_I, NONCE_R)

    def _auth(self, keys):
        return build_main_mode_auth(
            1, 2, keys.skeyid, keys.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, b"initiator@test", True
        )

    def test_auth_round_trip(self) -> None:
        keys = self._keys()
        raw = self._auth(keys)
        msg = parse_main_mode_auth(
            keys.skeyid, keys.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, raw, b"initiator@test"
        )
        assert msg.identity == b"initiator@test"
        assert msg.cookie_i == 1 and msg.cookie_r == 2

    def test_auth_tamper_detected(self) -> None:
        keys = self._keys()
        raw = bytearray(self._auth(keys))
        raw[-1] ^= 0xFF
        with pytest.raises(ValueError):
            parse_main_mode_auth(
                keys.skeyid,
                keys.skeyid_e,
                KE_I,
                KE_R,
                NONCE_I,
                NONCE_R,
                bytes(raw),
                b"initiator@test",
            )

    def test_auth_wrong_key_fails(self) -> None:
        keys = self._keys()
        other = derive_key_set(b"q" * 32, NONCE_I, NONCE_R)
        raw = self._auth(keys)
        with pytest.raises(ValueError):
            parse_main_mode_auth(
                other.skeyid, other.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, raw, b"initiator@test"
            )

    def test_auth_bad_hash_rejected(self) -> None:
        keys = self._keys()
        # 用伪造的 skeyid 计算 HASH（AEAD 仍用 keys.skeyid_e 加密，可解密）。
        raw = build_main_mode_auth(
            1, 2, b"x" * 32, keys.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, b"initiator@test", True
        )
        with pytest.raises(ValueError, match="HASH"):
            parse_main_mode_auth(
                keys.skeyid, keys.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, raw, b"initiator@test"
            )

    def test_auth_wrong_identity_rejected(self) -> None:
        keys = self._keys()
        raw = self._auth(keys)
        with pytest.raises(ValueError, match="identity"):
            parse_main_mode_auth(
                keys.skeyid, keys.skeyid_e, KE_I, KE_R, NONCE_I, NONCE_R, raw, b"other@test"
            )

    def test_bad_length(self) -> None:
        keys = self._keys()
        with pytest.raises(ValueError):
            parse_main_mode_sa(b"\x00" * 10)
        with pytest.raises(ValueError):
            parse_main_mode_ke(b"\x00" * 10)
        with pytest.raises(ValueError):
            parse_main_mode_auth(
                keys.skeyid,
                keys.skeyid_e,
                KE_I,
                KE_R,
                NONCE_I,
                NONCE_R,
                b"\x00" * 10,
                b"initiator@test",
            )


class TestQuickMode:
    def test_quick_mode_round_trip(self) -> None:
        keys = derive_key_set(PSK, NONCE_I, NONCE_R)
        nonce2 = generate_nonce()
        raw = build_quick_mode_msg(1, 2, keys.skeyid_a, nonce2, is_initiator=True)
        assert parse_quick_mode_msg(keys.skeyid_a, raw) == nonce2

    def test_quick_mode_ack(self) -> None:
        keys = derive_key_set(PSK, NONCE_I, NONCE_R)
        ack = build_quick_mode_msg(1, 2, keys.skeyid_a, b"", is_initiator=True, final_ack=True)
        assert parse_quick_mode_msg(keys.skeyid_a, ack, final_ack=True) is None

    def test_quick_mode_tamper(self) -> None:
        keys = derive_key_set(PSK, NONCE_I, NONCE_R)
        raw = bytearray(build_quick_mode_msg(1, 2, keys.skeyid_a, generate_nonce(), True))
        raw[-1] ^= 0xFF
        with pytest.raises(ValueError):
            parse_quick_mode_msg(keys.skeyid_a, bytes(raw))
