"""WireGuard 数据面（transport）报文格式与 ChaCha20-Poly1305 加解密。

WireGuard 握手（Noise_IKpsk2）完成后，双方各派生一对传输密钥（见
`crypto.derive_transport_keys`）。本模块用这对密钥真实加解密**数据面**报文：

- 报文格式（WireGuard 白皮书 §5.4.4）：::

    type(4, LE) | receiver_index(4, LE) | counter(8, LE) | ciphertext+tag

- AEAD：ChaCha20-Poly1305，nonce = ``counter(8, LE) || 0x00000000``（12 字节）。
- 关联数据（AD）为空；密文尾部附 16 字节认证标签。
- 重放防护：接收方拒绝 ``counter <= 已见最大 counter``（单调递增简化，滑动位图
  窗口留作后续增强）。

本模块只做单条数据报文的加解密与格式，真正的 socket 往返编排见
`services/wireguard_transport.py`。
"""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

MSG_TYPE_DATA = 4

DATA_HEADER_LEN = 16  # type(4) + receiver_index(4) + counter(8)
TAG_LEN = 16


def _nonce(counter: int) -> bytes:
    """数据面 nonce：counter（8 字节小端）后补 4 个零字节。"""
    return counter.to_bytes(8, "little") + b"\x00\x00\x00\x00"


def build_data_packet(
    send_key: bytes,
    receiver_index: int,
    counter: int,
    plaintext: bytes,
) -> bytes:
    """加密并组帧一条数据面报文。

    Args:
        send_key: 发送方向传输密钥（32 字节）。
        receiver_index: 对端分配的接收索引（4 字节无符号整数）。
        counter: 64 位小端计数器（每报文递增，不可复用）。
        plaintext: 待封装的数据面明文。

    Returns:
        完整数据报文字节。
    """
    ciphertext = ChaCha20Poly1305(send_key).encrypt(_nonce(counter), plaintext, b"")
    return (
        MSG_TYPE_DATA.to_bytes(4, "little")
        + receiver_index.to_bytes(4, "little")
        + counter.to_bytes(8, "little")
        + ciphertext
    )


def parse_data_packet(recv_key: bytes, raw: bytes) -> tuple[int, int, bytes]:
    """解帧并解密一条数据面报文。

    Args:
        recv_key: 接收方向传输密钥（32 字节）。
        raw: 完整数据报文字节。

    Returns:
        ``(receiver_index, counter, plaintext)``。

    Raises:
        ValueError: 长度不足、类型不符、或 AEAD 认证失败（密钥不符/密文被篡改）。
    """
    if len(raw) < DATA_HEADER_LEN + TAG_LEN:
        raise ValueError(f"invalid data packet length: {len(raw)}")
    if int.from_bytes(raw[0:4], "little") != MSG_TYPE_DATA:
        raise ValueError(f"invalid data packet type: {int.from_bytes(raw[0:4], 'little')}")

    receiver_index = int.from_bytes(raw[4:8], "little")
    counter = int.from_bytes(raw[8:16], "little")
    ciphertext = raw[16:]
    try:
        plaintext = ChaCha20Poly1305(recv_key).decrypt(_nonce(counter), ciphertext, b"")
    except InvalidTag as exc:
        raise ValueError("AEAD authentication failed") from exc
    return receiver_index, counter, plaintext


@dataclass
class WireGuardTransportSession:
    """一侧的 WireGuard 数据面会话：持有传输密钥与计数器。

    Attributes:
        send_key: 发送方向传输密钥（本地→对端）。
        recv_key: 接收方向传输密钥（对端→本地）。
        send_counter: 下一次发送要用的计数器（seal 时递增）。
        highest_recv_counter: 已见最大接收计数器（重放防护）。
    """

    send_key: bytes
    recv_key: bytes
    send_counter: int = 0
    highest_recv_counter: int = -1

    def seal(self, receiver_index: int, plaintext: bytes) -> bytes:
        """加密一条数据报文并推进发送计数器。"""
        packet = build_data_packet(self.send_key, receiver_index, self.send_counter, plaintext)
        self.send_counter += 1
        return packet

    def open(self, raw: bytes) -> tuple[int, bytes]:
        """解密一条数据报文并做重放防护，返回 ``(receiver_index, plaintext)``。

        Raises:
            ValueError: 解密失败，或 ``counter <= highest_recv_counter``（重放）。
        """
        receiver_index, counter, plaintext = parse_data_packet(self.recv_key, raw)
        if counter <= self.highest_recv_counter:
            raise ValueError(f"replay detected: counter {counter} <= {self.highest_recv_counter}")
        self.highest_recv_counter = counter
        return receiver_index, plaintext
