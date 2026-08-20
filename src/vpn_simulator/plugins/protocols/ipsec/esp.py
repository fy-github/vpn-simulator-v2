"""IPsec ESP 数据面报文与 AES-256-GCM 加解密（RFC 4303 教学简化）。

在 IKE 控制面握手建立后，ESP（Encapsulating Security Payload）用对称加密传输
真实数据载荷。本模块实现：

- 报文格式（RFC 4303 教学简化）：::

      ESP 报文: SPI(4,BE) | Sequence Number(4,BE) | ciphertext+tag(AES-256-GCM)

- AEAD：AES-256-GCM，nonce = ``seq(4,BE) || 0x00*8``（12 字节），关联数据
  AD = ``SPI(4) || seq(4)``（8 字节）。密文尾部附 16 字节认证标签。
- 加密明文为原始 payload（教学简化，不含显式 padding / next-header）。
- 重放防护：``seq <= highest_recv_seq`` 拒绝。

socket 往返编排见 `services/esp_transport.py`。
"""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SPI_LEN = 4
SEQ_LEN = 4
TAG_LEN = 16
ESP_HEADER_LEN = SPI_LEN + SEQ_LEN  # 8


def _nonce(seq: int) -> bytes:
    return seq.to_bytes(SEQ_LEN, "big") + b"\x00" * 8


def _aad(spi: int, seq: int) -> bytes:
    return spi.to_bytes(SPI_LEN, "big") + seq.to_bytes(SEQ_LEN, "big")


def build_esp_packet(spi: int, seq: int, key: bytes, plaintext: bytes) -> bytes:
    """加密并组帧一条 ESP 报文。"""
    ciphertext = AESGCM(key).encrypt(_nonce(seq), plaintext, _aad(spi, seq))
    return spi.to_bytes(SPI_LEN, "big") + seq.to_bytes(SEQ_LEN, "big") + ciphertext


def parse_esp_packet(key: bytes, raw: bytes) -> tuple[int, int, bytes]:
    """解帧并解密一条 ESP 报文，返回 ``(spi, seq, plaintext)``。

    Raises:
        ValueError: 长度不足，或 AEAD 认证失败（密钥不符/密文被篡改）。
    """
    if len(raw) < ESP_HEADER_LEN + TAG_LEN:
        raise ValueError(f"invalid ESP packet length: {len(raw)}")
    spi = int.from_bytes(raw[0:SPI_LEN], "big")
    seq = int.from_bytes(raw[SPI_LEN:ESP_HEADER_LEN], "big")
    ciphertext = raw[ESP_HEADER_LEN:]
    try:
        plaintext = AESGCM(key).decrypt(_nonce(seq), ciphertext, _aad(spi, seq))
    except InvalidTag as exc:
        raise ValueError("ESP AEAD authentication failed") from exc
    return spi, seq, plaintext


@dataclass
class ESPSession:
    """一侧的 ESP 会话：持有密钥与计数器。

    Attributes:
        key: ESP 密钥（32 字节）。
        send_seq: 下一次发送要用的 sequence number（seal 时递增）。
        highest_recv_seq: 已见最大接收 sequence number（重放防护）。
    """

    key: bytes
    send_seq: int = 0
    highest_recv_seq: int = -1

    def seal(self, peer_spi: int, plaintext: bytes) -> bytes:
        """加密一条 ESP 报文并推进发送 seq。"""
        packet = build_esp_packet(peer_spi, self.send_seq, self.key, plaintext)
        self.send_seq += 1
        return packet

    def open(self, raw: bytes) -> tuple[int, bytes]:
        """解密一条 ESP 报文并做重放防护，返回 ``(spi, plaintext)``。"""
        spi, seq, plaintext = parse_esp_packet(self.key, raw)
        if seq <= self.highest_recv_seq:
            raise ValueError(f"ESP replay detected: seq {seq} <= {self.highest_recv_seq}")
        self.highest_recv_seq = seq
        return spi, plaintext
