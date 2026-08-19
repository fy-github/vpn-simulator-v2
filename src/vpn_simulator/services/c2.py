"""C2 攻击场景模拟服务（F8）。

提供 6 种 C2 攻击场景（DNS C2、HTTP Beacon、Sliver HTTPS、ICMP 隧道、
WebSocket C2、DGA 回退）的行为模拟与检测特征输出，并暴露伦理声明。
场景仅模拟协议行为与检测特征，不含可部署的恶意载荷。

Example:
    >>> service = C2Service()
    >>> result = service.simulate("dns_c2")
    >>> result.detected_indicators
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import structlog
import yaml

from vpn_simulator.domain.c2 import C2Scenario, C2SimulationResult

logger = structlog.get_logger(__name__)

_ETHICS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "c2" / "ethics.yaml"

# 6 种 C2 场景（≥5）
_SCENARIOS: list[C2Scenario] = [
    C2Scenario(
        id="dns_c2",
        name="DNS C2",
        description="通过 DNS TXT 记录承载下行指令、子域名承载上行数据的 C2 信道。",
        channel="dns",
        technique="DNS 隧道 / 子域名编码",
        mitre_attck_id="T1071.004",
        beacon_interval_seconds=300,
        indicators=[
            "周期性 DNS 查询（固定间隔）",
            "DNS TXT 记录熵异常",
            "可疑子域名（随机前缀）",
            "单域名高频查询",
        ],
        severity="high",
    ),
    C2Scenario(
        id="http_beacon",
        name="HTTP Beacon",
        description="Cobalt Strike 风格的周期性 HTTP 信标，轮询 /submit 下发指令。",
        channel="http",
        technique="HTTP 轮询信标",
        mitre_attck_id="T1071.001",
        beacon_interval_seconds=60,
        indicators=["周期性 GET /submit", "User-Agent 异常", "固定长度载荷", "心跳抖动（jitter）"],
        severity="high",
    ),
    C2Scenario(
        id="https_sliver",
        name="Sliver HTTPS C2",
        description="Sliver 风格的 HTTPS C2，使用 TLS 隧道 + 证书指纹可识别。",
        channel="https",
        technique="TLS 隧道",
        mitre_attck_id="T1071.001",
        beacon_interval_seconds=30,
        indicators=["TLS JA3 指纹命中已知 C2 家族", "自签名/异常证书", "固定间隔 TLS 会话"],
        severity="critical",
    ),
    C2Scenario(
        id="icmp_tunnel",
        name="ICMP Tunnel",
        description="利用 ICMP Echo 载荷双向传输数据（非对称载荷大小）。",
        channel="icmp",
        technique="ICMP 数据外渗",
        mitre_attck_id="T1095",
        beacon_interval_seconds=10,
        indicators=["ICMP 载荷过大/非对称", "高频 ICMP Echo", "载荷高熵"],
        severity="medium",
    ),
    C2Scenario(
        id="websocket_c2",
        name="WebSocket C2",
        description="基于持久 WebSocket 长连接的双向实时 C2 信道。",
        channel="websocket",
        technique="持久 WebSocket 长连接",
        mitre_attck_id="T1071.001",
        beacon_interval_seconds=0,
        indicators=["长连接 WS 会话", "心跳帧（ping/pong）", "非浏览器 WS 握手"],
        severity="high",
    ),
    C2Scenario(
        id="dga_fallback",
        name="DGA Fallback",
        description="使用域生成算法（DGA）定期生成回退 C2 域名。",
        channel="dga",
        technique="域生成算法回退",
        mitre_attck_id="T1568.002",
        beacon_interval_seconds=3600,
        indicators=["域名熵高（随机字符）", "大量 NXDOMAIN 响应", "时间/种子同步的域名生成"],
        severity="medium",
    ),
]


class C2Service:
    """C2 攻击场景模拟服务。"""

    def __init__(self) -> None:
        self._scenarios = {s.id: s for s in _SCENARIOS}

    def list_scenarios(self) -> list[dict[str, Any]]:
        """列出所有 C2 场景。"""
        return [s.to_dict() for s in self._scenarios.values()]

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        """获取指定场景。"""
        scenario = self._scenarios.get(scenario_id)
        return scenario.to_dict() if scenario else None

    def simulate(self, scenario_id: str) -> C2SimulationResult | None:
        """模拟一次 C2 场景，返回行为步骤与检测特征。"""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return None

        interval = scenario.beacon_interval_seconds
        steps: list[dict[str, str]] = [
            {
                "stage": "staging",
                "channel": scenario.channel,
                "detail": "载荷初始化（抽象模拟，无真实载荷）",
            },
            {
                "stage": "beacon",
                "channel": scenario.channel,
                "detail": f"首轮信标（周期 {interval}s）",
            },
            {
                "stage": "c2_channel",
                "channel": scenario.channel,
                "detail": f"建立 {scenario.channel} 信道",
            },
            {"stage": "command", "channel": scenario.channel, "detail": "指令下发与回传（模拟）"},
        ]
        logger.info("c2_simulated", scenario_id=scenario_id, channel=scenario.channel)
        return C2SimulationResult(
            scenario_id=scenario_id,
            steps=steps,
            detected_indicators=list(scenario.indicators),
        )

    def detection_features(self, scenario_id: str) -> dict[str, Any] | None:
        """返回场景的检测特征（供 SIEM/EDR 规则编写参考）。"""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return None
        return {
            "scenario_id": scenario.id,
            "channel": scenario.channel,
            "mitre_attck_id": scenario.mitre_attck_id,
            "indicators": scenario.indicators,
        }

    def ethics(self) -> dict[str, Any]:
        """返回伦理声明（优先读取 config/c2/ethics.yaml）。"""
        fallback: dict[str, Any] = {
            "title": "C2 攻击场景模拟伦理声明",
            "purpose": "仅用于网络安全教学、防御测试与安全研究。",
            "restrictions": [
                "不包含可实际部署的恶意载荷或真实 C2 基础设施地址。",
                "严禁用于未经授权的入侵、破坏或窃取活动。",
            ],
            "authorization": "使用者须获得所在网络环境的合法授权。",
        }
        if not _ETHICS_PATH.exists():
            return fallback
        try:
            data = yaml.safe_load(_ETHICS_PATH.read_text(encoding="utf-8"))
            return cast(dict[str, Any], data) if data else fallback
        except Exception as e:
            logger.error("c2_ethics_load_error", path=str(_ETHICS_PATH), error=str(e))
            return fallback
