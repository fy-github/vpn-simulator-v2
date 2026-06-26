"""报文模型。

提供 VPN 报文的数据结构、字段级解析和 PCAP 格式导出。
支持控制报文、数据报文和错误报文三种类型。

Example:
    >>> packet = PacketInfo(
    ...     id="pkt-001",
    ...     timestamp=datetime.now(),
    ...     direction=PacketDirection.INCOMING,
    ...     packet_type=PacketType.CONTROL,
    ...     protocol="pptp",
    ... )
    >>> record = packet.to_pcap_record()
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class PacketDirection(Enum):
    """报文方向枚举。

    Attributes:
        INCOMING: 入站报文（从客户端到服务端）。
        OUTGOING: 出站报文（从服务端到客户端）。
    """

    INCOMING = "incoming"
    OUTGOING = "outgoing"


class PacketType(Enum):
    """报文类型枚举。

    Attributes:
        CONTROL: 控制报文（握手、协商等）。
        DATA: 数据报文（隧道传输的用户数据）。
        ERROR: 错误报文（协议错误通知）。
    """

    CONTROL = "control"
    DATA = "data"
    ERROR = "error"


@dataclass
class PacketField:
    """报文字段定义。

    描述报文中的一个字段，包括其在原始数据中的位置、
    长度、解析后的值和类型信息。

    Attributes:
        name: 字段名称。
        offset: 字段在原始数据中的偏移量（字节）。
        length: 字段长度（字节）。
        value: 解析后的字段值。
        description: 字段的可读描述。
        field_type: 字段类型（bytes, int, string, ip, mac）。
    """

    name: str
    offset: int
    length: int
    value: Any
    description: str
    field_type: str = "bytes"

    def to_dict(self) -> dict[str, Any]:
        """将字段转换为字典。

        Returns:
            包含字段信息的字典。
        """
        return {
            "name": self.name,
            "offset": self.offset,
            "length": self.length,
            "value": str(self.value),
            "description": self.description,
            "field_type": self.field_type,
        }


@dataclass
class PacketInfo:
    """报文信息数据类。

    封装了一个网络报文的完整信息，包括网络层信息、
    原始数据、解析后的字段列表和关联信息。

    Attributes:
        id: 报文唯一标识符。
        timestamp: 报文捕获时间戳。
        direction: 报文方向（入站/出站）。
        packet_type: 报文类型（控制/数据/错误）。
        protocol: 协议名称。
        src_ip: 源 IP 地址。
        dst_ip: 目的 IP 地址。
        src_port: 源端口。
        dst_port: 目的端口。
        raw_data: 原始报文字节数据。
        fields: 解析后的字段列表。
        parsed: 是否已解析。
        parse_error: 解析错误信息。
        connection_id: 关联的连接 ID。
        session_id: 关联的会话 ID。
    """

    id: str
    timestamp: datetime
    direction: PacketDirection
    packet_type: PacketType
    protocol: str

    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0

    raw_data: bytes = b""
    fields: list[PacketField] = field(default_factory=list)

    parsed: bool = False
    parse_error: Optional[str] = None

    connection_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """将报文信息转换为字典。

        raw_data 转换为十六进制字符串表示。

        Returns:
            包含所有报文信息的字典。
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "packet_type": self.packet_type.value,
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "raw_data_hex": self.raw_data.hex(),
            "fields": [f.to_dict() for f in self.fields],
            "parsed": self.parsed,
            "parse_error": self.parse_error,
            "connection_id": self.connection_id,
            "session_id": self.session_id,
        }

    def to_pcap_record(self) -> bytes:
        """将报文转换为 PCAP 记录格式。

        PCAP 记录格式：
        - ts_sec (4 bytes): 时间戳秒数
        - ts_usec (4 bytes): 时间戳微秒数
        - incl_len (4 bytes): 捕获的数据长度
        - orig_len (4 bytes): 原始数据长度
        - data: 原始报文数据

        Returns:
            PCAP 记录的字节数据。
        """
        ts_sec = int(self.timestamp.timestamp())
        ts_usec = int((self.timestamp.timestamp() % 1) * 1_000_000)
        incl_len = len(self.raw_data)
        orig_len = incl_len

        header = struct.pack("<IIII", ts_sec, ts_usec, incl_len, orig_len)
        return header + self.raw_data

    @staticmethod
    def pcap_global_header() -> bytes:
        """生成 PCAP 文件的全局头。

        PCAP 全局头格式：
        - magic_number (4 bytes): 0xa1b2c3d4 (小端序)
        - version_major (2 bytes): 2
        - version_minor (2 bytes): 4
        - thiszone (4 bytes): 0 (UTC)
        - sigfigs (4 bytes): 0
        - snaplen (4 bytes): 65535
        - network (4 bytes): 1 (Ethernet)

        Returns:
            PCAP 全局头的字节数据。
        """
        return struct.pack(
            "<IHHiIII",
            0xA1B2C3D4,  # magic_number
            2,            # version_major
            4,            # version_minor
            0,            # thiszone
            0,            # sigfigs
            65535,        # snaplen
            1,            # network (LINKTYPE_ETHERNET)
        )

    def to_pcap_file(self) -> bytes:
        """将报文导出为完整的 PCAP 文件。

        Returns:
            完整 PCAP 文件的字节数据（全局头 + 记录）。
        """
        return self.pcap_global_header() + self.to_pcap_record()


def export_packets_to_pcap(packets: list[PacketInfo]) -> bytes:
    """将多个报文导出为一个 PCAP 文件。

    Args:
        packets: 报文列表。

    Returns:
        完整 PCAP 文件的字节数据。
    """
    header = PacketInfo.pcap_global_header()
    records = b"".join(p.to_pcap_record() for p in packets)
    return header + records
