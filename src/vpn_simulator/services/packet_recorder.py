"""真实报文记录器：把真实捕获的报文写入 packets 表与 WS 流。

Phase 1 打通层：将 packetio 真实收发的协议报文（如 WireGuard 握手）
同时写入：
1. `packet_parser`（`/api/v1/packets` 背后的报文表），供报文列表/搜索/PCAP 导出使用。
2. `TrafficService`（`/api/v1/traffic/stream` 背后的 WS 流），供前端流量可视化实时消费。
"""

from __future__ import annotations

from vpn_simulator.domain.packet import PacketDirection
from vpn_simulator.services.packet_parser import packet_parser
from vpn_simulator.services.traffic import get_traffic_service


def record_real_packet(
    *,
    protocol: str,
    message_type: str,
    direction: PacketDirection,
    raw_data: bytes,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    connection_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """把真实捕获的报文同时写入 packets 表与 WS 流。

    Args:
        protocol: 协议名称（如 "wireguard"）。
        message_type: 消息类型（如 "HANDSHAKE_INITIATION"）。
        direction: 报文方向。
        raw_data: 原始报文字节。
        src_ip: 源 IP。
        dst_ip: 目的 IP。
        src_port: 源端口。
        dst_port: 目的端口。
        connection_id: 关联连接 ID。
        session_id: 关联会话 ID。
    """
    packet_parser.parse_packet(
        raw_data,
        protocol,
        message_type,
        direction=direction,
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        connection_id=connection_id,
        session_id=session_id,
    )

    get_traffic_service().record_external_packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        size=len(raw_data),
        payload_preview=raw_data.hex()[:32],
    )
