"""PPTP 控制信道报文格式（RFC 2637 教学简化）。

PPTP 控制信道走 TCP 1723，为明文（PPTP 本身无加密，认证在 PPP 层 MS-CHAPv2）。
本模块实现控制面握手报文 framing：::

    控制报文: length(2,BE) | message_type(2,BE)=1 | magic_cookie(4,BE)=0x1A2B3C4D
              | control_type(2,BE) | reserved(2)=0 | body
    SCCRQ(1) body: protocol_version(2)=0x0100
    SCCRP(2) body: protocol_version(2) | result_code(1)=1 | error_code(1)=0
    OCRQ(7)  body: call_id(2,BE) | call_serial(2,BE)
    OCRP(8)  body: call_id(2,BE) | peer_call_id(2,BE) | result_code(1)=1

消息类型取 RFC 2637 值：SCCRQ=1、SCCRP=2、OCRQ=7、OCRP=8。
"""

from __future__ import annotations

from dataclasses import dataclass

MAGIC_COOKIE = 0x1A2B3C4D
MSG_CONTROL = 1
CTL_SCCRQ = 1
CTL_SCCRP = 2
CTL_OCRQ = 7
CTL_OCRP = 8

HEADER_LEN = 2 + 2 + 4 + 2 + 2  # 12


@dataclass(frozen=True)
class ControlMessage:
    """解析后的 PPTP 控制报文。"""

    control_type: int
    body: bytes


def build_control_message(control_type: int, body: bytes = b"") -> bytes:
    """组帧一条 PPTP 控制报文。"""
    length = HEADER_LEN + len(body)
    return (
        length.to_bytes(2, "big")
        + MSG_CONTROL.to_bytes(2, "big")
        + MAGIC_COOKIE.to_bytes(4, "big")
        + control_type.to_bytes(2, "big")
        + b"\x00\x00"
        + body
    )


def parse_control_message(raw: bytes) -> ControlMessage:
    """解析一条 PPTP 控制报文。"""
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid PPTP message length: {len(raw)}")
    length = int.from_bytes(raw[0:2], "big")
    if length != len(raw):
        raise ValueError(f"PPTP length mismatch: {length} != {len(raw)}")
    if int.from_bytes(raw[2:4], "big") != MSG_CONTROL:
        raise ValueError(f"invalid PPTP message type: {int.from_bytes(raw[2:4], 'big')}")
    if int.from_bytes(raw[4:8], "big") != MAGIC_COOKIE:
        raise ValueError("invalid PPTP magic cookie")
    return ControlMessage(
        control_type=int.from_bytes(raw[8:10], "big"),
        body=raw[HEADER_LEN:],
    )


def _require(msg: ControlMessage, expected: int) -> None:
    if msg.control_type != expected:
        raise ValueError(f"unexpected control type: {msg.control_type} (expected {expected})")


def build_sccrq() -> bytes:
    """SCCRQ：Protocol Version 1.0。"""
    return build_control_message(CTL_SCCRQ, b"\x01\x00")


def parse_sccrq(raw: bytes) -> ControlMessage:
    msg = parse_control_message(raw)
    _require(msg, CTL_SCCRQ)
    return msg


def build_sccrp() -> bytes:
    """SCCRP：Protocol Version 1.0 + result_code=1（成功）+ error_code=0。"""
    return build_control_message(CTL_SCCRP, b"\x01\x00\x01\x00")


def parse_sccrp(raw: bytes) -> ControlMessage:
    msg = parse_control_message(raw)
    _require(msg, CTL_SCCRP)
    if len(msg.body) < 4 or msg.body[2] != 1:
        raise ValueError("SCCRP result code is not success")
    return msg


def build_ocrq(call_id: int, call_serial: int) -> bytes:
    """OCRQ：Call ID + Call Serial Number。"""
    return build_control_message(
        CTL_OCRQ, call_id.to_bytes(2, "big") + call_serial.to_bytes(2, "big")
    )


def parse_ocrq(raw: bytes) -> tuple[ControlMessage, int, int]:
    msg = parse_control_message(raw)
    _require(msg, CTL_OCRQ)
    if len(msg.body) != 4:
        raise ValueError(f"invalid OCRQ body length: {len(msg.body)}")
    return msg, int.from_bytes(msg.body[0:2], "big"), int.from_bytes(msg.body[2:4], "big")


def build_ocrp(call_id: int, peer_call_id: int) -> bytes:
    """OCRP：Call ID + Peer Call ID + result_code=1（已连接）。"""
    return build_control_message(
        CTL_OCRP, call_id.to_bytes(2, "big") + peer_call_id.to_bytes(2, "big") + b"\x01\x00"
    )


def parse_ocrp(raw: bytes) -> tuple[ControlMessage, int, int]:
    msg = parse_control_message(raw)
    _require(msg, CTL_OCRP)
    if len(msg.body) < 5 or msg.body[4] != 1:
        raise ValueError("OCRP result code is not connected")
    return msg, int.from_bytes(msg.body[0:2], "big"), int.from_bytes(msg.body[2:4], "big")
