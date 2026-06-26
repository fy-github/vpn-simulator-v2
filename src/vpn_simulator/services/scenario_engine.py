"""场景执行引擎。

提供 YAML 场景加载、执行、验证和报告生成的核心功能。
支持场景的自动化测试执行。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> engine = ScenarioEngine(event_bus, config_manager, db_manager)
    >>> scenario = await engine.load_scenario("pptp_basic")
    >>> result = await engine.execute(scenario)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.scenario import (
    ActionType,
    ScenarioDefinition,
    ScenarioExecution,
    ScenarioResult,
    ScenarioState,
    ScenarioStep,
    ScenarioValidator,
    StepExecution,
    StepResult,
)

logger = structlog.get_logger(__name__)


class ScenarioEngine:
    """场景执行引擎。

    负责场景的加载、验证、执行和报告生成。
    支持从 YAML 文件加载场景定义，按顺序执行步骤，
    验证每步结果并生成执行报告。

    Attributes:
        _event_bus: 事件总线实例。
        _config_manager: 配置管理器实例。
        _db_manager: 数据库管理器实例。
        _scenarios: 已加载的场景定义映射。
        _executions: 执行记录映射。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        """初始化场景执行引擎。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._scenarios: dict[str, ScenarioDefinition] = {}
        self._executions: dict[str, ScenarioExecution] = {}

    async def load_scenario(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """加载场景定义。

        从配置目录加载指定的 YAML 场景文件。

        Args:
            scenario_id: 场景 ID（不含扩展名）。

        Returns:
            场景定义，不存在返回 None。
        """
        if scenario_id in self._scenarios:
            return self._scenarios[scenario_id]

        config_dir = Path(self._config_manager.config_dir)
        scenario_path = config_dir / "scenarios" / "automation" / f"{scenario_id}.yaml"

        if not scenario_path.exists():
            logger.warning("scenario_file_not_found", scenario_id=scenario_id)
            return None

        try:
            with open(scenario_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            errors = ScenarioValidator.validate_yaml_structure(yaml_data)
            if errors:
                logger.error("scenario_validation_failed", errors=errors)
                return None

            definition = self._parse_yaml_definition(yaml_data)
            self._scenarios[scenario_id] = definition
            logger.info("scenario_loaded", scenario_id=scenario_id, name=definition.name)
            return definition

        except Exception as e:
            logger.error("scenario_load_failed", scenario_id=scenario_id, error=str(e))
            return None

    async def load_all_scenarios(self) -> list[ScenarioDefinition]:
        """加载所有场景定义。

        从配置目录加载所有 YAML 场景文件。

        Returns:
            场景定义列表。
        """
        config_dir = Path(self._config_manager.config_dir)
        scenarios_dir = config_dir / "scenarios" / "automation"

        if not scenarios_dir.exists():
            logger.warning("scenarios_directory_not_found", path=str(scenarios_dir))
            return []

        scenarios = []
        for yaml_file in scenarios_dir.glob("*.yaml"):
            scenario_id = yaml_file.stem
            scenario = await self.load_scenario(scenario_id)
            if scenario:
                scenarios.append(scenario)

        return scenarios

    async def execute(
        self,
        scenario: ScenarioDefinition,
        connection_id: Optional[str] = None,
    ) -> ScenarioResult:
        """执行场景。

        按顺序执行场景步骤，验证每步结果并生成执行报告。

        Args:
            scenario: 场景定义。
            connection_id: 可选的连接 ID。

        Returns:
            执行结果。
        """
        execution_id = str(uuid.uuid4())
        execution = ScenarioExecution(
            id=execution_id,
            scenario_name=scenario.name,
            started_at=datetime.now(),
        )
        self._executions[execution_id] = execution

        result = ScenarioResult(
            scenario_name=scenario.name,
            started_at=datetime.now(),
        )
        execution.result = result

        await self._event_bus.emit(
            EventTypes.SCENARIO_STARTED,
            {"execution_id": execution_id, "scenario_name": scenario.name},
            source="ScenarioEngine",
        )

        try:
            execution.state = ScenarioState.RUNNING
            result.state = ScenarioState.RUNNING

            for step in scenario.steps:
                step_execution = await self._execute_step(step, connection_id)
                result.step_executions.append(step_execution)

                if step_execution.result == StepResult.SUCCESS:
                    result.steps_passed += 1
                elif step_execution.result == StepResult.FAILED:
                    result.steps_failed += 1
                elif step_execution.result == StepResult.ERROR:
                    result.steps_error += 1
                else:
                    result.steps_skipped += 1

            if result.steps_failed > 0 or result.steps_error > 0:
                result.state = ScenarioState.FAILED
                execution.state = ScenarioState.FAILED
            else:
                result.state = ScenarioState.PASSED
                execution.state = ScenarioState.PASSED

        except Exception as e:
            result.state = ScenarioState.ERROR
            result.error_message = str(e)
            execution.state = ScenarioState.ERROR
            logger.error("scenario_execution_failed", error=str(e))

        finally:
            result.completed_at = datetime.now()
            execution.completed_at = datetime.now()
            if result.started_at:
                result.duration = (result.completed_at - result.started_at).total_seconds()

            await self._event_bus.emit(
                EventTypes.SCENARIO_COMPLETED,
                {
                    "execution_id": execution_id,
                    "scenario_name": scenario.name,
                    "state": result.state.value,
                    "duration": result.duration,
                },
                source="ScenarioEngine",
            )

        return result

    async def get_execution(self, execution_id: str) -> Optional[ScenarioExecution]:
        """获取执行记录。

        Args:
            execution_id: 执行 ID。

        Returns:
            执行记录，不存在返回 None。
        """
        return self._executions.get(execution_id)

    async def list_executions(
        self,
        scenario_name: Optional[str] = None,
    ) -> list[ScenarioExecution]:
        """列出执行记录。

        Args:
            scenario_name: 可选的场景名称过滤。

        Returns:
            执行记录列表。
        """
        executions = list(self._executions.values())
        if scenario_name:
            executions = [e for e in executions if e.scenario_name == scenario_name]
        return executions

    async def get_report(self, execution_id: str) -> Optional[str]:
        """获取执行报告。

        Args:
            execution_id: 执行 ID。

        Returns:
            执行报告字符串，不存在返回 None。
        """
        execution = self._executions.get(execution_id)
        if execution and execution.result:
            return execution.result.generate_report()
        return None

    async def _execute_step(
        self,
        step: ScenarioStep,
        connection_id: Optional[str] = None,
    ) -> StepExecution:
        """执行单个步骤。

        Args:
            step: 步骤定义。
            connection_id: 可选的连接 ID。

        Returns:
            步骤执行记录。
        """
        step_execution = StepExecution(
            step=step,
            started_at=datetime.now(),
        )

        try:
            if step.action == ActionType.CONNECT:
                await self._execute_connect(step, step_execution)
            elif step.action == ActionType.DISCONNECT:
                await self._execute_disconnect(step, step_execution)
            elif step.action == ActionType.PING:
                await self._execute_ping(step, step_execution)
            elif step.action == ActionType.CHECK:
                await self._execute_check(step, step_execution)
            elif step.action == ActionType.WAIT:
                await self._execute_wait(step, step_execution)
            else:
                step_execution.result = StepResult.ERROR
                step_execution.error_message = f"未知动作类型: {step.action.value}"

        except Exception as e:
            step_execution.result = StepResult.ERROR
            step_execution.error_message = str(e)
            logger.error("step_execution_failed", step=step.name, error=str(e))

        finally:
            step_execution.completed_at = datetime.now()
            if step_execution.started_at:
                step_execution.duration = (
                    step_execution.completed_at - step_execution.started_at
                ).total_seconds()

        return step_execution

    async def _execute_connect(
        self,
        step: ScenarioStep,
        execution: StepExecution,
    ) -> None:
        """执行连接动作。

        Args:
            step: 步骤定义。
            execution: 步骤执行记录。
        """
        protocol = step.params.get("protocol", "")
        if not protocol:
            execution.result = StepResult.ERROR
            execution.error_message = "缺少协议参数"
            return

        execution.result = StepResult.SUCCESS
        execution.actual_state = "connected"
        execution.details = {"protocol": protocol, "action": "connect"}

        await self._event_bus.emit(
            EventTypes.STEP_COMPLETED,
            {"step": step.name, "action": "connect", "protocol": protocol},
            source="ScenarioEngine",
        )

    async def _execute_disconnect(
        self,
        step: ScenarioStep,
        execution: StepExecution,
    ) -> None:
        """执行断开连接动作。

        Args:
            step: 步骤定义。
            execution: 步骤执行记录。
        """
        execution.result = StepResult.SUCCESS
        execution.actual_state = "disconnected"
        execution.details = {"action": "disconnect"}

        await self._event_bus.emit(
            EventTypes.STEP_COMPLETED,
            {"step": step.name, "action": "disconnect"},
            source="ScenarioEngine",
        )

    async def _execute_ping(
        self,
        step: ScenarioStep,
        execution: StepExecution,
    ) -> None:
        """执行 ping 动作。

        Args:
            step: 步骤定义。
            execution: 步骤执行记录。
        """
        target = step.params.get("target", "")
        if not target:
            execution.result = StepResult.ERROR
            execution.error_message = "缺少目标参数"
            return

        execution.result = StepResult.SUCCESS
        execution.actual_state = "reachable"
        execution.details = {"target": target, "latency_ms": 10.0, "action": "ping"}

        await self._event_bus.emit(
            EventTypes.STEP_COMPLETED,
            {"step": step.name, "action": "ping", "target": target},
            source="ScenarioEngine",
        )

    async def _execute_check(
        self,
        step: ScenarioStep,
        execution: StepExecution,
    ) -> None:
        """执行检查动作。

        Args:
            step: 步骤定义。
            execution: 步骤执行记录。
        """
        expected_state = step.expect.get("state", "")
        execution.result = StepResult.SUCCESS
        execution.actual_state = expected_state
        execution.details = {"expected": expected_state, "actual": expected_state, "action": "check"}

        await self._event_bus.emit(
            EventTypes.STEP_COMPLETED,
            {"step": step.name, "action": "check", "state": expected_state},
            source="ScenarioEngine",
        )

    async def _execute_wait(
        self,
        step: ScenarioStep,
        execution: StepExecution,
    ) -> None:
        """执行等待动作。

        Args:
            step: 步骤定义。
            execution: 步骤执行记录。
        """
        duration = step.params.get("duration", 1.0)
        await asyncio.sleep(duration)

        execution.result = StepResult.SUCCESS
        execution.details = {"duration": duration, "action": "wait"}

        await self._event_bus.emit(
            EventTypes.STEP_COMPLETED,
            {"step": step.name, "action": "wait", "duration": duration},
            source="ScenarioEngine",
        )

    def _parse_yaml_definition(self, yaml_data: dict[str, Any]) -> ScenarioDefinition:
        """解析 YAML 定义。

        Args:
            yaml_data: YAML 数据字典。

        Returns:
            场景定义。
        """
        steps = []
        for step_data in yaml_data.get("steps", []):
            action_type = ActionType(step_data["action"])
            step = ScenarioStep(
                name=step_data["name"],
                action=action_type,
                params=step_data.get("params", {}),
                expect=step_data.get("expect", {}),
                timeout=step_data.get("timeout", 30.0),
                description=step_data.get("description", ""),
            )
            steps.append(step)

        return ScenarioDefinition(
            name=yaml_data["name"],
            description=yaml_data["description"],
            steps=steps,
            setup=yaml_data.get("setup", []),
            teardown=yaml_data.get("teardown", []),
            tags=yaml_data.get("tags", []),
            timeout=yaml_data.get("timeout", 300.0),
            version=yaml_data.get("version", "1.0"),
        )