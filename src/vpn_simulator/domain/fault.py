"""故障模型。

提供网络故障注入的数据模型，支持 6 种故障类型：
延迟、丢包、带宽限制、报文重排、报文重复和数据损坏。

每个故障实例可配置参数、目标和激活状态。

Example:
    >>> fault = FaultInfo(
    ...     id="fault-001",
    ...     fault_type=FaultType.LATENCY,
    ...     params={"delay_ms": 100, "jitter_ms": 20},
    ...     target="pptp",
    ... )
    >>> fault.active
    True
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class FaultType(Enum):
    """故障类型枚举。

    Attributes:
        LATENCY: 延迟故障，在报文中引入额外延迟。
        PACKET_LOSS: 丢包故障，随机丢弃报文。
        BANDWIDTH: 带宽限制故障，限制传输带宽。
        REORDER: 报文重排故障，打乱报文顺序。
        DUPLICATE: 报文重复故障，复制发送报文。
        CORRUPT: 数据损坏故障，修改报文内容。
    """

    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    BANDWIDTH = "bandwidth"
    REORDER = "reorder"
    DUPLICATE = "duplicate"
    CORRUPT = "corrupt"


@dataclass
class FaultParams:
    """故障参数数据类。

    为每种故障类型提供标准化的参数定义。
    并非所有字段都适用于每种故障类型。

    Attributes:
        delay_ms: 延迟毫秒数（LATENCY）。
        jitter_ms: 抖动毫秒数（LATENCY）。
        loss_rate: 丢包率 0.0-1.0（PACKET_LOSS）。
        bandwidth_kbps: 带宽限制 Kbps（BANDWIDTH）。
        reorder_probability: 重排概率 0.0-1.0（REORDER）。
        duplicate_count: 重复次数（DUPLICATE）。
        corrupt_probability: 损坏概率 0.0-1.0（CORRUPT）。
    """

    delay_ms: int = 0
    jitter_ms: int = 0
    loss_rate: float = 0.0
    bandwidth_kbps: int = 0
    reorder_probability: float = 0.0
    duplicate_count: int = 0
    corrupt_probability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """将参数转换为字典。

        Returns:
            包含所有参数的字典。
        """
        return {
            "delay_ms": self.delay_ms,
            "jitter_ms": self.jitter_ms,
            "loss_rate": self.loss_rate,
            "bandwidth_kbps": self.bandwidth_kbps,
            "reorder_probability": self.reorder_probability,
            "duplicate_count": self.duplicate_count,
            "corrupt_probability": self.corrupt_probability,
        }


@dataclass
class FaultInfo:
    """故障信息数据类。

    封装一个故障注入实例的完整信息。

    Attributes:
        id: 故障唯一标识符（UUID）。
        fault_type: 故障类型。
        params: 故障参数字典。
        target: 故障目标（协议名称、连接 ID 等）。
        active: 故障是否激活。
        created_at: 创建时间。
        updated_at: 最后更新时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fault_type: FaultType = FaultType.LATENCY
    params: dict[str, Any] = field(default_factory=dict)
    target: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """将故障信息转换为字典。

        Returns:
            包含所有故障信息的字典。
        """
        return {
            "id": self.id,
            "type": self.fault_type.value,
            "params": self.params,
            "target": self.target,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def activate(self) -> None:
        """激活故障。"""
        self.active = True
        self.updated_at = datetime.now()

    def deactivate(self) -> None:
        """停用故障。"""
        self.active = False
        self.updated_at = datetime.now()


class FaultManager:
    """故障管理器。

    负责故障的创建、查询、激活/停用和移除。
    """

    def __init__(self) -> None:
        """初始化故障管理器。"""
        self._faults: dict[str, FaultInfo] = {}

    async def create_fault(
        self,
        fault_type: FaultType,
        params: Optional[dict[str, Any]] = None,
        target: str = "",
    ) -> FaultInfo:
        """创建一个故障。

        Args:
            fault_type: 故障类型。
            params: 故障参数。
            target: 故障目标。

        Returns:
            新创建的故障信息。
        """
        fault = FaultInfo(
            fault_type=fault_type,
            params=params or {},
            target=target,
        )
        self._faults[fault.id] = fault
        return fault

    async def get_fault(self, fault_id: str) -> Optional[FaultInfo]:
        """获取指定故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            故障信息，不存在返回 None。
        """
        return self._faults.get(fault_id)

    async def list_faults(
        self,
        fault_type: Optional[FaultType] = None,
        active_only: bool = False,
    ) -> list[FaultInfo]:
        """列出故障。

        Args:
            fault_type: 可选的故障类型过滤。
            active_only: 是否只返回激活的故障。

        Returns:
            故障信息列表。
        """
        faults = list(self._faults.values())
        if fault_type:
            faults = [f for f in faults if f.fault_type == fault_type]
        if active_only:
            faults = [f for f in faults if f.active]
        return faults

    async def remove_fault(self, fault_id: str) -> bool:
        """移除故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            True 表示成功移除，False 表示故障不存在。
        """
        if fault_id in self._faults:
            del self._faults[fault_id]
            return True
        return False

    async def activate_fault(self, fault_id: str) -> Optional[FaultInfo]:
        """激活故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            更新后的故障信息，不存在返回 None。
        """
        fault = self._faults.get(fault_id)
        if fault:
            fault.activate()
        return fault

    async def deactivate_fault(self, fault_id: str) -> Optional[FaultInfo]:
        """停用故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            更新后的故障信息，不存在返回 None。
        """
        fault = self._faults.get(fault_id)
        if fault:
            fault.deactivate()
        return fault
