"""事件系统模块

提供事件总线、事件类型定义和事件处理功能。
支持同步和异步事件处理器，以及事件历史记录。

Example:
    >>> from vpn_simulator.core.events import EventBus, EventTypes
    >>> bus = EventBus()
    >>> bus.on(EventTypes.CONNECTION_CREATED, lambda e: print(e.data))
    >>> await bus.emit(EventTypes.CONNECTION_CREATED, {"id": "123"})
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# 类型别名
SyncHandler = Callable[["Event"], None]
AsyncHandler = Callable[["Event"], Any]  # 协程函数


@dataclass
class Event:
    """事件数据类

    Attributes:
        name: 事件名称，使用点分隔的命名空间 (如 "connection.created")
        data: 事件携带的数据
        timestamp: 事件发生时间
        source: 事件来源标识
        event_id: 唯一事件 ID
    """

    name: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class EventBus:
    """事件总线

    提供事件的发布/订阅机制，支持同步和异步处理器。
    事件处理器按照注册顺序依次执行。

    Attributes:
        _handlers: 同步事件处理器映射
        _async_handlers: 异步事件处理器映射
        _history: 事件历史记录
        _max_history: 最大历史记录数量

    Example:
        >>> bus = EventBus()
        >>> async def on_connection(event: Event):
        ...     print(f"Connection {event.data['id']} created")
        >>> bus.on_async(EventTypes.CONNECTION_CREATED, on_connection)
        >>> await bus.emit(EventTypes.CONNECTION_CREATED, {"id": "123"})
    """

    def __init__(self, max_history: int = 1000) -> None:
        """初始化事件总线

        Args:
            max_history: 最大历史记录数量，默认 1000
        """
        self._handlers: Dict[str, List[SyncHandler]] = defaultdict(list)
        self._async_handlers: Dict[str, List[AsyncHandler]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = max_history

    def on(self, event_name: str, handler: SyncHandler) -> None:
        """注册同步事件处理器

        Args:
            event_name: 事件名称
            handler: 同步处理函数，接收 Event 参数
        """
        self._handlers[event_name].append(handler)
        logger.debug("sync_handler_registered", event=event_name, handler=handler.__name__)

    def on_async(self, event_name: str, handler: AsyncHandler) -> None:
        """注册异步事件处理器

        Args:
            event_name: 事件名称
            handler: 异步处理函数，接收 Event 参数
        """
        self._async_handlers[event_name].append(handler)
        logger.debug("async_handler_registered", event=event_name, handler=handler.__name__)

    def off(self, event_name: str, handler: SyncHandler | AsyncHandler) -> None:
        """取消注册事件处理器

        Args:
            event_name: 事件名称
            handler: 要移除的处理函数
        """
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)
        if handler in self._async_handlers[event_name]:
            self._async_handlers[event_name].remove(handler)
        logger.debug("handler_unregistered", event=event_name, handler=handler.__name__)

    async def emit(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        source: str = "",
    ) -> Event:
        """触发事件

        创建事件对象并依次执行所有注册的处理器。

        Args:
            event_name: 事件名称
            data: 事件数据，默认为空字典
            source: 事件来源标识

        Returns:
            创建的 Event 对象
        """
        event = Event(
            name=event_name,
            data=data or {},
            source=source,
        )

        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        logger.debug(
            "event_emitted",
            event_name=event_name,
            event_id=event.event_id,
            source=source,
        )

        # 执行同步处理器
        for handler in self._handlers.get(event_name, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    "sync_handler_error",
                    event=event_name,
                    handler=handler.__name__,
                    error=str(e),
                )

        # 执行异步处理器
        for handler in self._async_handlers.get(event_name, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "async_handler_error",
                    event=event_name,
                    handler=handler.__name__,
                    error=str(e),
                )

        return event

    def get_history(
        self,
        event_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """获取事件历史

        Args:
            event_name: 过滤的事件名称，None 表示所有事件
            limit: 返回的最大事件数量

        Returns:
            事件列表
        """
        if event_name:
            events = [e for e in self._history if e.name == event_name]
        else:
            events = self._history
        return events[-limit:]

    def clear_history(self) -> None:
        """清空事件历史"""
        self._history.clear()
        logger.debug("event_history_cleared")

    def has_handlers(self, event_name: str) -> bool:
        """检查事件是否有注册的处理器

        Args:
            event_name: 事件名称

        Returns:
            是否有处理器
        """
        return bool(
            self._handlers.get(event_name) or self._async_handlers.get(event_name)
        )


class EventTypes:
    """事件类型常量

    定义系统中所有标准事件类型，使用点分隔的命名空间。
    """

    # 协议事件
    PROTOCOL_STARTED = "protocol.started"
    PROTOCOL_STOPPED = "protocol.stopped"
    PROTOCOL_ERROR = "protocol.error"

    # 连接事件
    CONNECTION_CREATED = "connection.created"
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_CLOSED = "connection.closed"
    CONNECTION_ERROR = "connection.error"

    # 状态机事件
    STATE_TRANSITION = "state.transition"

    # 报文事件
    PACKET_RECEIVED = "packet.received"
    PACKET_SENT = "packet.sent"
    PACKET_DROPPED = "packet.dropped"

    # 故障注入事件
    FAULT_INJECTED = "fault.injected"
    FAULT_REMOVED = "fault.removed"

    # 攻击事件
    ATTACK_STARTED = "attack.started"
    ATTACK_COMPLETED = "attack.completed"
    ATTACK_DETECTED = "attack.detected"

    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "config.changed"

    # 场景自动化事件
    SCENARIO_STARTED = "scenario.started"
    SCENARIO_COMPLETED = "scenario.completed"
    STEP_COMPLETED = "step.completed"
