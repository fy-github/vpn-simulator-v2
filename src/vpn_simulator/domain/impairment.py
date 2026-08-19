"""时间变化网络损伤模型（F1）。

在故障注入（fault）之上叠加"调度层"：一条损伤（Impairment）把某个故障
参数（如 latency.delay_ms、packet_loss.loss_rate）随时间按某条变化曲线
（linear / exponential / step / sine / random）从 start_value 演变到
end_value（或在其间波动）。损伤参数最终作用于真实报文流（Phase 1 后）。

Example:
    >>> imp = Impairment(
    ...     fault_type="latency", param="delay_ms",
    ...     change_type=ChangeType.LINEAR,
    ...     start_value=0.0, end_value=300.0, duration_seconds=60.0,
    ... )
    >>> imp.value_at(30.0)  # 150.0
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """损伤变化类型枚举。

    Attributes:
        LINEAR: 线性变化（匀速从 start 到 end）。
        EXPONENTIAL: 指数变化（先缓后陡逼近 end）。
        STEP: 阶跃变化（在 step_at 时刻从 start 跳变到 end）。
        SINE: 正弦波动（在 start 与 end 之间周期性振荡）。
        RANDOM: 随机变化（在 [start, end] 内随机取值）。
    """

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"
    SINE = "sine"
    RANDOM = "random"


_EXPONENTIAL_RATE = 5.0


@dataclass
class Impairment:
    """一条时间变化损伤。

    Attributes:
        id: 损伤唯一标识（UUID）。
        name: 展示名称（预设名称，可选）。
        fault_type: 目标故障类型（latency / packet_loss / bandwidth / reorder /
            duplicate / corrupt）。
        param: 随曲线变化的故障参数名（如 delay_ms、loss_rate、bandwidth_kbps）。
        change_type: 变化曲线类型。
        start_value: 起始值。
        end_value: 结束值（或正弦/随机的上界）。
        duration_seconds: 变化总时长（秒）。
        period_seconds: 正弦周期（秒），仅 SINE 使用；<=0 时取 duration。
        step_at_seconds: 阶跃时刻（秒），仅 STEP 使用；None 时取 duration/2。
        target: 损伤目标（协议名、连接 ID 等）。
        active: 是否激活。
        created_at: 创建时间。
        started_at: 启动时间。
        stopped_at: 停止时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    fault_type: str = "latency"
    param: str = "delay_ms"
    change_type: ChangeType = ChangeType.LINEAR
    start_value: float = 0.0
    end_value: float = 100.0
    duration_seconds: float = 60.0
    period_seconds: float = 0.0
    step_at_seconds: float | None = None
    target: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    def value_at(self, t: float) -> float:
        """返回曲线在已流逝时间 `t`（秒）处的损伤参数值。

        Args:
            t: 自启动以来的流逝秒数（可为负，负值按 0 处理）。

        Returns:
            损伤参数值（float）。除 RANDOM 外均为确定性函数。
        """
        t = max(0.0, t)
        if self.change_type == ChangeType.RANDOM:
            return random.uniform(self.start_value, self.end_value)

        # 非周期曲线在 duration 之后保持终态（clamp 到 [0,1]）。
        if self.change_type == ChangeType.SINE:
            period = self.period_seconds if self.period_seconds > 0 else self.duration_seconds
            mid = (self.start_value + self.end_value) / 2.0
            amp = (self.end_value - self.start_value) / 2.0
            return mid + amp * math.sin(2.0 * math.pi * t / period)

        x = min(t / self.duration_seconds, 1.0)
        if self.change_type == ChangeType.LINEAR:
            norm = x
        elif self.change_type == ChangeType.EXPONENTIAL:
            norm = (math.exp(_EXPONENTIAL_RATE * x) - 1.0) / (math.exp(_EXPONENTIAL_RATE) - 1.0)
        else:  # STEP
            step_at = (
                self.step_at_seconds
                if self.step_at_seconds is not None
                else self.duration_seconds / 2.0
            )
            return self.start_value if t < step_at else self.end_value

        return self.start_value + (self.end_value - self.start_value) * norm

    def timeline(self, samples: int = 60) -> list[dict[str, Any]]:
        """返回曲线的等间隔采样时间线（供图表展示）。

        Args:
            samples: 采样点数量（含 t=0 与 t=duration 两个端点）。

        Returns:
            形如 ``[{"t": 0.0, "value": ...}, ...]`` 的时间线列表。
        """
        samples = max(2, samples)
        step = self.duration_seconds / (samples - 1)
        return [
            {"t": round(step * i, 3), "value": round(self.value_at(step * i), 3)}
            for i in range(samples)
        ]

    def elapsed_seconds(self, now: datetime | None = None) -> float | None:
        """返回自启动以来的流逝秒数；未启动返回 None。"""
        if self.started_at is None:
            return None
        end = self.stopped_at or (now or datetime.now())
        return max(0.0, (end - self.started_at).total_seconds())

    def current_value(self, now: datetime | None = None) -> float | None:
        """返回当前时刻的损伤参数值；未启动返回 None。"""
        elapsed = self.elapsed_seconds(now)
        if elapsed is None:
            return None
        return self.value_at(elapsed)

    def start(self, now: datetime | None = None) -> None:
        """启动损伤，记录启动时间。"""
        self.active = True
        self.started_at = now or datetime.now()
        self.stopped_at = None

    def stop(self, now: datetime | None = None) -> None:
        """停止损伤，冻结当前进度。"""
        self.active = False
        self.stopped_at = now or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "fault_type": self.fault_type,
            "param": self.param,
            "change_type": self.change_type.value,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "duration_seconds": self.duration_seconds,
            "period_seconds": self.period_seconds,
            "step_at_seconds": self.step_at_seconds,
            "target": self.target,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
        }
