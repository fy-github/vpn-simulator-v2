"""Tests for ImpairmentService - time-varying network impairment service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.domain.impairment import ChangeType
from vpn_simulator.services.impairment import ImpairmentService


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    cm = MagicMock(spec=ConfigManager)
    cm.config = MagicMock()
    cm.config.faults = {}
    return cm


@pytest.fixture
def mock_db_manager():
    dm = MagicMock(spec=DatabaseManager)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    dm.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    dm.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return dm


@pytest.fixture
def service(mock_event_bus, mock_config_manager, mock_db_manager) -> ImpairmentService:
    return ImpairmentService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


class TestCreateImpairment:
    @pytest.mark.asyncio
    async def test_create_linear_impairment(self, service: ImpairmentService):
        imp = await service.create_impairment(
            fault_type="latency",
            param="delay_ms",
            change_type="linear",
            start_value=0,
            end_value=300,
            duration_seconds=60,
        )
        assert imp.id
        assert imp.fault_type == "latency"
        assert imp.change_type == ChangeType.LINEAR
        assert service.get_impairment(imp.id) is imp

    @pytest.mark.asyncio
    async def test_create_invalid_change_type(self, service: ImpairmentService):
        with pytest.raises(ValueError, match="Invalid change_type"):
            await service.create_impairment(
                fault_type="latency",
                param="delay_ms",
                change_type="unknown",
                start_value=0,
                end_value=1,
                duration_seconds=60,
            )

    @pytest.mark.asyncio
    async def test_create_invalid_fault_type(self, service: ImpairmentService):
        with pytest.raises(ValueError, match="Invalid fault_type"):
            await service.create_impairment(
                fault_type="bogus",
                param="delay_ms",
                change_type="linear",
                start_value=0,
                end_value=1,
                duration_seconds=60,
            )


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop_and_status(self, service: ImpairmentService):
        imp = await service.create_impairment(
            fault_type="latency",
            param="delay_ms",
            change_type="linear",
            start_value=0,
            end_value=300,
            duration_seconds=60,
        )
        before = await service.status(imp.id)
        assert before is not None
        assert before["current_value"] is None  # 未启动

        started = await service.start(imp.id)
        assert started is not None
        assert started["active"] is True

        status = await service.status(imp.id)
        assert status is not None
        assert status["active"] is True
        assert status["current_value"] is not None
        assert 0.0 <= status["current_value"] <= 300.0

        stopped = await service.stop(imp.id)
        assert stopped is not None
        assert stopped["active"] is False

    @pytest.mark.asyncio
    async def test_timeline(self, service: ImpairmentService):
        imp = await service.create_impairment(
            fault_type="latency",
            param="delay_ms",
            change_type="linear",
            start_value=0,
            end_value=100,
            duration_seconds=60,
        )
        timeline = service.timeline(imp.id, samples=5)
        assert len(timeline) == 5
        assert timeline[0]["t"] == 0.0
        assert timeline[-1]["t"] == 60.0

    @pytest.mark.asyncio
    async def test_current_params_requires_started(self, service: ImpairmentService):
        imp = await service.create_impairment(
            fault_type="latency",
            param="delay_ms",
            change_type="linear",
            start_value=0,
            end_value=300,
            duration_seconds=60,
        )
        assert service.current_params() == {}  # 未启动
        await service.start(imp.id)
        assert "delay_ms" in service.current_params()


class TestPresets:
    def test_list_presets(self, service: ImpairmentService):
        presets = service.list_presets()
        assert len(presets) >= 5
        change_types = {p["change_type"] for p in presets}
        assert {"linear", "exponential", "step", "sine", "random"} <= change_types

    @pytest.mark.asyncio
    async def test_apply_preset(self, service: ImpairmentService):
        preset = service.list_presets()[0]
        applied = await service.apply_preset(preset["name"])
        assert applied["name"] == preset["name"]
        assert applied["change_type"] == preset["change_type"]
        assert applied["fault_type"] == preset["fault_type"]

    @pytest.mark.asyncio
    async def test_apply_unknown_preset(self, service: ImpairmentService):
        with pytest.raises(ValueError, match="Unknown preset"):
            await service.apply_preset("does-not-exist")


class TestRestore:
    @pytest.mark.asyncio
    async def test_restore_impairments_roundtrip(self):
        db = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await db.initialize()
        try:
            bus = EventBus()
            cm = ConfigManager()
            service = ImpairmentService(bus, cm, db)

            imp = await service.create_impairment(
                fault_type="packet_loss",
                param="loss_rate",
                change_type="step",
                start_value=0.0,
                end_value=0.3,
                duration_seconds=60,
                step_at_seconds=30,
                target="wireguard",
            )
            await service.start(imp.id)

            service2 = ImpairmentService(bus, cm, db)
            await service2.restore_impairments()

            restored = service2.get_impairment(imp.id)
            assert restored is not None
            assert restored.fault_type == "packet_loss"
            assert restored.param == "loss_rate"
            assert restored.change_type == ChangeType.STEP
            assert restored.end_value == pytest.approx(0.3)
            assert restored.started_at is not None
            assert restored.active is True
        finally:
            await db.close()
