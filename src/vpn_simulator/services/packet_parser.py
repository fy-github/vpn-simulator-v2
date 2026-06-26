"""报文解析服务。

提供报文解析、搜索和过滤功能。
支持字段级解析、报文结构树形展示和 PCAP 导出。

Example:
    >>> parser = PacketParser()
    >>> packet = parser.parse_packet(raw_data, "pptp", "SCCRQ")
    >>> print(packet.fields)
"""

from __future__ import annotations

import struct
import uuid
from datetime import datetime
from typing import Any, Optional

from ..domain.packet import (
    PacketDirection,
    PacketField,
    PacketInfo,
    PacketType,
    export_packets_to_pcap,
)
from ..domain.packet_fields import (
    ALL_PROTOCOL_FIELDS,
    FieldDefinition,
    FieldType,
    get_field_definitions,
    get_message_types,
    get_supported_protocols,
)


class PacketParser:
    """报文解析器。

    提供报文解析、搜索和过滤功能。

    Attributes:
        _packets: 存储所有解析过的报文。
    """

    def __init__(self):
        """初始化报文解析器。"""
        self._packets: dict[str, PacketInfo] = {}

    def parse_packet(
        self,
        raw_data: bytes,
        protocol: str,
        message_type: str,
        direction: PacketDirection = PacketDirection.INCOMING,
        src_ip: str = "",
        dst_ip: str = "",
        src_port: int = 0,
        dst_port: int = 0,
        connection_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> PacketInfo:
        """解析报文。

        Args:
            raw_data: 原始报文数据。
            protocol: 协议名称。
            message_type: 消息类型。
            direction: 报文方向。
            src_ip: 源 IP 地址。
            dst_ip: 目的 IP 地址。
            src_port: 源端口。
            dst_port: 目的端口。
            connection_id: 关联的连接 ID。
            session_id: 关联的会话 ID。

        Returns:
            解析后的报文信息。
        """
        packet_id = str(uuid.uuid4())
        timestamp = datetime.now()

        packet = PacketInfo(
            id=packet_id,
            timestamp=timestamp,
            direction=direction,
            packet_type=self._get_packet_type(protocol, message_type),
            protocol=protocol,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            raw_data=raw_data,
            connection_id=connection_id,
            session_id=session_id,
        )

        # 解析字段
        field_definitions = get_field_definitions(protocol, message_type)
        if field_definitions:
            packet.fields = self._parse_fields(raw_data, field_definitions)
            packet.parsed = True
        else:
            packet.parse_error = f"Unknown message type: {message_type}"

        # 存储报文
        self._packets[packet_id] = packet

        return packet

    def _get_packet_type(self, protocol: str, message_type: str) -> PacketType:
        """根据协议和消息类型确定报文类型。

        Args:
            protocol: 协议名称。
            message_type: 消息类型。

        Returns:
            报文类型。
        """
        # 控制报文关键字
        control_keywords = [
            "SCCRQ", "SCCRP", "StopCCN", "OCRQ", "OCRP", "ICRQ", "ICRP", "ICCN",
            "CCRQ", "CDN", "WEN", "SLI", "HELLO",
            "P_CONTROL", "P_ACK", "P_HARD_RESET", "P_SOFT_RESET",
            "IKE_SA_INIT", "IKE_AUTH", "CREATE_CHILD_SA", "INFORMATIONAL",
            "MAIN_MODE", "QUICK_MODE",
        ]

        # 数据报文关键字
        data_keywords = ["P_DATA"]

        message_upper = message_type.upper()
        for keyword in control_keywords:
            if keyword.upper() in message_upper:
                return PacketType.CONTROL

        for keyword in data_keywords:
            if keyword.upper() in message_upper:
                return PacketType.DATA

        return PacketType.CONTROL

    def _parse_fields(
        self,
        raw_data: bytes,
        field_definitions: list[FieldDefinition],
    ) -> list[PacketField]:
        """解析报文字段。

        Args:
            raw_data: 原始报文数据。
            field_definitions: 字段定义列表。

        Returns:
            解析后的字段列表。
        """
        fields = []
        for field_def in field_definitions:
            try:
                field_value = self._extract_field_value(raw_data, field_def)
                field = PacketField(
                    name=field_def.name,
                    offset=field_def.offset,
                    length=field_def.length,
                    value=field_value,
                    description=field_def.description,
                    field_type=field_def.field_type.value,
                )
                fields.append(field)
            except Exception as e:
                # 解析失败时创建错误字段
                field = PacketField(
                    name=field_def.name,
                    offset=field_def.offset,
                    length=field_def.length,
                    value=None,
                    description=f"{field_def.description} (解析错误: {e})",
                    field_type="error",
                )
                fields.append(field)

        return fields

    def _extract_field_value(
        self,
        raw_data: bytes,
        field_def: FieldDefinition,
    ) -> Any:
        """从原始数据中提取字段值。

        Args:
            raw_data: 原始报文数据。
            field_def: 字段定义。

        Returns:
            提取的字段值。
        """
        offset = field_def.offset
        length = field_def.length

        # 检查边界
        if offset + length > len(raw_data):
            raise ValueError(f"Field extends beyond data: offset={offset}, length={length}, data_len={len(raw_data)}")

        data = raw_data[offset:offset + length]

        if field_def.field_type == FieldType.UINT8:
            return struct.unpack(">B", data)[0]
        elif field_def.field_type == FieldType.UINT16:
            return struct.unpack(">H", data)[0]
        elif field_def.field_type == FieldType.UINT32:
            return struct.unpack(">I", data)[0]
        elif field_def.field_type == FieldType.UINT64:
            return struct.unpack(">Q", data)[0]
        elif field_def.field_type == FieldType.STRING:
            # 移除空终止符
            return data.rstrip(b"\x00").decode("ascii", errors="replace")
        elif field_def.field_type == FieldType.IP:
            if length == 4:
                return f"{data[0]}.{data[1]}.{data[2]}.{data[3]}"
            return data.hex()
        elif field_def.field_type == FieldType.MAC:
            return ":".join(f"{b:02x}" for b in data)
        elif field_def.field_type == FieldType.FLAGS:
            value = struct.unpack(">I", data)[0] if length == 4 else struct.unpack(">H", data)[0]
            return self._parse_flags(value, field_def.bit_fields)
        elif field_def.field_type == FieldType.ENUM:
            value = struct.unpack(">H", data)[0] if length == 2 else struct.unpack(">B", data)[0]
            if field_def.enum_values:
                return field_def.enum_values.get(value, f"Unknown ({value})")
            return value
        elif field_def.field_type == FieldType.BYTES:
            return data.hex()
        else:
            return data.hex()

    def _parse_flags(
        self,
        value: int,
        bit_fields: Optional[list[Any]],
    ) -> dict[str, Any]:
        """解析标志位字段。

        Args:
            value: 标志位值。
            bit_fields: 位字段定义列表。

        Returns:
            解析后的标志位字典。
        """
        if not bit_fields:
            return {"raw": value}

        result = {}
        for bf in bit_fields:
            mask = (1 << bf.bit_length) - 1
            bit_value = (value >> bf.bit_offset) & mask
            result[bf.name] = {
                "value": bit_value,
                "description": bf.description,
            }

        return result

    def get_packet(self, packet_id: str) -> Optional[PacketInfo]:
        """获取报文详情。

        Args:
            packet_id: 报文 ID。

        Returns:
            报文信息，如果未找到则返回 None。
        """
        return self._packets.get(packet_id)

    def get_packets(
        self,
        protocol: Optional[str] = None,
        direction: Optional[PacketDirection] = None,
        packet_type: Optional[PacketType] = None,
        connection_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PacketInfo]:
        """获取报文列表。

        Args:
            protocol: 协议过滤。
            direction: 方向过滤。
            packet_type: 报文类型过滤。
            connection_id: 连接 ID 过滤。
            session_id: 会话 ID 过滤。
            limit: 返回数量限制。
            offset: 偏移量。

        Returns:
            报文列表。
        """
        packets = list(self._packets.values())

        # 应用过滤器
        if protocol:
            packets = [p for p in packets if p.protocol == protocol]
        if direction:
            packets = [p for p in packets if p.direction == direction]
        if packet_type:
            packets = [p for p in packets if p.packet_type == packet_type]
        if connection_id:
            packets = [p for p in packets if p.connection_id == connection_id]
        if session_id:
            packets = [p for p in packets if p.session_id == session_id]

        # 按时间戳排序
        packets.sort(key=lambda p: p.timestamp, reverse=True)

        # 应用分页
        return packets[offset:offset + limit]

    def search_packets(
        self,
        query: str,
        protocol: Optional[str] = None,
        limit: int = 100,
    ) -> list[PacketInfo]:
        """搜索报文。

        Args:
            query: 搜索查询（在字段名称、描述和值中搜索）。
            protocol: 协议过滤。
            limit: 返回数量限制。

        Returns:
            匹配的报文列表。
        """
        packets = list(self._packets.values())

        if protocol:
            packets = [p for p in packets if p.protocol == protocol]

        query_lower = query.lower()
        results = []

        for packet in packets:
            if (
                query_lower in packet.protocol.lower()
                or query_lower in packet.src_ip.lower()
                or query_lower in packet.dst_ip.lower()
            ):
                results.append(packet)
                if len(results) >= limit:
                    break
                continue

            if query_lower in packet.raw_data.hex().lower():
                results.append(packet)
                if len(results) >= limit:
                    break
                continue

            for field in packet.fields:
                if (
                    query_lower in field.name.lower()
                    or query_lower in field.description.lower()
                    or query_lower in str(field.value).lower()
                ):
                    results.append(packet)
                    break

            if len(results) >= limit:
                break

        return results

    def get_packet_count(self) -> int:
        """获取报文总数。

        Returns:
            报文总数。
        """
        return len(self._packets)

    def clear_packets(self) -> None:
        """清空所有报文。"""
        self._packets.clear()

    def export_to_pcap(
        self,
        protocol: Optional[str] = None,
        direction: Optional[PacketDirection] = None,
        packet_type: Optional[PacketType] = None,
        connection_id: Optional[str] = None,
    ) -> bytes:
        """导出报文为 PCAP 格式。

        Args:
            protocol: 协议过滤。
            direction: 方向过滤。
            packet_type: 报文类型过滤。
            connection_id: 连接 ID 过滤。

        Returns:
            PCAP 文件的字节数据。
        """
        packets = self.get_packets(
            protocol=protocol,
            direction=direction,
            packet_type=packet_type,
            connection_id=connection_id,
            limit=10000,  # 导出限制
        )
        return export_packets_to_pcap(packets)

    def get_statistics(self) -> dict[str, Any]:
        """获取报文统计信息。

        Returns:
            统计信息字典。
        """
        packets = list(self._packets.values())

        # 按协议统计
        by_protocol: dict[str, int] = {}
        for p in packets:
            by_protocol[p.protocol] = by_protocol.get(p.protocol, 0) + 1

        # 按方向统计
        by_direction: dict[str, int] = {}
        for p in packets:
            key = p.direction.value
            by_direction[key] = by_direction.get(key, 0) + 1

        # 按类型统计
        by_type: dict[str, int] = {}
        for p in packets:
            key = p.packet_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total": len(packets),
            "by_protocol": by_protocol,
            "by_direction": by_direction,
            "by_type": by_type,
        }

    def get_supported_protocols(self) -> list[str]:
        """获取支持的协议列表。

        Returns:
            协议名称列表。
        """
        return get_supported_protocols()

    def get_message_types(self, protocol: str) -> list[str]:
        """获取指定协议的消息类型列表。

        Args:
            protocol: 协议名称。

        Returns:
            消息类型列表。
        """
        return get_message_types(protocol)

    def generate_sample_packets(self) -> list[PacketInfo]:
        """生成示例报文数据。

        Returns:
            示例报文列表。
        """
        samples = []

        # PPTP SCCRQ 示例
        pptp_sccrq_data = bytes([
            0x00, 0x9C,  # length = 156
            0x00, 0x01,  # message_type = 1 (SCCRQ)
            0x1A, 0x2B, 0x3C, 0x4D,  # magic_cookie
            0x00, 0x01,  # control_message_type = 1
            0x00, 0x00,  # reserved
            0x01, 0x00,  # protocol_version = 256
            0x00, 0x00, 0x00, 0x03,  # framing_capabilities (async + sync)
            0x00, 0x00, 0x00, 0x03,  # bearer_capabilities (analog + digital)
            0x00, 0x01,  # max_channels = 1
            0x01, 0x00,  # firmware_revision = 256
        ] + [0x00] * 64 + [ord(c) for c in "Simulator"] + [0x00] * 55 +  # host_name
        [0x00] * 64 + [ord(c) for c in "VPN Simulator v2"] + [0x00] * 48)  # vendor_name

        samples.append(self.parse_packet(
            pptp_sccrq_data, "pptp", "SCCRQ",
            direction=PacketDirection.INCOMING,
            src_ip="192.168.1.100", dst_ip="192.168.1.1",
            src_port=50000, dst_port=1723,
        ))

        # PPTP SCCRP 示例
        pptp_sccrp_data = bytes([
            0x00, 0x9C,  # length = 156
            0x00, 0x02,  # message_type = 2 (SCCRP)
            0x1A, 0x2B, 0x3C, 0x4D,  # magic_cookie
            0x00, 0x02,  # control_message_type = 2
            0x00, 0x00,  # reserved
            0x01, 0x00,  # protocol_version = 256
            0x00, 0x00, 0x00, 0x03,  # framing_capabilities
            0x00, 0x00, 0x00, 0x03,  # bearer_capabilities
            0x00, 0x01,  # max_channels = 1
            0x01, 0x00,  # firmware_revision = 256
        ] + [0x00] * 64 + [ord(c) for c in "VPNServer"] + [0x00] * 55 +  # host_name
        [0x00] * 64 + [ord(c) for c in "VPN Simulator v2"] + [0x00] * 48)  # vendor_name

        samples.append(self.parse_packet(
            pptp_sccrp_data, "pptp", "SCCRP",
            direction=PacketDirection.OUTGOING,
            src_ip="192.168.1.1", dst_ip="192.168.1.100",
            src_port=1723, dst_port=50000,
        ))

        # L2TP SCCRQ 示例
        l2tp_sccrq_data = bytes([
            0xC8, 0x02,  # flags (type=1, length=1, sequence=1, version=2)
            0x00, 0x3C,  # length = 60
            0x00, 0x01,  # tunnel_id = 1
            0x00, 0x00,  # session_id = 0
            0x00, 0x00,  # ns = 0
            0x00, 0x00,  # nr = 0
            0x00, 0x00,  # offset_size = 0
        ] + [0x00] * 20)  # AVP 数据

        samples.append(self.parse_packet(
            l2tp_sccrq_data, "l2tp", "SCCRQ",
            direction=PacketDirection.INCOMING,
            src_ip="192.168.1.100", dst_ip="192.168.1.1",
            src_port=50001, dst_port=1701,
        ))

        # OpenVPN P_CONTROL 示例
        openvpn_ctrl_data = bytes([
            0x40,  # opcode = P_CONTROL_V1 (4), key_id = 0
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,  # session_id = 1
            0x00, 0x00, 0x00, 0x01,  # message_id = 1
            0x00,  # ack_length = 0
            0x00, 0x10,  # payload_length = 16
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # TLS payload
        ])

        samples.append(self.parse_packet(
            openvpn_ctrl_data, "openvpn", "P_CONTROL",
            direction=PacketDirection.INCOMING,
            src_ip="192.168.1.100", dst_ip="192.168.1.1",
            src_port=50002, dst_port=1194,
        ))

        # IPSec IKE_SA_INIT 示例
        ike_sa_init_data = bytes([
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,  # initiator_spi = 1
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # responder_spi = 0
            0x21,  # next_payload = 33 (SA)
            0x20,  # version = 2.0
            0x22,  # exchange_type = 34 (IKE_SA_INIT)
            0x08,  # flags (initiator=1)
            0x00, 0x00, 0x00, 0x00,  # message_id = 0
            0x00, 0x00, 0x00, 0x2C,  # length = 44
        ] + [0x00] * 16)  # 载荷数据

        samples.append(self.parse_packet(
            ike_sa_init_data, "ipsec", "IKE_SA_INIT",
            direction=PacketDirection.INCOMING,
            src_ip="192.168.1.100", dst_ip="192.168.1.1",
            src_port=500, dst_port=500,
        ))

        return samples


# 全局报文解析器实例
packet_parser = PacketParser()
