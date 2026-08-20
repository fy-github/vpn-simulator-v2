"""IKEv1/IPSec 握手密码学实现（真实曲线/真实 PRF/AEAD，DH 组教学简化）。

依据 RFC 2409 的 IKEv1 Main Mode（Phase 1，6 消息）与 Quick Mode（Phase 2，
3 消息），使用 `cryptography` 库真实实现：

- DH：X25519（教学简化，替代 IKEv1 传统 MODP 组，明示）。
- PRF：HKDF-SHA256——``SKEYID = HKDF(psk, salt=Ni||Nr)``，再派生 ``SKEYID_a``
  （认证）、``SKEYID_e``（加密）。
- 认证：``HASH = HMAC-SHA256(SKEYID, KE_i||KE_r||Ni||Nr||ID)``（教学简化 PSK 认证）。
- Phase 1 消息 5/6 加密：ChaCha20-Poly1305，nonce = ``msgid(4,LE)||方向(4,LE)||0x00*4``
  （方向位避免对称密钥 nonce 复用）。
- Phase 2（Quick Mode）：HMAC-SHA256(SKEYID_a, ...) 认证的 3 消息（教学简化，
  真实 Quick Mode 用 SKEYID_e 加密）。

报文格式（教学简化版）：::

    头部: cookie_i(8) | cookie_r(8) | exchange(1) | flags(1) | msgid(4)   # 22B
    Main Mode(2) msg1(I): 头部 + SA_placeholder(4)
                msg2(R): 头部 + SA_placeholder(4)
                msg3(I): 头部 + KE_i(32) + Nonce_i(32)
                msg4(R): 头部 + KE_r(32) + Nonce_r(32)
                msg5(I): 头部 + AEAD(ID_i + HASH_I)
                msg6(R): 头部 + AEAD(ID_r + HASH_R)
    Quick Mode(32) qm1(I): 头部(msgid=1) + HASH1(32) + Nonce2_i(32)
                qm2(R): 头部(msgid=1) + HASH2(32) + Nonce2_r(32)
                qm3(I): 头部(msgid=1) + HASH3(32)

本模块只做控制面握手（ISAKMP/IPSec SA 建立），不实现 ESP 数据面转发，也不作为
生产 VPN 网关。
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

EXCHANGE_IDENTITY_PROTECTION = 2  # Main Mode
EXCHANGE_QUICK_MODE = 32
FLAG_ENCRYPTION = 0x01
FLAG_INITIATOR = 0x08
FLAG_RESPONSE = 0x20

COOKIE_LEN = 8
NONCE_LEN = 32
KEY_LEN = 32
TAG_LEN = 16
HASH_LEN = 32
KE_LEN = 32
HEADER_LEN = COOKIE_LEN * 2 + 1 + 1 + 4  # 22

SA_PROPOSAL = b"\x00\x00\x00\x01"  # 教学占位：AES-256-GCM / X25519 / PSK 提议 id 1
SA_PROPOSAL_LEN = 4


@dataclass(frozen=True)
class IPsecKeySet:
    """Main Mode 之后派生的密钥集。

    Attributes:
        skeyid: 主密钥（HASH 认证用）。
        skeyid_a: 认证密钥（Quick Mode HASH 用）。
        skeyid_e: 加密密钥（msg5/msg6 AEAD 用）。
    """

    skeyid: bytes
    skeyid_a: bytes
    skeyid_e: bytes


@dataclass(frozen=True)
class MainModeSaMsg:
    cookie_i: int
    cookie_r: int
    is_initiator: bool


@dataclass(frozen=True)
class MainModeKeMsg:
    cookie_i: int
    cookie_r: int
    ke: bytes
    nonce: bytes
    is_initiator: bool


@dataclass(frozen=True)
class MainModeAuthMsg:
    cookie_i: int
    cookie_r: int
    identity: bytes
    is_initiator: bool


def generate_cookie() -> int:
    """生成 64 位随机 cookie。"""
    return int.from_bytes(secrets.token_bytes(COOKIE_LEN), "big")


def generate_nonce() -> bytes:
    """生成 32 字节随机 Nonce。"""
    return secrets.token_bytes(NONCE_LEN)


def generate_psk() -> bytes:
    """生成 32 字节随机预共享密钥（PSK）。"""
    return secrets.token_bytes(KEY_LEN)


def generate_ephemeral() -> tuple[bytes, bytes]:
    """生成 X25519 临时密钥对，返回 (私钥字节, 公钥字节)。"""
    private = X25519PrivateKey.generate()
    private_bytes = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_bytes = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private_bytes, public_bytes


def dh(private_bytes: bytes, public_bytes: bytes) -> bytes:
    """X25519 Diffie-Hellman，返回 32 字节共享密钥。"""
    private = X25519PrivateKey.from_private_bytes(private_bytes)
    public = X25519PublicKey.from_public_bytes(public_bytes)
    return private.exchange(public)


def _hkdf(ikm: bytes, salt: bytes, info: bytes, length: int = KEY_LEN) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def derive_key_set(psk: bytes, nonce_i: bytes, nonce_r: bytes) -> IPsecKeySet:
    """从 PSK + 双方 nonce 派生 IKEv1 密钥集（HKDF-SHA256）。"""
    skeyid = _hkdf(psk, salt=nonce_i + nonce_r, info=b"IKEv1 SKEYID")
    return IPsecKeySet(
        skeyid=skeyid,
        skeyid_a=_hkdf(skeyid, salt=b"", info=b"IKEv1 SKEYID_a"),
        skeyid_e=_hkdf(skeyid, salt=b"", info=b"IKEv1 SKEYID_e"),
    )


def _phase1_hash(
    skeyid: bytes,
    ke_i: bytes,
    ke_r: bytes,
    nonce_i: bytes,
    nonce_r: bytes,
    identity: bytes,
) -> bytes:
    """Phase 1 HASH 认证（教学简化 PSK 认证）。"""
    return hmac_mod.new(skeyid, ke_i + ke_r + nonce_i + nonce_r + identity, hashlib.sha256).digest()


def _header(cookie_i: int, cookie_r: int, exchange: int, flags: int, msgid: int) -> bytes:
    return (
        cookie_i.to_bytes(COOKIE_LEN, "big")
        + cookie_r.to_bytes(COOKIE_LEN, "big")
        + bytes([exchange, flags])
        + msgid.to_bytes(4, "big")
    )


def _flags(is_initiator: bool, encrypted: bool = False) -> int:
    flags = FLAG_INITIATOR if is_initiator else FLAG_RESPONSE
    if encrypted:
        flags |= FLAG_ENCRYPTION
    return flags


def build_main_mode_sa(cookie_i: int, cookie_r: int, is_initiator: bool) -> bytes:
    """组帧 Main Mode msg1/msg2（SA 协商，教学占位 proposal）。"""
    return (
        _header(cookie_i, cookie_r, EXCHANGE_IDENTITY_PROTECTION, _flags(is_initiator), 0)
        + SA_PROPOSAL
    )


def parse_main_mode_sa(raw: bytes) -> MainModeSaMsg:
    """解析 Main Mode msg1/msg2。"""
    if len(raw) != HEADER_LEN + SA_PROPOSAL_LEN:
        raise ValueError(f"invalid Main Mode SA length: {len(raw)}")
    if raw[16] != EXCHANGE_IDENTITY_PROTECTION:
        raise ValueError(f"invalid Main Mode exchange: {raw[16]}")
    return MainModeSaMsg(
        cookie_i=int.from_bytes(raw[0:COOKIE_LEN], "big"),
        cookie_r=int.from_bytes(raw[COOKIE_LEN : COOKIE_LEN * 2], "big"),
        is_initiator=bool(raw[17] & FLAG_INITIATOR),
    )


def build_main_mode_ke(
    cookie_i: int,
    cookie_r: int,
    ke: bytes,
    nonce: bytes,
    is_initiator: bool,
) -> bytes:
    """组帧 Main Mode msg3/msg4（DH 公钥 + Nonce）。"""
    return (
        _header(cookie_i, cookie_r, EXCHANGE_IDENTITY_PROTECTION, _flags(is_initiator), 0)
        + ke
        + nonce
    )


def parse_main_mode_ke(raw: bytes) -> MainModeKeMsg:
    """解析 Main Mode msg3/msg4。"""
    if len(raw) != HEADER_LEN + KE_LEN + NONCE_LEN:
        raise ValueError(f"invalid Main Mode KE length: {len(raw)}")
    if raw[16] != EXCHANGE_IDENTITY_PROTECTION:
        raise ValueError(f"invalid Main Mode exchange: {raw[16]}")
    return MainModeKeMsg(
        cookie_i=int.from_bytes(raw[0:COOKIE_LEN], "big"),
        cookie_r=int.from_bytes(raw[COOKIE_LEN : COOKIE_LEN * 2], "big"),
        ke=raw[HEADER_LEN : HEADER_LEN + KE_LEN],
        nonce=raw[HEADER_LEN + KE_LEN :],
        is_initiator=bool(raw[17] & FLAG_INITIATOR),
    )


def _aead_nonce(msgid: int, is_initiator: bool) -> bytes:
    """Phase 1 加密 nonce：msgid + 方向位，避免对称密钥 nonce 复用。"""
    direction = 0 if is_initiator else 1
    return msgid.to_bytes(4, "little") + direction.to_bytes(4, "little") + b"\x00" * 4


def build_main_mode_auth(
    cookie_i: int,
    cookie_r: int,
    skeyid: bytes,
    skeyid_e: bytes,
    ke_i: bytes,
    ke_r: bytes,
    nonce_i: bytes,
    nonce_r: bytes,
    identity: bytes,
    is_initiator: bool,
) -> bytes:
    """组帧并加密 Main Mode msg5/msg6（明文 = identity + HASH）。"""
    digest = _phase1_hash(skeyid, ke_i, ke_r, nonce_i, nonce_r, identity)
    plaintext = identity + digest
    ciphertext = ChaCha20Poly1305(skeyid_e).encrypt(_aead_nonce(0, is_initiator), plaintext, b"")
    return (
        _header(cookie_i, cookie_r, EXCHANGE_IDENTITY_PROTECTION, _flags(is_initiator, True), 0)
        + ciphertext
    )


def parse_main_mode_auth(
    skeyid: bytes,
    skeyid_e: bytes,
    ke_i: bytes,
    ke_r: bytes,
    nonce_i: bytes,
    nonce_r: bytes,
    raw: bytes,
    expected_identity: bytes,
) -> MainModeAuthMsg:
    """解析并校验 Main Mode msg5/msg6（AEAD 解密 + HASH + identity 校验）。"""
    if len(raw) < HEADER_LEN + TAG_LEN:
        raise ValueError(f"invalid Main Mode AUTH length: {len(raw)}")
    if raw[16] != EXCHANGE_IDENTITY_PROTECTION:
        raise ValueError(f"invalid Main Mode exchange: {raw[16]}")

    cookie_i = int.from_bytes(raw[0:COOKIE_LEN], "big")
    cookie_r = int.from_bytes(raw[COOKIE_LEN : COOKIE_LEN * 2], "big")
    is_initiator = bool(raw[17] & FLAG_INITIATOR)
    ciphertext = raw[HEADER_LEN:]
    try:
        plaintext = ChaCha20Poly1305(skeyid_e).decrypt(
            _aead_nonce(0, is_initiator), ciphertext, b""
        )
    except InvalidTag as exc:
        raise ValueError("AEAD authentication failed") from exc

    if len(plaintext) < HASH_LEN:
        raise ValueError(f"invalid Main Mode AUTH plaintext length: {len(plaintext)}")
    identity = plaintext[:-HASH_LEN]
    digest = plaintext[-HASH_LEN:]
    expected_digest = _phase1_hash(skeyid, ke_i, ke_r, nonce_i, nonce_r, identity)
    if not hmac_mod.compare_digest(digest, expected_digest):
        raise ValueError("Main Mode HASH verification failed")
    if identity != expected_identity:
        raise ValueError(f"unexpected identity: {identity!r}")

    return MainModeAuthMsg(
        cookie_i=cookie_i, cookie_r=cookie_r, identity=identity, is_initiator=is_initiator
    )


def build_quick_mode_msg(
    cookie_i: int,
    cookie_r: int,
    skeyid_a: bytes,
    nonce2: bytes,
    is_initiator: bool,
    final_ack: bool = False,
) -> bytes:
    """组帧 Quick Mode 消息（教学简化：HMAC 认证，不加密）。

    qm1/qm2 携带 HASH + Nonce2；qm3（final_ack）只携带 HASH(ack)。
    """
    if final_ack:
        payload = hmac_mod.new(skeyid_a, b"ack", hashlib.sha256).digest()
    else:
        payload = hmac_mod.new(skeyid_a, SA_PROPOSAL + nonce2, hashlib.sha256).digest() + nonce2
    return _header(cookie_i, cookie_r, EXCHANGE_QUICK_MODE, _flags(is_initiator), 1) + payload


def parse_quick_mode_msg(
    skeyid_a: bytes,
    raw: bytes,
    final_ack: bool = False,
) -> bytes | None:
    """解析并校验 Quick Mode 消息。

    返回 Nonce2（qm1/qm2），final_ack 时返回 None。校验失败抛 ValueError。
    """
    if raw[16] != EXCHANGE_QUICK_MODE:
        raise ValueError(f"invalid Quick Mode exchange: {raw[16]}")
    payload = raw[HEADER_LEN:]
    if final_ack:
        if len(payload) != HASH_LEN:
            raise ValueError(f"invalid Quick Mode ack length: {len(payload)}")
        expected = hmac_mod.new(skeyid_a, b"ack", hashlib.sha256).digest()
        if not hmac_mod.compare_digest(payload, expected):
            raise ValueError("Quick Mode ack HASH verification failed")
        return None
    if len(payload) != HASH_LEN + NONCE_LEN:
        raise ValueError(f"invalid Quick Mode length: {len(payload)}")
    digest = payload[:HASH_LEN]
    nonce2 = payload[HASH_LEN:]
    expected = hmac_mod.new(skeyid_a, SA_PROPOSAL + nonce2, hashlib.sha256).digest()
    if not hmac_mod.compare_digest(digest, expected):
        raise ValueError("Quick Mode HASH verification failed")
    return nonce2
