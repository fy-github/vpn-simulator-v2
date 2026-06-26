"""连接模型。

提供 VPN 连接的状态追踪、生命周期管理和统计信息收集。
支持连接创建、状态更新、数据传输统计等核心功能。

Example:
    >>> manager = ConnectionManager()
    >>> conn = await manager.create_connection("pptp")
    >>> await manager.update_state(conn.id, ConnectionState.CONNECTED)
    >>> conn.bytes_sent += 1024
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ConnectionState(Enum):
    """连接状态枚举。

    Attributes:
        CONNECTING: 正在建立连接。
        CONNECTED: 连接已建立。
        DISCONNECTING: 正在断开连接。
        DISCONNECTED: 连接已断开。
        ERROR: 连接发生错误。
    """

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionType(Enum):
    """连接类型枚举。

    Attributes:
        CLIENT: 客户端连接。
        SERVER: 服务端连接。
    """

    CLIENT = "client"
    SERVER = "server"


@dataclass
class ConnectionInfo:
    """连接信息数据类。

    封装了连接的所有元数据，包括网络信息、时间信息、
    统计信息和协议特定数据。

    Attributes:
        id: 连接唯一标识符（UUID）。
        protocol: 协议名称（如 pptp、l2tp）。
        state: 当前连接状态。
        connection_type: 连接类型（客户端/服务端）。
        local_address: 本地地址。
        local_port: 本地端口。
        remote_address: 远程地址。
        remote_port: 远程端口。
        created_at: 连接创建时间。
        connected_at: 连接建立时间。
        disconnected_at: 连接断开时间。
        bytes_sent: 已发送字节数。
        bytes_received: 已接收字节数。
        packets_sent: 已发送报文数。
        packets_received: 已接收报文数。
        protocol_data: 协议特定的额外数据。
        error_message: 错误信息。
        error_code: 错误代码。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = ""
    state: ConnectionState = ConnectionState.CONNECTING
    connection_type: ConnectionType = ConnectionType.CLIENT

    local_address: str = ""
    local_port: int = 0
    remote_address: str = ""
    remote_port: int = 0

    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None

    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0

    protocol_data: dict[str, Any] = field(default_factory=dict)

    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """将连接信息转换为字典。

        所有 datetime 字段转换为 ISO 8601 格式字符串，
        枚举字段转换为其值。

        Returns:
            包含所有连接信息的字典。
        """
        return {
            "id": self.id,
            "protocol": self.protocol,
            "state": self.state.value,
            "connection_type": self.connection_type.value,
            "local_address": self.local_address,
            "local_port": self.local_port,
            "remote_address": self.remote_address,
            "remote_port": self.remote_port,
            "created_at": self.created_at.isoformat(),
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": (
                self.disconnected_at.isoformat() if self.disconnected_at else None
            ),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "protocol_data": self.protocol_data,
            "error_message": self.error_message,
            "error_code": self.error_code,
        }

    @property
    def duration(self) -> Optional[float]:
        """连接持续时间（秒）。

        Returns:
            如果连接已建立，返回持续秒数；否则返回 None。
        """
        if self.connected_at is None:
            return None
        end = self.disconnected_at or datetime.now()
        return (end - self.connected_at).total_seconds()


@dataclass
class ConnectionStateChangedEvent:
    """连接状态变更事件。

    Attributes:
        connection_id: 连接 ID。
        old_state: 变更前的状态。
        new_state: 变更后的状态。
        timestamp: 变更时间戳。
    """

    connection_id: str
    old_state: ConnectionState
    new_state: ConnectionState
    timestamp: str


class ConnectionManager:
    """连接管理器。

    负责连接的创建、查询、状态更新和移除。
    支持按协议过滤连接列表。
    """

    def __init__(self) -> None:
        """初始化连接管理器。"""
        self._connections: dict[str, ConnectionInfo] = {}

    async def create_connection(
        self, protocol: str, **kwargs: Any
    ) -> ConnectionInfo:
        """创建一个新连接。

        Args:
            protocol: 协议名称。
            **kwargs: 传递给 ConnectionInfo 的额外参数。

        Returns:
            新创建的连接信息。
        """
        conn = ConnectionInfo(protocol=protocol, **kwargs)
        self._connections[conn.id] = conn
        return conn

    async def update_state(
        self, conn_id: str, state: ConnectionState
    ) -> ConnectionStateChangedEvent:
        """更新连接状态。

        自动记录状态变更时间（connected_at / disconnected_at）。

        Args:
            conn_id: 连接 ID。
            state: 新的连接状态。

        Returns:
            状态变更事件。

        Raises:
            ValueError: 如果连接 ID 不存在。
        """
        conn = self._connections.get(conn_id)
        if not conn:
            raise ValueError(f"Connection {conn_id} not found")

        old_state = conn.state
        conn.state = state

        if state == ConnectionState.CONNECTED:
            conn.connected_at = datetime.now()
        elif state == ConnectionState.DISCONNECTED:
            conn.disconnected_at = datetime.now()

        return ConnectionStateChangedEvent(
            connection_id=conn_id,
            old_state=old_state,
            new_state=state,
            timestamp=datetime.now().isoformat(),
        )

    async def get_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """获取指定连接。

        Args:
            conn_id: 连接 ID。

        Returns:
            连接信息，不存在返回 None。
        """
        return self._connections.get(conn_id)

    async def list_connections(
        self, protocol: Optional[str] = None
    ) -> list[ConnectionInfo]:
        """列出连接。

        Args:
            protocol: 可选的协议名称过滤。

        Returns:
            连接信息列表。
        """
        connections = list(self._connections.values())
        if protocol:
            connections = [c for c in connections if c.protocol == protocol]
        return connections

    async def remove_connection(self, conn_id: str) -> bool:
        """移除连接。

        Args:
            conn_id: 连接 ID。

        Returns:
            True 表示成功移除，False 表示连接不存在。
        """
        if conn_id in self._connections:
            del self._connections[conn_id]
            return True
        return False
