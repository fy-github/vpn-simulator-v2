"""攻击模型。

提供网络攻击模拟的数据模型，支持 5 种攻击类型：
中间人攻击、重放攻击、暴力破解、协议降级和流量分析。

每个攻击实例跟踪其状态和执行结果。

Example:
    >>> attack = AttackInfo(
    ...     id="atk-001",
    ...     attack_type=AttackType.MITM,
    ...     params={"proxy_port": 8888},
    ...     target="pptp",
    ... )
    >>> attack.status
    AttackStatus.PENDING
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AttackType(Enum):
    """攻击类型枚举。

    Attributes:
        MITM: 中间人攻击，拦截和篡改通信数据。
        REPLAY: 重放攻击，捕获并重放合法报文。
        BRUTE_FORCE: 暴力破解，穷举尝试认证凭据。
        DOWNGRADE: 协议降级攻击，强制使用弱加密协议。
        TRAFFIC_ANALYSIS: 流量分析，分析通信模式和元数据。
    """

    MITM = "mitm"
    REPLAY = "replay"
    BRUTE_FORCE = "brute_force"
    DOWNGRADE = "downgrade"
    TRAFFIC_ANALYSIS = "traffic_analysis"


class AttackStatus(Enum):
    """攻击状态枚举。

    Attributes:
        PENDING: 等待执行。
        RUNNING: 正在执行。
        COMPLETED: 执行完成。
        FAILED: 执行失败。
        STOPPED: 已停止。
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AttackResult:
    """攻击结果数据类。

    Attributes:
        success: 攻击是否成功。
        data: 攻击获取的数据（如捕获的凭据、报文等）。
        error: 错误信息（攻击失败时）。
        duration_seconds: 攻击持续时间（秒）。
        attempts: 尝试次数（暴力破解等场景）。
    """

    success: bool = False
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        """将结果转换为字典。

        Returns:
            包含所有结果信息的字典。
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "attempts": self.attempts,
        }


@dataclass
class AttackInfo:
    """攻击信息数据类。

    封装一个攻击实例的完整信息。

    Attributes:
        id: 攻击唯一标识符（UUID）。
        attack_type: 攻击类型。
        status: 攻击状态。
        params: 攻击参数字典。
        target: 攻击目标（协议名称、连接 ID 等）。
        started_at: 开始时间。
        completed_at: 完成时间。
        result: 攻击结果。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attack_type: AttackType = AttackType.MITM
    status: AttackStatus = AttackStatus.PENDING
    params: dict[str, Any] = field(default_factory=dict)
    target: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[AttackResult] = None

    def to_dict(self) -> dict[str, Any]:
        """将攻击信息转换为字典。

        Returns:
            包含所有攻击信息的字典。
        """
        return {
            "id": self.id,
            "type": self.attack_type.value,
            "status": self.status.value,
            "params": self.params,
            "target": self.target,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result.to_dict() if self.result else None,
        }

    def mark_running(self) -> None:
        """将攻击标记为正在执行。"""
        self.status = AttackStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: AttackResult) -> None:
        """将攻击标记为完成。

        Args:
            result: 攻击结果。
        """
        self.status = AttackStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """将攻击标记为失败。

        Args:
            error: 错误信息。
        """
        self.status = AttackStatus.FAILED
        self.completed_at = datetime.now()
        self.result = AttackResult(success=False, error=error)

    def mark_stopped(self) -> None:
        """将攻击标记为已停止。"""
        self.status = AttackStatus.STOPPED
        self.completed_at = datetime.now()


class AttackManager:
    """攻击管理器。

    负责攻击的创建、查询、状态更新和移除。
    """

    def __init__(self) -> None:
        """初始化攻击管理器。"""
        self._attacks: dict[str, AttackInfo] = {}

    async def create_attack(
        self,
        attack_type: AttackType,
        params: Optional[dict[str, Any]] = None,
        target: str = "",
    ) -> AttackInfo:
        """创建一个攻击实例。

        Args:
            attack_type: 攻击类型。
            params: 攻击参数。
            target: 攻击目标。

        Returns:
            新创建的攻击信息。
        """
        attack = AttackInfo(
            attack_type=attack_type,
            params=params or {},
            target=target,
        )
        self._attacks[attack.id] = attack
        return attack

    async def get_attack(self, attack_id: str) -> Optional[AttackInfo]:
        """获取指定攻击。

        Args:
            attack_id: 攻击 ID。

        Returns:
            攻击信息，不存在返回 None。
        """
        return self._attacks.get(attack_id)

    async def list_attacks(
        self,
        attack_type: Optional[AttackType] = None,
        status: Optional[AttackStatus] = None,
    ) -> list[AttackInfo]:
        """列出攻击。

        Args:
            attack_type: 可选的攻击类型过滤。
            status: 可选的攻击状态过滤。

        Returns:
            攻击信息列表。
        """
        attacks = list(self._attacks.values())
        if attack_type:
            attacks = [a for a in attacks if a.attack_type == attack_type]
        if status:
            attacks = [a for a in attacks if a.status == status]
        return attacks

    async def remove_attack(self, attack_id: str) -> bool:
        """移除攻击。

        Args:
            attack_id: 攻击 ID。

        Returns:
            True 表示成功移除，False 表示攻击不存在。
        """
        if attack_id in self._attacks:
            del self._attacks[attack_id]
            return True
        return False

    async def start_attack(self, attack_id: str) -> Optional[AttackInfo]:
        """启动攻击。

        Args:
            attack_id: 攻击 ID。

        Returns:
            更新后的攻击信息，不存在返回 None。
        """
        attack = self._attacks.get(attack_id)
        if attack:
            attack.mark_running()
        return attack

    async def stop_attack(self, attack_id: str) -> Optional[AttackInfo]:
        """停止攻击。

        Args:
            attack_id: 攻击 ID。

        Returns:
            更新后的攻击信息，不存在返回 None。
        """
        attack = self._attacks.get(attack_id)
        if attack and attack.status == AttackStatus.RUNNING:
            attack.mark_stopped()
        return attack

    async def complete_attack(
        self, attack_id: str, result: AttackResult
    ) -> Optional[AttackInfo]:
        """完成攻击。

        Args:
            attack_id: 攻击 ID。
            result: 攻击结果。

        Returns:
            更新后的攻击信息，不存在返回 None。
        """
        attack = self._attacks.get(attack_id)
        if attack:
            attack.mark_completed(result)
        return attack

    async def fail_attack(
        self, attack_id: str, error: str
    ) -> Optional[AttackInfo]:
        """标记攻击失败。

        Args:
            attack_id: 攻击 ID。
            error: 错误信息。

        Returns:
            更新后的攻击信息，不存在返回 None。
        """
        attack = self._attacks.get(attack_id)
        if attack:
            attack.mark_failed(error)
        return attack
