"""Unit tests: MPPE key derivation (RFC 3079) + RC4 (RFC 6229) + session (P1/P3)."""

from __future__ import annotations

import pytest
from vpn_simulator.plugins.protocols.ppp.mppe import (
    MPPESession,
    derive_session_keys,
    rc4_crypt,
)

# RFC 3079 §4.1 输入（与 RFC 2759 §9.2 一致）。
NT_HASH = bytes.fromhex("44EBBA8D5312B8D611474411F56989AE")
NT_RESPONSE = bytes.fromhex("82309ECD8D708B5EA08FAA3981CD83544233114A3D85D6DF")


class TestMPPEKeyDerivation:
    """P1 — RFC 3079 §3.2/§3.4 密钥派生（官方向量）。"""

    def test_master_key_vector(self) -> None:
        send, recv = derive_session_keys(NT_HASH, NT_RESPONSE)
        # RFC 3079 §4.1：SendSessionKey = ReceiveSessionKey = BD005EBA...
        assert send == bytes.fromhex("BD005EBA041CD3AFEE847C5A2CB19064")
        assert recv == send  # MS-CHAPv2 对称

    def test_bad_input_lengths(self) -> None:
        with pytest.raises(ValueError):
            derive_session_keys(b"\x00" * 15, NT_RESPONSE)
        with pytest.raises(ValueError):
            derive_session_keys(NT_HASH, b"\x00" * 23)


class TestRC4:
    """P1 — RC4 流加密（RFC 6229 向量 + 往返）。"""

    def test_keystream_vector(self) -> None:
        # RFC 6229 §1.2：128-bit key 01..10 → keystream 9AC7CC9A...
        key = bytes(range(1, 17))
        assert rc4_crypt(key, bytes(16)).hex().upper() == "9AC7CC9A609D1EF7B2932899CDE41B97"

    def test_roundtrip(self) -> None:
        key = b"k" * 16
        ct = rc4_crypt(key, b"hello mppe")
        assert rc4_crypt(key, ct) == b"hello mppe"

    def test_wrong_key_fails(self) -> None:
        ct = rc4_crypt(b"a" * 16, b"secret")
        assert rc4_crypt(b"b" * 16, ct) != b"secret"


class TestMPPESession:
    """P1 — 会话加解密 + coherency_count 重放检测。"""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        key = b"s" * 16
        sender = MPPESession(send_key=key, recv_key=key)
        receiver = MPPESession(send_key=key, recv_key=key)
        packet = sender.encrypt(b"ppp encrypted payload")
        assert receiver.decrypt(packet) == b"ppp encrypted payload"

    def test_different_keys_per_direction(self) -> None:
        # 客户端用 send_key 加密，服务端用同一 send_key 作为 recv_key 解密。
        client = MPPESession(send_key=b"c" * 16, recv_key=b"s" * 16)
        server = MPPESession(send_key=b"s" * 16, recv_key=b"c" * 16)
        packet = client.encrypt(b"up")
        assert server.decrypt(packet) == b"up"

    def test_replay_rejected(self) -> None:
        key = b"k" * 16
        sender = MPPESession(send_key=key, recv_key=key)
        receiver = MPPESession(send_key=key, recv_key=key)
        packet = sender.encrypt(b"m")
        receiver.decrypt(packet)
        with pytest.raises(ValueError, match="replay"):
            receiver.decrypt(packet)

    def test_short_packet_rejected(self) -> None:
        receiver = MPPESession(send_key=b"k" * 16, recv_key=b"k" * 16)
        with pytest.raises(ValueError, match="length"):
            receiver.decrypt(b"\x00")
