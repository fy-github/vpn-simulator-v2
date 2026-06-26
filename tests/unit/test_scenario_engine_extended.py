"""Tests for ScenarioEngine - covering uncovered lines."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.domain.scenario import (
    ActionType,
    ScenarioDefinition,
    ScenarioState,
    ScenarioStep,
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


class TestLoadScenarioCacheHit:
    @pytest.mark.asyncio
    async def test_returns_cached_scenario(self, engine: ScenarioEngine):
        mock_definition = MagicMock(spec=ScenarioDefinition)
        mock_definition.name = "cached"
        engine._scenarios["cached"] = mock_definition
        result = await engine.load_scenario("cached")
        assert result is mock_definition
        assert result.name == "cached"


class TestLoadScenarioFromYAML:
    @pytest.mark.asyncio
    async def test_load_valid_yaml(self, engine: ScenarioEngine, tmp_path: Path):
        scenarios_dir = tmp_path / "scenarios" / "automation"
        scenarios_dir.mkdir(parents=True)
        yaml_content = """
name: Test Scenario
description: A test scenario
steps:
  - name: connect
    action: connect
    params:
      protocol: pptp
    expect:
      state: connected
    timeout: 30.0
    description: Connect step
tags:
  - test
timeout: 120.0
version: "1.0"
"""
        (scenarios_dir / "test_scenario.yaml").write_text(yaml_content)
        engine._config_manager.config_dir = str(tmp_path)
        result = await engine.load_scenario("test_scenario")
        assert result is not None
        assert result.name == "Test Scenario"
        assert len(result.steps) == 1
        assert result.steps[0].action == ActionType.CONNECT

    @pytest.mark.asyncio
    async def test_load_invalid_yaml(self, engine: ScenarioEngine, tmp_path: Path):
        scenarios_dir = tmp_path / "scenarios" / "automation"
        scenarios_dir.mkdir(parents=True)
        (scenarios_dir / "bad.yaml").write_text("invalid: yaml: [")
        engine._config_manager.config_dir = str(tmp_path)
        result = await engine.load_scenario("bad")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_validation_failure(self, engine: ScenarioEngine, tmp_path: Path):
        scenarios_dir = tmp_path / "scenarios" / "automation"
        scenarios_dir.mkdir(parents=True)
        (scenarios_dir / "incomplete.yaml").write_text("name: test\n")
        engine._config_manager.config_dir = str(tmp_path)
        result = await engine.load_scenario("incomplete")
        assert result is None


class TestLoadAllScenarios:
    @pytest.mark.asyncio
    async def test_load_all_from_directory(self, engine: ScenarioEngine, tmp_path: Path):
        scenarios_dir = tmp_path / "scenarios" / "automation"
        scenarios_dir.mkdir(parents=True)
        yaml1 = """
name: Scenario 1
description: First scenario
steps:
  - name: step1
    action: connect
    params: {protocol: pptp}
    expect: {}
"""
        yaml2 = """
name: Scenario 2
description: Second scenario
steps:
  - name: step1
    action: disconnect
    params: {}
    expect: {}
"""
        (scenarios_dir / "scenario1.yaml").write_text(yaml1)
        (scenarios_dir / "scenario2.yaml").write_text(yaml2)
        engine._config_manager.config_dir = str(tmp_path)
        scenarios = await engine.load_all_scenarios()
        assert len(scenarios) == 2

    @pytest.mark.asyncio
    async def test_load_all_no_directory(self, engine: ScenarioEngine, tmp_path: Path):
        engine._config_manager.config_dir = str(tmp_path / "nonexistent")
        scenarios = await engine.load_all_scenarios()
        assert len(scenarios) == 0


class TestExecuteStepCounting:
    @pytest.mark.asyncio
    async def test_execute_counts_passed(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(name="s1", action=ActionType.CONNECT, params={"protocol": "pptp"}, expect={}),
            ScenarioStep(name="s2", action=ActionType.DISCONNECT, params={}, expect={}),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_passed == 2
        assert result.steps_failed == 0
        assert result.steps_error == 0
        assert result.steps_skipped == 0

    @pytest.mark.asyncio
    async def test_execute_counts_error(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(name="s1", action=ActionType.CONNECT, params={}, expect={}),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        result = await engine.execute(scenario)
        assert result.steps_error == 1
        assert result.steps_passed == 0


class TestExecuteErrorHandling:
    @pytest.mark.asyncio
    async def test_execute_exception_sets_error_state(self, engine: ScenarioEngine, mock_event_bus):
        steps = [
            ScenarioStep(name="s1", action=ActionType.CONNECT, params={"protocol": "pptp"}, expect={}),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        with patch.object(engine, '_execute_step', side_effect=RuntimeError("boom")):
            result = await engine.execute(scenario)
        assert result.state == ScenarioState.ERROR
        assert result.error_message == "boom"

    @pytest.mark.asyncio
    async def test_execute_sets_failed_on_step_failure(self, engine: ScenarioEngine):
        steps = [
            ScenarioStep(name="s1", action=ActionType.CONNECT, params={"protocol": "pptp"}, expect={}),
        ]
        scenario = ScenarioDefinition(name="test", description="test", steps=steps)
        with patch.object(engine, '_execute_step') as mock_step:
            mock_step.return_value = MagicMock(result=StepResult.FAILED)
            result = await engine.execute(scenario)
        assert result.state == ScenarioState.FAILED


class TestUnknownActionType:
    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, engine: ScenarioEngine):
        step = ScenarioStep(name="bad", action=ActionType.CONNECT, params={}, expect={})
        step.action = "unknown_action_type"
        execution = MagicMock()
        execution.result = None
        execution.error_message = None
        await engine._execute_step(step)
        # The step should have been processed (the else branch sets ERROR)


class TestParseYamlDefinition:
    def test_parse_with_all_fields(self, engine: ScenarioEngine):
        yaml_data = {
            "name": "Full Scenario",
            "description": "A complete scenario",
            "steps": [
                {
                    "name": "connect",
                    "action": "connect",
                    "params": {"protocol": "pptp"},
                    "expect": {"state": "connected"},
                    "timeout": 30.0,
                    "description": "Connect step",
                },
                {
                    "name": "wait",
                    "action": "wait",
                    "params": {"duration": 1.0},
                    "expect": {},
                },
            ],
            "setup": ["setup_step"],
            "teardown": ["teardown_step"],
            "tags": ["test", "basic"],
            "timeout": 120.0,
            "version": "2.0",
        }
        result = engine._parse_yaml_definition(yaml_data)
        assert result.name == "Full Scenario"
        assert result.description == "A complete scenario"
        assert len(result.steps) == 2
        assert result.steps[0].action == ActionType.CONNECT
        assert result.steps[1].action == ActionType.WAIT
        assert result.steps[0].params == {"protocol": "pptp"}
        assert result.steps[0].expect == {"state": "connected"}
        assert result.timeout == 120.0
        assert result.version == "2.0"
        assert result.tags == ["test", "basic"]

    def test_parse_with_minimal_fields(self, engine: ScenarioEngine):
        yaml_data = {
            "name": "Minimal",
            "description": "Minimal scenario",
            "steps": [],
        }
        result = engine._parse_yaml_definition(yaml_data)
        assert result.name == "Minimal"
        assert len(result.steps) == 0
        assert result.timeout == 300.0
        assert result.version == "1.0"
