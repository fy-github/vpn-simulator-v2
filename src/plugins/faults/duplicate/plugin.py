"""重复注入插件。

复制网络报文并多次发送，模拟报文重复场景。

Example:
    >>> plugin = DuplicatePlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"duplicate_count": 2, "duplicate_probability": 0.5})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("duplicate")
class DuplicatePlugin(Plugin):
    """重复注入插件。

    按照配置的概率和次数复制网络报文，用于模拟报文重复场景。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _duplicate_count: 重复次数。
        _duplicate_probability: 重复概率 (0.0-1.0)。
    """

    def __init__(self) -> None:
        """初始化重复插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._duplicate_count: int = 0
        self._duplicate_probability: float = 0.0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="duplicate",
            version="1.0.0",
            author="VPN Simulator",
            description="重复注入插件，复制网络报文并多次发送",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "duplicate_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                        "description": "重复次数",
                    },
                    "duplicate_probability": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.3,
                        "description": "重复概率 (0.0-1.0)",
                    },
                },
                "required": ["duplicate_count"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("重复注入插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("重复注入插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入重复故障。

        Args:
            params: 故障参数，包含 duplicate_count 和 duplicate_probability。
        """
        params = params or {}
        self._duplicate_count = params.get("duplicate_count", 1)
        self._duplicate_probability = params.get("duplicate_probability", 0.3)
        self._active = True

        if self._context:
            self._context.logger.info(
                f"重复故障已注入: count={self._duplicate_count}, "
                f"probability={self._duplicate_probability}"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "duplicate",
                "duplicate_count": self._duplicate_count,
                "duplicate_probability": self._duplicate_probability,
            })

    async def remove(self) -> None:
        """移除重复故障。"""
        self._active = False
        self._duplicate_count = 0
        self._duplicate_probability = 0.0

        if self._context:
            self._context.logger.info("重复故障已移除")
            self._context.emit_event("fault.removed", {"fault_type": "duplicate"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def duplicate_count(self) -> int:
        """当前重复次数。"""
        return self._duplicate_count

    @property
    def duplicate_probability(self) -> float:
        """当前重复概率。"""
        return self._duplicate_probability
