"""Tests for ScenarioEngine - scenario execution engine."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.domain.scenario import (
    ActionType,
    ScenarioDefinition,
    ScenarioStep,
    ScenarioState,
    StepResult,
)
from vpn_simulator.services.scenario_engine import ScenarioEngine


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    cm = MagicMock(spec=ConfigManager)
    cm.config_dir = "/tmp/test_config"
    return cm


@pytest.fixture
def mock_db_manager():
    return MagicMock(spec=DatabaseManager)


@pytest.fixture
def engine(mock_event_bus, mock_config_manager, mock_db_manager) -> ScenarioEngine:
    return ScenarioEngine(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


@pytest.fixture
def sample_scenario() -> ScenarioDefinition:
    steps = [
        ScenarioStep(
            name="connect",
            action=ActionType.CONNECT,
            params={"protocol": "pptp"},
            expect={"state": "connected"},
            timeout=30.0,
        ),
        ScenarioStep(
            name="wait",
            action=ActionType.WAIT,
            params={"duration": 0.01},
            expect={},
            timeout=5.0,
        ),
        ScenarioStep(
            name="disconnect",
            action=ActionType.DISCONNECT,
            params={},
            expect={"state": "disconnected"},
            timeout=10.0,
        ),
    ]
    return ScenarioDefinition(
        name="Test Scenario",
        description="A test scenario",
        steps=steps,
    )


@pytest.fixture
def ping_scenario() -> ScenarioDefinition:
    steps = [
        ScenarioStep(
            name="ping",
            action=ActionType.PING,
            params={"target": "10.0.0.1"},
            expect={"state": "reachable"},
            timeout=10.0,
        ),
    ]
    return ScenarioDefinition(
        name="Ping Scenario",
        description="A ping test scenario",
        steps=steps,
    )


@pytest.fixture
def check_scenario() -> ScenarioDefinition:
    steps = [
        ScenarioStep(
            name="check_state",
            action=ActionType.CHECK,
            params={},
            expect={"state": "connected"},
            timeout=10.0,
        ),
    ]
    return ScenarioDefinition(
        name="Check Scenario",
        description="A check test scenario",
        steps=steps,
    )


class TestScenarioEngineInit:
    def test_engine_creation(self, engine: ScenarioEngine):
        assert engine is not None
        assert len(engine._scenarios) == 0
        assert len(engine._executions) == 0


class TestLoadScenario:
    @pytest.mark.asyncio
    async def test_load_scenario_not_found(self, engine: ScenarioEngine):
        result = await engine.load_scenario("nonexistent")
        assert result is None


class TestLoadAllScenarios:
    @pytest.mark.asyncio
    async def test_load_all_scenarios_no_dir(self, engine: ScenarioEngine):
        scenarios = await engine.load_all_scenarios()
        assert len(scenarios) == 0


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_success(self, engine: ScenarioEngine, sample_scenario, mock_event_bus):
        result = await engine.execute(sample_scenario)
        assert result is not None
        assert result.state == ScenarioState.PASSED
        assert result.steps_passed == 3
        assert result.steps_failed == 0

    @pytest.mark.asyncio
    async def test_execute_ping(self, engine: ScenarioEngine, ping_scenario):
        result = await engine.execute(ping_scenario)
        assert result.state == ScenarioState.PASSED
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_execute_check(self, engine: ScenarioEngine, check_scenario):
        result = await engine.execute(check_scenario)
        assert result.state == ScenarioState.PASSED
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_execute_emits_events(self, engine: ScenarioEngine, sample_scenario, mock_event_bus):
        await engine.execute(sample_scenario)
        assert mock_event_bus.emit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_records_duration(self, engine: ScenarioEngine, sample_scenario):
        result = await engine.execute(sample_scenario)
        assert result.duration is not None
        assert result.duration >= 0

    @pytest.mark.asyncio
    async def test_execute_with_connection_id(self, engine: ScenarioEngine, sample_scenario):
        result = await engine.execute(sample_scenario, connection_id="conn-001")
        assert result.state == ScenarioState.PASSED


class TestGetExecution:
    @pytest.mark.asyncio
    async def test_get_execution(self, engine: ScenarioEngine, sample_scenario):
        await engine.execute(sample_scenario)
        executions = await engine.list_executions()
        assert len(executions) == 1

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, engine: ScenarioEngine):
        result = await engine.get_execution("nonexistent")
        assert result is None


class TestListExecutions:
    @pytest.mark.asyncio
    async def test_list_executions_empty(self, engine: ScenarioEngine):
        executions = await engine.list_executions()
        assert len(executions) == 0

    @pytest.mark.asyncio
    async def test_list_executions_with_data(self, engine: ScenarioEngine, sample_scenario):
        await engine.execute(sample_scenario)
        await engine.execute(sample_scenario)
        executions = await engine.list_executions()
        assert len(executions) == 2

    @pytest.mark.asyncio
    async def test_list_executions_by_scenario(self, engine: ScenarioEngine, sample_scenario, ping_scenario):
        await engine.execute(sample_scenario)
        await engine.execute(ping_scenario)
        executions = await engine.list_executions(scenario_name="Test Scenario")
        assert len(executions) == 1


class TestGetReport:
    @pytest.mark.asyncio
    async def test_get_report(self, engine: ScenarioEngine, sample_scenario):
        await engine.execute(sample_scenario)
        executions = await engine.list_executions()
        report = await engine.get_report(executions[0].id)
        assert report is not None
        assert isinstance(report, str)

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, engine: ScenarioEngine):
        report = await engine.get_report("nonexistent")
        assert report is None


class TestStepExecution:
    @pytest.mark.asyncio
    async def test_connect_step(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="connect",
                action=ActionType.CONNECT,
                params={"protocol": "pptp"},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_connect_step_no_protocol(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="connect",
                action=ActionType.CONNECT,
                params={},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_error == 1

    @pytest.mark.asyncio
    async def test_disconnect_step(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="disconnect",
                action=ActionType.DISCONNECT,
                params={},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_ping_step(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="ping",
                action=ActionType.PING,
                params={"target": "10.0.0.1"},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_ping_step_no_target(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="ping",
                action=ActionType.PING,
                params={},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_error == 1

    @pytest.mark.asyncio
    async def test_check_step(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="check",
                action=ActionType.CHECK,
                params={},
                expect={"state": "connected"},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_wait_step(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="wait",
                action=ActionType.WAIT,
                params={"duration": 0.01},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 1

    @pytest.mark.asyncio
    async def test_unknown_action(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(
                name="unknown",
                action=ActionType.CONNECT,
                params={},
                expect={},
            ),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_error == 1


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_scenario(self, engine: ScenarioEngine):
        scenario = ScenarioDefinition(name="empty", description="empty", steps=[])
        result = await engine.execute(scenario)
        assert result.state == ScenarioState.PASSED
        assert result.steps_passed == 0

    @pytest.mark.asyncio
    async def test_multiple_scenarios(self, engine: ScenarioEngine, sample_scenario, ping_scenario):
        result1 = await engine.execute(sample_scenario)
        result2 = await engine.execute(ping_scenario)
        assert result1.state == ScenarioState.PASSED
        assert result2.state == ScenarioState.PASSED
        executions = await engine.list_executions()
        assert len(executions) == 2

    @pytest.mark.asyncio
    async def test_scenario_result_structure(self, engine: ScenarioEngine, sample_scenario):
        result = await engine.execute(sample_scenario)
        assert hasattr(result, "scenario_name")
        assert hasattr(result, "state")
        assert hasattr(result, "steps_passed")
        assert hasattr(result, "steps_failed")
        assert hasattr(result, "duration")
        assert hasattr(result, "step_executions")
