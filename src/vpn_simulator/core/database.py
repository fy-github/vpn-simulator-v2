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

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

import structlog
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
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
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    context = Column(JSON, default=dict)


class FaultRecord(Base):
    """故障配置表"""

    __tablename__ = "faults"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    params = Column(JSON, nullable=False)
    target = Column(String(100))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime)


class AttackRecord(Base):
    """攻击记录表"""

    __tablename__ = "attacks"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    target = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    params = Column(JSON, default=dict)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)
    result = Column(JSON)


class ConfigHistoryRecord(Base):
    """配置历史表"""

    __tablename__ = "config_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config = Column(JSON, nullable=False)
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    applied_by = Column(String(100))


class TopologyRecord(Base):
    """拓扑配置表"""

    __tablename__ = "topologies"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    topology = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime)


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
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None

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

        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
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
