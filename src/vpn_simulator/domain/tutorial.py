"""教程引导系统领域模型。

提供教程、教程步骤、教程会话等核心模型定义。
用于实现分步引导式学习 VPN 协议的握手流程。

Example:
    >>> step = TutorialStep(
    ...     title="发送 SCCRQ",
    ...     description="客户端发起控制连接请求",
    ...     packet_info="SCCRQ 报文包含...",
    ...     rfc_reference="RFC 2637 Section 3.1",
    ... )
    >>> tutorial = Tutorial(
    ...     id="pptp_basics",
    ...     name="PPTP 基础教程",
    ...     protocol="pptp",
    ...     steps=[step],
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class TutorialStep:
    """教程步骤定义。

    Attributes:
        title: 步骤标题。
        description: 步骤详细描述。
        packet_info: 报文信息说明。
        rfc_reference: RFC 文档引用。
        expected_state: 执行此步骤后期望的状态机状态。
        hint: 可选的提示信息。
    """

    title: str
    description: str
    packet_info: str = ""
    rfc_reference: str = ""
    expected_state: str = ""
    hint: str = ""


@dataclass
class Tutorial:
    """教程定义。

    Attributes:
        id: 教程唯一标识符。
        name: 教程显示名称。
        protocol: 关联的协议名称。
        description: 教程描述。
        steps: 教程步骤列表。
        difficulty: 难度级别 (beginner/intermediate/advanced)。
        estimated_time: 预计完成时间（分钟）。
    """

    id: str
    name: str
    protocol: str
    description: str = ""
    steps: list[TutorialStep] = field(default_factory=list)
    difficulty: str = "beginner"
    estimated_time: int = 10

    @property
    def total_steps(self) -> int:
        """获取教程总步骤数。"""
        return len(self.steps)

    def get_step(self, index: int) -> Optional[TutorialStep]:
        """获取指定索引的步骤。

        Args:
            index: 步骤索引（从 0 开始）。

        Returns:
            教程步骤，索引越界返回 None。
        """
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None


@dataclass
class TutorialSession:
    """教程学习会话。

    跟踪用户在教程中的进度和状态。

    Attributes:
        tutorial_id: 教程 ID。
        current_step: 当前步骤索引。
        started_at: 会话开始时间。
        completed_at: 会话完成时间。
        is_completed: 是否已完成。
        step_history: 步骤操作历史记录。
    """

    tutorial_id: str
    current_step: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    is_completed: bool = False
    step_history: list[dict[str, Any]] = field(default_factory=list)

    def advance(self) -> bool:
        """前进到下一步骤。

        Returns:
            True 表示成功前进，False 表示已到最后一步。
        """
        self.step_history.append({
            "action": "next",
            "from_step": self.current_step,
            "timestamp": datetime.now().isoformat(),
        })
        self.current_step += 1
        return True

    def go_back(self) -> bool:
        """后退到上一步骤。

        Returns:
            True 表示成功后退，False 表示已在第一步。
        """
        if self.current_step <= 0:
            return False
        self.step_history.append({
            "action": "prev",
            "from_step": self.current_step,
            "timestamp": datetime.now().isoformat(),
        })
        self.current_step -= 1
        return True

    def reset(self) -> None:
        """重置会话到初始状态。"""
        self.step_history.append({
            "action": "reset",
            "from_step": self.current_step,
            "timestamp": datetime.now().isoformat(),
        })
        self.current_step = 0
        self.completed_at = None
        self.is_completed = False

    def complete(self) -> None:
        """标记会话为已完成。"""
        self.is_completed = True
        self.completed_at = datetime.now().isoformat()
        self.step_history.append({
            "action": "complete",
            "from_step": self.current_step,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict[str, Any]:
        """将会话转换为字典。"""
        return {
            "tutorial_id": self.tutorial_id,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "is_completed": self.is_completed,
            "step_history": self.step_history,
        }
