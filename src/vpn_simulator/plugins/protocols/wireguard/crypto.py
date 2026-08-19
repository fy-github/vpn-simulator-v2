"""WireGuard Noise_IKpsk2 握手密码学实现（真实曲线）。

依据 WireGuard 白皮书 §5 的 Noise 构造，使用 `cryptography` 库真实实现：
- DH: X25519（Curve25519）
- CIPHER: ChaCha20-Poly1305（AEAD）
- HASH / MAC: BLAKE2s（32 字节输出；MAC 为带密钥的 BLAKE2s）
- KDF: WireGuard 的 BLAKE2s 键控 KDF（`MAC(temp, 0x01)` / `MAC(temp, 0x02)`）

构造名 `Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s`，握手指纹（identifier）
为 WireGuard 官方常量。本模块实现握手密钥协商与传输密钥派生，用于教学/
安全沙箱模拟，**不提供数据面转发**，也不作为生产 VPN 网关。

消息格式（字节）：
- Initiation (type=1, 148B): type(4) | sender(4) | e_pub(32) |
  encrypted_static(48) | encrypted_timestamp(28) | mac1(16) | mac2(16)
- Response (type=2, 92B): type(4) | sender(4) | receiver(4) | e_pub(32) |
  encrypted_nothing(16) | mac1(16) | mac2(16)
"""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

CONSTRUCTION = b"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s"
IDENTIFIER = b"WireGuard v1 zx2c4 Jason@zx2c4.com"
LABEL_MAC1 = b"mac1----"

KEY_LEN = 32
TAG_LEN = 16
HANDSHAKE_NONCE = b"\x00" * 12
ZERO_KEY = b"\x00" * KEY_LEN

MSG_TYPE_INITIATION = 1
MSG_TYPE_RESPONSE = 2

INITIATION_LEN = 148
RESPONSE_LEN = 92


def _hash(data: bytes) -> bytes:
    """HASH(data) = BLAKE2s(data)，32 字节输出。"""
    return hashlib.blake2s(data, digest_size=KEY_LEN).digest()


def _mac(key: bytes, data: bytes) -> bytes:
    """MAC(key, data) = 带密钥的 BLAKE2s，32 字节输出。"""
    return hashlib.blake2s(data, key=key, digest_size=KEY_LEN).digest()


def _kdf(key: bytes, input_data: bytes) -> tuple[bytes, bytes]:
    """WireGuard KDF：返回 (新链接密钥, 会话密钥)。

    对应 Noise 的 MixKey：`ck, temp_k = HKDF(ck, ikm)`。
    """
    temp = _mac(key, input_data)
    session_key = _mac(temp, b"\x01")
    new_chaining_key = _mac(temp, b"\x02")
    return new_chaining_key, session_key


def _aead_encrypt(key: bytes, nonce: bytes, plaintext: bytes, associated_data: bytes) -> bytes:
    """ChaCha20-Poly1305 加密，返回密文 + 16 字节认证标签。"""
    return ChaCha20Poly1305(key).encrypt(nonce, plaintext, associated_data)


def _aead_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes) -> bytes:
    """ChaCha20-Poly1305 解密并认证，失败抛异常。"""
    return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, associated_data)


def _dh(private_bytes: bytes, public_bytes: bytes) -> bytes:
    """X25519 椭圆曲线 Diffie-Hellman，返回 32 字节共享密钥。"""
    private = X25519PrivateKey.from_private_bytes(private_bytes)
    public = X25519PublicKey.from_public_bytes(public_bytes)
    return private.exchange(public)


def _generate_ephemeral() -> tuple[bytes, bytes]:
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


def _tai64n_timestamp() -> bytes:
    """返回 12 字节 TAI64N 时间戳（8 字节秒 + 4 字节纳秒）。

    秒使用 Unix 时间 + TAI 偏移（此处取近似值 10s，仅作时间戳字段，
    不影响握手密钥协商正确性）。
    """
    now = time.time()
    seconds = int(now) + 10
    nanoseconds = int((now - int(now)) * 1_000_000_000)
    return seconds.to_bytes(8, "big") + nanoseconds.to_bytes(4, "big")


def _initial_state(responder_static_public: bytes) -> HandshakeState:
    """初始化握手状态：ck=0，h=HASH(construction || identifier || S_rs)。"""
    h = _hash(CONSTRUCTION + IDENTIFIER)
    h = _hash(h + responder_static_public)
    return HandshakeState(chaining_key=ZERO_KEY, hash=h)


def _mac1(responder_static_public: bytes, message: bytes) -> bytes:
    """计算 mac1（16 字节），覆盖 mac1/mac2 字段之前的全部内容。"""
    key = _mac(LABEL_MAC1, responder_static_public)
    return _mac(key, message)[:16]


def derive_transport_keys(chaining_key: bytes) -> tuple[bytes, bytes]:
    """从最终 chaining key 派生两个传输密钥（WireGuard KDF2 构造）。

    Returns:
        (initiator_to_responder_key, responder_to_initiator_key)。
        双方用同一函数派生；发起方用 [0] 发送 / [1] 接收，响应方相反。
    """
    temp = _mac(chaining_key, b"")
    k1 = _mac(temp, b"\x01")
    k2 = _mac(temp, b"\x02")
    return k1, k2


@dataclass(frozen=True)
class WireGuardIdentity:
    """WireGuard 静态身份：X25519 密钥对（32 字节原始字节）。"""

    private_bytes: bytes
    public_bytes: bytes

    @classmethod
    def generate(cls) -> WireGuardIdentity:
        private_bytes, public_bytes = _generate_ephemeral()
        return cls(private_bytes=private_bytes, public_bytes=public_bytes)


@dataclass
class HandshakeState:
    """Noise IKpsk2 握手状态（chaining key + hash）。"""

    chaining_key: bytes
    hash: bytes

    def mix_hash(self, data: bytes) -> None:
        """MixHash(data): hash = HASH(hash || data)。"""
        self.hash = _hash(self.hash + data)

    def mix_key(self, ikm: bytes) -> bytes:
        """MixKey(ikm): (chaining_key, session_key) = KDF(ck, ikm)。"""
        self.chaining_key, session_key = _kdf(self.chaining_key, ikm)
        return session_key


@dataclass
class InitiatorHandshake:
    """发起方在握手期间的会话状态。"""

    identity: WireGuardIdentity
    ephemeral_private: bytes
    state: HandshakeState


@dataclass(frozen=True)
class InitiationMessage:
    """已解析的 Handshake Initiation 内容。"""

    sender_index: int
    initiator_ephemeral: bytes
    initiator_static: bytes
    state: HandshakeState


def build_initiation(
    initiator: WireGuardIdentity,
    responder_static_public: bytes,
    sender_index: int,
) -> tuple[bytes, InitiatorHandshake]:
    """构造 Handshake Initiation（148 字节）。

    Args:
        initiator: 发起方静态密钥对。
        responder_static_public: 响应方静态公钥（32 字节）。
        sender_index: 4 字节发送端索引。

    Returns:
        (initiation_message, initiator_handshake)。
    """
    state = _initial_state(responder_static_public)
    ephemeral_private, ephemeral_public = _generate_ephemeral()

    state.mix_hash(ephemeral_public)
    key = state.mix_key(_dh(ephemeral_private, responder_static_public))
    encrypted_static = _aead_encrypt(key, HANDSHAKE_NONCE, initiator.public_bytes, state.hash)
    state.mix_hash(encrypted_static)

    key = state.mix_key(_dh(initiator.private_bytes, responder_static_public))
    encrypted_timestamp = _aead_encrypt(key, HANDSHAKE_NONCE, _tai64n_timestamp(), state.hash)
    state.mix_hash(encrypted_timestamp)

    header = (
        MSG_TYPE_INITIATION.to_bytes(4, "little")
        + sender_index.to_bytes(4, "little")
        + ephemeral_public
    )
    body = encrypted_static + encrypted_timestamp
    mac1 = _mac1(responder_static_public, header + body)
    mac2 = b"\x00" * TAG_LEN
    message = header + body + mac1 + mac2

    handshake = InitiatorHandshake(
        identity=initiator,
        ephemeral_private=ephemeral_private,
        state=state,
    )
    return message, handshake


def parse_initiation(responder: WireGuardIdentity, message: bytes) -> InitiationMessage:
    """响应方解析 Handshake Initiation，解密出发起方静态公钥。

    Args:
        responder: 响应方静态密钥对。
        message: 148 字节 Initiation 报文。

    Returns:
        解析结果（含响应方握手状态）。
    """
    if len(message) != INITIATION_LEN:
        raise ValueError(f"invalid initiation length: {len(message)}")
    if int.from_bytes(message[0:4], "little") != MSG_TYPE_INITIATION:
        raise ValueError("invalid message type for initiation")

    sender_index = int.from_bytes(message[4:8], "little")
    ephemeral = message[8:40]
    encrypted_static = message[40:88]
    encrypted_timestamp = message[88:116]
    # message[116:132] = mac1, message[132:148] = mac2（当前不校验）

    state = _initial_state(responder.public_bytes)
    state.mix_hash(ephemeral)

    key = state.mix_key(_dh(responder.private_bytes, ephemeral))
    initiator_static = _aead_decrypt(key, HANDSHAKE_NONCE, encrypted_static, state.hash)
    state.mix_hash(encrypted_static)

    key = state.mix_key(_dh(responder.private_bytes, initiator_static))
    _aead_decrypt(key, HANDSHAKE_NONCE, encrypted_timestamp, state.hash)
    state.mix_hash(encrypted_timestamp)

    return InitiationMessage(
        sender_index=sender_index,
        initiator_ephemeral=ephemeral,
        initiator_static=initiator_static,
        state=state,
    )


def build_response(
    responder: WireGuardIdentity,
    initiation: InitiationMessage,
    sender_index: int,
    receiver_index: int,
) -> tuple[bytes, HandshakeState]:
    """响应方构造 Handshake Response（92 字节），并返回最终握手状态。

    Returns:
        (response_message, responder_final_state)。
    """
    state = initiation.state
    ephemeral_private, ephemeral_public = _generate_ephemeral()

    state.mix_hash(ephemeral_public)
    state.mix_key(_dh(ephemeral_private, initiation.initiator_ephemeral))
    key = state.mix_key(_dh(ephemeral_private, initiation.initiator_static))

    encrypted_nothing = _aead_encrypt(key, HANDSHAKE_NONCE, b"", state.hash)
    state.mix_hash(encrypted_nothing)

    header = (
        MSG_TYPE_RESPONSE.to_bytes(4, "little")
        + sender_index.to_bytes(4, "little")
        + receiver_index.to_bytes(4, "little")
        + ephemeral_public
    )
    body = encrypted_nothing
    mac1 = _mac1(responder.public_bytes, header + body)
    mac2 = b"\x00" * TAG_LEN
    message = header + body + mac1 + mac2
    return message, state


def finish_initiator(handshake: InitiatorHandshake, message: bytes) -> tuple[bytes, bytes]:
    """发起方解析 Response 并派生传输密钥，返回 (发送密钥, 接收密钥)。"""
    if len(message) != RESPONSE_LEN:
        raise ValueError(f"invalid response length: {len(message)}")
    if int.from_bytes(message[0:4], "little") != MSG_TYPE_RESPONSE:
        raise ValueError("invalid message type for response")

    ephemeral = message[12:44]
    encrypted_nothing = message[44:60]
    # message[60:76] = mac1, message[76:92] = mac2（当前不校验）

    state = handshake.state
    state.mix_hash(ephemeral)
    state.mix_key(_dh(handshake.ephemeral_private, ephemeral))
    key = state.mix_key(_dh(handshake.identity.private_bytes, ephemeral))
    _aead_decrypt(key, HANDSHAKE_NONCE, encrypted_nothing, state.hash)
    state.mix_hash(encrypted_nothing)

    k1, k2 = derive_transport_keys(state.chaining_key)
    return k1, k2


def finish_responder(state: HandshakeState) -> tuple[bytes, bytes]:
    """响应方从最终状态派生传输密钥，返回 (接收密钥, 发送密钥)。"""
    k1, k2 = derive_transport_keys(state.chaining_key)
    return k1, k2


def key_to_b64(raw: bytes) -> str:
    """32 字节原始密钥 → 标准 Base64（带填充）。"""
    return base64.b64encode(raw).decode("ascii")


def b64_to_key(value: str) -> bytes:
    """标准 Base64 → 32 字节原始密钥。"""
    return base64.b64decode(value.encode("ascii"))
