"""数据库管理模块

提供 SQLAlchemy 2.0 异步数据库管理功能。
支持数据库初始化、会话管理和迁移。

Example:
    >>> from vpn_simulator.core.database import DatabaseManager
    >>> manager = DatabaseManager("sqlite+aiosqlite:///vpn_simulator.db")
    >>> await manager.initialize()
    >>> async with manager.session() as session:
    ...     result = await session.execute(select(Connection))
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


class ConnectionRecord(Base):
    """连接记录表"""

    __tablename__ = "connections"

    id = Column(String(36), primary_key=True)
    protocol = Column(String(50), nullable=False, index=True)
    state = Column(String(20), nullable=False, index=True)
    connection_type = Column(String(20), nullable=False)
    local_address = Column(String(45))
    local_port = Column(Integer)
    remote_address = Column(String(45))
    remote_port = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    connected_at = Column(DateTime)
    disconnected_at = Column(DateTime)
    bytes_sent = Column(Integer, default=0)
    bytes_received = Column(Integer, default=0)
    packets_sent = Column(Integer, default=0)
    packets_received = Column(Integer, default=0)
    protocol_data = Column(JSON, default=dict)
    error_message = Column(Text)
    error_code = Column(String(50))


class PacketRecord(Base):
    """报文记录表"""

    __tablename__ = "packets"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    direction = Column(String(10), nullable=False)
    packet_type = Column(String(20), nullable=False)
    protocol = Column(String(50), nullable=False)
    src_ip = Column(String(45))
    dst_ip = Column(String(45))
    src_port = Column(Integer)
    dst_port = Column(Integer)
    raw_data = Column(Text)  # hex encoded
    fields = Column(JSON, default=list)
    connection_id = Column(String(36), index=True)
    session_id = Column(String(36))


class StateTransitionRecord(Base):
    """状态机历史表"""

    __tablename__ = "state_transitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol = Column(String(50), nullable=False, index=True)
    connection_id = Column(String(36), index=True)
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False)
    event = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    context = Column(JSON, default=dict)


class FaultRecord(Base):
    """故障配置表"""

    __tablename__ = "faults"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    params = Column(JSON, nullable=False)
    target = Column(String(100))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime)


class ImpairmentRecord(Base):
    """时间变化网络损伤配置表（F1）"""

    __tablename__ = "impairments"

    id = Column(String(36), primary_key=True)
    name = Column(String(100))
    fault_type = Column(String(50), nullable=False)
    param = Column(String(50), nullable=False)
    change_type = Column(String(20), nullable=False)
    start_value = Column(Float, nullable=False)
    end_value = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    period_seconds = Column(Float, default=0.0)
    step_at_seconds = Column(Float)
    target = Column(String(100))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)


class AttackRecord(Base):
    """攻击记录表"""

    __tablename__ = "attacks"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    target = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    params = Column(JSON, default=dict)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)
    result = Column(JSON)


class ValidationRecord(Base):
    """VPN 配置验证历史表（F2）"""

    __tablename__ = "validations"

    id = Column(String(36), primary_key=True)
    protocol = Column(String(50), nullable=False, index=True)
    config = Column(JSON, default=dict)
    status = Column(String(20), nullable=False)
    steps = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class ConfigHistoryRecord(Base):
    """配置历史表"""

    __tablename__ = "config_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config = Column(JSON, nullable=False)
    applied_at = Column(DateTime, default=lambda: datetime.now(UTC))
    applied_by = Column(String(100))


class TopologyRecord(Base):
    """拓扑配置表"""

    __tablename__ = "topologies"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    topology = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime)


class ProtocolRecord(Base):
    """协议运行状态表

    记录协议"运行/停止"状态，使应用重启后能恢复此前启动的协议。
    """

    __tablename__ = "protocols"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DatabaseManager:
    """数据库管理器

    提供异步数据库引擎和会话管理。
    使用 SQLAlchemy 2.0 异步模式。

    Attributes:
        database_url: 数据库连接 URL
        _engine: 异步数据库引擎
        _session_factory: 会话工厂

    Example:
        >>> manager = DatabaseManager("sqlite+aiosqlite:///vpn_simulator.db")
        >>> await manager.initialize()
        >>> async with manager.session() as session:
        ...     record = ConnectionRecord(id="123", protocol="pptp", state="connected")
        ...     session.add(record)
        ...     await session.commit()
        >>> await manager.close()
    """

    def __init__(self, database_url: str = "sqlite+aiosqlite:///vpn_simulator.db") -> None:
        """初始化数据库管理器

        Args:
            database_url: 数据库连接 URL，默认使用 SQLite
        """
        self.database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """初始化数据库

        创建引擎、注册事件监听器并创建所有表。
        """
        logger.info("database_initializing", url=self.database_url)

        self._engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
        )

        # SQLite 特殊配置
        if "sqlite" in self.database_url:

            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

        # 创建所有表
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("database_initialized")

    async def close(self) -> None:
        """关闭数据库连接

        清理引擎和会话工厂。
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("database_closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话

        提供异步上下文管理器，自动处理会话提交和回滚。

        Yields:
            异步数据库会话

        Raises:
            RuntimeError: 数据库未初始化

        Example:
            >>> async with manager.session() as session:
            ...     result = await session.execute(select(ConnectionRecord))
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @property
    def engine(self) -> AsyncEngine:
        """获取异步引擎

        Returns:
            异步数据库引擎

        Raises:
            RuntimeError: 数据库未初始化
        """
        if not self._engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def health_check(self) -> bool:
        try:
            async with self.session() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# ---------------------------------------------------------------------------
# 进程内共享的 DatabaseManager
#
# 应用为单进程内存模拟器，此处提供惰性单例，供应用启动时初始化、各服务
# 复用同一个已初始化的引擎，避免调用方各自 new DatabaseManager() 却从未
# initialize() 导致 `RuntimeError: Database not initialized`。
# ---------------------------------------------------------------------------

_default_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """获取进程内共享的 DatabaseManager 实例（惰性创建）。

    优先使用 VPN_SIM_DATABASE_URL 环境变量（与 ConfigManager 一致），
    未设置时回退到默认 SQLite URL。
    """
    global _default_manager
    if _default_manager is None:
        database_url = os.getenv("VPN_SIM_DATABASE_URL") or "sqlite+aiosqlite:///vpn_simulator.db"
        _default_manager = DatabaseManager(database_url)
    return _default_manager


async def initialize_database() -> DatabaseManager:
    """初始化共享数据库（幂等）。"""
    manager = get_database_manager()
    if manager._engine is None:
        await manager.initialize()
    return manager


async def close_database() -> None:
    """关闭共享数据库（幂等）。

    关闭引擎但保留单例对象，使下一次 initialize_database() 能在同一实例上
    重新初始化；各服务缓存的 manager 引用因此始终有效。
    """
    if _default_manager is not None:
        await _default_manager.close()
