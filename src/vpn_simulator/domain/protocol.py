"""协议状态机核心模型。

提供协议状态机的基类实现，支持状态定义、转换规则、守卫条件、动作回调。
所有协议插件（PPTP、L2TP、OpenVPN 等）都基于此模块实现各自的状态机。

Example:
    >>> class MyProtocol(ProtocolStateMachine):
    ...     def __init__(self):
    ...         super().__init__("MyProtocol")
    ...         self.add_state(State("INIT", "初始状态", is_initial=True))
    ...         self.add_state(State("READY", "就绪", is_final=True))
    ...         self.add_transition(StateTransition("INIT", "READY", "START"))
    ...
    >>> sm = MyProtocol()
    >>> await sm.trigger("START")
    True
"""

from __future__ import annotations

import asyncio
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class State:
    """协议状态定义。

    Attributes:
        name: 状态名称，全局唯一。
        description: 状态的可读描述。
        is_initial: 是否为初始状态。每个状态机只能有一个初始状态。
        is_final: 是否为终态。进入终态后不再接受事件。
        on_enter: 进入该状态时执行的异步回调。
        on_exit: 退出该状态时执行的异步回调。
    """

    name: str
    description: str
    is_initial: bool = False
    is_final: bool = False
    on_enter: Optional[Callable[..., Any]] = None
    on_exit: Optional[Callable[..., Any]] = None


@dataclass
class StateTransition:
    """状态转换规则。

    Attributes:
        from_state: 源状态名称。
        to_state: 目标状态名称。
        event: 触发此转换的事件名称。
        guard: 守卫条件，返回 True 时允许转换。
        action: 转换执行时的异步回调。
        description: 转换的可读描述。
    """

    from_state: str
    to_state: str
    event: str
    guard: Optional[Callable[..., bool]] = None
    action: Optional[Callable[..., Any]] = None
    description: str = ""


@dataclass
class TransitionRecord:
    """状态转换历史记录。

    Attributes:
        timestamp: 转换发生的时间戳。
        from_state: 源状态名称。
        to_state: 目标状态名称。
        event: 触发事件名称。
        context: 转换时的上下文数据。
    """

    timestamp: str
    from_state: str
    to_state: str
    event: str
    context: Optional[dict[str, Any]] = None


class ProtocolStateMachine(ABC):
    """协议状态机基类。

    提供状态注册、转换定义、事件触发、守卫检查、动作执行等核心功能。
    协议插件通过继承此类并定义状态和转换来实现协议状态机。

    Attributes:
        protocol_name: 协议名称。
        states: 已注册的状态集合。
        transitions: 已定义的转换规则列表。
        current_state: 当前状态名称。
        history: 状态转换历史记录。
    """

    def __init__(self, protocol_name: str) -> None:
        """初始化状态机。

        Args:
            protocol_name: 协议名称。
        """
        self.protocol_name = protocol_name
        self.states: dict[str, State] = {}
        self.transitions: list[StateTransition] = []
        self.current_state: Optional[str] = None
        self.history: list[TransitionRecord] = []
        self._listeners: list[Callable[..., Any]] = []

    def add_state(self, state: State) -> None:
        """注册一个状态。

        如果状态标记为初始状态，则自动设置为当前状态。

        Args:
            state: 要注册的状态对象。

        Raises:
            ValueError: 如果同名状态已存在。
        """
        if state.name in self.states:
            raise ValueError(f"State '{state.name}' already exists")
        self.states[state.name] = state
        if state.is_initial:
            self.current_state = state.name

    def add_transition(self, transition: StateTransition) -> None:
        """注册一条转换规则。

        Args:
            transition: 要注册的转换规则。
        """
        self.transitions.append(transition)

    async def trigger(
        self, event: str, context: Optional[dict[str, Any]] = None
    ) -> bool:
        """触发一个事件，尝试执行状态转换。

        流程：查找转换 -> 检查守卫 -> 记录历史 -> 执行退出动作 ->
        执行转换动作 -> 更新状态 -> 执行进入动作 -> 通知监听器。

        Args:
            event: 事件名称。
            context: 可选的上下文数据，传递给守卫和动作回调。

        Returns:
            True 表示转换成功，False 表示未找到匹配转换或守卫拒绝。
        """
        transition = self._find_transition(self.current_state, event)
        if not transition:
            return False

        if transition.guard and not transition.guard(context):
            return False

        record = TransitionRecord(
            timestamp=datetime.now().isoformat(),
            from_state=self.current_state,  # type: ignore[arg-type]
            to_state=transition.to_state,
            event=event,
            context=context,
        )
        self.history.append(record)

        current = self.states[self.current_state]  # type: ignore[index]
        if current.on_exit:
            await current.on_exit(context)

        if transition.action:
            await transition.action(context)

        old_state = self.current_state
        self.current_state = transition.to_state

        new = self.states[self.current_state]
        if new.on_enter:
            await new.on_enter(context)

        await self._notify_listeners(old_state, self.current_state, event)

        return True

    def _find_transition(
        self, from_state: Optional[str], event: str
    ) -> Optional[StateTransition]:
        """查找匹配的转换规则。

        Args:
            from_state: 源状态名称。
            event: 事件名称。

        Returns:
            匹配的转换规则，未找到返回 None。
        """
        for t in self.transitions:
            if t.from_state == from_state and t.event == event:
                return t
        return None

    def on_transition(self, listener: Callable[..., Any]) -> None:
        """注册状态转换监听器。

        监听器签名: async def listener(from_state, to_state, event)

        Args:
            listener: 监听器回调函数。
        """
        self._listeners.append(listener)

    async def _notify_listeners(
        self,
        from_state: Optional[str],
        to_state: Optional[str],
        event: str,
    ) -> None:
        """通知所有监听器。

        Args:
            from_state: 源状态名称。
            to_state: 目标状态名称。
            event: 事件名称。
        """
        for listener in self._listeners:
            await listener(from_state, to_state, event)

    def get_visualization_data(self) -> dict[str, Any]:
        """获取状态机可视化数据。

        返回包含协议名称、当前状态、所有状态和转换的字典，
        可直接用于前端状态图渲染。

        Returns:
            可视化数据字典。
        """
        return {
            "protocol": self.protocol_name,
            "current_state": self.current_state,
            "states": [
                {
                    "name": s.name,
                    "description": s.description,
                    "is_initial": s.is_initial,
                    "is_final": s.is_final,
                    "is_current": s.name == self.current_state,
                }
                for s in self.states.values()
            ],
            "transitions": [
                {
                    "from": t.from_state,
                    "to": t.to_state,
                    "event": t.event,
                    "description": t.description,
                }
                for t in self.transitions
            ],
            "history": [
                {
                    "timestamp": r.timestamp,
                    "from": r.from_state,
                    "to": r.to_state,
                    "event": r.event,
                    "context": r.context,
                }
                for r in self.history
            ],
        }
