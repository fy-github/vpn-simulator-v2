"""PPP MS-CHAPv2 挑战-响应认证（RFC 2759，真实密码学）。

PPTP/L2TP（及 SSTP/OpenConnect 承载的 PPP）最常见认证。算法：

```
NtPasswordHash = MD4( UTF-16LE(password) )                        # 16 字节
Challenge      = SHA1( PeerChallenge(16) + ServerChallenge(16) + Username )[0:8]
ChallengeResponse = DES(NtHash[0:7], Challenge) || DES(NtHash[7:14], Challenge)
                    || DES(NtHash[14:16] + 5×0, Challenge)         # 24 字节
```

7 字节 DES key 展开为 8 字节（每 7 位插 1 位奇校验）。3 段 DES 加密同一 8 字节
Challenge（非 3DES 链式）。校验用常量时间比较。
"""

from __future__ import annotations

import hmac
import os
import struct
import warnings

from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.utils import CryptographyDeprecationWarning

NT_HASH_LEN = 16
CHALLENGE_LEN = 16
RESPONSE_LEN = 24

# MD4 轮常量（第 2/3 轮各加一个加法常量，RFC 1320 第 3.4 节）
_MD4_ROUND2_CONST = 0x5A827999
_MD4_ROUND3_CONST = 0x6ED9EBA1


def md4(data: bytes) -> bytes:
    """MD4 摘要（RFC 1320）。

    ``cryptography`` 42+ 移除了 MD4，而 NT 口令散列必需 MD4，故按 RFC 1320 自实现。
    返回 16 字节摘要。
    """

    def _f(x: int, y: int, z: int) -> int:
        return (x & y) | (~x & z)

    def _g(x: int, y: int, z: int) -> int:
        return (x & y) | (x & z) | (y & z)

    def _h(x: int, y: int, z: int) -> int:
        return x ^ y ^ z

    def _rotl(x: int, n: int) -> int:
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    msg = bytearray(data)
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", len(data) * 8)

    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476

    round1 = [
        (0, 3),
        (1, 7),
        (2, 11),
        (3, 19),
        (4, 3),
        (5, 7),
        (6, 11),
        (7, 19),
        (8, 3),
        (9, 7),
        (10, 11),
        (11, 19),
        (12, 3),
        (13, 7),
        (14, 11),
        (15, 19),
    ]
    round2 = [
        (0, 3),
        (4, 5),
        (8, 9),
        (12, 13),
        (1, 3),
        (5, 5),
        (9, 9),
        (13, 13),
        (2, 3),
        (6, 5),
        (10, 9),
        (14, 13),
        (3, 3),
        (7, 5),
        (11, 9),
        (15, 13),
    ]
    round3 = [
        (0, 3),
        (8, 9),
        (4, 11),
        (12, 15),
        (2, 3),
        (10, 9),
        (6, 11),
        (14, 15),
        (1, 3),
        (9, 9),
        (5, 11),
        (13, 15),
        (3, 3),
        (11, 9),
        (7, 11),
        (15, 15),
    ]

    # MD4 轮常量（第 2/3 轮各加一个加法常量，RFC 1320 第 3.4 节）
    for off in range(0, len(msg), 64):
        x = list(struct.unpack("<16I", bytes(msg[off : off + 64])))
        aa, bb, cc, dd = a, b, c, d

        for k, s in round1:
            a = _rotl((a + _f(b, c, d) + x[k]) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c
        for k, s in round2:
            a = _rotl((a + _g(b, c, d) + x[k] + _MD4_ROUND2_CONST) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c
        for k, s in round3:
            a = _rotl((a + _h(b, c, d) + x[k] + _MD4_ROUND3_CONST) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c

        a = (a + aa) & 0xFFFFFFFF
        b = (b + bb) & 0xFFFFFFFF
        c = (c + cc) & 0xFFFFFFFF
        d = (d + dd) & 0xFFFFFFFF

    return struct.pack("<4I", a, b, c, d)


def generate_challenge() -> bytes:
    """生成 16 字节挑战（服务端 / 对端各一个）。"""
    return os.urandom(CHALLENGE_LEN)


def compute_nt_hash(password: str) -> bytes:
    """NT 口令散列 = MD4(UTF-16LE(password))。"""
    return md4(password.encode("utf-16-le"))


def compute_challenge(
    peer_challenge: bytes,
    server_challenge: bytes,
    username: str,
) -> bytes:
    """8 字节 Challenge = SHA1(peer + server + username)[0:8]。"""
    digest = hashes.Hash(hashes.SHA1())
    digest.update(peer_challenge + server_challenge + username.encode())
    return digest.finalize()[:8]


def _expand_des_key(key7: bytes) -> bytes:
    """7 字节 DES key → 8 字节（每 7 位插 1 位奇校验位）。"""
    bits = "".join(f"{b:08b}" for b in key7)
    out = bytearray(8)
    for i in range(8):
        chunk = bits[i * 7 : (i + 1) * 7]
        parity = "1" if chunk.count("1") % 2 == 0 else "0"
        out[i] = int(chunk + parity, 2)
    return bytes(out)


def _des_encrypt(key7: bytes, data8: bytes) -> bytes:
    """单次 DES 加密（7 字节 key 展开奇校验 + ECB）。

    MS-CHAPv2 规范要求单 DES（3 段各自独立加密同一 8 字节 Challenge），
    故显式使用 8 字节单 DES key 并抑制单 DES 弃用告警。
    """
    key8 = _expand_des_key(key7)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", CryptographyDeprecationWarning)
        encryptor = Cipher(TripleDES(key8), modes.ECB()).encryptor()
        return encryptor.update(data8) + encryptor.finalize()


def compute_challenge_response(
    nt_hash: bytes,
    peer_challenge: bytes,
    server_challenge: bytes,
    username: str,
) -> bytes:
    """24 字节 ChallengeResponse = 3×DES(同一 Challenge)。"""
    if len(nt_hash) != NT_HASH_LEN:
        raise ValueError("NT hash must be 16 bytes")
    challenge = compute_challenge(peer_challenge, server_challenge, username)
    key1 = nt_hash[0:7]
    key2 = nt_hash[7:14]
    key3 = nt_hash[14:16] + b"\x00" * 5
    return (
        _des_encrypt(key1, challenge)
        + _des_encrypt(key2, challenge)
        + _des_encrypt(key3, challenge)
    )


def verify_challenge_response(
    password: str,
    username: str,
    peer_challenge: bytes,
    server_challenge: bytes,
    response: bytes,
) -> bool:
    """校验 MS-CHAPv2 挑战-响应（常量时间比较）。"""
    expected = compute_challenge_response(
        compute_nt_hash(password), peer_challenge, server_challenge, username
    )
    return hmac.compare_digest(expected, response)
