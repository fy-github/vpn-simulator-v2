"""C2 攻击场景模型（F8）。

表示一种命令与控制（C2）攻击场景及其检测特征。仅用于教学/测试/防御研究，
不含任何可实际部署的恶意载荷（见伦理声明）。

Example:
    >>> scenario = C2Scenario(name="DNS C2", channel="dns", mitre_attck_id="T1071.004")
    >>> scenario.to_dict()["channel"]
    'dns'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class C2Scenario:
    """一种 C2 攻击场景。

    Attributes:
        id: 场景唯一标识。
        name: 场景名。
        description: 场景描述。
        channel: 通信信道（dns/http/https/icmp/websocket/dga）。
        technique: 使用的攻击技术。
        mitre_attck_id: 对应 MITRE ATT&CK 技术 ID。
        beacon_interval_seconds: 信标周期（秒）。
        indicators: 检测特征/指标（IOC）列表。
        severity: 严重程度（low/medium/high/critical）。
    """

    id: str = ""
    name: str = ""
    description: str = ""
    channel: str = ""
    technique: str = ""
    mitre_attck_id: str = ""
    beacon_interval_seconds: int = 60
    indicators: list[str] = field(default_factory=list)
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "channel": self.channel,
            "technique": self.technique,
            "mitre_attck_id": self.mitre_attck_id,
            "beacon_interval_seconds": self.beacon_interval_seconds,
            "indicators": self.indicators,
            "severity": self.severity,
        }


@dataclass
class C2SimulationResult:
    """一次 C2 场景模拟的结果。

    Attributes:
        scenario_id: 场景 ID。
        steps: 模拟步骤列表（stage/channel/detail）。
        detected_indicators: 该场景可被检测到的特征。
        started_at: 开始时间。
    """

    scenario_id: str = ""
    steps: list[dict[str, str]] = field(default_factory=list)
    detected_indicators: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "scenario_id": self.scenario_id,
            "steps": self.steps,
            "detected_indicators": self.detected_indicators,
            "started_at": self.started_at.isoformat(),
        }
