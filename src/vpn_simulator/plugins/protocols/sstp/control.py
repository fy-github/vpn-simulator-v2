"""SSTP 控制报文格式（MS-SSTP 教学简化）。

SSTP 为 Microsoft 专有协议（MS-SSTP）。控制报文（承载于 TLS 之上）格式：:

    SSTP 控制报文: version_c(1B)=0x11 | message_type(2B,BE) | length(2B,BE) | payload

- ``version_c`` 高 4 位为版本号 1，C 位（0x01）=1 表示控制消息。
- ``length`` 为报文总长（含 5 字节头）。
- 消息类型取 MS-SSTP 值：CALL_CONNECT_REQUEST=0x0001、CALL_CONNECT_ACK=0x0002、
  CALL_CONNECT_NAK=0x0003、CALL_CONNECTED=0x0004。
- payload 教学简化为空（不携带 crypto binding 等属性）。
"""

from __future__ import annotations

from dataclasses import dataclass

CTL_CALL_CONNECT_REQUEST = 0x0001
CTL_CALL_CONNECT_ACK = 0x0002
CTL_CALL_CONNECT_NAK = 0x0003
CTL_CALL_CONNECTED = 0x0004

HEADER_LEN = 5  # version_c(1) + message_type(2) + length(2)
VERSION_C_CONTROL = 0x11
VERSION_MASK = 0xF0
C_BIT_MASK = 0x01


@dataclass(frozen=True)
class ControlMessage:
    """解析后的 SSTP 控制报文。"""

    message_type: int
    payload: bytes


def build_sstp_message(message_type: int, payload: bytes = b"") -> bytes:
    """组帧一条 SSTP 控制报文。"""
    length = HEADER_LEN + len(payload)
    return (
        bytes([VERSION_C_CONTROL])
        + message_type.to_bytes(2, "big")
        + length.to_bytes(2, "big")
        + payload
    )


def parse_sstp_message(raw: bytes) -> ControlMessage:
    """解析一条 SSTP 控制报文。"""
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid SSTP message length: {len(raw)}")
    version_c = raw[0]
    if version_c & VERSION_MASK != 0x10:
        raise ValueError(f"unsupported SSTP version: {(version_c & VERSION_MASK) >> 4}")
    if version_c & C_BIT_MASK == 0:
        raise ValueError("SSTP C bit not set (not a control message)")
    length = int.from_bytes(raw[3:5], "big")
    if length != len(raw):
        raise ValueError(f"SSTP length mismatch: {length} != {len(raw)}")
    return ControlMessage(
        message_type=int.from_bytes(raw[1:3], "big"),
        payload=raw[HEADER_LEN:],
    )


def _require(msg: ControlMessage, expected: int) -> None:
    if msg.message_type != expected:
        raise ValueError(f"unexpected SSTP message type: 0x{msg.message_type:04x}")


def parse_call_connect_request(raw: bytes) -> ControlMessage:
    msg = parse_sstp_message(raw)
    _require(msg, CTL_CALL_CONNECT_REQUEST)
    return msg


def parse_call_connect_ack(raw: bytes) -> ControlMessage:
    msg = parse_sstp_message(raw)
    _require(msg, CTL_CALL_CONNECT_ACK)
    return msg
