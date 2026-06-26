"""流量混淆测试服务。

提供 VPN 流量混淆技术的模拟测试和评估功能。
支持多种混淆技术的协议识别率、流量特征、Shannon 熵和检测难度评分。

Example:
    >>> from vpn_simulator.services.obfuscation import obfuscation_service
    >>> result = obfuscation_service.run_test("obfs4")
    >>> print(result.detection_rate)
    0.15
"""

from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ObfuscationTechnique(str, Enum):
    """支持的混淆技术。"""
    OBFS4 = "obfs4"
    SHADOWSOCKS = "shadowsocks"
    UDP2RAW = "udp2raw"
    MEEK = "meek"
    SNOWFLAKE = "snowflake"


class DetectionDifficulty(str, Enum):
    """检测难度等级。"""
    TRIVIAL = "trivial"       # 容易检测
    EASY = "easy"             # 较易检测
    MEDIUM = "medium"         # 中等难度
    HARD = "hard"             # 较难检测
    VERY_HARD = "very_hard"   # 很难检测


@dataclass
class TrafficFeatures:
    """流量特征。"""
    avg_packet_size: float = 0.0
    packet_size_std: float = 0.0
    avg_interval_ms: float = 0.0
    interval_std_ms: float = 0.0
    burst_ratio: float = 0.0
    protocol_distribution: dict[str, float] = field(default_factory=dict)
    port_distribution: dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "avg_packet_size": round(self.avg_packet_size, 2),
            "packet_size_std": round(self.packet_size_std, 2),
            "avg_interval_ms": round(self.avg_interval_ms, 2),
            "interval_std_ms": round(self.interval_std_ms, 2),
            "burst_ratio": round(self.burst_ratio, 3),
            "protocol_distribution": self.protocol_distribution,
            "port_distribution": {str(k): v for k, v in self.port_distribution.items()},
        }


@dataclass
class ShannonEntropy:
    """Shannon 熵分析。"""
    payload_entropy: float = 0.0
    header_entropy: float = 0.0
    overall_entropy: float = 0.0
    randomness_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_entropy": round(self.payload_entropy, 4),
            "header_entropy": round(self.header_entropy, 4),
            "overall_entropy": round(self.overall_entropy, 4),
            "randomness_score": round(self.randomness_score, 4),
        }


@dataclass
class ObfuscationTestResult:
    """混淆测试结果。"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    technique: ObfuscationTechnique = ObfuscationTechnique.OBFS4
    detection_rate: float = 0.0
    false_positive_rate: float = 0.0
    traffic_features: TrafficFeatures = field(default_factory=TrafficFeatures)
    shannon_entropy: ShannonEntropy = field(default_factory=ShannonEntropy)
    detection_difficulty: DetectionDifficulty = DetectionDifficulty.MEDIUM
    detection_score: float = 0.0
    packets_analyzed: int = 0
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "technique": self.technique.value,
            "detection_rate": round(self.detection_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "traffic_features": self.traffic_features.to_dict(),
            "shannon_entropy": self.shannon_entropy.to_dict(),
            "detection_difficulty": self.detection_difficulty.value,
            "detection_score": round(self.detection_score, 2),
            "packets_analyzed": self.packets_analyzed,
            "duration_seconds": round(self.duration_seconds, 2),
            "metadata": self.metadata,
        }


@dataclass
class TechniqueInfo:
    """混淆技术信息。"""
    name: str
    technique: ObfuscationTechnique
    description: str
    transport_protocol: str
    default_port: int
    encryption: str
    resistance_level: str
    use_cases: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "technique": self.technique.value,
            "description": self.description,
            "transport_protocol": self.transport_protocol,
            "default_port": self.default_port,
            "encryption": self.encryption,
            "resistance_level": self.resistance_level,
            "use_cases": self.use_cases,
        }


# 混淆技术配置
_TECHNIQUE_CONFIGS: dict[ObfuscationTechnique, dict[str, Any]] = {
    ObfuscationTechnique.OBFS4: {
        "name": "obfs4",
        "description": "流量随机化混淆，通过随机填充和加密使流量看起来像随机数据",
        "transport_protocol": "TCP",
        "default_port": 443,
        "encryption": "内置加密",
        "resistance_level": "高",
        "use_cases": ["绕过深度包检测", "规避协议识别"],
        "detection_rate_range": (0.05, 0.20),
        "false_positive_range": (0.02, 0.10),
        "packet_size_range": (64, 1500),
        "interval_range": (10, 200),
        "entropy_range": (7.5, 8.0),
        "detection_score_range": (80, 95),
    },
    ObfuscationTechnique.SHADOWSOCKS: {
        "name": "Shadowsocks",
        "description": "加密代理协议，使用 SOCKS5 代理和流加密",
        "transport_protocol": "TCP",
        "default_port": 8388,
        "encryption": "AES-256-GCM 等",
        "resistance_level": "中高",
        "use_cases": ["加密代理", "绕过地理限制"],
        "detection_rate_range": (0.15, 0.35),
        "false_positive_range": (0.05, 0.15),
        "packet_size_range": (100, 1400),
        "interval_range": (5, 100),
        "entropy_range": (7.0, 7.8),
        "detection_score_range": (65, 85),
    },
    ObfuscationTechnique.UDP2RAW: {
        "name": "udp2raw",
        "description": "将 UDP 流量封装为 TCP，绕过 UDP 限制和 QoS",
        "transport_protocol": "TCP (封装 UDP)",
        "default_port": 4096,
        "encryption": "可选加密",
        "resistance_level": "中",
        "use_cases": ["绕过 UDP 限制", "避免 QoS 限速"],
        "detection_rate_range": (0.25, 0.45),
        "false_positive_range": (0.08, 0.20),
        "packet_size_range": (128, 1500),
        "interval_range": (5, 50),
        "entropy_range": (6.5, 7.5),
        "detection_score_range": (50, 70),
    },
    ObfuscationTechnique.MEEK: {
        "name": "Meek",
        "description": "域名前置技术，通过 CDN 中转流量，看起来像正常 HTTPS",
        "transport_protocol": "HTTPS",
        "default_port": 443,
        "encryption": "TLS",
        "resistance_level": "很高",
        "use_cases": ["严格审查环境", "域名前置"],
        "detection_rate_range": (0.02, 0.12),
        "false_positive_range": (0.01, 0.05),
        "packet_size_range": (200, 1400),
        "interval_range": (20, 300),
        "entropy_range": (7.8, 8.0),
        "detection_score_range": (90, 98),
    },
    ObfuscationTechnique.SNOWFLAKE: {
        "name": "Snowflake",
        "description": "使用 WebRTC 技术通过志愿者代理中转流量",
        "transport_protocol": "WebRTC/DTLS",
        "default_port": 443,
        "encryption": "DTLS/SRTP",
        "resistance_level": "很高",
        "use_cases": ["抗封锁", "分布式代理"],
        "detection_rate_range": (0.03, 0.15),
        "false_positive_range": (0.02, 0.08),
        "packet_size_range": (100, 1200),
        "interval_range": (15, 250),
        "entropy_range": (7.6, 8.0),
        "detection_score_range": (85, 97),
    },
}


class ObfuscationService:
    """流量混淆测试服务。

    提供多种混淆技术的模拟测试，评估其对抗 DPI 检测的能力。
    """

    def __init__(self) -> None:
        """初始化混淆测试服务。"""
        self._results: list[ObfuscationTestResult] = []
        self._techniques: dict[ObfuscationTechnique, TechniqueInfo] = {}
        self._load_techniques()

    def _load_techniques(self) -> None:
        """加载混淆技术信息。"""
        for technique, config in _TECHNIQUE_CONFIGS.items():
            self._techniques[technique] = TechniqueInfo(
                name=config["name"],
                technique=technique,
                description=config["description"],
                transport_protocol=config["transport_protocol"],
                default_port=config["default_port"],
                encryption=config["encryption"],
                resistance_level=config["resistance_level"],
                use_cases=config["use_cases"],
            )

    def get_supported_techniques(self) -> list[dict[str, Any]]:
        """获取支持的混淆技术列表。

        Returns:
            技术信息列表。
        """
        return [t.to_dict() for t in self._techniques.values()]

    def _calculate_shannon_entropy(self, data: bytes) -> float:
        """计算 Shannon 熵。

        Args:
            data: 输入数据。

        Returns:
            Shannon 熵值 (0-8)。
        """
        if not data:
            return 0.0

        # 统计字节频率
        freq: dict[int, int] = defaultdict(int)
        for byte in data:
            freq[byte] += 1

        # 计算熵
        length = len(data)
        entropy = 0.0
        for count in freq.values():
            if count > 0:
                probability = count / length
                entropy -= probability * math.log2(probability)

        return entropy

    def _generate_simulated_traffic(
        self,
        technique: ObfuscationTechnique,
        packet_count: int = 1000,
    ) -> tuple[list[dict[str, Any]], TrafficFeatures, ShannonEntropy]:
        """生成模拟的混淆流量。

        Args:
            technique: 混淆技术。
            packet_count: 数据包数量。

        Returns:
            (数据包列表, 流量特征, Shannon 熵)。
        """
        config = _TECHNIQUE_CONFIGS[technique]
        packets = []
        sizes = []
        intervals = []
        protocols = defaultdict(int)
        ports = defaultdict(int)

        # 生成模拟数据包
        current_time = 0.0
        for _ in range(packet_count):
            # 随机包大小
            size = random.randint(*config["packet_size_range"])
            sizes.append(size)

            # 随机时间间隔
            interval = random.uniform(*config["interval_range"])
            intervals.append(interval)
            current_time += interval

            # 协议分布
            if technique == ObfuscationTechnique.UDP2RAW:
                proto = random.choices(["TCP", "UDP"], weights=[0.9, 0.1])[0]
            elif technique == ObfuscationTechnique.SNOWFLAKE:
                proto = random.choices(["DTLS", "SRTP", "STUN"], weights=[0.6, 0.3, 0.1])[0]
            else:
                proto = random.choices(["TCP", "TLS", "HTTPS"], weights=[0.7, 0.2, 0.1])[0]
            protocols[proto] += 1

            # 端口分布
            port = config["default_port"]
            if random.random() < 0.3:
                port = random.choice([80, 443, 8080, 8443])
            ports[port] += 1

            # 生成模拟载荷
            payload_entropy = random.uniform(*config["entropy_range"])
            payload = bytes([random.randint(0, 255) for _ in range(size)])

            packets.append({
                "timestamp": current_time,
                "size": size,
                "protocol": proto,
                "port": port,
                "payload_entropy": payload_entropy,
            })

        # 计算流量特征
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        size_std = math.sqrt(sum((s - avg_size) ** 2 for s in sizes) / len(sizes)) if sizes else 0
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        interval_std = math.sqrt(sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)) if intervals else 0

        # 计算突发比率
        burst_threshold = avg_interval * 0.5
        burst_packets = sum(1 for i in intervals if i < burst_threshold)
        burst_ratio = burst_packets / len(intervals) if intervals else 0

        # 协议分布百分比
        total_protocols = sum(protocols.values())
        protocol_dist = {k: v / total_protocols for k, v in protocols.items()}

        # 端口分布百分比
        total_ports = sum(ports.values())
        port_dist = {k: v / total_ports for k, v in ports.items()}

        traffic_features = TrafficFeatures(
            avg_packet_size=avg_size,
            packet_size_std=size_std,
            avg_interval_ms=avg_interval,
            interval_std_ms=interval_std,
            burst_ratio=burst_ratio,
            protocol_distribution=protocol_dist,
            port_distribution=port_dist,
        )

        # 计算 Shannon 熵
        # 使用模拟的熵值范围
        payload_entropy = random.uniform(*config["entropy_range"])
        header_entropy = random.uniform(3.0, 5.0)  # 头部熵通常较低
        overall_entropy = (payload_entropy * 0.7 + header_entropy * 0.3)

        shannon_entropy = ShannonEntropy(
            payload_entropy=payload_entropy,
            header_entropy=header_entropy,
            overall_entropy=overall_entropy,
            randomness_score=overall_entropy / 8.0,  # 归一化到 0-1
        )

        return packets, traffic_features, shannon_entropy

    def run_test(
        self,
        technique: str,
        packet_count: int = 1000,
        duration_seconds: float = 10.0,
    ) -> dict[str, Any]:
        """运行混淆测试。

        Args:
            technique: 混淆技术名称。
            packet_count: 模拟的数据包数量。
            duration_seconds: 模拟的测试时长。

        Returns:
            测试结果字典。

        Raises:
            ValueError: 不支持的混淆技术。
        """
        try:
            tech = ObfuscationTechnique(technique.lower())
        except ValueError:
            raise ValueError(f"不支持的混淆技术: {technique}。支持的技术: {[t.value for t in ObfuscationTechnique]}")

        config = _TECHNIQUE_CONFIGS[tech]

        # 生成模拟流量
        packets, traffic_features, shannon_entropy = self._generate_simulated_traffic(tech, packet_count)

        # 计算检测率
        detection_rate = random.uniform(*config["detection_rate_range"])
        false_positive_rate = random.uniform(*config["false_positive_range"])

        # 计算检测难度评分
        detection_score = random.uniform(*config["detection_score_range"])

        # 确定检测难度等级
        if detection_score >= 90:
            difficulty = DetectionDifficulty.VERY_HARD
        elif detection_score >= 75:
            difficulty = DetectionDifficulty.HARD
        elif detection_score >= 60:
            difficulty = DetectionDifficulty.MEDIUM
        elif detection_score >= 40:
            difficulty = DetectionDifficulty.EASY
        else:
            difficulty = DetectionDifficulty.TRIVIAL

        # 创建测试结果
        result = ObfuscationTestResult(
            technique=tech,
            detection_rate=detection_rate,
            false_positive_rate=false_positive_rate,
            traffic_features=traffic_features,
            shannon_entropy=shannon_entropy,
            detection_difficulty=difficulty,
            detection_score=detection_score,
            packets_analyzed=packet_count,
            duration_seconds=duration_seconds,
            metadata={
                "transport_protocol": config["transport_protocol"],
                "default_port": config["default_port"],
                "encryption": config["encryption"],
            },
        )

        self._results.append(result)
        return result.to_dict()

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取测试结果。

        Args:
            limit: 返回的最大结果数。

        Returns:
            测试结果列表。
        """
        return [r.to_dict() for r in self._results[-limit:]]

    def get_comparison(self) -> dict[str, Any]:
        """获取混淆技术对比结果。

        Returns:
            对比数据字典。
        """
        if not self._results:
            return {
                "techniques": [],
                "metrics": {},
                "rankings": {},
            }

        # 按技术分组
        by_technique: dict[str, list[ObfuscationTestResult]] = defaultdict(list)
        for result in self._results:
            by_technique[result.technique.value].append(result)

        # 计算每个技术的平均指标
        techniques = []
        metrics = {}
        detection_scores = []

        for tech_name, results in by_technique.items():
            avg_detection_rate = sum(r.detection_rate for r in results) / len(results)
            avg_false_positive = sum(r.false_positive_rate for r in results) / len(results)
            avg_score = sum(r.detection_score for r in results) / len(results)
            avg_entropy = sum(r.shannon_entropy.overall_entropy for r in results) / len(results)

            techniques.append(tech_name)
            metrics[tech_name] = {
                "avg_detection_rate": round(avg_detection_rate, 4),
                "avg_false_positive_rate": round(avg_false_positive, 4),
                "avg_detection_score": round(avg_score, 2),
                "avg_entropy": round(avg_entropy, 4),
                "test_count": len(results),
            }
            detection_scores.append((tech_name, avg_score))

        # 按检测难度评分排名（分数越高越难检测）
        detection_scores.sort(key=lambda x: x[1], reverse=True)
        rankings = {
            "by_detection_difficulty": [
                {"rank": i + 1, "technique": t[0], "score": round(t[1], 2)}
                for i, t in enumerate(detection_scores)
            ]
        }

        return {
            "techniques": techniques,
            "metrics": metrics,
            "rankings": rankings,
        }

    def clear(self) -> None:
        """清除所有测试结果。"""
        self._results.clear()


# 全局混淆测试服务实例
obfuscation_service = ObfuscationService()