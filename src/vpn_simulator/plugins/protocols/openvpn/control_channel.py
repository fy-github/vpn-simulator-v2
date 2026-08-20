"""OpenVPN 控制信道报文组帧与 ``--tls-auth`` 静态密钥 HMAC 实现。

依据 OpenVPN 协议控制信道格式，使用标准库 `hmac` + `hashlib`（SHA-256）
真实实现控制信道报文的组帧/解帧与 ``--tls-auth`` 预共享密钥认证：

- 报文头：opcode（1 字节）
- 会话标识：session_id（8 字节，大端）
- ``--tls-auth``：HMAC-SHA256（32 字节），覆盖 ``opcode | session_id |
  packet_id | payload``
- 可靠层：packet_id（4 字节，大端）
- 载荷：TLS 记录（控制信道内为 TLS over 可靠层）

本模块只做控制面握手报文封装与认证，不提供数据面转发，也不作为生产
VPN 网关。

报文字节布局（``--tls-auth`` 开启）::

    opcode(1) | session_id(8) | hmac(32) | packet_id(4) | payload(N)
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import secrets
from dataclasses import dataclass

# OpenVPN 控制信道 opcode 常量。
P_CONTROL_HARD_RESET_CLIENT_V1 = 1
P_CONTROL_HARD_RESET_SERVER_V1 = 2
P_CONTROL_SOFT_RESET_V1 = 3
P_CONTROL_V1 = 4
P_ACK_V1 = 5
P_DATA_V1 = 6
P_CONTROL_HARD_RESET_CLIENT_V2 = 7
P_CONTROL_HARD_RESET_SERVER_V2 = 8
P_DATA_V2 = 9
P_CONTROL_HARD_RESET_CLIENT_V3 = 10

SESSION_ID_LEN = 8
PACKET_ID_LEN = 4
HMAC_LEN = 32
TLS_AUTH_KEY_LEN = 32

_OPCODE_NAMES = {
    P_CONTROL_HARD_RESET_CLIENT_V1: "P_CONTROL_HARD_RESET_CLIENT_V1",
    P_CONTROL_HARD_RESET_SERVER_V1: "P_CONTROL_HARD_RESET_SERVER_V1",
    P_CONTROL_SOFT_RESET_V1: "P_CONTROL_SOFT_RESET_V1",
    P_CONTROL_V1: "P_CONTROL_V1",
    P_ACK_V1: "P_ACK_V1",
    P_DATA_V1: "P_DATA_V1",
    P_CONTROL_HARD_RESET_CLIENT_V2: "P_CONTROL_HARD_RESET_CLIENT_V2",
    P_CONTROL_HARD_RESET_SERVER_V2: "P_CONTROL_HARD_RESET_SERVER_V2",
    P_DATA_V2: "P_DATA_V2",
    P_CONTROL_HARD_RESET_CLIENT_V3: "P_CONTROL_HARD_RESET_CLIENT_V3",
}


@dataclass(frozen=True)
class ControlPacket:
    """已解析的 OpenVPN 控制信道报文。"""

    opcode: int
    session_id: int
    packet_id: int
    payload: bytes

    @property
    def opcode_name(self) -> str:
        """opcode 的可读名称。"""
        return _OPCODE_NAMES.get(self.opcode, f"UNKNOWN({self.opcode})")


def generate_tls_auth_key() -> bytes:
    """生成 32 字节 ``--tls-auth`` 静态预共享密钥（模拟 tls-auth 密钥文件）。"""
    return secrets.token_bytes(TLS_AUTH_KEY_LEN)


def generate_session_id() -> int:
    """生成 64 位随机 session_id。"""
    return int.from_bytes(secrets.token_bytes(SESSION_ID_LEN), "big")


def _hmac_input(opcode: int, session_id: int, packet_id: int, payload: bytes) -> bytes:
    """HMAC 覆盖的报文字段：opcode | session_id | packet_id | payload。"""
    return (
        opcode.to_bytes(1, "big")
        + session_id.to_bytes(SESSION_ID_LEN, "big")
        + packet_id.to_bytes(PACKET_ID_LEN, "big")
        + payload
    )


def build_control_packet(
    opcode: int,
    session_id: int,
    packet_id: int,
    payload: bytes,
    tls_auth_key: bytes,
) -> bytes:
    """组帧一个控制信道报文并附上 ``--tls-auth`` HMAC。

    Args:
        opcode: 控制信道 opcode（见模块常量）。
        session_id: 64 位会话标识。
        packet_id: 32 位可靠层报文序号。
        payload: 载荷（TLS 记录）。
        tls_auth_key: 32 字节 ``--tls-auth`` 静态预共享密钥。

    Returns:
        完整报文字节：``opcode|session_id|hmac|packet_id|payload``。
    """
    digest = hmac_mod.new(
        tls_auth_key, _hmac_input(opcode, session_id, packet_id, payload), hashlib.sha256
    ).digest()
    return (
        opcode.to_bytes(1, "big")
        + session_id.to_bytes(SESSION_ID_LEN, "big")
        + digest
        + packet_id.to_bytes(PACKET_ID_LEN, "big")
        + payload
    )


def parse_control_packet(raw: bytes, tls_auth_key: bytes) -> ControlPacket:
    """解帧控制信道报文并校验 ``--tls-auth`` HMAC。

    Args:
        raw: 完整报文字节。
        tls_auth_key: 32 字节 ``--tls-auth`` 静态预共享密钥。

    Returns:
        解析结果 `ControlPacket`。

    Raises:
        ValueError: 报文长度不足或 HMAC 校验失败（篡改/密钥不符）。
    """
    if len(raw) < 1 + SESSION_ID_LEN + HMAC_LEN + PACKET_ID_LEN:
        raise ValueError(f"invalid control packet length: {len(raw)}")

    opcode = raw[0]
    session_id = int.from_bytes(raw[1 : 1 + SESSION_ID_LEN], "big")
    digest = raw[1 + SESSION_ID_LEN : 1 + SESSION_ID_LEN + HMAC_LEN]
    packet_id = int.from_bytes(
        raw[1 + SESSION_ID_LEN + HMAC_LEN : 1 + SESSION_ID_LEN + HMAC_LEN + PACKET_ID_LEN],
        "big",
    )
    payload = raw[1 + SESSION_ID_LEN + HMAC_LEN + PACKET_ID_LEN :]

    expected = hmac_mod.new(
        tls_auth_key, _hmac_input(opcode, session_id, packet_id, payload), hashlib.sha256
    ).digest()
    if not hmac_mod.compare_digest(digest, expected):
        raise ValueError("tls-auth HMAC verification failed")

    return ControlPacket(opcode=opcode, session_id=session_id, packet_id=packet_id, payload=payload)
