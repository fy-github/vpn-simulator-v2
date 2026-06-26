"""数据损坏插件。

修改网络报文内容，模拟数据传输错误。

Example:
    >>> plugin = CorruptPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"corrupt_probability": 0.2, "corrupt_bytes": 4})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("corrupt")
class CorruptPlugin(Plugin):
    """数据损坏插件。

    按照配置的概率修改网络报文内容，用于模拟数据传输错误。
    支持配置损坏概率和每次损坏的字节数。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _corrupt_probability: 损坏概率 (0.0-1.0)。
        _corrupt_bytes: 每次损坏的字节数。
    """

    def __init__(self) -> None:
        """初始化数据损坏插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._corrupt_probability: float = 0.0
        self._corrupt_bytes: int = 0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="corrupt",
            version="1.0.0",
            author="VPN Simulator",
            description="数据损坏插件，修改网络报文内容模拟传输错误",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "corrupt_probability": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.1,
                        "description": "损坏概率 (0.0-1.0)",
                    },
                    "corrupt_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 256,
                        "default": 1,
                        "description": "每次损坏的字节数",
                    },
                },
                "required": ["corrupt_probability"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("数据损坏插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("数据损坏插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入数据损坏故障。

        Args:
            params: 故障参数，包含 corrupt_probability 和 corrupt_bytes。
        """
        params = params or {}
        self._corrupt_probability = params.get("corrupt_probability", 0.1)
        self._corrupt_bytes = params.get("corrupt_bytes", 1)
        self._active = True

        if self._context:
            self._context.logger.info(
                f"数据损坏故障已注入: probability={self._corrupt_probability}, "
                f"bytes={self._corrupt_bytes}"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "corrupt",
                "corrupt_probability": self._corrupt_probability,
                "corrupt_bytes": self._corrupt_bytes,
            })

    async def remove(self) -> None:
        """移除数据损坏故障。"""
        self._active = False
        self._corrupt_probability = 0.0
        self._corrupt_bytes = 0

        if self._context:
            self._context.logger.info("数据损坏故障已移除")
            self._context.emit_event("fault.removed", {"fault_type": "corrupt"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def corrupt_probability(self) -> float:
        """当前损坏概率。"""
        return self._corrupt_probability

    @property
    def corrupt_bytes(self) -> int:
        """每次损坏的字节数。"""
        return self._corrupt_bytes
