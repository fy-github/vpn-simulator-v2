"""攻击管理服务。

提供网络攻击模拟的创建、查询、启动、停止和完成等业务逻辑。
协调 Domain 层的 AttackManager、Plugin 系统的攻击插件和数据库持久化。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> service = AttackService(event_bus, config_manager, db_manager)
    >>> attack = await service.create_attack("mitm", {"proxy_port": 8888}, target="pptp")
    >>> await service.start_attack(attack["id"])
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import AttackRecord, DatabaseManager
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.attack import (
    AttackInfo,
    AttackManager,
    AttackResult,
    AttackStatus,
    AttackType,
)
from vpn_simulator.plugins.registry import PluginRegistry, PluginType

logger = structlog.get_logger(__name__)


class AttackService:
    """攻击管理服务。

    负责网络攻击模拟的全生命周期管理，包括创建、查询、
    启动、停止和完成。通过事件总线发布攻击相关事件。

    Attributes:
        _event_bus: 事件总线实例。
        _config_manager: 配置管理器实例。
        _db_manager: 数据库管理器实例。
        _attack_manager: 领域层攻击管理器实例。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        """初始化攻击管理服务。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._attack_manager = AttackManager()

    async def list_attack_plugins(self) -> list[dict[str, Any]]:
        """列出所有已注册的攻击插件。

        Returns:
            攻击插件元数据列表。
        """
        plugins = PluginRegistry.get_by_type(PluginType.ATTACK)
        return [
            {
                "name": p.meta().name,
                "version": p.meta().version,
                "description": p.meta().description,
            }
            for p in plugins
        ]

    async def create_attack(
        self,
        attack_type: str,
        params: Optional[dict[str, Any]] = None,
        target: str = "",
    ) -> dict[str, Any]:
        """创建一个攻击实例。

        在领域层创建攻击对象，持久化到数据库。

        Args:
            attack_type: 攻击类型（mitm, replay, brute_force, downgrade, traffic_analysis）。
            params: 攻击参数字典。
            target: 攻击目标（协议名称、连接 ID 等）。

        Returns:
            新创建的攻击信息字典。

        Raises:
            ValueError: 无效的攻击类型。
        """
        try:
            at = AttackType(attack_type)
        except ValueError:
            raise ValueError(
                f"Invalid attack type '{attack_type}'. "
                f"Valid types: {[t.value for t in AttackType]}"
            )

        # 合并配置文件中的默认参数
        config_params = self._config_manager.config.attacks.get(attack_type, {})
        merged_params = {**config_params, **(params or {})}

        attack = await self._attack_manager.create_attack(
            attack_type=at,
            params=merged_params,
            target=target,
        )

        # 持久化到数据库
        record = AttackRecord(
            id=attack.id,
            type=attack.attack_type.value,
            target=attack.target,
            status=attack.status.value,
            params=attack.params,
            started_at=attack.started_at,
        )
        async with self._db_manager.session() as session:
            session.add(record)

        logger.info(
            "attack_created",
            attack_id=attack.id,
            attack_type=attack_type,
            target=target,
        )
        return attack.to_dict()

    async def get_attack(self, attack_id: str) -> Optional[dict[str, Any]]:
        """获取指定攻击的详细信息。

        Args:
            attack_id: 攻击 ID。

        Returns:
            攻击信息字典，不存在返回 None。
        """
        attack = await self._attack_manager.get_attack(attack_id)
        if attack is None:
            logger.warning("attack_not_found", attack_id=attack_id)
            return None
        return attack.to_dict()

    async def list_attacks(
        self,
        attack_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """列出攻击。

        Args:
            attack_type: 可选的攻击类型过滤。
            status: 可选的攻击状态过滤。

        Returns:
            攻击信息字典列表。
        """
        at = AttackType(attack_type) if attack_type else None
        ast = AttackStatus(status) if status else None
        attacks = await self._attack_manager.list_attacks(
            attack_type=at,
            status=ast,
        )
        result = [a.to_dict() for a in attacks]
        logger.info(
            "attacks_listed",
            count=len(result),
            attack_type=attack_type,
            status=status,
        )
        return result

    async def start_attack(self, attack_id: str) -> dict[str, Any]:
        """启动攻击。

        将攻击状态更新为运行中，更新数据库记录并发布事件。

        Args:
            attack_id: 攻击 ID。

        Returns:
            更新后的攻击信息字典。

        Raises:
            ValueError: 攻击不存在或状态不允许启动。
        """
        attack = await self._attack_manager.start_attack(attack_id)
        if attack is None:
            raise ValueError(f"Attack '{attack_id}' not found")

        if attack.status != AttackStatus.RUNNING:
            raise ValueError(
                f"Cannot start attack in state '{attack.status.value}'"
            )

        # 更新数据库
        await self._update_attack_in_db(attack)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.ATTACK_STARTED,
            attack.to_dict(),
            source="AttackService",
        )

        logger.info("attack_started", attack_id=attack_id)
        return attack.to_dict()

    async def stop_attack(self, attack_id: str) -> dict[str, Any]:
        """停止攻击。

        将攻击状态更新为已停止，更新数据库记录。

        Args:
            attack_id: 攻击 ID。

        Returns:
            更新后的攻击信息字典。

        Raises:
            ValueError: 攻击不存在。
        """
        attack = await self._attack_manager.stop_attack(attack_id)
        if attack is None:
            raise ValueError(f"Attack '{attack_id}' not found")

        # 更新数据库
        await self._update_attack_in_db(attack)

        logger.info("attack_stopped", attack_id=attack_id)
        return attack.to_dict()

    async def complete_attack(
        self,
        attack_id: str,
        success: bool,
        data: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_seconds: float = 0.0,
        attempts: int = 0,
    ) -> dict[str, Any]:
        """完成攻击。

        记录攻击结果，更新数据库并发布完成事件。

        Args:
            attack_id: 攻击 ID。
            success: 攻击是否成功。
            data: 攻击获取的数据。
            error: 错误信息（失败时）。
            duration_seconds: 攻击持续时间。
            attempts: 尝试次数。

        Returns:
            更新后的攻击信息字典。

        Raises:
            ValueError: 攻击不存在。
        """
        result = AttackResult(
            success=success,
            data=data or {},
            error=error,
            duration_seconds=duration_seconds,
            attempts=attempts,
        )

        attack = await self._attack_manager.complete_attack(attack_id, result)
        if attack is None:
            raise ValueError(f"Attack '{attack_id}' not found")

        # 更新数据库
        await self._update_attack_in_db(attack)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.ATTACK_COMPLETED,
            attack.to_dict(),
            source="AttackService",
        )

        logger.info(
            "attack_completed",
            attack_id=attack_id,
            success=success,
            duration_seconds=duration_seconds,
        )
        return attack.to_dict()

    async def fail_attack(
        self,
        attack_id: str,
        error: str,
    ) -> dict[str, Any]:
        """标记攻击失败。

        Args:
            attack_id: 攻击 ID。
            error: 错误信息。

        Returns:
            更新后的攻击信息字典。

        Raises:
            ValueError: 攻击不存在。
        """
        attack = await self._attack_manager.fail_attack(attack_id, error)
        if attack is None:
            raise ValueError(f"Attack '{attack_id}' not found")

        # 更新数据库
        await self._update_attack_in_db(attack)

        logger.info("attack_failed", attack_id=attack_id, error=error)
        return attack.to_dict()

    async def remove_attack(self, attack_id: str) -> bool:
        """移除攻击。

        从领域模型和数据库中同时移除攻击记录。

        Args:
            attack_id: 攻击 ID。

        Returns:
            True 表示成功移除，False 表示攻击不存在。
        """
        removed = await self._attack_manager.remove_attack(attack_id)
        if not removed:
            return False

        # 从数据库删除
        async with self._db_manager.session() as session:
            stmt = select(AttackRecord).where(AttackRecord.id == attack_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                await session.delete(record)

        logger.info("attack_removed", attack_id=attack_id)
        return True

    async def get_attack_stats(self) -> dict[str, Any]:
        """获取攻击统计汇总。

        Returns:
            包含总攻击数、各类型/状态攻击数的统计字典。
        """
        all_attacks = await self._attack_manager.list_attacks()

        stats: dict[str, Any] = {
            "total": len(all_attacks),
            "by_type": {},
            "by_status": {},
        }

        for attack in all_attacks:
            # 按类型统计
            at = attack.attack_type.value
            stats["by_type"][at] = stats["by_type"].get(at, 0) + 1

            # 按状态统计
            ast = attack.status.value
            stats["by_status"][ast] = stats["by_status"].get(ast, 0) + 1

        return stats

    async def _update_attack_in_db(self, attack: AttackInfo) -> None:
        """更新数据库中的攻击记录。

        Args:
            attack: 攻击信息对象。
        """
        async with self._db_manager.session() as session:
            stmt = select(AttackRecord).where(AttackRecord.id == attack.id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.status = attack.status.value
                record.started_at = attack.started_at
                record.completed_at = attack.completed_at
                record.result = attack.result.to_dict() if attack.result else None
