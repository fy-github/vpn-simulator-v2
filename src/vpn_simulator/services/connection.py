"""连接管理服务。

提供 VPN 连接的创建、查询、状态更新和移除等业务逻辑。
协调 Domain 层的 ConnectionManager 和数据库持久化。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> service = ConnectionService(event_bus, config_manager, db_manager)
    >>> conn = await service.create_connection("pptp", remote_address="10.0.0.1")
    >>> await service.update_connection_state(conn["id"], "connected")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import ConnectionRecord, DatabaseManager
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.connection import (
    ConnectionInfo,
    ConnectionManager,
    ConnectionState,
    ConnectionType,
)

logger = structlog.get_logger(__name__)


class ConnectionService:
    """连接管理服务。

    负责 VPN 连接的全生命周期管理，包括创建、状态更新、
    统计信息收集和持久化。通过事件总线发布连接相关事件。

    Attributes:
        _event_bus: 事件总线实例。
        _config_manager: 配置管理器实例。
        _db_manager: 数据库管理器实例。
        _connection_manager: 领域层连接管理器实例。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        """初始化连接管理服务。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._connection_manager = ConnectionManager()

    async def create_connection(
        self,
        protocol: str,
        connection_type: str = "client",
        local_address: str = "",
        local_port: int = 0,
        remote_address: str = "",
        remote_port: int = 0,
        protocol_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """创建一个新的 VPN 连接。

        在领域层创建连接对象，持久化到数据库，并发布连接创建事件。

        Args:
            protocol: 协议名称（如 "pptp", "l2tp"）。
            connection_type: 连接类型，"client" 或 "server"。
            local_address: 本地地址。
            local_port: 本地端口。
            remote_address: 远程地址。
            remote_port: 远程端口。
            protocol_data: 协议特定的额外数据。

        Returns:
            新创建的连接信息字典。
        """
        conn_type = ConnectionType(connection_type)
        conn = await self._connection_manager.create_connection(
            protocol=protocol,
            connection_type=conn_type,
            local_address=local_address,
            local_port=local_port,
            remote_address=remote_address,
            remote_port=remote_port,
            protocol_data=protocol_data or {},
        )

        # 持久化到数据库
        record = ConnectionRecord(
            id=conn.id,
            protocol=conn.protocol,
            state=conn.state.value,
            connection_type=conn.connection_type.value,
            local_address=conn.local_address,
            local_port=conn.local_port,
            remote_address=conn.remote_address,
            remote_port=conn.remote_port,
            created_at=conn.created_at,
            protocol_data=conn.protocol_data,
        )
        async with self._db_manager.session() as session:
            session.add(record)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.CONNECTION_CREATED,
            conn.to_dict(),
            source="ConnectionService",
        )

        logger.info(
            "connection_created",
            connection_id=conn.id,
            protocol=protocol,
            remote_address=remote_address,
        )
        return conn.to_dict()

    async def get_connection(self, connection_id: str) -> Optional[dict[str, Any]]:
        """获取指定连接的详细信息。

        Args:
            connection_id: 连接 ID。

        Returns:
            连接信息字典，不存在返回 None。
        """
        conn = await self._connection_manager.get_connection(connection_id)
        if conn is None:
            logger.warning("connection_not_found", connection_id=connection_id)
            return None
        return conn.to_dict()

    async def list_connections(
        self,
        protocol: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """列出连接。

        Args:
            protocol: 可选的协议名称过滤。
            state: 可选的连接状态过滤。

        Returns:
            连接信息字典列表。
        """
        connections = await self._connection_manager.list_connections(protocol)

        if state:
            target_state = ConnectionState(state)
            connections = [c for c in connections if c.state == target_state]

        result = [c.to_dict() for c in connections]
        logger.info("connections_listed", count=len(result), protocol=protocol, state=state)
        return result

    async def update_connection_state(
        self,
        connection_id: str,
        state: str,
    ) -> dict[str, Any]:
        """更新连接状态。

        更新领域模型中的连接状态，同步更新数据库记录，
        并根据状态变化发布相应事件。

        Args:
            connection_id: 连接 ID。
            state: 新的连接状态（connecting, connected, disconnecting, disconnected, error）。

        Returns:
            状态变更信息字典。

        Raises:
            ValueError: 连接不存在。
        """
        new_state = ConnectionState(state)
        state_event = await self._connection_manager.update_state(connection_id, new_state)

        # 更新数据库记录
        conn = await self._connection_manager.get_connection(connection_id)
        if conn:
            async with self._db_manager.session() as session:
                stmt = select(ConnectionRecord).where(ConnectionRecord.id == connection_id)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if record:
                    record.state = conn.state.value
                    record.connected_at = conn.connected_at
                    record.disconnected_at = conn.disconnected_at

        # 根据状态发布不同事件
        event_map = {
            ConnectionState.CONNECTED: EventTypes.CONNECTION_ESTABLISHED,
            ConnectionState.DISCONNECTED: EventTypes.CONNECTION_CLOSED,
            ConnectionState.ERROR: EventTypes.CONNECTION_ERROR,
        }
        event_name = event_map.get(new_state, EventTypes.CONNECTION_CREATED)

        await self._event_bus.emit(
            event_name,
            {
                "connection_id": state_event.connection_id,
                "old_state": state_event.old_state.value,
                "new_state": state_event.new_state.value,
                "timestamp": state_event.timestamp,
            },
            source="ConnectionService",
        )

        logger.info(
            "connection_state_updated",
            connection_id=connection_id,
            old_state=state_event.old_state.value,
            new_state=state_event.new_state.value,
        )
        return {
            "connection_id": state_event.connection_id,
            "old_state": state_event.old_state.value,
            "new_state": state_event.new_state.value,
            "timestamp": state_event.timestamp,
        }

    async def update_connection_stats(
        self,
        connection_id: str,
        bytes_sent: int = 0,
        bytes_received: int = 0,
        packets_sent: int = 0,
        packets_received: int = 0,
    ) -> None:
        """更新连接统计信息。

        Args:
            connection_id: 连接 ID。
            bytes_sent: 新增发送字节数。
            bytes_received: 新增接收字节数。
            packets_sent: 新增发送报文数。
            packets_received: 新增接收报文数。
        """
        conn = await self._connection_manager.get_connection(connection_id)
        if conn is None:
            logger.warning("connection_not_found", connection_id=connection_id)
            return

        conn.bytes_sent += bytes_sent
        conn.bytes_received += bytes_received
        conn.packets_sent += packets_sent
        conn.packets_received += packets_received

        # 同步更新数据库
        async with self._db_manager.session() as session:
            stmt = select(ConnectionRecord).where(ConnectionRecord.id == connection_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.bytes_sent = conn.bytes_sent
                record.bytes_received = conn.bytes_received
                record.packets_sent = conn.packets_sent
                record.packets_received = conn.packets_received

    async def remove_connection(self, connection_id: str) -> bool:
        """移除连接。

        从领域模型中移除连接，更新数据库记录的断开时间。

        Args:
            connection_id: 连接 ID。

        Returns:
            True 表示成功移除，False 表示连接不存在。
        """
        conn = await self._connection_manager.get_connection(connection_id)
        if conn is None:
            return False

        # 如果连接尚未断开，先更新状态
        if conn.state not in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
            await self.update_connection_state(connection_id, "disconnected")

        # 从领域模型移除
        removed = await self._connection_manager.remove_connection(connection_id)

        if removed:
            await self._event_bus.emit(
                EventTypes.CONNECTION_CLOSED,
                {"connection_id": connection_id},
                source="ConnectionService",
            )
            logger.info("connection_removed", connection_id=connection_id)

        return removed

    async def get_connection_stats(self) -> dict[str, Any]:
        """获取连接统计汇总。

        Returns:
            包含总连接数、各状态连接数的统计字典。
        """
        all_connections = await self._connection_manager.list_connections()

        stats: dict[str, Any] = {
            "total": len(all_connections),
            "by_state": {},
            "by_protocol": {},
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_packets_sent": 0,
            "total_packets_received": 0,
        }

        for conn in all_connections:
            # 按状态统计
            state_val = conn.state.value
            stats["by_state"][state_val] = stats["by_state"].get(state_val, 0) + 1

            # 按协议统计
            stats["by_protocol"][conn.protocol] = stats["by_protocol"].get(conn.protocol, 0) + 1

            # 累计流量统计
            stats["total_bytes_sent"] += conn.bytes_sent
            stats["total_bytes_received"] += conn.bytes_received
            stats["total_packets_sent"] += conn.packets_sent
            stats["total_packets_received"] += conn.packets_received

        return stats
