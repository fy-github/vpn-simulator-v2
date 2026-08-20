"""OpenVPN 数据信道报文格式与 AES-256-GCM 加解密。

OpenVPN 控制信道（Hard Reset + TLS，见 `control_channel.py` 与 `tls.py`）建立后，
数据信道用对称加密传输真实载荷。本模块实现：

- 数据密钥：由 `services/openvpn_handshake.py` 在真实 TLS 加密信道内交换（本环境
  Python ssl 未暴露 ``export_keying_material``，见 `tls.py`），以 ``OpenVPNDataSession``
  的 ``data_key`` 注入，双向对称。
- 报文格式（P_DATA_V2 教学版）：::

    opcode(1, =9) | peer_id(8, BE) | packet_id(4, BE) | ciphertext+tag

- AEAD：AES-256-GCM，nonce = ``packet_id(4, BE) || 0x0000000000000000``（12 字节）。
- 关联数据（AD）为空；密文尾部附 16 字节认证标签。
- ``peer_id`` 为接收方 session_id；``packet_id`` 每方向单调递增，用于重放防护。

socket 往返编排见 `services/openvpn_transport.py`。
"""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from vpn_simulator.plugins.protocols.openvpn.control_channel import (
    P_DATA_V2,
    SESSION_ID_LEN,
)

PACKET_ID_LEN = 4
TAG_LEN = 16
DATA_KEY_LEN = 32
DATA_HEADER_LEN = 1 + SESSION_ID_LEN + PACKET_ID_LEN  # opcode + peer_id + packet_id


def _nonce(packet_id: int) -> bytes:
    """数据信道 nonce：packet_id（4 字节大端）后补 8 个零字节。"""
    return packet_id.to_bytes(PACKET_ID_LEN, "big") + b"\x00" * 8


def build_data_packet(
    data_key: bytes,
    peer_id: int,
    packet_id: int,
    plaintext: bytes,
) -> bytes:
    """加密并组帧一条数据信道报文。

    Args:
        data_key: 数据密钥（32 字节）。
        peer_id: 接收方 session_id（8 字节无符号整数）。
        packet_id: 32 位大端计数器（每报文递增，不可复用）。
        plaintext: 待封装明文。

    Returns:
        完整数据报文字节。
    """
    ciphertext = AESGCM(data_key).encrypt(_nonce(packet_id), plaintext, b"")
    return (
        P_DATA_V2.to_bytes(1, "big")
        + peer_id.to_bytes(SESSION_ID_LEN, "big")
        + packet_id.to_bytes(PACKET_ID_LEN, "big")
        + ciphertext
    )


def parse_data_packet(data_key: bytes, raw: bytes) -> tuple[int, int, bytes]:
    """解帧并解密一条数据信道报文。

    Returns:
        ``(peer_id, packet_id, plaintext)``。

    Raises:
        ValueError: 长度不足、类型不符、或 AEAD 认证失败（密钥不符/密文被篡改）。
    """
    if len(raw) < DATA_HEADER_LEN + TAG_LEN:
        raise ValueError(f"invalid data packet length: {len(raw)}")
    if raw[0] != P_DATA_V2:
        raise ValueError(f"invalid data packet opcode: {raw[0]}")

    peer_id = int.from_bytes(raw[1 : 1 + SESSION_ID_LEN], "big")
    packet_id = int.from_bytes(raw[1 + SESSION_ID_LEN : 1 + SESSION_ID_LEN + PACKET_ID_LEN], "big")
    ciphertext = raw[1 + SESSION_ID_LEN + PACKET_ID_LEN :]
    try:
        plaintext = AESGCM(data_key).decrypt(_nonce(packet_id), ciphertext, b"")
    except InvalidTag as exc:
        raise ValueError("AEAD authentication failed") from exc
    return peer_id, packet_id, plaintext


@dataclass
class OpenVPNDataSession:
    """一侧的 OpenVPN 数据信道会话：持有数据密钥与计数器。

    Attributes:
        data_key: 数据密钥（32 字节，双向对称）。
        send_packet_id: 下一次发送要用的 packet_id（seal 时递增）。
        highest_recv_packet_id: 已见最大接收 packet_id（重放防护）。
    """

    data_key: bytes
    send_packet_id: int = 0
    highest_recv_packet_id: int = -1

    def seal(self, peer_id: int, plaintext: bytes) -> bytes:
        """加密一条数据报文并推进发送 packet_id。"""
        packet = build_data_packet(self.data_key, peer_id, self.send_packet_id, plaintext)
        self.send_packet_id += 1
        return packet

    def open(self, raw: bytes) -> tuple[int, bytes]:
        """解密一条数据报文并做重放防护，返回 ``(peer_id, plaintext)``。

        Raises:
            ValueError: 解密失败，或 ``packet_id <= highest_recv_packet_id``（重放）。
        """
        peer_id, packet_id, plaintext = parse_data_packet(self.data_key, raw)
        if packet_id <= self.highest_recv_packet_id:
            raise ValueError(
                f"replay detected: packet_id {packet_id} <= {self.highest_recv_packet_id}"
            )
        self.highest_recv_packet_id = packet_id
        return peer_id, plaintext
