"""L2TP 控制信道报文格式与隧道认证（RFC 2661 教学简化）。

在 UDP 1701 上完成 L2TP 控制连接与会话建立。本模块实现：

- 隧道认证（真实 HMAC）：SCCRQ 携带 16 字节随机 challenge；SCCRP 携带
  ``HMAC-SHA256(共享密钥, challenge || tunnel_id)`` 的 challenge response；客户端
  校验。这是 RFC 2661 隧道认证的**教学简化**（RFC 用 MD5，本模块用 HMAC-SHA256，
  明示）。
- 控制报文 framing（教学简化版）：::

      头部: version_flags(2) | tunnel_id(2,BE) | session_id(2,BE) | ns(2,BE) | nr(2,BE)
            | message_type(2,BE)     # 12B
      SCCRQ(1)  载荷: challenge(16) | assigned_tunnel_id(2)
      SCCRP(2)  载荷: challenge_response(32) | assigned_tunnel_id(2)
      SCCCN(4)  载荷: (空)
      ICRQ(10)  载荷: assigned_session_id(2)
      ICRP(11)  载荷: assigned_session_id(2)
      ICCN(12)  载荷: (空)

消息类型取 RFC 2661 值：SCCRQ=1、SCCRP=2、SCCCN=4、ICRQ=10、ICRP=11、ICCN=12。

L2TP 本身无加密（PPP 层才有），本模块只做控制面握手与隧道认证，不实现 PPP。
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import secrets
from dataclasses import dataclass

MSG_SCCRQ = 1
MSG_SCCRP = 2
MSG_SCCCN = 4
MSG_ICRQ = 10
MSG_ICRP = 11
MSG_ICCN = 12

CHALLENGE_LEN = 16
RESPONSE_LEN = 32  # HMAC-SHA256
ID_LEN = 2
HEADER_LEN = 2 + ID_LEN + ID_LEN + 2 + 2 + 2  # 12
VERSION_FLAGS = b"\x00\x02"  # version 2, 无标志


@dataclass(frozen=True)
class ControlMessage:
    """解析后的 L2TP 控制报文。"""

    tunnel_id: int
    session_id: int
    ns: int
    nr: int
    message_type: int
    payload: bytes


def generate_shared_secret() -> bytes:
    """生成 32 字节随机共享密钥（隧道认证用）。"""
    return secrets.token_bytes(32)


def generate_challenge() -> bytes:
    """生成 16 字节随机 challenge。"""
    return secrets.token_bytes(CHALLENGE_LEN)


def compute_challenge_response(secret: bytes, challenge: bytes, tunnel_id: int) -> bytes:
    """计算隧道认证 challenge response = HMAC-SHA256(secret, challenge || tunnel_id)。"""
    return hmac_mod.new(
        secret, challenge + tunnel_id.to_bytes(ID_LEN, "big"), hashlib.sha256
    ).digest()


def build_control_message(
    tunnel_id: int,
    session_id: int,
    ns: int,
    nr: int,
    message_type: int,
    payload: bytes = b"",
) -> bytes:
    """组帧一条 L2TP 控制报文。"""
    return (
        VERSION_FLAGS
        + tunnel_id.to_bytes(ID_LEN, "big")
        + session_id.to_bytes(ID_LEN, "big")
        + ns.to_bytes(2, "big")
        + nr.to_bytes(2, "big")
        + message_type.to_bytes(2, "big")
        + payload
    )


def parse_control_message(raw: bytes) -> ControlMessage:
    """解析一条 L2TP 控制报文。"""
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid L2TP message length: {len(raw)}")
    return ControlMessage(
        tunnel_id=int.from_bytes(raw[2:4], "big"),
        session_id=int.from_bytes(raw[4:6], "big"),
        ns=int.from_bytes(raw[6:8], "big"),
        nr=int.from_bytes(raw[8:10], "big"),
        message_type=int.from_bytes(raw[10:12], "big"),
        payload=raw[HEADER_LEN:],
    )


def _require(msg: ControlMessage, expected: int) -> None:
    if msg.message_type != expected:
        raise ValueError(f"unexpected message type: {msg.message_type} (expected {expected})")


def build_sccrq(tunnel_id: int, challenge: bytes, ns: int = 0, nr: int = 0) -> bytes:
    return build_control_message(
        tunnel_id, 0, ns, nr, MSG_SCCRQ, challenge + tunnel_id.to_bytes(ID_LEN, "big")
    )


def parse_sccrq(raw: bytes) -> tuple[ControlMessage, bytes, int]:
    msg = parse_control_message(raw)
    _require(msg, MSG_SCCRQ)
    if len(msg.payload) != CHALLENGE_LEN + ID_LEN:
        raise ValueError(f"invalid SCCRQ payload length: {len(msg.payload)}")
    return msg, msg.payload[:CHALLENGE_LEN], int.from_bytes(msg.payload[CHALLENGE_LEN:], "big")


def build_sccrp(tunnel_id: int, challenge_response: bytes, ns: int = 0, nr: int = 0) -> bytes:
    return build_control_message(
        tunnel_id, 0, ns, nr, MSG_SCCRP, challenge_response + tunnel_id.to_bytes(ID_LEN, "big")
    )


def parse_sccrp(raw: bytes) -> tuple[ControlMessage, bytes, int]:
    msg = parse_control_message(raw)
    _require(msg, MSG_SCCRP)
    if len(msg.payload) != RESPONSE_LEN + ID_LEN:
        raise ValueError(f"invalid SCCRP payload length: {len(msg.payload)}")
    return msg, msg.payload[:RESPONSE_LEN], int.from_bytes(msg.payload[RESPONSE_LEN:], "big")


def build_icrq(session_id: int, ns: int = 0, nr: int = 0) -> bytes:
    return build_control_message(
        1, session_id, ns, nr, MSG_ICRQ, session_id.to_bytes(ID_LEN, "big")
    )


def parse_icrq(raw: bytes) -> tuple[ControlMessage, int]:
    msg = parse_control_message(raw)
    _require(msg, MSG_ICRQ)
    if len(msg.payload) != ID_LEN:
        raise ValueError(f"invalid ICRQ payload length: {len(msg.payload)}")
    return msg, int.from_bytes(msg.payload, "big")


def build_icrp(session_id: int, ns: int = 0, nr: int = 0) -> bytes:
    return build_control_message(
        2, session_id, ns, nr, MSG_ICRP, session_id.to_bytes(ID_LEN, "big")
    )


def parse_icrp(raw: bytes) -> tuple[ControlMessage, int]:
    msg = parse_control_message(raw)
    _require(msg, MSG_ICRP)
    if len(msg.payload) != ID_LEN:
        raise ValueError(f"invalid ICRP payload length: {len(msg.payload)}")
    return msg, int.from_bytes(msg.payload, "big")


def build_empty(
    tunnel_id: int, session_id: int, message_type: int, ns: int = 0, nr: int = 0
) -> bytes:
    """组帧无载荷的控制报文（SCCCN / ICCN）。"""
    return build_control_message(tunnel_id, session_id, ns, nr, message_type, b"")


def parse_empty(raw: bytes, expected: int) -> ControlMessage:
    """解析无载荷的控制报文（SCCCN / ICCN）。"""
    msg = parse_control_message(raw)
    _require(msg, expected)
    return msg
