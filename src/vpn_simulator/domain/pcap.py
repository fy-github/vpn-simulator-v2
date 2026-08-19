"""PCAP 回放模型（F3）。

表示一个已上传的 PCAP/PCAPNG 文件及其解析元数据，以及一次回放会话
（按原始时序重放、可变速、可按协议过滤）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PcapFileInfo:
    """已上传的 PCAP 文件元数据。

    Attributes:
        id: 文件唯一标识（UUID）。
        filename: 原始文件名。
        packet_count: 报文数量。
        protocols: 文件包含的协议集合（如 ["udp", "tcp", "icmp"]）。
        duration_seconds: 首末报文时间跨度（秒）。
        size_bytes: 文件大小（字节）。
        uploaded_at: 上传时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = ""
    packet_count: int = 0
    protocols: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    size_bytes: int = 0
    uploaded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "filename": self.filename,
            "packet_count": self.packet_count,
            "protocols": self.protocols,
            "duration_seconds": round(self.duration_seconds, 3),
            "size_bytes": self.size_bytes,
            "uploaded_at": self.uploaded_at.isoformat(),
        }


@dataclass
class ReplaySession:
    """一次 PCAP 回放会话。

    Attributes:
        id: 会话唯一标识（UUID）。
        pcap_file_id: 回放的 PCAP 文件 ID。
        speed: 回放速度倍率（0.5x-10x）。
        protocol_filter: 协议过滤（None 表示不过滤）。
        status: idle / running / completed / stopped。
        packets_replayed: 已回放报文数。
        total_packets: 应回放报文总数（过滤后）。
        started_at: 开始时间。
        finished_at: 结束时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pcap_file_id: str = ""
    speed: float = 1.0
    protocol_filter: str | None = None
    status: str = "idle"
    packets_replayed: int = 0
    total_packets: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "pcap_file_id": self.pcap_file_id,
            "speed": self.speed,
            "protocol_filter": self.protocol_filter,
            "status": self.status,
            "packets_replayed": self.packets_replayed,
            "total_packets": self.total_packets,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
