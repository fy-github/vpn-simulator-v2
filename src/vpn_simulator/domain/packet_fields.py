"""报文字段定义。

定义各 VPN 协议的报文字段结构，用于报文解析和展示。
支持 PPTP、L2TP、OpenVPN、IPSec/IKEv1、IKEv2 协议。

Example:
    >>> fields = PPTP_FIELDS["SCCRQ"]
    >>> for field in fields:
    ...     print(f"{field.name}: {field.description}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ProtocolType(Enum):
    """协议类型枚举。"""

    PPTP = "pptp"
    L2TP = "l2tp"
    OPENVPN = "openvpn"
    IPSEC = "ipsec"
    IKEV2 = "ikev2"
    WIREGUARD = "wireguard"


class FieldType(Enum):
    """字段类型枚举。"""

    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    BYTES = "bytes"
    STRING = "string"
    IP = "ip"
    MAC = "mac"
    FLAGS = "flags"
    ENUM = "enum"


@dataclass
class BitFieldDefinition:
    """位字段定义。

    描述字段中的位级结构。

    Attributes:
        name: 位字段名称。
        bit_offset: 位偏移量。
        bit_length: 位长度。
        description: 位字段描述。
    """

    name: str
    bit_offset: int
    bit_length: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "name": self.name,
            "bit_offset": self.bit_offset,
            "bit_length": self.bit_length,
            "description": self.description,
        }


@dataclass
class FieldDefinition:
    """字段定义。

    描述协议报文中一个字段的结构信息。

    Attributes:
        name: 字段名称。
        offset: 字段在报文中的偏移量（字节）。
        length: 字段长度（字节）。
        field_type: 字段类型。
        description: 字段描述。
        bit_fields: 位字段定义（仅当 field_type 为 FLAGS 时使用）。
        enum_values: 枚举值映射（仅当 field_type 为 ENUM 时使用）。
    """

    name: str
    offset: int
    length: int
    field_type: FieldType
    description: str
    bit_fields: Optional[list[BitFieldDefinition]] = None
    enum_values: Optional[dict[int, str]] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        result = {
            "name": self.name,
            "offset": self.offset,
            "length": self.length,
            "field_type": self.field_type.value,
            "description": self.description,
        }
        if self.bit_fields:
            result["bit_fields"] = [bf.to_dict() for bf in self.bit_fields]
        if self.enum_values:
            result["enum_values"] = {str(k): v for k, v in self.enum_values.items()}
        return result


# PPTP 报文类型枚举
PPTP_MESSAGE_TYPE = {
    1: "SCCRQ (Start-Control-Connection-Request)",
    2: "SCCRP (Start-Control-Connection-Reply)",
    3: "StopCCN (Stop-Control-Connection-Notification)",
    4: "ECHO-REQUEST",
    5: "ECHO-REPLY",
    6: "OCRQ (Outgoing-Call-Request)",
    7: "OCRP (Outgoing-Call-Reply)",
    8: "ICRQ (Incoming-Call-Request)",
    9: "ICRP (Incoming-Call-Reply)",
    10: "ICCN (Incoming-Call-Connected)",
    11: "CCRQ (Call-Clear-Request)",
    12: "CDN (Call-Disconnect-Notify)",
    13: "WEN (WAN-Error-Notify)",
    14: "SLIP-INFO (Set-Link-Info)",
}

# PPTP SCCRQ 报文字段
PPTP_SCCRQ_FIELDS = [
    FieldDefinition("length", 0, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("message_type", 2, 2, FieldType.ENUM, "报文类型", enum_values=PPTP_MESSAGE_TYPE),
    FieldDefinition("magic_cookie", 4, 4, FieldType.UINT32, "幻数 cookie (0x1A2B3C4D)"),
    FieldDefinition("control_message_type", 8, 2, FieldType.UINT16, "控制消息类型 (1=SCCRQ)"),
    FieldDefinition("reserved", 10, 2, FieldType.UINT16, "保留字段"),
    FieldDefinition("protocol_version", 12, 2, FieldType.UINT16, "协议版本"),
    FieldDefinition("framing_capabilities", 14, 4, FieldType.FLAGS, "帧能力", bit_fields=[
        BitFieldDefinition("async_framing", 0, 1, "异步帧支持"),
        BitFieldDefinition("sync_framing", 1, 1, "同步帧支持"),
        BitFieldDefinition("reserved", 2, 30, "保留位"),
    ]),
    FieldDefinition("bearer_capabilities", 18, 4, FieldType.FLAGS, "承载能力", bit_fields=[
        BitFieldDefinition("analog_access", 0, 1, "模拟接入"),
        BitFieldDefinition("digital_access", 1, 1, "数字接入"),
        BitFieldDefinition("reserved", 2, 30, "保留位"),
    ]),
    FieldDefinition("max_channels", 22, 2, FieldType.UINT16, "最大通道数"),
    FieldDefinition("firmware_revision", 24, 2, FieldType.UINT16, "固件版本"),
    FieldDefinition("host_name", 26, 64, FieldType.STRING, "主机名"),
    FieldDefinition("vendor_name", 90, 64, FieldType.STRING, "厂商名称"),
]

# PPTP SCCRP 报文字段
PPTP_SCCRP_FIELDS = [
    FieldDefinition("length", 0, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("message_type", 2, 2, FieldType.ENUM, "报文类型", enum_values=PPTP_MESSAGE_TYPE),
    FieldDefinition("magic_cookie", 4, 4, FieldType.UINT32, "幻数 cookie (0x1A2B3C4D)"),
    FieldDefinition("control_message_type", 8, 2, FieldType.UINT16, "控制消息类型 (2=SCCRP)"),
    FieldDefinition("reserved", 10, 2, FieldType.UINT16, "保留字段"),
    FieldDefinition("protocol_version", 12, 2, FieldType.UINT16, "协议版本"),
    FieldDefinition("framing_capabilities", 14, 4, FieldType.FLAGS, "帧能力", bit_fields=[
        BitFieldDefinition("async_framing", 0, 1, "异步帧支持"),
        BitFieldDefinition("sync_framing", 1, 1, "同步帧支持"),
        BitFieldDefinition("reserved", 2, 30, "保留位"),
    ]),
    FieldDefinition("bearer_capabilities", 18, 4, FieldType.FLAGS, "承载能力", bit_fields=[
        BitFieldDefinition("analog_access", 0, 1, "模拟接入"),
        BitFieldDefinition("digital_access", 1, 1, "数字接入"),
        BitFieldDefinition("reserved", 2, 30, "保留位"),
    ]),
    FieldDefinition("max_channels", 22, 2, FieldType.UINT16, "最大通道数"),
    FieldDefinition("firmware_revision", 24, 2, FieldType.UINT16, "固件版本"),
    FieldDefinition("host_name", 26, 64, FieldType.STRING, "主机名"),
    FieldDefinition("vendor_name", 90, 64, FieldType.STRING, "厂商名称"),
    FieldDefinition("result_code", 154, 2, FieldType.ENUM, "结果代码", enum_values={
        1: "成功 (Successful channel establishment)",
        2: "一般错误",
        3: "通道已存在",
        4: "通道不存在",
        5: "协议错误",
    }),
]

# PPTP OCRQ 报文字段
PPTP_OCRQ_FIELDS = [
    FieldDefinition("length", 0, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("message_type", 2, 2, FieldType.ENUM, "报文类型", enum_values=PPTP_MESSAGE_TYPE),
    FieldDefinition("magic_cookie", 4, 4, FieldType.UINT32, "幻数 cookie (0x1A2B3C4D)"),
    FieldDefinition("control_message_type", 8, 2, FieldType.UINT16, "控制消息类型 (6=OCRQ)"),
    FieldDefinition("reserved", 10, 2, FieldType.UINT16, "保留字段"),
    FieldDefinition("call_id", 12, 2, FieldType.UINT16, "呼叫 ID"),
    FieldDefinition("call_serial_number", 14, 2, FieldType.UINT16, "呼叫序列号"),
    FieldDefinition("min_bps", 16, 4, FieldType.UINT32, "最小比特率"),
    FieldDefinition("max_bps", 20, 4, FieldType.UINT32, "最大比特率"),
    FieldDefinition("bearer_type", 24, 4, FieldType.FLAGS, "承载类型", bit_fields=[
        BitFieldDefinition("analog", 0, 1, "模拟"),
        BitFieldDefinition("digital", 1, 1, "数字"),
        BitFieldDefinition("any", 2, 1, "任意"),
        BitFieldDefinition("reserved", 3, 29, "保留位"),
    ]),
    FieldDefinition("framing_type", 28, 4, FieldType.FLAGS, "帧类型", bit_fields=[
        BitFieldDefinition("async", 0, 1, "异步"),
        BitFieldDefinition("sync", 1, 1, "同步"),
        BitFieldDefinition("any", 2, 1, "任意"),
        BitFieldDefinition("reserved", 3, 29, "保留位"),
    ]),
    FieldDefinition("packet_recv_size", 32, 2, FieldType.UINT16, "接收包大小"),
    FieldDefinition("packet_processing_delay", 34, 2, FieldType.UINT16, "包处理延迟"),
    FieldDefinition("phone_number", 36, 64, FieldType.STRING, "电话号码"),
    FieldDefinition("subaddress", 100, 64, FieldType.STRING, "子地址"),
]

# PPTP OCRP 报文字段
PPTP_OCRP_FIELDS = [
    FieldDefinition("length", 0, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("message_type", 2, 2, FieldType.ENUM, "报文类型", enum_values=PPTP_MESSAGE_TYPE),
    FieldDefinition("magic_cookie", 4, 4, FieldType.UINT32, "幻数 cookie (0x1A2B3C4D)"),
    FieldDefinition("control_message_type", 8, 2, FieldType.UINT16, "控制消息类型 (7=OCRP)"),
    FieldDefinition("reserved", 10, 2, FieldType.UINT16, "保留字段"),
    FieldDefinition("call_id", 12, 2, FieldType.UINT16, "呼叫 ID"),
    FieldDefinition("peer_call_id", 14, 2, FieldType.UINT16, "对端呼叫 ID"),
    FieldDefinition("result_code", 16, 2, FieldType.ENUM, "结果代码", enum_values={
        1: "成功 (Connected)",
        2: "一般错误",
        3: "无载波",
        4: "忙",
        5: "无拨号音",
        6: "超时",
    }),
    FieldDefinition("error_code", 18, 2, FieldType.UINT16, "错误代码"),
    FieldDefinition("cause_code", 20, 2, FieldType.UINT16, "原因代码"),
    FieldDefinition("connect_speed", 22, 4, FieldType.UINT32, "连接速度"),
    FieldDefinition("packet_recv_size", 26, 2, FieldType.UINT16, "接收包大小"),
    FieldDefinition("packet_processing_delay", 28, 2, FieldType.UINT16, "包处理延迟"),
    FieldDefinition("physical_channel_id", 30, 2, FieldType.UINT16, "物理通道 ID"),
]

# PPTP 报文字段映射
PPTP_FIELDS = {
    "SCCRQ": PPTP_SCCRQ_FIELDS,
    "SCCRP": PPTP_SCCRP_FIELDS,
    "OCRQ": PPTP_OCRQ_FIELDS,
    "OCRP": PPTP_OCRP_FIELDS,
}

# L2TP 报文类型
L2TP_MESSAGE_TYPE = {
    1: "SCCRQ (Start-Control-Connection-Request)",
    2: "SCCRP (Start-Control-Connection-Reply)",
    3: "StopCCN (Stop-Control-Connection-Notification)",
    4: "HELLO (Keep-Alive)",
    6: "OCRQ (Outgoing-Call-Request)",
    7: "OCRP (Outgoing-Call-Reply)",
    8: "OCCN (Outgoing-Call-Connected)",
    9: "ICRQ (Incoming-Call-Request)",
    10: "ICRP (Incoming-Call-Reply)",
    11: "ICCN (Incoming-Call-Connected)",
    12: "Reserved",
    13: "CDN (Call-Disconnect-Notify)",
    14: "WEN (WAN-Error-Notify)",
    15: "SLI (Set-Link-Info)",
}

# L2TP SCCRQ 报文字段
L2TP_SCCRQ_FIELDS = [
    FieldDefinition("flags", 0, 2, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("type", 0, 1, "类型 (0=数据, 1=控制)"),
        BitFieldDefinition("length", 1, 1, "长度位"),
        BitFieldDefinition("sequence", 2, 1, "序列号位"),
        BitFieldDefinition("offset", 3, 1, "偏移位"),
        BitFieldDefinition("priority", 4, 1, "优先级位"),
        BitFieldDefinition("reserved", 5, 3, "保留位"),
        BitFieldDefinition("version", 8, 4, "版本号"),
        BitFieldDefinition("reserved2", 12, 4, "保留位"),
    ]),
    FieldDefinition("length", 2, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("tunnel_id", 4, 2, FieldType.UINT16, "隧道 ID"),
    FieldDefinition("session_id", 6, 2, FieldType.UINT16, "会话 ID"),
    FieldDefinition("ns", 8, 2, FieldType.UINT16, "发送序列号"),
    FieldDefinition("nr", 10, 2, FieldType.UINT16, "接收序列号"),
    FieldDefinition("offset_size", 12, 2, FieldType.UINT16, "偏移大小"),
    # AVP 字段从偏移 14 开始
    FieldDefinition("avp_message_type", 14, 6, FieldType.ENUM, "消息类型 AVP", enum_values=L2TP_MESSAGE_TYPE),
    FieldDefinition("avp_protocol_version", 20, 6, FieldType.UINT16, "协议版本 AVP"),
    FieldDefinition("avp_framer_capabilities", 26, 6, FieldType.FLAGS, "帧能力 AVP"),
    FieldDefinition("avp_bearer_capabilities", 32, 6, FieldType.FLAGS, "承载能力 AVP"),
    FieldDefinition("avp_firmware_revision", 38, 6, FieldType.UINT16, "固件版本 AVP"),
    FieldDefinition("avp_host_name", 44, 6, FieldType.STRING, "主机名 AVP"),
    FieldDefinition("avp_vendor_name", 50, 6, FieldType.STRING, "厂商名称 AVP"),
    FieldDefinition("avp_tunnel_id", 56, 6, FieldType.UINT16, "隧道 ID AVP"),
    FieldDefinition("avp_receive_window_size", 62, 6, FieldType.UINT16, "接收窗口大小 AVP"),
]

# L2TP SCCRP 报文字段
L2TP_SCCRP_FIELDS = [
    FieldDefinition("flags", 0, 2, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("type", 0, 1, "类型 (0=数据, 1=控制)"),
        BitFieldDefinition("length", 1, 1, "长度位"),
        BitFieldDefinition("sequence", 2, 1, "序列号位"),
        BitFieldDefinition("offset", 3, 1, "偏移位"),
        BitFieldDefinition("priority", 4, 1, "优先级位"),
        BitFieldDefinition("reserved", 5, 3, "保留位"),
        BitFieldDefinition("version", 8, 4, "版本号"),
        BitFieldDefinition("reserved2", 12, 4, "保留位"),
    ]),
    FieldDefinition("length", 2, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("tunnel_id", 4, 2, FieldType.UINT16, "隧道 ID"),
    FieldDefinition("session_id", 6, 2, FieldType.UINT16, "会话 ID"),
    FieldDefinition("ns", 8, 2, FieldType.UINT16, "发送序列号"),
    FieldDefinition("nr", 10, 2, FieldType.UINT16, "接收序列号"),
    FieldDefinition("offset_size", 12, 2, FieldType.UINT16, "偏移大小"),
    FieldDefinition("avp_message_type", 14, 6, FieldType.ENUM, "消息类型 AVP", enum_values=L2TP_MESSAGE_TYPE),
    FieldDefinition("avp_protocol_version", 20, 6, FieldType.UINT16, "协议版本 AVP"),
    FieldDefinition("avp_framer_capabilities", 26, 6, FieldType.FLAGS, "帧能力 AVP"),
    FieldDefinition("avp_bearer_capabilities", 32, 6, FieldType.FLAGS, "承载能力 AVP"),
    FieldDefinition("avp_firmware_revision", 38, 6, FieldType.UINT16, "固件版本 AVP"),
    FieldDefinition("avp_host_name", 44, 6, FieldType.STRING, "主机名 AVP"),
    FieldDefinition("avp_vendor_name", 50, 6, FieldType.STRING, "厂商名称 AVP"),
    FieldDefinition("avp_tunnel_id", 56, 6, FieldType.UINT16, "隧道 ID AVP"),
    FieldDefinition("avp_receive_window_size", 62, 6, FieldType.UINT16, "接收窗口大小 AVP"),
    FieldDefinition("avp_challenge", 68, 6, FieldType.BYTES, "挑战 AVP"),
    FieldDefinition("avp_challenge_response", 74, 6, FieldType.BYTES, "挑战响应 AVP"),
]

# L2TP ICRQ 报文字段
L2TP_ICRQ_FIELDS = [
    FieldDefinition("flags", 0, 2, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("type", 0, 1, "类型 (0=数据, 1=控制)"),
        BitFieldDefinition("length", 1, 1, "长度位"),
        BitFieldDefinition("sequence", 2, 1, "序列号位"),
        BitFieldDefinition("offset", 3, 1, "偏移位"),
        BitFieldDefinition("priority", 4, 1, "优先级位"),
        BitFieldDefinition("reserved", 5, 3, "保留位"),
        BitFieldDefinition("version", 8, 4, "版本号"),
        BitFieldDefinition("reserved2", 12, 4, "保留位"),
    ]),
    FieldDefinition("length", 2, 2, FieldType.UINT16, "报文总长度"),
    FieldDefinition("tunnel_id", 4, 2, FieldType.UINT16, "隧道 ID"),
    FieldDefinition("session_id", 6, 2, FieldType.UINT16, "会话 ID"),
    FieldDefinition("ns", 8, 2, FieldType.UINT16, "发送序列号"),
    FieldDefinition("nr", 10, 2, FieldType.UINT16, "接收序列号"),
    FieldDefinition("offset_size", 12, 2, FieldType.UINT16, "偏移大小"),
    FieldDefinition("avp_message_type", 14, 6, FieldType.ENUM, "消息类型 AVP", enum_values=L2TP_MESSAGE_TYPE),
    FieldDefinition("avp_assigned_session_id", 20, 6, FieldType.UINT16, "分配会话 ID AVP"),
    FieldDefinition("avp_call_serial_number", 26, 6, FieldType.UINT16, "呼叫序列号 AVP"),
    FieldDefinition("avp_bearer_type", 32, 6, FieldType.FLAGS, "承载类型 AVP"),
    FieldDefinition("avp_called_number", 38, 6, FieldType.STRING, "被叫号码 AVP"),
    FieldDefinition("avp_calling_number", 44, 6, FieldType.STRING, "主叫号码 AVP"),
    FieldDefinition("avp_sub_address", 50, 6, FieldType.STRING, "子地址 AVP"),
]

# L2TP 报文字段映射
L2TP_FIELDS = {
    "SCCRQ": L2TP_SCCRQ_FIELDS,
    "SCCRP": L2TP_SCCRP_FIELDS,
    "ICRQ": L2TP_ICRQ_FIELDS,
}

# OpenVPN 报文类型
OPENVPN_PACKET_TYPE = {
    1: "P_CONTROL_HARD_RESET_CLIENT_V1",
    2: "P_CONTROL_HARD_RESET_SERVER_V1",
    3: "P_CONTROL_SOFT_RESET_V1",
    4: "P_CONTROL_V1",
    5: "P_ACK_V1",
    6: "P_DATA_V1",
    7: "P_CONTROL_HARD_RESET_CLIENT_V2",
    8: "P_CONTROL_HARD_RESET_SERVER_V2",
    9: "P_DATA_V2",
    10: "P_CONTROL_HARD_RESET_CLIENT_V3",
}

# OpenVPN P_CONTROL 报文字段
OPENVPN_P_CONTROL_FIELDS = [
    FieldDefinition("opcode", 0, 1, FieldType.ENUM, "操作码", enum_values=OPENVPN_PACKET_TYPE),
    FieldDefinition("key_id", 0, 1, FieldType.UINT8, "密钥 ID (低6位)"),
    FieldDefinition("session_id", 1, 8, FieldType.UINT64, "会话 ID"),
    FieldDefinition("message_id", 9, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("ack_length", 13, 1, FieldType.UINT8, "确认列表长度"),
    FieldDefinition("ack_list", 14, 4, FieldType.UINT32, "确认消息 ID 列表"),
    FieldDefinition("payload_length", 18, 2, FieldType.UINT16, "载荷长度"),
    FieldDefinition("payload", 20, 0, FieldType.BYTES, "TLS 控制载荷"),
]

# OpenVPN P_DATA 报文字段
OPENVPN_P_DATA_FIELDS = [
    FieldDefinition("opcode", 0, 1, FieldType.ENUM, "操作码", enum_values=OPENVPN_PACKET_TYPE),
    FieldDefinition("key_id", 0, 1, FieldType.UINT8, "密钥 ID (低6位)"),
    FieldDefinition("session_id", 1, 8, FieldType.UINT64, "会话 ID"),
    FieldDefinition("message_id", 9, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("payload_length", 13, 2, FieldType.UINT16, "载荷长度"),
    FieldDefinition("payload", 15, 0, FieldType.BYTES, "加密数据载荷"),
]

# OpenVPN 报文字段映射
OPENVPN_FIELDS = {
    "P_CONTROL": OPENVPN_P_CONTROL_FIELDS,
    "P_DATA": OPENVPN_P_DATA_FIELDS,
}

# IPSec/IKEv1 报文类型
IKEV1_EXCHANGE_TYPE = {
    1: "Base",
    2: "Identity Protection (Main Mode)",
    3: "Authentication Only",
    4: "Aggressive",
    5: "Informational",
    32: "Quick Mode",
}

# IPSec IKE_SA_INIT 报文字段 (IKEv2)
IKEV2_IKE_SA_INIT_FIELDS = [
    FieldDefinition("initiator_spi", 0, 8, FieldType.UINT64, "发起方 SPI"),
    FieldDefinition("responder_spi", 8, 8, FieldType.UINT64, "响应方 SPI"),
    FieldDefinition("next_payload", 16, 1, FieldType.UINT8, "下一个载荷类型"),
    FieldDefinition("version", 17, 1, FieldType.UINT8, "IKE 版本"),
    FieldDefinition("exchange_type", 18, 1, FieldType.ENUM, "交换类型", enum_values={
        34: "IKE_SA_INIT",
        35: "IKE_AUTH",
        36: "CREATE_CHILD_SA",
        37: "INFORMATIONAL",
    }),
    FieldDefinition("flags", 19, 1, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("initiator", 3, 1, "发起方标志"),
        BitFieldDefinition("version", 4, 1, "更高版本标志"),
        BitFieldDefinition("response", 5, 1, "响应标志"),
        BitFieldDefinition("reserved", 6, 2, "保留位"),
    ]),
    FieldDefinition("message_id", 20, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("length", 24, 4, FieldType.UINT32, "报文总长度"),
    # 载荷从偏移 28 开始
    FieldDefinition("sa_payload", 28, 0, FieldType.BYTES, "SA 载荷"),
    FieldDefinition("ke_payload", 28, 0, FieldType.BYTES, "密钥交换载荷"),
    FieldDefinition("nonce_payload", 28, 0, FieldType.BYTES, "随机数载荷"),
]

# IPSec IKE_AUTH 报文字段 (IKEv2)
IKEV2_IKE_AUTH_FIELDS = [
    FieldDefinition("initiator_spi", 0, 8, FieldType.UINT64, "发起方 SPI"),
    FieldDefinition("responder_spi", 8, 8, FieldType.UINT64, "响应方 SPI"),
    FieldDefinition("next_payload", 16, 1, FieldType.UINT8, "下一个载荷类型"),
    FieldDefinition("version", 17, 1, FieldType.UINT8, "IKE 版本"),
    FieldDefinition("exchange_type", 18, 1, FieldType.ENUM, "交换类型", enum_values={
        34: "IKE_SA_INIT",
        35: "IKE_AUTH",
        36: "CREATE_CHILD_SA",
        37: "INFORMATIONAL",
    }),
    FieldDefinition("flags", 19, 1, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("initiator", 3, 1, "发起方标志"),
        BitFieldDefinition("version", 4, 1, "更高版本标志"),
        BitFieldDefinition("response", 5, 1, "响应标志"),
        BitFieldDefinition("reserved", 6, 2, "保留位"),
    ]),
    FieldDefinition("message_id", 20, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("length", 24, 4, FieldType.UINT32, "报文总长度"),
    # 载荷从偏移 28 开始
    FieldDefinition("id_payload", 28, 0, FieldType.BYTES, "身份载荷"),
    FieldDefinition("auth_payload", 28, 0, FieldType.BYTES, "认证载荷"),
    FieldDefinition("sa_payload", 28, 0, FieldType.BYTES, "SA 载荷"),
    FieldDefinition("tsi_payload", 28, 0, FieldType.BYTES, "流量选择器-发起方"),
    FieldDefinition("tsr_payload", 28, 0, FieldType.BYTES, "流量选择器-响应方"),
    FieldDefinition("cp_payload", 28, 0, FieldType.BYTES, "配置载荷"),
]

# IPSec/IKEv1 Main Mode 报文字段
IKEV1_MAIN_MODE_FIELDS = [
    FieldDefinition("initiator_cookie", 0, 8, FieldType.UINT64, "发起方 Cookie"),
    FieldDefinition("responder_cookie", 8, 8, FieldType.UINT64, "响应方 Cookie"),
    FieldDefinition("next_payload", 16, 1, FieldType.UINT8, "下一个载荷类型"),
    FieldDefinition("version", 17, 1, FieldType.UINT8, "IKE 版本"),
    FieldDefinition("exchange_type", 18, 1, FieldType.ENUM, "交换类型", enum_values=IKEV1_EXCHANGE_TYPE),
    FieldDefinition("flags", 19, 1, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("encryption", 0, 1, "加密标志"),
        BitFieldDefinition("commit", 1, 1, "提交标志"),
        BitFieldDefinition("auth_only", 2, 1, "仅认证标志"),
        BitFieldDefinition("reserved", 3, 5, "保留位"),
    ]),
    FieldDefinition("message_id", 20, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("length", 24, 4, FieldType.UINT32, "报文总长度"),
]

# IPSec Quick Mode 报文字段
IKEV1_QUICK_MODE_FIELDS = [
    FieldDefinition("initiator_cookie", 0, 8, FieldType.UINT64, "发起方 Cookie"),
    FieldDefinition("responder_cookie", 8, 8, FieldType.UINT64, "响应方 Cookie"),
    FieldDefinition("next_payload", 16, 1, FieldType.UINT8, "下一个载荷类型"),
    FieldDefinition("version", 17, 1, FieldType.UINT8, "IKE 版本"),
    FieldDefinition("exchange_type", 18, 1, FieldType.ENUM, "交换类型", enum_values=IKEV1_EXCHANGE_TYPE),
    FieldDefinition("flags", 19, 1, FieldType.FLAGS, "标志位", bit_fields=[
        BitFieldDefinition("encryption", 0, 1, "加密标志"),
        BitFieldDefinition("commit", 1, 1, "提交标志"),
        BitFieldDefinition("auth_only", 2, 1, "仅认证标志"),
        BitFieldDefinition("reserved", 3, 5, "保留位"),
    ]),
    FieldDefinition("message_id", 20, 4, FieldType.UINT32, "消息 ID"),
    FieldDefinition("length", 24, 4, FieldType.UINT32, "报文总长度"),
    FieldDefinition("flags_qm", 28, 4, FieldType.FLAGS, "Quick Mode 标志", bit_fields=[
        BitFieldDefinition("nonce", 0, 1, "随机数标志"),
        BitFieldDefinition("identity", 1, 1, "身份标志"),
        BitFieldDefinition("reserved", 2, 30, "保留位"),
    ]),
]

# IPSec 报文字段映射
IPSEC_FIELDS = {
    "IKE_SA_INIT": IKEV2_IKE_SA_INIT_FIELDS,
    "IKE_AUTH": IKEV2_IKE_AUTH_FIELDS,
    "MAIN_MODE": IKEV1_MAIN_MODE_FIELDS,
    "QUICK_MODE": IKEV1_QUICK_MODE_FIELDS,
}

# 所有协议的报文字段映射
ALL_PROTOCOL_FIELDS = {
    "pptp": PPTP_FIELDS,
    "l2tp": L2TP_FIELDS,
    "openvpn": OPENVPN_FIELDS,
    "ipsec": IPSEC_FIELDS,
    "ikev2": IPSEC_FIELDS,  # IKEv2 使用与 IPSec 相同的字段定义
}


def get_field_definitions(protocol: str, message_type: str) -> Optional[list[FieldDefinition]]:
    """获取指定协议和消息类型的字段定义。

    Args:
        protocol: 协议名称。
        message_type: 消息类型。

    Returns:
        字段定义列表，如果未找到则返回 None。
    """
    protocol_fields = ALL_PROTOCOL_FIELDS.get(protocol.lower())
    if not protocol_fields:
        return None
    return protocol_fields.get(message_type)


def get_supported_protocols() -> list[str]:
    """获取支持的协议列表。

    Returns:
        协议名称列表。
    """
    return list(ALL_PROTOCOL_FIELDS.keys())


def get_message_types(protocol: str) -> list[str]:
    """获取指定协议的消息类型列表。

    Args:
        protocol: 协议名称。

    Returns:
        消息类型列表。
    """
    protocol_fields = ALL_PROTOCOL_FIELDS.get(protocol.lower(), {})
    return list(protocol_fields.keys())
