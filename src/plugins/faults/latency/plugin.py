"""延迟注入插件。

在网络链路中引入可配置的延迟和抖动，用于模拟高延迟网络环境。

Example:
    >>> plugin = LatencyPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"delay_ms": 100, "jitter_ms": 20})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("latency")
class LatencyPlugin(Plugin):
    """延迟注入插件。

    在网络报文中引入额外延迟，支持配置固定延迟和随机抖动。
    用于模拟高延迟、网络拥塞等场景。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _delay_ms: 延迟毫秒数。
        _jitter_ms: 抖动毫秒数。
    """

    def __init__(self) -> None:
        """初始化延迟插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._delay_ms: int = 0
        self._jitter_ms: int = 0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="latency",
            version="1.0.0",
            author="VPN Simulator",
            description="延迟注入插件，在网络链路中引入可配置的延迟和抖动",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "delay_ms": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 60000,
                        "default": 100,
                        "description": "延迟毫秒数",
                    },
                    "jitter_ms": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10000,
                        "default": 0,
                        "description": "抖动毫秒数（随机偏移范围）",
                    },
                },
                "required": ["delay_ms"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("延迟注入插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("延迟注入插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入延迟故障。

        Args:
            params: 故障参数，包含 delay_ms 和 jitter_ms。
        """
        params = params or {}
        self._delay_ms = params.get("delay_ms", 100)
        self._jitter_ms = params.get("jitter_ms", 0)
        self._active = True

        if self._context:
            self._context.logger.info(
                f"延迟故障已注入: delay={self._delay_ms}ms, jitter={self._jitter_ms}ms"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "latency",
                "delay_ms": self._delay_ms,
                "jitter_ms": self._jitter_ms,
            })

    async def remove(self) -> None:
        """移除延迟故障。"""
        self._active = False
        self._delay_ms = 0
        self._jitter_ms = 0

        if self._context:
            self._context.logger.info("延迟故障已移除")
            self._context.emit_event("fault.removed", {"fault_type": "latency"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def delay_ms(self) -> int:
        """当前延迟毫秒数。"""
        return self._delay_ms

    @property
    def jitter_ms(self) -> int:
        """当前抖动毫秒数。"""
        return self._jitter_ms
