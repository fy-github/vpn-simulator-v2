"""Scenario automation tests."""

import pytest
import yaml
from pathlib import Path

from vpn_simulator.domain.scenario import (
    ActionType,
    ScenarioDefinition,
    ScenarioState,
    ScenarioStep,
    ScenarioValidator,
    StepResult,
)


def test_scenario_step_creation():
    step = ScenarioStep(
        name="Test Step",
        action=ActionType.CONNECT,
        params={"protocol": "pptp"},
        expect={"state": "connected"},
    )
    assert step.name == "Test Step"
    assert step.action == ActionType.CONNECT
    assert step.params == {"protocol": "pptp"}
    assert step.expect == {"state": "connected"}


def test_scenario_definition_creation():
    step = ScenarioStep(
        name="Connect",
        action=ActionType.CONNECT,
        params={"protocol": "pptp"},
    )
    definition = ScenarioDefinition(
        name="Test Scenario",
        description="A test scenario",
        steps=[step],
    )
    assert definition.name == "Test Scenario"
    assert definition.description == "A test scenario"
    assert len(definition.steps) == 1


def test_scenario_definition_to_dict():
    step = ScenarioStep(
        name="Connect",
        action=ActionType.CONNECT,
        params={"protocol": "pptp"},
    )
    definition = ScenarioDefinition(
        name="Test Scenario",
        description="A test scenario",
        steps=[step],
    )
    result = definition.to_dict()
    assert result["name"] == "Test Scenario"
    assert result["description"] == "A test scenario"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["action"] == "connect"


def test_scenario_validator_valid_definition():
    step = ScenarioStep(
        name="Connect",
        action=ActionType.CONNECT,
        params={"protocol": "pptp"},
    )
    definition = ScenarioDefinition(
        name="Test Scenario",
        description="A test scenario",
        steps=[step],
    )
    errors = ScenarioValidator.validate_definition(definition)
    assert len(errors) == 0


def test_scenario_validator_missing_name():
    step = ScenarioStep(
        name="Connect",
        action=ActionType.CONNECT,
        params={"protocol": "pptp"},
    )
    definition = ScenarioDefinition(
        name="",
        description="A test scenario",
        steps=[step],
    )
    errors = ScenarioValidator.validate_definition(definition)
    assert "场景名称不能为空" in errors


def test_scenario_validator_missing_protocol():
    step = ScenarioStep(
        name="Connect",
        action=ActionType.CONNECT,
        params={},
    )
    definition = ScenarioDefinition(
        name="Test Scenario",
        description="A test scenario",
        steps=[step],
    )
    errors = ScenarioValidator.validate_definition(definition)
    assert "步骤 1 缺少协议参数" in errors


def test_scenario_validator_yaml_structure():
    yaml_data = {
        "name": "Test Scenario",
        "description": "A test scenario",
        "steps": [
            {
                "name": "Connect",
                "action": "connect",
                "params": {"protocol": "pptp"},
            }
        ],
    }
    errors = ScenarioValidator.validate_yaml_structure(yaml_data)
    assert len(errors) == 0


def test_scenario_validator_yaml_missing_fields():
    yaml_data = {
        "name": "Test Scenario",
    }
    errors = ScenarioValidator.validate_yaml_structure(yaml_data)
    assert "缺少必填字段: description" in errors
    assert "缺少必填字段: steps" in errors


def test_scenario_validator_yaml_invalid_action():
    yaml_data = {
        "name": "Test Scenario",
        "description": "A test scenario",
        "steps": [
            {
                "name": "Connect",
                "action": "invalid_action",
            }
        ],
    }
    errors = ScenarioValidator.validate_yaml_structure(yaml_data)
    assert "步骤 1 动作类型无效: invalid_action" in errors


def test_scenario_state_enum():
    assert ScenarioState.PENDING.value == "pending"
    assert ScenarioState.RUNNING.value == "running"
    assert ScenarioState.PASSED.value == "passed"
    assert ScenarioState.FAILED.value == "failed"


def test_step_result_enum():
    assert StepResult.SUCCESS.value == "success"
    assert StepResult.FAILED.value == "failed"
    assert StepResult.ERROR.value == "error"


def test_action_type_enum():
    assert ActionType.CONNECT.value == "connect"
    assert ActionType.DISCONNECT.value == "disconnect"
    assert ActionType.PING.value == "ping"
    assert ActionType.CHECK.value == "check"
    assert ActionType.WAIT.value == "wait"


def test_load_yaml_scenario():
    yaml_content = """
name: "PPTP 基础连接测试"
description: "测试 PPTP 协议的基本连接功能"
tags: ["pptp", "basic", "connection"]
version: "1.0"
timeout: 120

setup:
  - start_protocol: "pptp"

steps:
  - name: "建立 PPTP 连接"
    action: "connect"
    params:
      protocol: "pptp"
      user: "test"
    expect:
      state: "connected"
    timeout: 30

  - name: "检查连接状态"
    action: "check"
    params:
      connection_type: "pptp"
    expect:
      state: "connected"

teardown:
  - stop_protocol: "pptp"
"""
    data = yaml.safe_load(yaml_content)
    assert data["name"] == "PPTP 基础连接测试"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["action"] == "connect"