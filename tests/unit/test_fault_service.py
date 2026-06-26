"""Tests for FaultService - fault injection service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.services.fault import FaultService


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
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.add = MagicMock()
    mock_session.delete = AsyncMock()
    dm.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    dm.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return dm


@pytest.fixture
def service(mock_event_bus, mock_config_manager, mock_db_manager) -> FaultService:
    return FaultService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


class TestFaultServiceInit:
    def test_service_creation(self, service: FaultService):
        assert service is not None
        assert service._fault_manager is not None


class TestCreateFault:
    @pytest.mark.asyncio
    async def test_create_fault_latency(self, service: FaultService):
        result = await service.create_fault("latency", {"delay_ms": 100}, target="pptp")
        assert result is not None
        assert result["type"] == "latency"
        assert result["target"] == "pptp"
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_create_fault_packet_loss(self, service: FaultService):
        result = await service.create_fault("packet_loss", {"loss_rate": 0.05})
        assert result["type"] == "packet_loss"

    @pytest.mark.asyncio
    async def test_create_fault_bandwidth(self, service: FaultService):
        result = await service.create_fault("bandwidth", {"bandwidth_kbps": 1000})
        assert result["type"] == "bandwidth"

    @pytest.mark.asyncio
    async def test_create_fault_invalid_type(self, service: FaultService):
        with pytest.raises(ValueError, match="Invalid fault type"):
            await service.create_fault("invalid")

    @pytest.mark.asyncio
    async def test_create_fault_with_params(self, service: FaultService):
        result = await service.create_fault("latency", {"delay_ms": 200, "jitter_ms": 50})
        assert result["params"]["delay_ms"] == 200
        assert result["params"]["jitter_ms"] == 50

    @pytest.mark.asyncio
    async def test_create_fault_emits_event(self, service: FaultService, mock_event_bus):
        await service.create_fault("latency", target="pptp")
        assert mock_event_bus.emit.called


class TestGetFault:
    @pytest.mark.asyncio
    async def test_get_fault(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        result = await service.get_fault(created["id"])
        assert result is not None
        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_fault_not_found(self, service: FaultService):
        result = await service.get_fault("nonexistent")
        assert result is None


class TestListFaults:
    @pytest.mark.asyncio
    async def test_list_faults_empty(self, service: FaultService):
        faults = await service.list_faults()
        assert len(faults) == 0

    @pytest.mark.asyncio
    async def test_list_faults_with_data(self, service: FaultService):
        await service.create_fault("latency", target="pptp")
        await service.create_fault("packet_loss", target="l2tp")
        faults = await service.list_faults()
        assert len(faults) == 2

    @pytest.mark.asyncio
    async def test_list_faults_by_type(self, service: FaultService):
        await service.create_fault("latency", target="pptp")
        await service.create_fault("packet_loss", target="l2tp")
        faults = await service.list_faults(fault_type="latency")
        assert len(faults) == 1

    @pytest.mark.asyncio
    async def test_list_faults_active_only(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        await service.activate_fault(created["id"])
        faults = await service.list_faults(active_only=True)
        assert len(faults) == 1


class TestActivateFault:
    @pytest.mark.asyncio
    async def test_activate_fault(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        result = await service.activate_fault(created["id"])
        assert result is not None
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_activate_fault_not_found(self, service: FaultService):
        result = await service.activate_fault("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_activate_fault_emits_event(self, service: FaultService, mock_event_bus):
        created = await service.create_fault("latency", target="pptp")
        await service.activate_fault(created["id"])
        assert mock_event_bus.emit.call_count >= 2


class TestDeactivateFault:
    @pytest.mark.asyncio
    async def test_deactivate_fault(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        await service.activate_fault(created["id"])
        result = await service.deactivate_fault(created["id"])
        assert result is not None
        assert result["active"] is False

    @pytest.mark.asyncio
    async def test_deactivate_fault_not_found(self, service: FaultService):
        result = await service.deactivate_fault("nonexistent")
        assert result is None


class TestRemoveFault:
    @pytest.mark.asyncio
    async def test_remove_fault(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        result = await service.remove_fault(created["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_fault_not_found(self, service: FaultService):
        result = await service.remove_fault("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_fault_emits_event(self, service: FaultService, mock_event_bus):
        created = await service.create_fault("latency", target="pptp")
        await service.remove_fault(created["id"])
        assert mock_event_bus.emit.call_count >= 2


class TestGetFaultStats:
    @pytest.mark.asyncio
    async def test_get_stats_empty(self, service: FaultService):
        stats = await service.get_fault_stats()
        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["inactive"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_faults(self, service: FaultService):
        await service.create_fault("latency", target="pptp")
        await service.create_fault("packet_loss", target="l2tp")
        stats = await service.get_fault_stats()
        assert stats["total"] == 2
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_get_stats_active_inactive(self, service: FaultService):
        created = await service.create_fault("latency", target="pptp")
        await service.deactivate_fault(created["id"])
        await service.create_fault("packet_loss", target="l2tp")
        stats = await service.get_fault_stats()
        assert stats["active"] == 1
        assert stats["inactive"] == 1


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_fault_lifecycle(self, service: FaultService):
        created = await service.create_fault("latency", {"delay_ms": 100}, target="pptp")
        assert created["active"] is True

        deactivated = await service.deactivate_fault(created["id"])
        assert deactivated["active"] is False

        activated = await service.activate_fault(created["id"])
        assert activated["active"] is True

        removed = await service.remove_fault(created["id"])
        assert removed is True

    @pytest.mark.asyncio
    async def test_multiple_fault_types(self, service: FaultService):
        for ftype in ["latency", "packet_loss", "bandwidth", "reorder", "duplicate", "corrupt"]:
            result = await service.create_fault(ftype, target="pptp")
            assert result["type"] == ftype

    @pytest.mark.asyncio
    async def test_fault_with_empty_params(self, service: FaultService):
        result = await service.create_fault("latency", params={}, target="pptp")
        assert result is not None
