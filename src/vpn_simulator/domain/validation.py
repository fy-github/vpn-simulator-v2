"""VPN 配置验证模型（F2）。

一条验证结果（ValidationResult）由若干验证步骤（ValidationStep）组成，
覆盖 7 个验证项：语法、端口可达性、握手、认证、隧道、延迟、吞吐。
握手/延迟/吞吐在 Phase 1 后对 WireGuard 走真实报文真测。

Example:
    >>> result = ValidationResult(
    ...     protocol="wireguard",
    ...     config={"port": 51820},
    ...     steps=[ValidationStep("syntax", StepStatus.PASS, "ok")],
    ... )
    >>> result.status  # "pass"
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepStatus(Enum):
    """验证步骤状态。"""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ValidationStep:
    """单个验证步骤。

    Attributes:
        name: 步骤名（syntax / port / handshake / auth / tunnel / latency / throughput）。
        status: 步骤状态。
        message: 可读说明（成功/失败/跳过原因）。
        metrics: 步骤级指标（如 {"latency_ms": 1.2}）。
    """

    name: str
    status: StepStatus
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "metrics": self.metrics,
        }


@dataclass
class ValidationResult:
    """一次完整的配置验证结果。

    Attributes:
        id: 结果唯一标识（UUID）。
        protocol: 协议名称。
        config: 被验证的配置。
        steps: 验证步骤列表。
        created_at: 验证时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    steps: list[ValidationStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def status(self) -> str:
        """整体状态：任一步骤 fail 则为 fail，否则 pass。"""
        return "fail" if any(s.status == StepStatus.FAIL for s in self.steps) else "pass"

    @property
    def metrics(self) -> dict[str, Any]:
        """聚合所有步骤的指标（后者覆盖同名前者的键）。"""
        merged: dict[str, Any] = {}
        for step in self.steps:
            merged.update(step.metrics)
        return merged

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "protocol": self.protocol,
            "config": self.config,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
        }
