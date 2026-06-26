"""场景预设服务。

提供网络场景预设的加载、查询、应用和移除等业务逻辑。
协调 Domain 层的 ScenarioManager、FaultService 和配置加载。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> service = ScenarioService(event_bus, config_manager, db_manager)
    >>> scenarios = await service.list_scenarios()
    >>> await service.apply_scenario("3g")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus, EventTypes
from vpn_simulator.domain.scenario import ScenarioManager, ScenarioPreset
from vpn_simulator.services.fault import FaultService

logger = structlog.get_logger(__name__)

# 默认预设配置路径
DEFAULT_PRESETS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "scenarios" / "presets.yaml"


class ScenarioService:
    """场景预设服务。

    负责网络场景预设的全生命周期管理，包括加载、查询、
    应用和移除。通过事件总线发布场景相关事件。

    Attributes:
        _event_bus: 事件总线实例。
        _config_manager: 配置管理器实例。
        _db_manager: 数据库管理器实例。
        _fault_service: 故障注入服务实例。
        _scenario_manager: 领域层场景管理器实例。
    """

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
        fault_service: FaultService,
        presets_path: Optional[Path] = None,
    ) -> None:
        """初始化场景预设服务。

        Args:
            event_bus: 事件总线实例。
            config_manager: 配置管理器实例。
            db_manager: 数据库管理器实例。
            fault_service: 故障注入服务实例。
            presets_path: 预设配置文件路径，默认使用内置预设。
        """
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager
        self._fault_service = fault_service
        self._scenario_manager = ScenarioManager()
        self._presets_path = presets_path or DEFAULT_PRESETS_PATH
        self._active_fault_ids: dict[str, list[str]] = {}

    def load_presets(self) -> None:
        """从 YAML 文件加载预设场景。"""
        if not self._presets_path.exists():
            logger.warning("presets_file_not_found", path=str(self._presets_path))
            return

        try:
            with open(self._presets_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            presets = []
            for scenario_id, scenario_data in data.get("scenarios", {}).items():
                preset = ScenarioPreset(
                    id=scenario_data.get("id", scenario_id),
                    name=scenario_data.get("name", scenario_id),
                    description=scenario_data.get("description", ""),
                    icon=scenario_data.get("icon", "network_check"),
                    category=scenario_data.get("category", "other"),
                    faults=scenario_data.get("faults", {}),
                )
                presets.append(preset)

            self._scenario_manager.load_presets(presets)
            logger.info("presets_loaded", count=len(presets), path=str(self._presets_path))
        except Exception as e:
            logger.error("presets_load_error", path=str(self._presets_path), error=str(e))

    async def list_scenarios(
        self,
        category: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """列出所有预设场景。

        Args:
            category: 可选的分类过滤。

        Returns:
            场景预设字典列表。
        """
        scenarios = self._scenario_manager.list_scenarios(category=category)
        active_id = self._scenario_manager.get_active_scenario()

        result = []
        for s in scenarios:
            d = s.to_dict()
            d["active"] = s.id == active_id
            result.append(d)

        logger.info(
            "scenarios_listed",
            count=len(result),
            category=category,
        )
        return result

    async def get_scenario(self, scenario_id: str) -> Optional[dict[str, Any]]:
        """获取指定场景的详细信息。

        Args:
            scenario_id: 场景 ID。

        Returns:
            场景信息字典，不存在返回 None。
        """
        scenario = self._scenario_manager.get_scenario(scenario_id)
        if scenario is None:
            logger.warning("scenario_not_found", scenario_id=scenario_id)
            return None

        d = scenario.to_dict()
        d["active"] = scenario_id == self._scenario_manager.get_active_scenario()
        return d

    async def apply_scenario(self, scenario_id: str) -> dict[str, Any]:
        """应用场景。

        根据场景预设创建并激活对应的故障注入实例。

        Args:
            scenario_id: 场景 ID。

        Returns:
            包含应用结果的字典。

        Raises:
            ValueError: 场景不存在。
        """
        scenario = self._scenario_manager.get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario '{scenario_id}' not found")

        # 如果已有激活场景，先移除
        current_active = self._scenario_manager.get_active_scenario()
        if current_active:
            await self.remove_scenario(current_active)

        # 为场景中的每种故障类型创建故障实例
        fault_ids = []
        for fault_type, params in scenario.faults.items():
            try:
                fault = await self._fault_service.create_fault(
                    fault_type=fault_type,
                    params=params,
                    target=f"scenario:{scenario_id}",
                )
                fault_ids.append(fault["id"])
                await self._fault_service.activate_fault(fault["id"])
            except Exception as e:
                logger.error(
                    "scenario_fault_create_error",
                    scenario_id=scenario_id,
                    fault_type=fault_type,
                    error=str(e),
                )

        # 记录激活的故障 ID
        self._active_fault_ids[scenario_id] = fault_ids

        # 设置激活场景
        self._scenario_manager.set_active_scenario(scenario_id)

        # 发布事件
        await self._event_bus.emit(
            EventTypes.FAULT_INJECTED,
            {
                "scenario_id": scenario_id,
                "action": "applied",
                "fault_ids": fault_ids,
            },
            source="ScenarioService",
        )

        logger.info(
            "scenario_applied",
            scenario_id=scenario_id,
            fault_count=len(fault_ids),
        )

        return {
            "scenario_id": scenario_id,
            "status": "applied",
            "fault_ids": fault_ids,
            "message": f"Scenario '{scenario.name}' applied with {len(fault_ids)} faults",
        }

    async def remove_scenario(self, scenario_id: str) -> dict[str, Any]:
        """移除场景。

        停用并移除场景关联的所有故障注入实例。

        Args:
            scenario_id: 场景 ID。

        Returns:
            包含移除结果的字典。

        Raises:
            ValueError: 场景不存在或未激活。
        """
        scenario = self._scenario_manager.get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario '{scenario_id}' not found")

        if self._scenario_manager.get_active_scenario() != scenario_id:
            raise ValueError(f"Scenario '{scenario_id}' is not active")

        # 移除关联的故障实例
        fault_ids = self._active_fault_ids.get(scenario_id, [])
        removed_count = 0
        for fault_id in fault_ids:
            try:
                removed = await self._fault_service.remove_fault(fault_id)
                if removed:
                    removed_count += 1
            except Exception as e:
                logger.error(
                    "scenario_fault_remove_error",
                    scenario_id=scenario_id,
                    fault_id=fault_id,
                    error=str(e),
                )

        # 清理状态
        self._active_fault_ids.pop(scenario_id, None)
        self._scenario_manager.remove_active_scenario()

        # 发布事件
        await self._event_bus.emit(
            EventTypes.FAULT_REMOVED,
            {
                "scenario_id": scenario_id,
                "action": "removed",
                "removed_faults": removed_count,
            },
            source="ScenarioService",
        )

        logger.info(
            "scenario_removed",
            scenario_id=scenario_id,
            removed_faults=removed_count,
        )

        return {
            "scenario_id": scenario_id,
            "status": "removed",
            "removed_faults": removed_count,
            "message": f"Scenario '{scenario.name}' removed ({removed_count} faults cleared)",
        }

    async def get_active_scenario(self) -> Optional[dict[str, Any]]:
        """获取当前激活的场景。

        Returns:
            激活的场景信息字典，无激活场景返回 None。
        """
        active_id = self._scenario_manager.get_active_scenario()
        if active_id is None:
            return None
        return await self.get_scenario(active_id)
