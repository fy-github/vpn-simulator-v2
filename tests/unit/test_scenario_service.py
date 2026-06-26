"""Tests for ScenarioService - scenario preset service."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.services.fault import FaultService
from vpn_simulator.services.scenario import ScenarioService


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def mock_db_manager():
    return MagicMock(spec=DatabaseManager)


@pytest.fixture
def mock_fault_service():
    service = MagicMock(spec=FaultService)
    service.create_fault = AsyncMock(return_value={"id": "fault-001", "type": "latency", "active": False})
    service.activate_fault = AsyncMock(return_value={"id": "fault-001", "active": True})
    service.remove_fault = AsyncMock(return_value=True)
    return service


@pytest.fixture
def temp_presets_file(tmp_path: Path) -> Path:
    import yaml
    presets_data = {
        "scenarios": {
            "3g": {
                "id": "3g",
                "name": "3G Network",
                "description": "Simulate 3G mobile network",
                "icon": "signal_cellular_alt",
                "category": "mobile",
                "faults": {
                    "latency": {"delay_ms": 200, "jitter_ms": 50},
                    "packet_loss": {"loss_rate": 0.02},
                },
            },
            "satellite": {
                "id": "satellite",
                "name": "Satellite Network",
                "description": "Simulate satellite network",
                "icon": "satellite",
                "category": "satellite",
                "faults": {
                    "latency": {"delay_ms": 600, "jitter_ms": 100},
                    "packet_loss": {"loss_rate": 0.05},
                    "bandwidth": {"bandwidth_kbps": 10000},
                },
            },
            "fiber": {
                "id": "fiber",
                "name": "Fiber Network",
                "description": "High-speed fiber network",
                "icon": "fiber_manual_record",
                "category": "wired",
                "faults": {
                    "latency": {"delay_ms": 5, "jitter_ms": 2},
                },
            },
        }
    }
    presets_file = tmp_path / "presets.yaml"
    presets_file.write_text(yaml.dump(presets_data, allow_unicode=True))
    return presets_file


@pytest.fixture
def service(
    mock_event_bus,
    mock_config_manager,
    mock_db_manager,
    mock_fault_service,
    temp_presets_file,
) -> ScenarioService:
    return ScenarioService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
        fault_service=mock_fault_service,
        presets_path=temp_presets_file,
    )


@pytest.fixture
def empty_service(
    mock_event_bus,
    mock_config_manager,
    mock_db_manager,
    mock_fault_service,
    tmp_path,
) -> ScenarioService:
    return ScenarioService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
        fault_service=mock_fault_service,
        presets_path=tmp_path / "nonexistent.yaml",
    )


class TestScenarioServiceInit:
    def test_service_creation(self, service: ScenarioService):
        assert service is not None
        assert service._event_bus is not None
        assert service._fault_service is not None

    def test_service_loads_presets(self, service: ScenarioService):
        service.load_presets()
        scenarios = service._scenario_manager.list_scenarios()
        assert len(scenarios) == 3


class TestListScenarios:
    @pytest.mark.asyncio
    async def test_list_all_scenarios(self, service: ScenarioService):
        service.load_presets()
        scenarios = await service.list_scenarios()
        assert len(scenarios) == 3
        assert any(s["id"] == "3g" for s in scenarios)
        assert any(s["id"] == "satellite" for s in scenarios)
        assert any(s["id"] == "fiber" for s in scenarios)

    @pytest.mark.asyncio
    async def test_list_scenarios_by_category(self, service: ScenarioService):
        service.load_presets()
        scenarios = await service.list_scenarios(category="mobile")
        assert len(scenarios) == 1
        assert scenarios[0]["id"] == "3g"

    @pytest.mark.asyncio
    async def test_list_scenarios_empty_category(self, service: ScenarioService):
        service.load_presets()
        scenarios = await service.list_scenarios(category="nonexistent")
        assert len(scenarios) == 0

    @pytest.mark.asyncio
    async def test_list_scenarios_no_presets(self, empty_service: ScenarioService):
        scenarios = await empty_service.list_scenarios()
        assert len(scenarios) == 0


class TestGetScenario:
    @pytest.mark.asyncio
    async def test_get_scenario(self, service: ScenarioService):
        service.load_presets()
        scenario = await service.get_scenario("3g")
        assert scenario is not None
        assert scenario["id"] == "3g"
        assert scenario["name"] == "3G Network"
        assert scenario["category"] == "mobile"
        assert "latency" in scenario["faults"]
        assert "packet_loss" in scenario["faults"]

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(self, service: ScenarioService):
        service.load_presets()
        scenario = await service.get_scenario("nonexistent")
        assert scenario is None

    @pytest.mark.asyncio
    async def test_get_scenario_structure(self, service: ScenarioService):
        service.load_presets()
        scenario = await service.get_scenario("satellite")
        assert "id" in scenario
        assert "name" in scenario
        assert "description" in scenario
        assert "icon" in scenario
        assert "category" in scenario
        assert "faults" in scenario
        assert "active" in scenario


class TestApplyScenario:
    @pytest.mark.asyncio
    async def test_apply_scenario(self, service: ScenarioService, mock_fault_service):
        service.load_presets()
        result = await service.apply_scenario("3g")
        assert result["scenario_id"] == "3g"
        assert result["status"] == "applied"
        assert len(result["fault_ids"]) == 2
        assert mock_fault_service.create_fault.call_count == 2
        assert mock_fault_service.activate_fault.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_scenario_not_found(self, service: ScenarioService):
        service.load_presets()
        with pytest.raises(ValueError, match="not found"):
            await service.apply_scenario("nonexistent")

    @pytest.mark.asyncio
    async def test_apply_scenario_removes_previous(self, service: ScenarioService, mock_fault_service):
        service.load_presets()
        await service.apply_scenario("3g")
        result = await service.apply_scenario("satellite")
        assert result["scenario_id"] == "satellite"
        assert mock_fault_service.remove_fault.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_scenario_emits_event(self, service: ScenarioService, mock_event_bus):
        service.load_presets()
        await service.apply_scenario("3g")
        mock_event_bus.emit.assert_called_once()
        call_args = mock_event_bus.emit.call_args
        assert call_args[0][0] == "fault.injected"


class TestRemoveScenario:
    @pytest.mark.asyncio
    async def test_remove_scenario(self, service: ScenarioService, mock_fault_service):
        service.load_presets()
        await service.apply_scenario("3g")
        result = await service.remove_scenario("3g")
        assert result["scenario_id"] == "3g"
        assert result["status"] == "removed"
        assert result["removed_faults"] == 2
        assert mock_fault_service.remove_fault.call_count == 2

    @pytest.mark.asyncio
    async def test_remove_scenario_not_found(self, service: ScenarioService):
        service.load_presets()
        with pytest.raises(ValueError, match="not found"):
            await service.remove_scenario("nonexistent")

    @pytest.mark.asyncio
    async def test_remove_scenario_not_active(self, service: ScenarioService):
        service.load_presets()
        with pytest.raises(ValueError, match="not active"):
            await service.remove_scenario("3g")

    @pytest.mark.asyncio
    async def test_remove_scenario_emits_event(self, service: ScenarioService, mock_event_bus):
        service.load_presets()
        await service.apply_scenario("3g")
        await service.remove_scenario("3g")
        assert mock_event_bus.emit.call_count == 2


class TestGetActiveScenario:
    @pytest.mark.asyncio
    async def test_get_active_scenario_none(self, service: ScenarioService):
        service.load_presets()
        active = await service.get_active_scenario()
        assert active is None

    @pytest.mark.asyncio
    async def test_get_active_scenario_after_apply(self, service: ScenarioService):
        service.load_presets()
        await service.apply_scenario("3g")
        active = await service.get_active_scenario()
        assert active is not None
        assert active["id"] == "3g"
        assert active["active"] is True

    @pytest.mark.asyncio
    async def test_get_active_scenario_after_remove(self, service: ScenarioService):
        service.load_presets()
        await service.apply_scenario("3g")
        await service.remove_scenario("3g")
        active = await service.get_active_scenario()
        assert active is None


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_apply_multiple_scenarios(self, service: ScenarioService, mock_fault_service):
        service.load_presets()
        await service.apply_scenario("3g")
        await service.apply_scenario("satellite")
        active = await service.get_active_scenario()
        assert active["id"] == "satellite"

    @pytest.mark.asyncio
    async def test_scenario_faults_structure(self, service: ScenarioService):
        service.load_presets()
        scenario = await service.get_scenario("satellite")
        faults = scenario["faults"]
        assert "latency" in faults
        assert "packet_loss" in faults
        assert "bandwidth" in faults
        assert faults["latency"]["delay_ms"] == 600

    @pytest.mark.asyncio
    async def test_load_presets_nonexistent_file(self, empty_service: ScenarioService):
        empty_service.load_presets()
        scenarios = await empty_service.list_scenarios()
        assert len(scenarios) == 0

    @pytest.mark.asyncio
    async def test_scenario_active_flag(self, service: ScenarioService):
        service.load_presets()
        scenarios = await service.list_scenarios()
        assert all(not s["active"] for s in scenarios)
        
        await service.apply_scenario("3g")
        scenarios = await service.list_scenarios()
        active_scenario = next(s for s in scenarios if s["id"] == "3g")
        assert active_scenario["active"] is True
