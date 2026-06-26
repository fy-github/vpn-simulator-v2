"""场景预设模型。

提供预定义网络场景的数据模型，每个场景包含一组故障注入参数。
支持场景的加载、查询和应用。

Example:
    >>> scenario = ScenarioPreset(
    ...     id="3g",
    ...     name="3G",
    ...     description="3G mobile network",
    ...     faults={"latency": {"delay_ms": 200}},
    ... )
    >>> scenario.name
    '3G'
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


@dataclass
class ScenarioFaultConfig:
    """场景故障配置。

    Attributes:
        fault_type: 故障类型（latency, packet_loss, bandwidth 等）。
        params: 故障参数字典。
    """

    fault_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {"type": self.fault_type, "params": self.params}


@dataclass
class ScenarioPreset:
    """场景预设数据类。

    封装一个预定义网络场景的完整信息。

    Attributes:
        id: 场景唯一标识符。
        name: 场景显示名称。
        description: 场景描述。
        icon: 场景图标名称。
        category: 场景分类（mobile, satellite, wifi, wired）。
        faults: 故障配置字典，key 为故障类型，value 为参数。
    """

    id: str
    name: str
    description: str = ""
    icon: str = "network_check"
    category: str = "other"
    faults: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "faults": self.faults,
        }


class ScenarioManager:
    """场景管理器。

    负责场景预设的加载、查询和管理。
    """

    def __init__(self) -> None:
        """初始化场景管理器。"""
        self._scenarios: dict[str, ScenarioPreset] = {}
        self._active_scenario: Optional[str] = None

    def load_presets(self, presets: list[ScenarioPreset]) -> None:
        """加载预设场景列表。

        Args:
            presets: 预设场景列表。
        """
        for preset in presets:
            self._scenarios[preset.id] = preset

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioPreset]:
        """获取指定场景。

        Args:
            scenario_id: 场景 ID。

        Returns:
            场景预设，不存在返回 None。
        """
        return self._scenarios.get(scenario_id)

    def list_scenarios(self, category: Optional[str] = None) -> list[ScenarioPreset]:
        """列出场景。

        Args:
            category: 可选的分类过滤。

        Returns:
            场景预设列表。
        """
        scenarios = list(self._scenarios.values())
        if category:
            scenarios = [s for s in scenarios if s.category == category]
        return scenarios

    def get_active_scenario(self) -> Optional[str]:
        """获取当前激活的场景 ID。

        Returns:
            激活的场景 ID，无激活场景返回 None。
        """
        return self._active_scenario

    def set_active_scenario(self, scenario_id: Optional[str]) -> bool:
        """设置激活场景。

        Args:
            scenario_id: 场景 ID，None 表示清除激活。

        Returns:
            True 表示设置成功，False 表示场景不存在。
        """
        if scenario_id is not None and scenario_id not in self._scenarios:
            return False
        self._active_scenario = scenario_id
        return True

    def remove_active_scenario(self) -> bool:
        """移除激活场景。

        Returns:
            True 表示移除成功，False 表示无激活场景。
        """
        if self._active_scenario is None:
            return False
        self._active_scenario = None
        return True


class ScenarioState(Enum):
    """场景执行状态枚举。

    Attributes:
        PENDING: 等待执行。
        RUNNING: 正在执行。
        PASSED: 执行成功。
        FAILED: 执行失败。
        ERROR: 执行出错。
        SKIPPED: 已跳过。
    """

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class StepResult(Enum):
    """步骤执行结果枚举。

    Attributes:
        SUCCESS: 步骤执行成功。
        FAILED: 步骤执行失败。
        ERROR: 步骤执行出错。
        SKIPPED: 步骤已跳过。
    """

    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ActionType(Enum):
    """动作类型枚举。

    Attributes:
        CONNECT: 建立连接。
        DISCONNECT: 断开连接。
        PING: 测试延迟。
        CHECK: 检查状态。
        WAIT: 等待。
    """

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    CHECK = "check"
    WAIT = "wait"


@dataclass
class ScenarioStep:
    """场景步骤定义。

    Attributes:
        name: 步骤名称。
        action: 动作类型。
        params: 动作参数。
        expect: 期望结果。
        timeout: 超时时间（秒）。
        description: 步骤描述。
    """

    name: str
    action: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    expect: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    description: str = ""


@dataclass
class StepExecution:
    """步骤执行记录。

    Attributes:
        step: 步骤定义。
        result: 执行结果。
        started_at: 开始时间。
        completed_at: 完成时间。
        duration: 执行时长（秒）。
        actual_state: 实际状态。
        error_message: 错误信息。
        details: 执行详情。
    """

    step: ScenarioStep
    result: StepResult = StepResult.SKIPPED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    actual_state: Optional[str] = None
    error_message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将步骤执行记录转换为字典。

        Returns:
            包含所有执行信息的字典。
        """
        return {
            "step_name": self.step.name,
            "action": self.step.action.value,
            "result": self.result.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "actual_state": self.actual_state,
            "error_message": self.error_message,
            "details": self.details,
        }


@dataclass
class ScenarioDefinition:
    """场景定义。

    Attributes:
        name: 场景名称。
        description: 场景描述。
        steps: 场景步骤列表。
        setup: 环境准备步骤。
        teardown: 环境清理步骤。
        tags: 场景标签。
        timeout: 整体超时时间（秒）。
        version: 场景版本。
    """

    name: str
    description: str
    steps: list[ScenarioStep] = field(default_factory=list)
    setup: list[dict[str, Any]] = field(default_factory=list)
    teardown: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timeout: float = 300.0
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """将场景定义转换为字典。

        Returns:
            包含所有场景信息的字典。
        """
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "name": step.name,
                    "action": step.action.value,
                    "params": step.params,
                    "expect": step.expect,
                    "timeout": step.timeout,
                    "description": step.description,
                }
                for step in self.steps
            ],
            "setup": self.setup,
            "teardown": self.teardown,
            "tags": self.tags,
            "timeout": self.timeout,
            "version": self.version,
        }


@dataclass
class ScenarioResult:
    """场景执行结果。

    Attributes:
        scenario_name: 场景名称。
        state: 执行状态。
        started_at: 开始时间。
        completed_at: 完成时间。
        duration: 执行时长（秒）。
        steps_passed: 成功步骤数。
        steps_failed: 失败步骤数。
        steps_error: 出错步骤数。
        steps_skipped: 跳过步骤数。
        step_executions: 步骤执行记录列表。
        error_message: 错误信息。
        details: 额外详情。
    """

    scenario_name: str
    state: ScenarioState = ScenarioState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    steps_passed: int = 0
    steps_failed: int = 0
    steps_error: int = 0
    steps_skipped: int = 0
    step_executions: list[StepExecution] = field(default_factory=list)
    error_message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        """总步骤数。

        Returns:
            步骤总数。
        """
        return self.steps_passed + self.steps_failed + self.steps_error + self.steps_skipped

    @property
    def success_rate(self) -> float:
        """成功率。

        Returns:
            成功率百分比。
        """
        if self.total_steps == 0:
            return 0.0
        return (self.steps_passed / self.total_steps) * 100

    def to_dict(self) -> dict[str, Any]:
        """将执行结果转换为字典。

        Returns:
            包含所有结果信息的字典。
        """
        return {
            "scenario_name": self.scenario_name,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "total_steps": self.total_steps,
            "steps_passed": self.steps_passed,
            "steps_failed": self.steps_failed,
            "steps_error": self.steps_error,
            "steps_skipped": self.steps_skipped,
            "success_rate": self.success_rate,
            "step_executions": [step.to_dict() for step in self.step_executions],
            "error_message": self.error_message,
            "details": self.details,
        }

    def generate_report(self) -> str:
        """生成执行报告。

        Returns:
            格式化的执行报告字符串。
        """
        report_lines = [
            f"场景执行报告: {self.scenario_name}",
            "=" * 50,
            f"状态: {self.state.value}",
            f"开始时间: {self.started_at.isoformat() if self.started_at else 'N/A'}",
            f"完成时间: {self.completed_at.isoformat() if self.completed_at else 'N/A'}",
            f"执行时长: {self.duration:.2f} 秒",
            "",
            "步骤统计:",
            f"  总步骤数: {self.total_steps}",
            f"  成功: {self.steps_passed}",
            f"  失败: {self.steps_failed}",
            f"  出错: {self.steps_error}",
            f"  跳过: {self.steps_skipped}",
            f"  成功率: {self.success_rate:.1f}%",
            "",
            "步骤详情:",
        ]

        for i, step_exec in enumerate(self.step_executions, 1):
            report_lines.append(f"  {i}. {step_exec.step.name}")
            report_lines.append(f"     动作: {step_exec.step.action.value}")
            report_lines.append(f"     结果: {step_exec.result.value}")
            if step_exec.duration > 0:
                report_lines.append(f"     耗时: {step_exec.duration:.2f} 秒")
            if step_exec.error_message:
                report_lines.append(f"     错误: {step_exec.error_message}")
            report_lines.append("")

        if self.error_message:
            report_lines.extend([
                "错误信息:",
                f"  {self.error_message}",
            ])

        return "\n".join(report_lines)


@dataclass
class ScenarioExecution:
    """场景执行记录。

    Attributes:
        id: 执行 ID。
        scenario_name: 场景名称。
        state: 执行状态。
        result: 执行结果。
        started_at: 开始时间。
        completed_at: 完成时间。
        metadata: 元数据。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scenario_name: str = ""
    state: ScenarioState = ScenarioState.PENDING
    result: Optional[ScenarioResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将执行记录转换为字典。

        Returns:
            包含所有执行信息的字典。
        """
        return {
            "id": self.id,
            "scenario_name": self.scenario_name,
            "state": self.state.value,
            "result": self.result.to_dict() if self.result else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class ScenarioValidator:
    """场景定义验证器。

    提供场景定义的验证功能，确保场景格式正确。
    """

    @staticmethod
    def validate_definition(definition: ScenarioDefinition) -> list[str]:
        """验证场景定义。

        Args:
            definition: 场景定义。

        Returns:
            错误信息列表，空列表表示验证通过。
        """
        errors = []

        if not definition.name:
            errors.append("场景名称不能为空")

        if not definition.description:
            errors.append("场景描述不能为空")

        if not definition.steps:
            errors.append("场景步骤不能为空")

        for i, step in enumerate(definition.steps):
            if not step.name:
                errors.append(f"步骤 {i+1} 名称不能为空")

            if not isinstance(step.action, ActionType):
                errors.append(f"步骤 {i+1} 动作类型无效: {step.action}")

            if step.action == ActionType.CONNECT:
                if "protocol" not in step.params:
                    errors.append(f"步骤 {i+1} 缺少协议参数")

            if step.action == ActionType.PING:
                if "target" not in step.params:
                    errors.append(f"步骤 {i+1} 缺少目标参数")

        return errors

    @staticmethod
    def validate_yaml_structure(yaml_data: dict[str, Any]) -> list[str]:
        """验证 YAML 结构。

        Args:
            yaml_data: YAML 数据字典。

        Returns:
            错误信息列表，空列表表示验证通过。
        """
        errors = []

        required_fields = ["name", "description", "steps"]
        for field_name in required_fields:
            if field_name not in yaml_data:
                errors.append(f"缺少必填字段: {field_name}")

        if "steps" in yaml_data:
            if not isinstance(yaml_data["steps"], list):
                errors.append("steps 必须是列表")

            for i, step in enumerate(yaml_data["steps"]):
                if not isinstance(step, dict):
                    errors.append(f"步骤 {i+1} 必须是字典")
                    continue

                if "name" not in step:
                    errors.append(f"步骤 {i+1} 缺少 name 字段")

                if "action" not in step:
                    errors.append(f"步骤 {i+1} 缺少 action 字段")
                elif step["action"] not in [e.value for e in ActionType]:
                    errors.append(f"步骤 {i+1} 动作类型无效: {step['action']}")

        return errors
