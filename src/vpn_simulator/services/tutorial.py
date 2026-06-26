"""教程引导服务。

提供教程的加载、查询、会话管理等功能。
从 YAML 配置文件加载教程定义，管理用户的学习会话。

Example:
    >>> service = TutorialService(config_path="config/tutorials")
    >>> tutorials = await service.list_tutorials()
    >>> session = await service.start_tutorial("pptp_basics")
    >>> await service.next_step("pptp_basics")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from vpn_simulator.domain.tutorial import Tutorial, TutorialSession, TutorialStep

logger = structlog.get_logger(__name__)


class TutorialService:
    """教程引导服务。

    负责教程的加载、查询和会话管理。
    从 YAML 配置文件加载教程定义，维护用户的学习会话状态。

    Attributes:
        _config_path: 教程配置文件目录路径。
        _tutorials: 已加载的教程映射。
        _sessions: 活跃的教程会话映射。
    """

    def __init__(self, config_path: str = "config/tutorials") -> None:
        """初始化教程服务。

        Args:
            config_path: 教程配置文件目录路径。
        """
        self._config_path = Path(config_path)
        self._tutorials: dict[str, Tutorial] = {}
        self._sessions: dict[str, TutorialSession] = {}
        self._load_tutorials()

    def _load_tutorials(self) -> None:
        """从 YAML 文件加载所有教程定义。"""
        if not self._config_path.exists():
            logger.warning("tutorial_config_path_not_exists", path=str(self._config_path))
            return

        for yaml_file in self._config_path.glob("*.yaml"):
            try:
                self._load_tutorial_file(yaml_file)
            except Exception as e:
                logger.error("failed_to_load_tutorial", file=str(yaml_file), error=str(e))

        for yml_file in self._config_path.glob("*.yml"):
            try:
                self._load_tutorial_file(yml_file)
            except Exception as e:
                logger.error("failed_to_load_tutorial", file=str(yml_file), error=str(e))

        logger.info("tutorials_loaded", count=len(self._tutorials))

    def _load_tutorial_file(self, file_path: Path) -> None:
        """加载单个教程配置文件。

        Args:
            file_path: YAML 文件路径。
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        tutorial_id = file_path.stem
        steps = []
        for step_data in data.get("steps", []):
            step = TutorialStep(
                title=step_data.get("title", ""),
                description=step_data.get("description", ""),
                packet_info=step_data.get("packet_info", ""),
                rfc_reference=step_data.get("rfc_reference", ""),
                expected_state=step_data.get("expected_state", ""),
                hint=step_data.get("hint", ""),
            )
            steps.append(step)

        tutorial = Tutorial(
            id=tutorial_id,
            name=data.get("name", tutorial_id),
            protocol=data.get("protocol", ""),
            description=data.get("description", ""),
            steps=steps,
            difficulty=data.get("difficulty", "beginner"),
            estimated_time=data.get("estimated_time", 10),
        )

        self._tutorials[tutorial_id] = tutorial
        logger.debug("tutorial_loaded", id=tutorial_id, name=tutorial.name)

    async def list_tutorials(self) -> list[dict[str, Any]]:
        """获取所有可用教程列表。

        Returns:
            教程摘要信息列表。
        """
        tutorials = []
        for tutorial in self._tutorials.values():
            tutorials.append({
                "id": tutorial.id,
                "name": tutorial.name,
                "protocol": tutorial.protocol,
                "description": tutorial.description,
                "difficulty": tutorial.difficulty,
                "estimated_time": tutorial.estimated_time,
                "total_steps": tutorial.total_steps,
            })
        return tutorials

    async def get_tutorial(self, tutorial_id: str) -> Optional[dict[str, Any]]:
        """获取教程详情。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            教程详细信息，不存在返回 None。
        """
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial is None:
            return None

        return {
            "id": tutorial.id,
            "name": tutorial.name,
            "protocol": tutorial.protocol,
            "description": tutorial.description,
            "difficulty": tutorial.difficulty,
            "estimated_time": tutorial.estimated_time,
            "total_steps": tutorial.total_steps,
            "steps": [
                {
                    "title": step.title,
                    "description": step.description,
                    "packet_info": step.packet_info,
                    "rfc_reference": step.rfc_reference,
                    "expected_state": step.expected_state,
                    "hint": step.hint,
                }
                for step in tutorial.steps
            ],
        }

    async def get_tutorial_session(
        self, tutorial_id: str
    ) -> Optional[dict[str, Any]]:
        """获取教程会话状态。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            会话状态信息，不存在返回 None。
        """
        session = self._sessions.get(tutorial_id)
        if session is None:
            return None

        tutorial = self._tutorials.get(tutorial_id)
        current_step = tutorial.get_step(session.current_step) if tutorial else None

        return {
            "tutorial_id": tutorial_id,
            "current_step": session.current_step,
            "total_steps": tutorial.total_steps if tutorial else 0,
            "is_completed": session.is_completed,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "current_step_info": {
                "title": current_step.title,
                "description": current_step.description,
                "packet_info": current_step.packet_info,
                "rfc_reference": current_step.rfc_reference,
                "hint": current_step.hint,
            } if current_step else None,
        }

    async def start_tutorial(self, tutorial_id: str) -> dict[str, Any]:
        """开始或恢复教程学习。

        如果会话已存在则返回当前状态，否则创建新会话。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            会话状态信息。

        Raises:
            ValueError: 教程不存在。
        """
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial is None:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")

        if tutorial_id in self._sessions:
            session = self._sessions[tutorial_id]
            if session.is_completed:
                session.reset()
        else:
            session = TutorialSession(tutorial_id=tutorial_id)
            self._sessions[tutorial_id] = session

        current_step = tutorial.get_step(session.current_step)

        logger.info("tutorial_started", tutorial_id=tutorial_id, step=session.current_step)

        return {
            "tutorial_id": tutorial_id,
            "current_step": session.current_step,
            "total_steps": tutorial.total_steps,
            "is_completed": session.is_completed,
            "started_at": session.started_at,
            "current_step_info": {
                "title": current_step.title,
                "description": current_step.description,
                "packet_info": current_step.packet_info,
                "rfc_reference": current_step.rfc_reference,
                "hint": current_step.hint,
            } if current_step else None,
        }

    async def next_step(self, tutorial_id: str) -> dict[str, Any]:
        """前进到下一步骤。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            更新后的会话状态。

        Raises:
            ValueError: 教程不存在或会话不存在。
        """
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial is None:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")

        session = self._sessions.get(tutorial_id)
        if session is None:
            raise ValueError(f"Tutorial session '{tutorial_id}' not started")

        if session.is_completed:
            return {
                "tutorial_id": tutorial_id,
                "current_step": session.current_step,
                "total_steps": tutorial.total_steps,
                "is_completed": True,
                "message": "Tutorial already completed",
            }

        if session.current_step >= tutorial.total_steps - 1:
            session.complete()
            logger.info("tutorial_completed", tutorial_id=tutorial_id)
            return {
                "tutorial_id": tutorial_id,
                "current_step": session.current_step,
                "total_steps": tutorial.total_steps,
                "is_completed": True,
                "message": "Tutorial completed!",
            }

        session.advance()
        current_step = tutorial.get_step(session.current_step)

        logger.info("tutorial_next_step", tutorial_id=tutorial_id, step=session.current_step)

        return {
            "tutorial_id": tutorial_id,
            "current_step": session.current_step,
            "total_steps": tutorial.total_steps,
            "is_completed": session.is_completed,
            "current_step_info": {
                "title": current_step.title,
                "description": current_step.description,
                "packet_info": current_step.packet_info,
                "rfc_reference": current_step.rfc_reference,
                "hint": current_step.hint,
            } if current_step else None,
        }

    async def prev_step(self, tutorial_id: str) -> dict[str, Any]:
        """后退到上一步骤。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            更新后的会话状态。

        Raises:
            ValueError: 教程不存在或会话不存在。
        """
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial is None:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")

        session = self._sessions.get(tutorial_id)
        if session is None:
            raise ValueError(f"Tutorial session '{tutorial_id}' not started")

        if not session.go_back():
            return {
                "tutorial_id": tutorial_id,
                "current_step": 0,
                "total_steps": tutorial.total_steps,
                "is_completed": session.is_completed,
                "message": "Already at first step",
            }

        current_step = tutorial.get_step(session.current_step)

        logger.info("tutorial_prev_step", tutorial_id=tutorial_id, step=session.current_step)

        return {
            "tutorial_id": tutorial_id,
            "current_step": session.current_step,
            "total_steps": tutorial.total_steps,
            "is_completed": session.is_completed,
            "current_step_info": {
                "title": current_step.title,
                "description": current_step.description,
                "packet_info": current_step.packet_info,
                "rfc_reference": current_step.rfc_reference,
                "hint": current_step.hint,
            } if current_step else None,
        }

    async def reset_tutorial(self, tutorial_id: str) -> dict[str, Any]:
        """重置教程到初始状态。

        Args:
            tutorial_id: 教程 ID。

        Returns:
            重置后的会话状态。

        Raises:
            ValueError: 教程不存在或会话不存在。
        """
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial is None:
            raise ValueError(f"Tutorial '{tutorial_id}' not found")

        session = self._sessions.get(tutorial_id)
        if session is None:
            raise ValueError(f"Tutorial session '{tutorial_id}' not started")

        session.reset()
        current_step = tutorial.get_step(0)

        logger.info("tutorial_reset", tutorial_id=tutorial_id)

        return {
            "tutorial_id": tutorial_id,
            "current_step": 0,
            "total_steps": tutorial.total_steps,
            "is_completed": False,
            "started_at": session.started_at,
            "current_step_info": {
                "title": current_step.title,
                "description": current_step.description,
                "packet_info": current_step.packet_info,
                "rfc_reference": current_step.rfc_reference,
                "hint": current_step.hint,
            } if current_step else None,
        }
