"""WireGuard 报文 wire 格式（scapy 层定义）。

用 scapy 定义 Handshake Initiation / Response 的报文结构，提供结构化
解析（字段级访问）与构造能力。密码学操作仍在 `crypto` 模块中进行，
本模块只负责"报文长什么样"。

字段布局（小端）：
- Initiation (148B): msg_type(4) | sender(4) | ephemeral(32) |
  encrypted_static(48) | encrypted_timestamp(28) | mac1(16) | mac2(16)
- Response (92B): msg_type(4) | sender(4) | receiver(4) | ephemeral(32) |
  encrypted_nothing(16) | mac1(16) | mac2(16)
"""

from __future__ import annotations

from scapy.fields import LEIntField, XStrFixedLenField
from scapy.packet import Packet

from vpn_simulator.plugins.protocols.wireguard.crypto import (
    MSG_TYPE_INITIATION,
    MSG_TYPE_RESPONSE,
)


class WireGuardInitiation(Packet):
    """WireGuard Handshake Initiation（148 字节）。"""

    name = "WireGuard Handshake Initiation"
    fields_desc = [
        LEIntField("msg_type", MSG_TYPE_INITIATION),
        LEIntField("sender_index", 0),
        XStrFixedLenField("ephemeral", b"\x00" * 32, length=32),
        XStrFixedLenField("encrypted_static", b"\x00" * 48, length=48),
        XStrFixedLenField("encrypted_timestamp", b"\x00" * 28, length=28),
        XStrFixedLenField("mac1", b"\x00" * 16, length=16),
        XStrFixedLenField("mac2", b"\x00" * 16, length=16),
    ]


class WireGuardResponse(Packet):
    """WireGuard Handshake Response（92 字节）。"""

    name = "WireGuard Handshake Response"
    fields_desc = [
        LEIntField("msg_type", MSG_TYPE_RESPONSE),
        LEIntField("sender_index", 0),
        LEIntField("receiver_index", 0),
        XStrFixedLenField("ephemeral", b"\x00" * 32, length=32),
        XStrFixedLenField("encrypted_nothing", b"\x00" * 16, length=16),
        XStrFixedLenField("mac1", b"\x00" * 16, length=16),
        XStrFixedLenField("mac2", b"\x00" * 16, length=16),
    ]


def parse_wireguard_message(data: bytes) -> WireGuardInitiation | WireGuardResponse:
    """按 msg_type 将 WireGuard 报文解析为 scapy 包结构。"""
    msg_type = int.from_bytes(data[0:4], "little")
    if msg_type == MSG_TYPE_INITIATION:
        return WireGuardInitiation(data)
    if msg_type == MSG_TYPE_RESPONSE:
        return WireGuardResponse(data)
    raise ValueError(f"unknown WireGuard message type: {msg_type}")
