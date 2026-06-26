"""乱序注入插件。

打乱网络报文的传输顺序，模拟网络乱序场景。

Example:
    >>> plugin = ReorderPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"reorder_probability": 0.3, "max_reorder_gap": 5})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("reorder")
class ReorderPlugin(Plugin):
    """乱序注入插件。

    按照配置的概率打乱网络报文顺序，用于模拟网络乱序场景。
    支持配置重排概率和最大重排间隔。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _reorder_probability: 重排概率 (0.0-1.0)。
        _max_reorder_gap: 最大重排间隔（报文数）。
    """

    def __init__(self) -> None:
        """初始化乱序插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._reorder_probability: float = 0.0
        self._max_reorder_gap: int = 5

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="reorder",
            version="1.0.0",
            author="VPN Simulator",
            description="乱序注入插件，打乱网络报文的传输顺序",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "reorder_probability": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.2,
                        "description": "重排概率 (0.0-1.0)",
                    },
                    "max_reorder_gap": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 5,
                        "description": "最大重排间隔（报文数）",
                    },
                },
                "required": ["reorder_probability"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("乱序注入插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("乱序注入插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入乱序故障。

        Args:
            params: 故障参数，包含 reorder_probability 和 max_reorder_gap。
        """
        params = params or {}
        self._reorder_probability = params.get("reorder_probability", 0.2)
        self._max_reorder_gap = params.get("max_reorder_gap", 5)
        self._active = True

        if self._context:
            self._context.logger.info(
                f"乱序故障已注入: probability={self._reorder_probability}, "
                f"max_gap={self._max_reorder_gap}"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "reorder",
                "reorder_probability": self._reorder_probability,
                "max_reorder_gap": self._max_reorder_gap,
            })

    async def remove(self) -> None:
        """移除乱序故障。"""
        self._active = False
        self._reorder_probability = 0.0
        self._max_reorder_gap = 5

        if self._context:
            self._context.logger.info("乱序故障已移除")
            self._context.emit_event("fault.removed", {"fault_type": "reorder"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def reorder_probability(self) -> float:
        """当前重排概率。"""
        return self._reorder_probability

    @property
    def max_reorder_gap(self) -> int:
        """最大重排间隔。"""
        return self._max_reorder_gap
