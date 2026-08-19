"""报文/状态历史保留策略服务（待确认问题 #3 落地）。

防止 `packets` 与 `state_transitions` 两张高写入量表无限增长：按「最大行数
（保留最新 N 行）」与「最大保留时长（TTL）」两个维度清理，支持手动触发与
周期性自动清理。

Example:
    >>> service = RetentionService(db_manager)
    >>> result = await service.cleanup()
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, select

from vpn_simulator.core.database import (
    DatabaseManager,
    PacketRecord,
    StateTransitionRecord,
    get_database_manager,
)

logger = structlog.get_logger(__name__)

# 默认保留策略
DEFAULT_MAX_PACKETS = 100_000
DEFAULT_PACKET_TTL_SECONDS = 7 * 24 * 3600  # 7 天
DEFAULT_MAX_TRANSITIONS = 50_000
DEFAULT_TRANSITION_TTL_SECONDS = 30 * 24 * 3600  # 30 天

# 周期性自动清理间隔（秒），可用 VPN_SIM_RETENTION_INTERVAL_SECONDS 覆盖
DEFAULT_CLEANUP_INTERVAL_SECONDS = 3600


def _rowcount(result: Any) -> int:
    """DELETE 语句的受影响行数（异步执行结果的类型标注不含 rowcount）。"""
    return max(0, int(getattr(result, "rowcount", 0) or 0))


class RetentionService:
    """报文/状态历史的保留策略清理服务。"""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self._db_manager = db_manager

    def _manager(self) -> DatabaseManager:
        """返回数据库管理器（注入优先，否则用进程内共享单例）。"""
        return self._db_manager or get_database_manager()

    async def counts(self) -> dict[str, int]:
        """返回 packets 与 state_transitions 的当前行数。"""
        manager = self._manager()
        if manager._engine is None:
            await manager.initialize()
        async with manager.session() as session:
            packets = await session.scalar(select(func.count()).select_from(PacketRecord))
            transitions = await session.scalar(
                select(func.count()).select_from(StateTransitionRecord)
            )
        return {"packets": int(packets or 0), "state_transitions": int(transitions or 0)}

    async def cleanup(
        self,
        max_packets: int | None = None,
        packet_ttl_seconds: int | None = None,
        max_transitions: int | None = None,
        transition_ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """按保留策略清理过期/超量行。

        Args:
            max_packets: packets 表最大保留行数（默认 100,000；<=0 表示跳过）。
            packet_ttl_seconds: packets 行最大保留秒数（默认 7 天；<=0 表示跳过）。
            max_transitions: state_transitions 表最大保留行数（默认 50,000）。
            transition_ttl_seconds: state_transitions 行最大保留秒数（默认 30 天）。

        Returns:
            删除行数与清理后的行数。
        """
        max_packets = DEFAULT_MAX_PACKETS if max_packets is None else max_packets
        packet_ttl = (
            DEFAULT_PACKET_TTL_SECONDS if packet_ttl_seconds is None else packet_ttl_seconds
        )
        max_transitions = DEFAULT_MAX_TRANSITIONS if max_transitions is None else max_transitions
        transition_ttl = (
            DEFAULT_TRANSITION_TTL_SECONDS
            if transition_ttl_seconds is None
            else transition_ttl_seconds
        )

        manager = self._manager()
        if manager._engine is None:
            await manager.initialize()

        deleted_packets = 0
        deleted_transitions = 0
        async with manager.session() as session:
            # TTL 清理
            if packet_ttl > 0:
                cutoff = datetime.now(UTC) - timedelta(seconds=packet_ttl)
                result = await session.execute(
                    delete(PacketRecord).where(PacketRecord.timestamp < cutoff)
                )
                deleted_packets += _rowcount(result)
            if transition_ttl > 0:
                cutoff = datetime.now(UTC) - timedelta(seconds=transition_ttl)
                result = await session.execute(
                    delete(StateTransitionRecord).where(StateTransitionRecord.timestamp < cutoff)
                )
                deleted_transitions += _rowcount(result)

            # 最大行数清理（保留最新 N 行）
            if max_packets > 0:
                packet_subq = (
                    select(PacketRecord.id)
                    .order_by(PacketRecord.timestamp.desc())
                    .limit(max_packets)
                )
                result = await session.execute(
                    delete(PacketRecord).where(~PacketRecord.id.in_(packet_subq))
                )
                deleted_packets += _rowcount(result)
            if max_transitions > 0:
                transition_subq = (
                    select(StateTransitionRecord.id)
                    .order_by(StateTransitionRecord.timestamp.desc())
                    .limit(max_transitions)
                )
                result = await session.execute(
                    delete(StateTransitionRecord).where(
                        ~StateTransitionRecord.id.in_(transition_subq)
                    )
                )
                deleted_transitions += _rowcount(result)

        counts = await self.counts()
        logger.info(
            "retention_cleanup_done",
            deleted_packets=deleted_packets,
            deleted_transitions=deleted_transitions,
        )
        return {
            "deleted_packets": deleted_packets,
            "deleted_state_transitions": deleted_transitions,
            "remaining_packets": counts["packets"],
            "remaining_state_transitions": counts["state_transitions"],
        }

    async def run_forever(self, interval_seconds: int | None = None) -> None:
        """周期性自动清理（供应用 lifespan 启动的后台任务）。

        Args:
            interval_seconds: 清理间隔；默认 3600 秒（可用环境变量覆盖）。
        """
        interval = interval_seconds or _cleanup_interval()
        while True:
            await asyncio.sleep(interval)
            try:
                await self.cleanup()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("retention_cleanup_failed", error=str(e))


def _cleanup_interval() -> int:
    """读取清理间隔（秒），非法值回退到默认。"""
    raw = os.getenv("VPN_SIM_RETENTION_INTERVAL_SECONDS")
    try:
        return int(raw) if raw and int(raw) > 0 else DEFAULT_CLEANUP_INTERVAL_SECONDS
    except ValueError:
        return DEFAULT_CLEANUP_INTERVAL_SECONDS
