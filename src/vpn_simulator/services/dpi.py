"""深度包检测 (DPI) 服务。

提供协议识别、流量分类和异常检测功能。
使用模拟数据实现协议指纹匹配。

Example:
    >>> dpi = DPIService()
    >>> result = dpi.analyze_packet(b"...", src_port=443, dst_port=50000)
    >>> print(result.protocol)
    "HTTPS"
"""

from __future__ import annotations

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ProtocolCategory(str, Enum):
    """协议类别。"""

    APPLICATION = "application"
    STREAMING = "streaming"
    VPN = "vpn"
    P2P = "p2p"
    MESSAGING = "messaging"
    GAMING = "gaming"
    UNKNOWN = "unknown"


class ThreatLevel(str, Enum):
    """威胁等级。"""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProtocolFingerprint:
    """协议指纹。"""

    name: str
    category: ProtocolCategory
    default_ports: list[int]
    signature_bytes: list[bytes] = field(default_factory=list)
    description: str = ""
    threat_level: ThreatLevel = ThreatLevel.SAFE
    is_encrypted: bool = False
    common_domains: list[str] = field(default_factory=list)


@dataclass
class DPIResult:
    """DPI 分析结果。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    protocol: str = ""
    category: ProtocolCategory = ProtocolCategory.UNKNOWN
    confidence: float = 0.0
    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0
    payload_size: int = 0
    is_encrypted: bool = False
    threat_level: ThreatLevel = ThreatLevel.SAFE
    metadata: dict[str, Any] = field(default_factory=dict)
    matched_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "protocol": self.protocol,
            "category": self.category.value,
            "confidence": self.confidence,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "payload_size": self.payload_size,
            "is_encrypted": self.is_encrypted,
            "threat_level": self.threat_level.value,
            "metadata": self.metadata,
            "matched_rules": self.matched_rules,
        }


@dataclass
class ProtocolStatistics:
    """协议统计信息。"""

    total_packets: int = 0
    protocol_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    threat_counts: dict[str, int] = field(default_factory=dict)
    total_bytes: int = 0
    protocol_bytes: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    anomaly_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "total_packets": self.total_packets,
            "protocol_counts": self.protocol_counts,
            "category_counts": self.category_counts,
            "threat_counts": self.threat_counts,
            "total_bytes": self.total_bytes,
            "protocol_bytes": self.protocol_bytes,
            "avg_confidence": round(self.avg_confidence, 2),
            "anomaly_count": self.anomaly_count,
        }


@dataclass
class TrafficClassification:
    """流量分类结果。"""

    category: str
    protocols: list[str]
    packet_count: int
    byte_count: int
    percentage: float
    avg_confidence: float


@dataclass
class AnomalyDetection:
    """异常检测结果。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    anomaly_type: str = ""
    severity: ThreatLevel = ThreatLevel.LOW
    description: str = ""
    source_ip: str = ""
    protocol: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class DPIService:
    """深度包检测服务。

    提供协议识别、流量分类和异常检测功能。
    使用模拟的协议指纹数据库进行匹配。
    """

    def __init__(self) -> None:
        """初始化 DPI 服务。"""
        self._fingerprints: dict[str, ProtocolFingerprint] = {}
        self._results: list[DPIResult] = []
        self._anomalies: list[AnomalyDetection] = []
        self._statistics = ProtocolStatistics()
        self._confidence_sum: float = 0.0
        self._load_fingerprints()

    def _load_fingerprints(self) -> None:
        """加载协议指纹数据库。"""
        fingerprints = [
            # 应用层协议
            ProtocolFingerprint(
                name="HTTP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[80, 8080, 8000],
                signature_bytes=[b"GET ", b"POST ", b"HTTP/1.", b"HEAD ", b"PUT "],
                description="超文本传输协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="HTTPS",
                category=ProtocolCategory.APPLICATION,
                default_ports=[443, 8443],
                signature_bytes=[b"\x16\x03\x01", b"\x16\x03\x03", b"\x16\x03\x02"],
                description="加密的 HTTP 协议 (TLS)",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.google.com", "*.github.com"],
            ),
            ProtocolFingerprint(
                name="DNS",
                category=ProtocolCategory.APPLICATION,
                default_ports=[53, 5353],
                signature_bytes=[],
                description="域名系统协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="SSH",
                category=ProtocolCategory.APPLICATION,
                default_ports=[22],
                signature_bytes=[b"SSH-2.0", b"SSH-1."],
                description="安全外壳协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
            ),
            ProtocolFingerprint(
                name="FTP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[20, 21],
                signature_bytes=[b"220 ", b"USER ", b"PASS "],
                description="文件传输协议",
                threat_level=ThreatLevel.LOW,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="SMTP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[25, 465, 587],
                signature_bytes=[b"220 ", b"EHLO ", b"HELO "],
                description="简单邮件传输协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="POP3",
                category=ProtocolCategory.APPLICATION,
                default_ports=[110, 995],
                signature_bytes=[b"+OK ", b"USER ", b"PASS "],
                description="邮局协议 v3",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="IMAP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[143, 993],
                signature_bytes=[b"* OK ", b"a1 LOGIN"],
                description="互联网消息访问协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="DHCP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[67, 68],
                signature_bytes=[b"\x01\x01\x06\x00"],
                description="动态主机配置协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="NTP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[123],
                signature_bytes=[],
                description="网络时间协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="SNMP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[161, 162],
                signature_bytes=[b"\x30"],
                description="简单网络管理协议",
                threat_level=ThreatLevel.LOW,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="RDP",
                category=ProtocolCategory.APPLICATION,
                default_ports=[3389],
                signature_bytes=[b"\x03\x00"],
                description="远程桌面协议",
                threat_level=ThreatLevel.LOW,
                is_encrypted=True,
            ),
            # 流媒体协议
            ProtocolFingerprint(
                name="YouTube",
                category=ProtocolCategory.STREAMING,
                default_ports=[443, 80],
                signature_bytes=[],
                description="YouTube 视频流",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.youtube.com", "*.googlevideo.com", "*.ytimg.com"],
            ),
            ProtocolFingerprint(
                name="Netflix",
                category=ProtocolCategory.STREAMING,
                default_ports=[443, 80],
                signature_bytes=[],
                description="Netflix 视频流",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.netflix.com", "*.nflxvideo.net", "*.nflximg.com"],
            ),
            ProtocolFingerprint(
                name="Spotify",
                category=ProtocolCategory.STREAMING,
                default_ports=[443, 80],
                signature_bytes=[],
                description="Spotify 音乐流",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.spotify.com", "*.scdn.co", "*.spotifycdn.com"],
            ),
            ProtocolFingerprint(
                name="Twitch",
                category=ProtocolCategory.STREAMING,
                default_ports=[443, 80],
                signature_bytes=[],
                description="Twitch 直播流",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.twitch.tv", "*.ttvnw.net", "*.jtvnw.net"],
            ),
            ProtocolFingerprint(
                name="Zoom",
                category=ProtocolCategory.STREAMING,
                default_ports=[443, 8801, 8802],
                signature_bytes=[],
                description="Zoom 视频会议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
                common_domains=["*.zoom.us", "*.zoomgov.com"],
            ),
            # VPN 协议
            ProtocolFingerprint(
                name="OpenVPN",
                category=ProtocolCategory.VPN,
                default_ports=[1194, 443],
                signature_bytes=[b"\x00\x0e\x40"],
                description="OpenVPN 协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
            ),
            ProtocolFingerprint(
                name="WireGuard",
                category=ProtocolCategory.VPN,
                default_ports=[51820],
                signature_bytes=[b"\x01\x00\x00\x00"],
                description="WireGuard 协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
            ),
            ProtocolFingerprint(
                name="IPSec",
                category=ProtocolCategory.VPN,
                default_ports=[500, 4500],
                signature_bytes=[],
                description="IPSec 协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
            ),
            ProtocolFingerprint(
                name="L2TP",
                category=ProtocolCategory.VPN,
                default_ports=[1701],
                signature_bytes=[b"\xc8\x02"],
                description="L2TP 隧道协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="PPTP",
                category=ProtocolCategory.VPN,
                default_ports=[1723],
                signature_bytes=[],
                description="PPTP 协议",
                threat_level=ThreatLevel.MEDIUM,
                is_encrypted=False,
            ),
            ProtocolFingerprint(
                name="SSTP",
                category=ProtocolCategory.VPN,
                default_ports=[443],
                signature_bytes=[],
                description="SSTP 协议",
                threat_level=ThreatLevel.SAFE,
                is_encrypted=True,
            ),
            # P2P 协议
            ProtocolFingerprint(
                name="BitTorrent",
                category=ProtocolCategory.P2P,
                default_ports=[6881, 6882, 6883, 6884, 6885, 6886, 6887, 6888, 6889, 6890],
                signature_bytes=[b"\x13BitTorrent protocol"],
                description="BitTorrent 协议",
                threat_level=ThreatLevel.LOW,
                is_encrypted=False,
            ),
        ]

        for fp in fingerprints:
            self._fingerprints[fp.name] = fp

    def get_supported_protocols(self) -> list[dict[str, Any]]:
        """获取支持的协议列表。

        Returns:
            协议信息列表。
        """
        protocols = []
        for fp in self._fingerprints.values():
            protocols.append({
                "name": fp.name,
                "category": fp.category.value,
                "default_ports": fp.default_ports,
                "description": fp.description,
                "threat_level": fp.threat_level.value,
                "is_encrypted": fp.is_encrypted,
                "common_domains": fp.common_domains,
            })
        return protocols

    def analyze_packet(
        self,
        payload: bytes,
        src_ip: str = "",
        dst_ip: str = "",
        src_port: int = 0,
        dst_port: int = 0,
    ) -> DPIResult:
        """分析数据包。

        使用协议指纹匹配和端口分析识别协议。

        Args:
            payload: 数据包载荷。
            src_ip: 源 IP。
            dst_ip: 目的 IP。
            src_port: 源端口。
            dst_port: 目的端口。

        Returns:
            DPI 分析结果。
        """
        best_match: Optional[ProtocolFingerprint] = None
        best_confidence = 0.0
        matched_rules: list[str] = []

        # 1. 签名匹配
        for fp in self._fingerprints.values():
            if fp.signature_bytes:
                for sig in fp.signature_bytes:
                    if payload.startswith(sig) or sig in payload[:64]:
                        confidence = 0.85 + random.uniform(0, 0.15)
                        if confidence > best_confidence:
                            best_match = fp
                            best_confidence = confidence
                            matched_rules = [f"signature_match:{fp.name}"]
                        break

        # 2. 端口匹配
        for fp in self._fingerprints.values():
            if src_port in fp.default_ports or dst_port in fp.default_ports:
                confidence = 0.6 + random.uniform(0, 0.2)
                if confidence > best_confidence:
                    best_match = fp
                    best_confidence = confidence
                    matched_rules = [f"port_match:{fp.name}"]
                elif best_match and best_match.name == fp.name:
                    best_confidence = min(best_confidence + 0.1, 0.99)
                    matched_rules.append(f"port_confirm:{fp.name}")

        # 3. 启发式检测
        if not best_match:
            if payload and payload[0:1] == b"\x16":
                best_match = self._fingerprints.get("HTTPS")
                best_confidence = 0.75
                matched_rules = ["heuristic:tls_handshake"]
            elif dst_port == 443 or src_port == 443:
                best_match = self._fingerprints.get("HTTPS")
                best_confidence = 0.65
                matched_rules = ["heuristic:port_443"]
            elif dst_port == 53 or src_port == 53:
                best_match = self._fingerprints.get("DNS")
                best_confidence = 0.7
                matched_rules = ["heuristic:port_53"]

        # 4. 未知协议
        if not best_match:
            best_match = ProtocolFingerprint(
                name="Unknown",
                category=ProtocolCategory.UNKNOWN,
                default_ports=[],
                description="未识别的协议",
                threat_level=ThreatLevel.LOW,
            )
            best_confidence = 0.0
            matched_rules = ["no_match"]

        # 添加随机波动
        best_confidence = min(best_confidence + random.uniform(-0.02, 0.02), 0.99)
        best_confidence = max(best_confidence, 0.0)

        result = DPIResult(
            protocol=best_match.name,
            category=best_match.category,
            confidence=round(best_confidence, 4),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            payload_size=len(payload),
            is_encrypted=best_match.is_encrypted,
            threat_level=best_match.threat_level,
            matched_rules=matched_rules,
            metadata={
                "description": best_match.description,
                "default_ports": best_match.default_ports,
            },
        )

        # 更新统计
        self._update_statistics(result)
        self._results.append(result)

        # 异常检测
        self._check_anomalies(result)

        return result

    def _update_statistics(self, result: DPIResult) -> None:
        """更新统计信息。"""
        self._statistics.total_packets += 1
        self._statistics.total_bytes += result.payload_size

        # 协议计数
        self._statistics.protocol_counts[result.protocol] = (
            self._statistics.protocol_counts.get(result.protocol, 0) + 1
        )

        # 类别计数
        self._statistics.category_counts[result.category.value] = (
            self._statistics.category_counts.get(result.category.value, 0) + 1
        )

        # 威胁等级计数
        self._statistics.threat_counts[result.threat_level.value] = (
            self._statistics.threat_counts.get(result.threat_level.value, 0) + 1
        )

        # 协议字节数
        self._statistics.protocol_bytes[result.protocol] = (
            self._statistics.protocol_bytes.get(result.protocol, 0) + result.payload_size
        )

        # 平均置信度
        self._confidence_sum += result.confidence
        self._statistics.avg_confidence = (
            self._confidence_sum / self._statistics.total_packets
        )

    def _check_anomalies(self, result: DPIResult) -> None:
        """检查异常。"""
        # 低置信度检测
        if result.confidence < 0.3 and result.protocol != "Unknown":
            anomaly = AnomalyDetection(
                anomaly_type="low_confidence",
                severity=ThreatLevel.LOW,
                description=f"协议 {result.confidence:.0%} 置信度较低",
                source_ip=result.src_ip,
                protocol=result.protocol,
                details={"confidence": result.confidence},
            )
            self._anomalies.append(anomaly)
            self._statistics.anomaly_count += 1

        # 高威胁协议
        if result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            anomaly = AnomalyDetection(
                anomaly_type="high_threat_protocol",
                severity=result.threat_level,
                description=f"检测到高威胁协议: {result.protocol}",
                source_ip=result.src_ip,
                protocol=result.protocol,
                details={"threat_level": result.threat_level.value},
            )
            self._anomalies.append(anomaly)
            self._statistics.anomaly_count += 1

        # 非标准端口
        fp = self._fingerprints.get(result.protocol)
        if fp and fp.default_ports:
            if (
                result.src_port not in fp.default_ports
                and result.dst_port not in fp.default_ports
                and result.src_port > 0
                and result.dst_port > 0
            ):
                anomaly = AnomalyDetection(
                    anomaly_type="non_standard_port",
                    severity=ThreatLevel.LOW,
                    description=f"{result.protocol} 使用非标准端口",
                    source_ip=result.src_ip,
                    protocol=result.protocol,
                    details={
                        "src_port": result.src_port,
                        "dst_port": result.dst_port,
                        "standard_ports": fp.default_ports,
                    },
                )
                self._anomalies.append(anomaly)
                self._statistics.anomaly_count += 1

    def get_statistics(self) -> dict[str, Any]:
        """获取协议统计信息。"""
        return self._statistics.to_dict()

    def get_traffic_classification(self) -> list[dict[str, Any]]:
        """获取流量分类。"""
        total = self._statistics.total_packets
        if total == 0:
            return []

        classifications: dict[str, dict[str, Any]] = {}

        for result in self._results:
            cat = result.category.value
            if cat not in classifications:
                classifications[cat] = {
                    "category": cat,
                    "protocols": set(),
                    "packet_count": 0,
                    "byte_count": 0,
                    "confidence_sum": 0.0,
                }
            classifications[cat]["protocols"].add(result.protocol)
            classifications[cat]["packet_count"] += 1
            classifications[cat]["byte_count"] += result.payload_size
            classifications[cat]["confidence_sum"] += result.confidence

        result_list = []
        for cat_data in classifications.values():
            count = cat_data["packet_count"]
            result_list.append({
                "category": cat_data["category"],
                "protocols": sorted(cat_data["protocols"]),
                "packet_count": count,
                "byte_count": cat_data["byte_count"],
                "percentage": round(count / total * 100, 2),
                "avg_confidence": round(cat_data["confidence_sum"] / count, 4) if count > 0 else 0,
            })

        result_list.sort(key=lambda x: x["packet_count"], reverse=True)
        return result_list

    def get_anomalies(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取异常检测结果。"""
        return [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "anomaly_type": a.anomaly_type,
                "severity": a.severity.value,
                "description": a.description,
                "source_ip": a.source_ip,
                "protocol": a.protocol,
                "details": a.details,
            }
            for a in self._anomalies[-limit:]
        ]

    def get_protocol_distribution(self) -> dict[str, Any]:
        """获取协议分布数据（用于图表）。"""
        total = self._statistics.total_packets
        if total == 0:
            return {
                "protocols": [],
                "counts": [],
                "percentages": [],
                "total": 0,
            }

        sorted_protocols = sorted(
            self._statistics.protocol_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        protocols = []
        counts = []
        percentages = []

        for name, count in sorted_protocols:
            protocols.append(name)
            counts.append(count)
            percentages.append(round(count / total * 100, 2))

        return {
            "protocols": protocols,
            "counts": counts,
            "percentages": percentages,
            "total": total,
        }

    def get_recent_results(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取最近的分析结果。"""
        return [r.to_dict() for r in self._results[-limit:]]

    def generate_sample_traffic(self, count: int = 50) -> list[dict[str, Any]]:
        import socket
        results = []
        for _ in range(count):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = bytes(random.randint(0, 255) for _ in range(random.randint(32, 256)))
                sock.sendto(payload, ('127.0.0.1', 9997))
                sock.close()
                result = self.analyze_packet(
                    payload=payload,
                    src_ip="127.0.0.1",
                    dst_ip="127.0.0.1",
                    src_port=random.randint(1024, 65535),
                    dst_port=random.choice([80, 443, 1723, 1701, 1194, 500, 51820]),
                )
                results.append(result.to_dict())
            except Exception:
                pass
        return results

    def clear(self) -> None:
        """清除所有数据。"""
        self._results.clear()
        self._anomalies.clear()
        self._statistics = ProtocolStatistics()
        self._confidence_sum = 0.0


# 全局 DPI 服务实例
dpi_service = DPIService()
