"""IKEv2/IPSec 握手密码学实现（真实曲线/真实 PRF/AEAD）。

依据 RFC 7296 的 IKEv2 两阶段交换，使用 `cryptography` 库真实实现：

- DH：X25519（Curve25519）。
- 密钥派生：HKDF-SHA256——``SKEYSEED = HKDF(salt=Ni||Nr, ikm=DH_shared)``，
  再派生 ``SK_ei/SK_er``（加密）、``SK_ai/SK_ar``（完整性）、``SK_pi``（PSK AUTH）。
- IKE_AUTH 加密：ChaCha20-Poly1305（AEAD），nonce = ``msgid(4, LE)||0x00*8``。
- AUTH：HMAC-SHA256(SK_pi, identity)——教学简化的 PSK 认证（明示，非完整
  IKEv2 SignedOctets 计算）。

报文格式（教学简化版）：::

    头部: spi_i(8) | spi_r(8) | version(1)=0x20 | exchange(1) | flags(1) | msgid(4)
    IKE_SA_INIT(34) 请求: 头部 + KE_i(32) + Nonce_i(32)   # spi_r 为 0
    IKE_SA_INIT(34) 响应: 头部 + KE_r(32) + Nonce_r(32)
    IKE_AUTH(35)    请求/响应: 头部 + ciphertext+tag(AEAD)  # 明文 = identity + AUTH

本模块只做控制面握手（IKE SA 建立），不实现 ESP 数据面转发，也不作为生产
VPN 网关。
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

IKE_VERSION = 0x20
EXCHANGE_IKE_SA_INIT = 34
EXCHANGE_IKE_AUTH = 35
FLAG_INITIATOR = 0x08
FLAG_RESPONSE = 0x20

SPI_LEN = 8
NONCE_LEN = 32
KEY_LEN = 32
TAG_LEN = 16
AUTH_LEN = 32  # HMAC-SHA256

HEADER_LEN = SPI_LEN * 2 + 1 + 1 + 1 + 4  # 23
KE_LEN = 32
SA_INIT_BODY_LEN = KE_LEN + NONCE_LEN  # 64


@dataclass(frozen=True)
class IKEv2KeySet:
    """IKE_SA_INIT 之后派生的密钥集。

    Attributes:
        sk_ei / sk_er: 发起方→响应方 / 响应方→发起方的加密密钥。
        sk_ai / sk_ar: 对应的完整性（HMAC）密钥。
        sk_pi: PSK AUTH 密钥（HMAC 认证用）。
    """

    sk_ei: bytes
    sk_er: bytes
    sk_ai: bytes
    sk_ar: bytes
    sk_pi: bytes


@dataclass(frozen=True)
class IkeSaInitMessage:
    """解析后的 IKE_SA_INIT 报文。"""

    spi_i: int
    spi_r: int
    ke_public: bytes
    nonce: bytes
    is_initiator: bool


@dataclass(frozen=True)
class IkeAuthMessage:
    """解析后的 IKE_AUTH 报文。"""

    spi_i: int
    spi_r: int
    msgid: int
    identity: bytes


def generate_spi() -> int:
    """生成 64 位随机 SPI。"""
    return int.from_bytes(secrets.token_bytes(SPI_LEN), "big")


def generate_nonce() -> bytes:
    """生成 32 字节随机 Nonce。"""
    return secrets.token_bytes(NONCE_LEN)


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


def derive_esp_key(sk_ei: bytes) -> bytes:
    """从 IKEv2 加密密钥派生 ESP 密钥（教学简化替代 CHILD_SA KEYMAT）。"""
    return _hkdf(sk_ei, salt=b"", info=b"IPsec ESP KEYMAT")


def derive_key_set(shared_secret: bytes, nonce_i: bytes, nonce_r: bytes) -> IKEv2KeySet:
    """从 DH 共享密钥 + 双方 nonce 派生 IKEv2 密钥集（HKDF-SHA256）。"""
    skeyseed = _hkdf(shared_secret, salt=nonce_i + nonce_r, info=b"IKEv2 SKEYSEED")
    return IKEv2KeySet(
        sk_ei=_hkdf(skeyseed, salt=b"", info=b"IKEv2 SK_ei"),
        sk_er=_hkdf(skeyseed, salt=b"", info=b"IKEv2 SK_er"),
        sk_ai=_hkdf(skeyseed, salt=b"", info=b"IKEv2 SK_ai"),
        sk_ar=_hkdf(skeyseed, salt=b"", info=b"IKEv2 SK_ar"),
        sk_pi=_hkdf(skeyseed, salt=b"", info=b"IKEv2 SK_pi"),
    )


def _header(
    spi_i: int,
    spi_r: int,
    exchange: int,
    flags: int,
    msgid: int,
) -> bytes:
    return (
        spi_i.to_bytes(SPI_LEN, "big")
        + spi_r.to_bytes(SPI_LEN, "big")
        + bytes([IKE_VERSION, exchange, flags])
        + msgid.to_bytes(4, "big")
    )


def build_ike_sa_init(
    spi_i: int,
    spi_r: int,
    ke_public: bytes,
    nonce: bytes,
    is_initiator: bool,
) -> bytes:
    """组帧 IKE_SA_INIT 报文（请求 spi_r=0，响应 spi_r=响应方 SPI）。"""
    flags = FLAG_INITIATOR if is_initiator else FLAG_RESPONSE
    return _header(spi_i, spi_r, EXCHANGE_IKE_SA_INIT, flags, 0) + ke_public + nonce


def parse_ike_sa_init(raw: bytes) -> IkeSaInitMessage:
    """解析 IKE_SA_INIT 报文。"""
    if len(raw) != HEADER_LEN + SA_INIT_BODY_LEN:
        raise ValueError(f"invalid IKE_SA_INIT length: {len(raw)}")
    if raw[16] != IKE_VERSION or raw[17] != EXCHANGE_IKE_SA_INIT:
        raise ValueError(f"invalid IKE_SA_INIT header: version={raw[16]} exchange={raw[17]}")
    return IkeSaInitMessage(
        spi_i=int.from_bytes(raw[0:SPI_LEN], "big"),
        spi_r=int.from_bytes(raw[SPI_LEN : SPI_LEN * 2], "big"),
        ke_public=raw[HEADER_LEN : HEADER_LEN + KE_LEN],
        nonce=raw[HEADER_LEN + KE_LEN :],
        is_initiator=bool(raw[18] & FLAG_INITIATOR),
    )


def _auth_nonce(msgid: int) -> bytes:
    """IKE_AUTH 的 AEAD nonce：msgid（4 字节小端）后补 8 个零字节。"""
    return msgid.to_bytes(4, "little") + b"\x00" * 8


def build_ike_auth(
    sk_e: bytes,
    sk_pi: bytes,
    spi_i: int,
    spi_r: int,
    msgid: int,
    identity: bytes,
    is_initiator: bool,
) -> bytes:
    """组帧并加密 IKE_AUTH 报文（明文 = identity + HMAC-AUTH）。"""
    auth = hmac_mod.new(sk_pi, identity, hashlib.sha256).digest()
    plaintext = identity + auth
    ciphertext = ChaCha20Poly1305(sk_e).encrypt(_auth_nonce(msgid), plaintext, b"")
    flags = FLAG_INITIATOR if is_initiator else FLAG_RESPONSE
    return _header(spi_i, spi_r, EXCHANGE_IKE_AUTH, flags, msgid) + ciphertext


def parse_ike_auth(
    sk_e: bytes,
    sk_pi: bytes,
    raw: bytes,
    expected_identity: bytes,
) -> IkeAuthMessage:
    """解析并校验 IKE_AUTH 报文（AEAD 解密 + HMAC-AUTH + identity 校验）。"""
    if len(raw) < HEADER_LEN + TAG_LEN:
        raise ValueError(f"invalid IKE_AUTH length: {len(raw)}")
    if raw[16] != IKE_VERSION or raw[17] != EXCHANGE_IKE_AUTH:
        raise ValueError(f"invalid IKE_AUTH header: version={raw[16]} exchange={raw[17]}")

    spi_i = int.from_bytes(raw[0:SPI_LEN], "big")
    spi_r = int.from_bytes(raw[SPI_LEN : SPI_LEN * 2], "big")
    msgid = int.from_bytes(raw[19:23], "big")
    ciphertext = raw[HEADER_LEN:]
    try:
        plaintext = ChaCha20Poly1305(sk_e).decrypt(_auth_nonce(msgid), ciphertext, b"")
    except InvalidTag as exc:
        raise ValueError("AEAD authentication failed") from exc

    if len(plaintext) < AUTH_LEN:
        raise ValueError(f"invalid IKE_AUTH plaintext length: {len(plaintext)}")
    identity = plaintext[:-AUTH_LEN]
    auth = plaintext[-AUTH_LEN:]
    expected_auth = hmac_mod.new(sk_pi, identity, hashlib.sha256).digest()
    if not hmac_mod.compare_digest(auth, expected_auth):
        raise ValueError("IKE_AUTH HMAC verification failed")
    if identity != expected_identity:
        raise ValueError(f"unexpected identity: {identity!r}")

    return IkeAuthMessage(spi_i=spi_i, spi_r=spi_r, msgid=msgid, identity=identity)
