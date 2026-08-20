"""MPPE 密钥派生与 RC4 数据面加密（RFC 3078 / RFC 3079）。

MS-CHAPv2 认证（见 ``mschapv2.py``）后，PPTP / L2TP+MPPE 按 RFC 3079 派生会话密钥，
用 RC4 加密 PPP 数据面。本模块实现 128-bit 密钥派生与 RC4 加解密：

- 密钥派生（RFC 3079 §3.2/§3.4，MS-CHAPv2 对称）：

  ``MasterKey = SHA1( MD4(NT-Hash) | NTResponse | "This is the MPPE Master Key" )[0:16]``
  ``SendSessionKey = ReceiveSessionKey = SHA1(MasterKey | 0x00*40 | MasterKey | 0xf2*40)[0:16]``

- 加密：RC4（``cryptography`` 的 decrepit ``ARC4``），每次报文用新 RC4 实例（教学简化：
  真实 MPPE 跨报文维护连续 RC4 状态，此处按报文重置并靠 coherency_count 做乱序/重放检测）。
- 报文：``coherency_count(2, BE) | RC4(session_key, plaintext)``。
"""

from __future__ import annotations

import hashlib
import warnings

from cryptography.hazmat.decrepit.ciphers.algorithms import ARC4
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.utils import CryptographyDeprecationWarning

from vpn_simulator.plugins.protocols.ppp.mschapv2 import md4

MPPE_MASTER_KEY_LABEL = b"This is the MPPE Master Key"
SESSION_KEY_LEN = 16
COHERENCY_COUNT_LEN = 2


def derive_session_keys(password_hash: bytes, nt_response: bytes) -> tuple[bytes, bytes]:
    """按 RFC 3079 派生 128-bit MPPE 会话密钥，返回 ``(send, receive)``。

    Args:
        password_hash: 16 字节 NT-Hash（``compute_nt_hash`` 输出）。
        nt_response: 24 字节 MS-CHAPv2 挑战响应（``compute_challenge_response`` 输出）。

    Returns:
        两个 16 字节会话密钥；MS-CHAPv2 对称，二者相等。
    """
    if len(password_hash) != 16 or len(nt_response) != 24:
        raise ValueError("password_hash must be 16 bytes and nt_response 24 bytes")
    password_hash_hash = md4(password_hash)
    master = hashlib.sha1(password_hash_hash + nt_response + MPPE_MASTER_KEY_LABEL).digest()[
        :SESSION_KEY_LEN
    ]
    session = hashlib.sha1(master + b"\x00" * 40 + master + b"\xf2" * 40).digest()[:SESSION_KEY_LEN]
    return session, session


def rc4_crypt(key: bytes, data: bytes) -> bytes:
    """RC4 加解密（流加密自反，同一函数加/解密）。"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", CryptographyDeprecationWarning)
        cipher = Cipher(ARC4(key), mode=None)
    return cipher.decryptor().update(data)


class MPPESession:
    """一侧 MPPE 会话：持有发送/接收密钥与 coherency_count，加/解密数据报文。"""

    def __init__(self, send_key: bytes, recv_key: bytes) -> None:
        self._send_key = send_key
        self._recv_key = recv_key
        self._send_count = 0
        self._highest_recv_count = -1

    def encrypt(self, plaintext: bytes) -> bytes:
        """加密一段明文，返回 ``coherency_count | RC4(plaintext)``。"""
        packet = self._send_count.to_bytes(COHERENCY_COUNT_LEN, "big") + rc4_crypt(
            self._send_key, plaintext
        )
        self._send_count += 1
        return packet

    def decrypt(self, raw: bytes) -> bytes:
        """解密一段报文，做 coherency_count 重放/乱序检测，返回明文。

        Raises:
            ValueError: 长度不足或 coherency_count 不递增（重放/乱序）。
        """
        if len(raw) < COHERENCY_COUNT_LEN:
            raise ValueError(f"invalid MPPE packet length: {len(raw)}")
        count = int.from_bytes(raw[:COHERENCY_COUNT_LEN], "big")
        if count <= self._highest_recv_count:
            raise ValueError(f"MPPE replay detected: {count} <= {self._highest_recv_count}")
        self._highest_recv_count = count
        return rc4_crypt(self._recv_key, raw[COHERENCY_COUNT_LEN:])
