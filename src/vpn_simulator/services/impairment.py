"""时间变化网络损伤服务（F1）。

在故障注入之上叠加调度层：管理时间变化损伤的创建、预设应用、启动/停止、
状态查询与时间线计算，并持久化损伤状态（应用重启后恢复）。

Example:
    >>> service = ImpairmentService(event_bus, config_manager, db_manager)
    >>> imp = await service.create_impairment(
    ...     fault_type="latency", param="delay_ms", change_type="linear",
    ...     start_value=0, end_value=300, duration_seconds=60,
    ... )
    >>> await service.start(imp.id)
    >>> await service.status(imp.id)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import structlog
import yaml
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager, ImpairmentRecord
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.fault import FaultType
from vpn_simulator.domain.impairment import ChangeType, Impairment

logger = structlog.get_logger(__name__)

DEFAULT_PRESETS_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "impairments" / "time_varying.yaml"
)


class ImpairmentService:
    """时间变化网络损伤服务。

    Attributes:
        _event_bus: 事件总线。
        _config_manager: 配置管理器。
        _db_manager: 数据库管理器。
        _impairments: 损伤实例字典（id -> Impairment）。
        _presets_path: 预设配置文件路径。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
        presets_path: Path | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._impairments: dict[str, Impairment] = {}
        self._presets_path = presets_path or DEFAULT_PRESETS_PATH

    # ------------------------------------------------------------------
    # 预设
    # ------------------------------------------------------------------
    def list_presets(self) -> list[dict[str, Any]]:
        """加载并返回内置损伤预设（来自 YAML 配置文件）。"""
        if not self._presets_path.exists():
            logger.warning("impairment_presets_not_found", path=str(self._presets_path))
            return []

        try:
            with open(self._presets_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            presets = cast(list[dict[str, Any]], data.get("presets", []))
            logger.info("impairment_presets_loaded", count=len(presets))
            return presets
        except Exception as e:
            logger.error(
                "impairment_presets_load_error", path=str(self._presets_path), error=str(e)
            )
            return []

    # ------------------------------------------------------------------
    # 创建 / 应用
    # ------------------------------------------------------------------
    async def create_impairment(
        self,
        *,
        fault_type: str,
        param: str,
        change_type: str,
        start_value: float,
        end_value: float,
        duration_seconds: float,
        period_seconds: float = 0.0,
        step_at_seconds: float | None = None,
        target: str = "",
        name: str = "",
    ) -> Impairment:
        """创建一个时间变化损伤实例并持久化。

        Raises:
            ValueError: 无效的故障类型或变化类型。
        """
        try:
            FaultType(fault_type)
        except ValueError:
            raise ValueError(
                f"Invalid fault_type '{fault_type}'. Valid: {[t.value for t in FaultType]}"
            )
        try:
            ct = ChangeType(change_type)
        except ValueError:
            raise ValueError(
                f"Invalid change_type '{change_type}'. Valid: {[c.value for c in ChangeType]}"
            )

        impairment = Impairment(
            name=name,
            fault_type=fault_type,
            param=param,
            change_type=ct,
            start_value=float(start_value),
            end_value=float(end_value),
            duration_seconds=float(duration_seconds),
            period_seconds=float(period_seconds),
            step_at_seconds=float(step_at_seconds) if step_at_seconds is not None else None,
            target=target,
        )
        self._impairments[impairment.id] = impairment

        await self._insert_record(impairment)
        await self._event_bus.emit(
            EventTypes.IMPAIRMENT_APPLIED,
            impairment.to_dict(),
            source="ImpairmentService",
        )
        logger.info(
            "impairment_created",
            impairment_id=impairment.id,
            fault_type=fault_type,
            change_type=change_type,
        )
        return impairment

    async def apply_preset(self, name: str) -> dict[str, Any]:
        """按名称应用一个内置预设，返回创建的损伤字典。

        Raises:
            ValueError: 预设不存在。
        """
        preset = next((p for p in self.list_presets() if p.get("name") == name), None)
        if preset is None:
            available = [p.get("name") for p in self.list_presets()]
            raise ValueError(f"Unknown preset '{name}'. Available: {available}")

        impairment = await self.create_impairment(
            fault_type=str(preset.get("fault_type", "latency")),
            param=str(preset.get("param", "delay_ms")),
            change_type=str(preset.get("change_type", "linear")),
            start_value=float(preset.get("start_value", 0)),
            end_value=float(preset.get("end_value", 100)),
            duration_seconds=float(preset.get("duration_seconds", 60)),
            period_seconds=float(preset.get("period_seconds", 0)),
            step_at_seconds=(
                float(preset["step_at_seconds"])
                if preset.get("step_at_seconds") is not None
                else None
            ),
            target=str(preset.get("target", "")),
            name=str(preset.get("name", name)),
        )
        return impairment.to_dict()

    # ------------------------------------------------------------------
    # 查询 / 状态 / 时间线
    # ------------------------------------------------------------------
    def list_impairments(self) -> list[dict[str, Any]]:
        """列出所有损伤。"""
        return [imp.to_dict() for imp in self._impairments.values()]

    def get_impairment(self, impairment_id: str) -> Impairment | None:
        """获取指定损伤。"""
        return self._impairments.get(impairment_id)

    async def status(self, impairment_id: str) -> dict[str, Any] | None:
        """返回损伤状态（含当前值与进度）。"""
        impairment = self._impairments.get(impairment_id)
        if impairment is None:
            return None

        elapsed = impairment.elapsed_seconds()
        progress = min(elapsed / impairment.duration_seconds, 1.0) if elapsed is not None else 0.0
        current = impairment.current_value()
        result = impairment.to_dict()
        result["elapsed_seconds"] = round(elapsed, 3) if elapsed is not None else None
        result["progress"] = round(progress, 3)
        result["current_value"] = round(current, 3) if current is not None else None
        return result

    def timeline(self, impairment_id: str, samples: int = 60) -> list[dict[str, Any]]:
        """返回指定损伤的时间线采样。"""
        impairment = self._impairments.get(impairment_id)
        if impairment is None:
            return []
        return impairment.timeline(samples)

    def current_params(self) -> dict[str, float]:
        """返回所有已激活损伤的当前参数值（作用于真实报文流的入口）。

        返回 ``{param: value}``，供 packetio/握手层按参数名查询当前损伤强度，
        例如 ``{"delay_ms": 150.0, "loss_rate": 0.3}``。
        """
        params: dict[str, float] = {}
        for impairment in self._impairments.values():
            if not impairment.active or impairment.started_at is None:
                continue
            value = impairment.current_value()
            if value is not None:
                params[impairment.param] = value
        return params

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    async def start(self, impairment_id: str) -> dict[str, Any] | None:
        """启动损伤。"""
        impairment = self._impairments.get(impairment_id)
        if impairment is None:
            return None
        impairment.start()
        await self._update_record(impairment)
        await self._event_bus.emit(
            EventTypes.IMPAIRMENT_STARTED,
            {"impairment_id": impairment_id},
            source="ImpairmentService",
        )
        logger.info("impairment_started", impairment_id=impairment_id)
        return impairment.to_dict()

    async def stop(self, impairment_id: str) -> dict[str, Any] | None:
        """停止损伤。"""
        impairment = self._impairments.get(impairment_id)
        if impairment is None:
            return None
        impairment.stop()
        await self._update_record(impairment)
        await self._event_bus.emit(
            EventTypes.IMPAIRMENT_STOPPED,
            {"impairment_id": impairment_id},
            source="ImpairmentService",
        )
        logger.info("impairment_stopped", impairment_id=impairment_id)
        return impairment.to_dict()

    async def remove(self, impairment_id: str) -> bool:
        """移除损伤。"""
        if impairment_id not in self._impairments:
            return False
        del self._impairments[impairment_id]
        await self._delete_record(impairment_id)
        logger.info("impairment_removed", impairment_id=impairment_id)
        return True

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    async def _insert_record(self, impairment: Impairment) -> None:
        record = ImpairmentRecord(
            id=impairment.id,
            name=impairment.name,
            fault_type=impairment.fault_type,
            param=impairment.param,
            change_type=impairment.change_type.value,
            start_value=impairment.start_value,
            end_value=impairment.end_value,
            duration_seconds=impairment.duration_seconds,
            period_seconds=impairment.period_seconds,
            step_at_seconds=impairment.step_at_seconds,
            target=impairment.target,
            active=impairment.active,
            created_at=impairment.created_at,
            started_at=impairment.started_at,
            stopped_at=impairment.stopped_at,
        )
        async with self._db_manager.session() as session:
            session.add(record)

    async def _update_record(self, impairment: Impairment) -> None:
        async with self._db_manager.session() as session:
            stmt = select(ImpairmentRecord).where(ImpairmentRecord.id == impairment.id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                record.active = impairment.active  # type: ignore[assignment]
                record.started_at = impairment.started_at  # type: ignore[assignment]
                record.stopped_at = impairment.stopped_at  # type: ignore[assignment]

    async def _delete_record(self, impairment_id: str) -> None:
        async with self._db_manager.session() as session:
            stmt = select(ImpairmentRecord).where(ImpairmentRecord.id == impairment_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                await session.delete(record)

    async def restore_impairments(self) -> None:
        """从数据库恢复损伤状态（应用启动时调用）。"""
        async with self._db_manager.session() as session:
            result = await session.execute(select(ImpairmentRecord))
            records = result.scalars().all()

        restored = 0
        for record in records:
            impairment = Impairment(
                id=cast(str, record.id),
                name=cast(str, record.name) or "",
                fault_type=cast(str, record.fault_type),
                param=cast(str, record.param),
                change_type=ChangeType(cast(str, record.change_type)),
                start_value=float(record.start_value),
                end_value=float(record.end_value),
                duration_seconds=float(record.duration_seconds),
                period_seconds=float(record.period_seconds or 0.0),
                step_at_seconds=(
                    float(record.step_at_seconds) if record.step_at_seconds is not None else None
                ),
                target=cast(str, record.target) or "",
                active=cast(bool, record.active),
                created_at=cast(datetime, record.created_at) or datetime.now(),
                started_at=cast(datetime | None, record.started_at),
                stopped_at=cast(datetime | None, record.stopped_at),
            )
            self._impairments[impairment.id] = impairment
            restored += 1

        logger.info("impairments_restored", count=restored)
