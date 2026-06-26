"""协议管理服务。

提供协议的注册、查询、启动和停止等业务逻辑。
协调 Domain 层的 ProtocolStateMachine 和 Plugin 系统的协议插件。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> service = ProtocolService(event_bus, config_manager, db_manager)
    >>> protocols = await service.list_protocols()
    >>> await service.start_protocol("pptp", port=1723)
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager, StateTransitionRecord
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.registry import PluginRegistry, PluginType

logger = structlog.get_logger(__name__)


class ProtocolService:
    """协议管理服务。

    负责协议插件的注册、查询、启动和停止。
    作为应用层服务，协调 Domain 模型和 Plugin 系统完成业务逻辑。

    Attributes:
        _event_bus: 事件总线，用于发布协议相关事件。
        _config_manager: 配置管理器，用于读取协议配置。
        _db_manager: 数据库管理器，用于持久化状态转换记录。
        _active_state_machines: 活跃的协议状态机实例映射。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        """初始化协议管理服务。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._active_state_machines: dict[str, ProtocolStateMachine] = {}

    async def list_protocols(self) -> list[dict[str, Any]]:
        """列出所有已注册的协议插件。

        从 PluginRegistry 中查询类型为 PROTOCOL 的插件，
        返回其元数据信息。

        Returns:
            协议插件元数据列表，每项包含 name, version, description 等字段。
        """
        plugins = PluginRegistry.get_by_type(PluginType.PROTOCOL)
        protocols = []
        for plugin in plugins:
            meta = plugin.meta()
            protocols.append({
                "name": meta.name,
                "version": meta.version,
                "author": meta.author,
                "description": meta.description,
                "dependencies": meta.dependencies,
                "config_schema": meta.config_schema,
            })
        logger.info("protocols_listed", count=len(protocols))
        return protocols

    async def get_protocol(self, name: str) -> Optional[dict[str, Any]]:
        """获取指定协议的详细信息。

        Args:
            name: 协议名称（如 "pptp", "l2tp"）。

        Returns:
            协议信息字典，不存在返回 None。
        """
        plugin = PluginRegistry.get(name)
        if plugin is None:
            logger.warning("protocol_not_found", name=name)
            return None

        meta = plugin.meta()
        if meta.plugin_type != PluginType.PROTOCOL:
            logger.warning("not_a_protocol", name=name, plugin_type=meta.plugin_type.value)
            return None

        config = self._config_manager.config
        protocol_config = config.protocols.get(name, {})

        return {
            "name": meta.name,
            "version": meta.version,
            "author": meta.author,
            "description": meta.description,
            "dependencies": meta.dependencies,
            "config_schema": meta.config_schema,
            "config": protocol_config,
            "active": name in self._active_state_machines,
        }

    async def start_protocol(
        self,
        name: str,
        port: Optional[int] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """启动指定协议。

        查找协议插件，创建状态机实例，触发启动事件，
        并将状态转换记录持久化到数据库。

        Args:
            name: 协议名称。
            port: 可选的监听端口，覆盖配置文件中的值。
            config: 可选的协议配置，覆盖默认配置。

        Returns:
            启动结果字典，包含 protocol, status, port 字段。

        Raises:
            ValueError: 协议不存在或不是协议类型的插件。
        """
        plugin = PluginRegistry.get(name)
        if plugin is None:
            raise ValueError(f"Protocol '{name}' not found")

        meta = plugin.meta()
        if meta.plugin_type != PluginType.PROTOCOL:
            raise ValueError(f"'{name}' is not a protocol plugin")

        if name in self._active_state_machines:
            logger.warning("protocol_already_active", name=name)
            return {"protocol": name, "status": "already_active"}

        # 合并配置
        file_config = self._config_manager.config.protocols.get(name, {})
        merged_config = {**file_config, **(config or {})}
        if port is not None:
            merged_config["port"] = port

        logger.info("starting_protocol", name=name, protocol_config=merged_config)

        # 发布协议启动事件
        await self._event_bus.emit(
            EventTypes.PROTOCOL_STARTED,
            {"protocol": name, "config": merged_config},
            source="ProtocolService",
        )

        result = {
            "protocol": name,
            "status": "started",
            "port": merged_config.get("port", 0),
            "config": merged_config,
        }
        logger.info("protocol_started", name=name, port=result["port"])
        return result

    async def stop_protocol(self, name: str) -> dict[str, Any]:
        """停止指定协议。

        停止协议的状态机实例，清理资源并发布停止事件。

        Args:
            name: 协议名称。

        Returns:
            停止结果字典，包含 protocol 和 status 字段。

        Raises:
            ValueError: 协议不存在或未启动。
        """
        if name not in self._active_state_machines:
            logger.warning("protocol_not_active", name=name)
            return {"protocol": name, "status": "not_active"}

        logger.info("stopping_protocol", name=name)

        # 清理状态机
        del self._active_state_machines[name]

        # 发布协议停止事件
        await self._event_bus.emit(
            EventTypes.PROTOCOL_STOPPED,
            {"protocol": name},
            source="ProtocolService",
        )

        logger.info("protocol_stopped", name=name)
        return {"protocol": name, "status": "stopped"}

    async def get_protocol_state(self, name: str) -> Optional[dict[str, Any]]:
        """获取协议当前状态。

        Args:
            name: 协议名称。

        Returns:
            状态机可视化数据字典，协议未激活返回 None。
        """
        sm = self._active_state_machines.get(name)
        if sm is None:
            return None
        return sm.get_visualization_data()

    async def trigger_protocol_event(
        self,
        name: str,
        event: str,
        context: Optional[dict[str, Any]] = None,
    ) -> bool:
        """触发协议状态机事件。

        Args:
            name: 协议名称。
            event: 事件名称。
            context: 可选的上下文数据。

        Returns:
            True 表示状态转换成功，False 表示失败。

        Raises:
            ValueError: 协议未激活。
        """
        sm = self._active_state_machines.get(name)
        if sm is None:
            raise ValueError(f"Protocol '{name}' is not active")

        old_state = sm.current_state
        result = await sm.trigger(event, context)

        if result:
            # 记录状态转换到数据库
            await self._record_state_transition(
                protocol=name,
                from_state=old_state or "",
                to_state=sm.current_state or "",
                event=event,
                context=context,
            )

            # 发布状态转换事件
            await self._event_bus.emit(
                EventTypes.STATE_TRANSITION,
                {
                    "protocol": name,
                    "from_state": old_state,
                    "to_state": sm.current_state,
                    "event": event,
                },
                source="ProtocolService",
            )

        return result

    async def get_state_history(
        self,
        name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """获取协议状态转换历史。

        从数据库查询指定协议的状态转换记录。

        Args:
            name: 协议名称。
            limit: 返回的最大记录数。

        Returns:
            状态转换记录列表。
        """
        async with self._db_manager.session() as session:
            stmt = (
                select(StateTransitionRecord)
                .where(StateTransitionRecord.protocol == name)
                .order_by(StateTransitionRecord.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

        return [
            {
                "protocol": r.protocol,
                "from_state": r.from_state,
                "to_state": r.to_state,
                "event": r.event,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "context": r.context,
            }
            for r in records
        ]

    async def _record_state_transition(
        self,
        protocol: str,
        from_state: str,
        to_state: str,
        event: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """将状态转换记录持久化到数据库。

        Args:
            protocol: 协议名称。
            from_state: 源状态。
            to_state: 目标状态。
            event: 触发事件。
            context: 可选的上下文数据。
        """
        record = StateTransitionRecord(
            protocol=protocol,
            from_state=from_state,
            to_state=to_state,
            event=event,
            context=context or {},
        )
        async with self._db_manager.session() as session:
            session.add(record)
        logger.debug(
            "state_transition_recorded",
            protocol=protocol,
            from_state=from_state,
            to_state=to_state,
            event=event,
        )
