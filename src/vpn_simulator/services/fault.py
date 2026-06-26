"""故障注入服务。

提供网络故障的创建、查询、激活/停用和移除等业务逻辑。
协调 Domain 层的 FaultManager、Plugin 系统的故障插件和数据库持久化。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> service = FaultService(event_bus, config_manager, db_manager)
    >>> fault = await service.create_fault("latency", {"delay_ms": 100}, target="pptp")
    >>> await service.activate_fault(fault["id"])
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager, FaultRecord
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.fault import FaultInfo, FaultManager, FaultType
from vpn_simulator.plugins.registry import PluginRegistry, PluginType

logger = structlog.get_logger(__name__)


class FaultService:
    """故障注入服务。

    负责网络故障注入的全生命周期管理，包括创建、查询、
    激活/停用和移除。通过事件总线发布故障相关事件。

    Attributes:
        _event_bus: 事件总线实例。
        _config_manager: 配置管理器实例。
        _db_manager: 数据库管理器实例。
        _fault_manager: 领域层故障管理器实例。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        """初始化故障注入服务。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._fault_manager = FaultManager()

    async def list_fault_plugins(self) -> list[dict[str, Any]]:
        """列出所有已注册的故障注入插件。

        Returns:
            故障插件元数据列表。
        """
        plugins = PluginRegistry.get_by_type(PluginType.FAULT)
        return [
            {
                "name": p.meta().name,
                "version": p.meta().version,
                "description": p.meta().description,
            }
            for p in plugins
        ]

    async def create_fault(
        self,
        fault_type: str,
        params: Optional[dict[str, Any]] = None,
        target: str = "",
    ) -> dict[str, Any]:
        """创建一个故障注入实例。

        在领域层创建故障对象，持久化到数据库，并发布故障注入事件。

        Args:
            fault_type: 故障类型（latency, packet_loss, bandwidth, reorder, duplicate, corrupt）。
            params: 故障参数字典。
            target: 故障目标（协议名称、连接 ID 等）。

        Returns:
            新创建的故障信息字典。

        Raises:
            ValueError: 无效的故障类型。
        """
        try:
            ft = FaultType(fault_type)
        except ValueError:
            raise ValueError(
                f"Invalid fault type '{fault_type}'. "
                f"Valid types: {[t.value for t in FaultType]}"
            )

        # 合并配置文件中的默认参数
        config_params = self._config_manager.config.faults.get(fault_type, {})
        merged_params = {**config_params, **(params or {})}

        fault = await self._fault_manager.create_fault(
            fault_type=ft,
            params=merged_params,
            target=target,
        )

        # 持久化到数据库
        record = FaultRecord(
            id=fault.id,
            type=fault.fault_type.value,
            params=fault.params,
            target=fault.target,
            active=fault.active,
            created_at=fault.created_at,
        )
        async with self._db_manager.session() as session:
            session.add(record)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.FAULT_INJECTED,
            fault.to_dict(),
            source="FaultService",
        )

        logger.info(
            "fault_created",
            fault_id=fault.id,
            fault_type=fault_type,
            target=target,
        )
        return fault.to_dict()

    async def get_fault(self, fault_id: str) -> Optional[dict[str, Any]]:
        """获取指定故障的详细信息。

        Args:
            fault_id: 故障 ID。

        Returns:
            故障信息字典，不存在返回 None。
        """
        fault = await self._fault_manager.get_fault(fault_id)
        if fault is None:
            logger.warning("fault_not_found", fault_id=fault_id)
            return None
        return fault.to_dict()

    async def list_faults(
        self,
        fault_type: Optional[str] = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """列出故障。

        Args:
            fault_type: 可选的故障类型过滤。
            active_only: 是否只返回激活的故障。

        Returns:
            故障信息字典列表。
        """
        ft = FaultType(fault_type) if fault_type else None
        faults = await self._fault_manager.list_faults(
            fault_type=ft,
            active_only=active_only,
        )
        result = [f.to_dict() for f in faults]
        logger.info(
            "faults_listed",
            count=len(result),
            fault_type=fault_type,
            active_only=active_only,
        )
        return result

    async def activate_fault(self, fault_id: str) -> Optional[dict[str, Any]]:
        """激活故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            更新后的故障信息字典，不存在返回 None。
        """
        fault = await self._fault_manager.activate_fault(fault_id)
        if fault is None:
            logger.warning("fault_not_found", fault_id=fault_id)
            return None

        # 更新数据库
        await self._update_fault_in_db(fault)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.FAULT_INJECTED,
            {"fault_id": fault_id, "action": "activated"},
            source="FaultService",
        )

        logger.info("fault_activated", fault_id=fault_id)
        return fault.to_dict()

    async def deactivate_fault(self, fault_id: str) -> Optional[dict[str, Any]]:
        """停用故障。

        Args:
            fault_id: 故障 ID。

        Returns:
            更新后的故障信息字典，不存在返回 None。
        """
        fault = await self._fault_manager.deactivate_fault(fault_id)
        if fault is None:
            logger.warning("fault_not_found", fault_id=fault_id)
            return None

        # 更新数据库
        await self._update_fault_in_db(fault)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.FAULT_REMOVED,
            {"fault_id": fault_id, "action": "deactivated"},
            source="FaultService",
        )

        logger.info("fault_deactivated", fault_id=fault_id)
        return fault.to_dict()

    async def remove_fault(self, fault_id: str) -> bool:
        """移除故障。

        从领域模型和数据库中同时移除故障记录。

        Args:
            fault_id: 故障 ID。

        Returns:
            True 表示成功移除，False 表示故障不存在。
        """
        removed = await self._fault_manager.remove_fault(fault_id)
        if not removed:
            return False

        # 从数据库删除
        async with self._db_manager.session() as session:
            stmt = select(FaultRecord).where(FaultRecord.id == fault_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                await session.delete(record)

        await self._event_bus.emit(
            EventTypes.FAULT_REMOVED,
            {"fault_id": fault_id, "action": "removed"},
            source="FaultService",
        )

        logger.info("fault_removed", fault_id=fault_id)
        return True

    async def get_fault_stats(self) -> dict[str, Any]:
        """获取故障统计汇总。

        Returns:
            包含总故障数、各类型故障数、激活/停用数量的统计字典。
        """
        all_faults = await self._fault_manager.list_faults()

        stats: dict[str, Any] = {
            "total": len(all_faults),
            "active": sum(1 for f in all_faults if f.active),
            "inactive": sum(1 for f in all_faults if not f.active),
            "by_type": {},
        }

        for fault in all_faults:
            ft = fault.fault_type.value
            stats["by_type"][ft] = stats["by_type"].get(ft, 0) + 1

        return stats

    async def _update_fault_in_db(self, fault: FaultInfo) -> None:
        """更新数据库中的故障记录。

        Args:
            fault: 故障信息对象。
        """
        async with self._db_manager.session() as session:
            stmt = select(FaultRecord).where(FaultRecord.id == fault.id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.active = fault.active
                record.params = fault.params
                record.updated_at = fault.updated_at
