"""大规模设备模拟模型（F7）。

表示一台大规模仿真中的网络设备。为支持 30,000+ 设备规模，设备属性
由索引确定性推导（惰性加载），服务层不一次性物化全部设备。

Example:
    >>> device = SimulatedDevice(index=7)
    >>> device.to_dict()["name"]
    'access_point-000007'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEVICE_STATES: list[str] = ["online", "idle", "busy", "offline"]


@dataclass
class SimulatedDevice:
    """一台大规模仿真设备，属性由索引确定性推导。

    Attributes:
        index: 设备索引（0-based，作为稳定标识）。
        name: 设备名。
        device_type: 设备类型。
        ip: 管理 IP（10.0.0.0/8 内确定性分配）。
        state: 设备状态。
        cpu_percent: CPU 占用（确定性伪随机）。
        memory_percent: 内存占用（确定性伪随机）。
    """

    index: int
    name: str
    device_type: str
    ip: str
    state: str
    cpu_percent: int
    memory_percent: int

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "index": self.index,
            "name": self.name,
            "device_type": self.device_type,
            "ip": self.ip,
            "state": self.state,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
        }
