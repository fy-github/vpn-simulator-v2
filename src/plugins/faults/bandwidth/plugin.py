"""带宽限制插件。

限制网络链路的传输带宽，模拟低带宽网络环境。

Example:
    >>> plugin = BandwidthPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"bandwidth_kbps": 512})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("bandwidth")
class BandwidthPlugin(Plugin):
    """带宽限制插件。

    限制网络链路的传输带宽，用于模拟低带宽、网络拥塞等场景。
    支持配置上行和下行带宽限制。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _bandwidth_kbps: 带宽限制 (Kbps)。
        _direction: 限制方向 (both/upload/download)。
    """

    def __init__(self) -> None:
        """初始化带宽限制插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._bandwidth_kbps: int = 0
        self._direction: str = "both"

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="bandwidth",
            version="1.0.0",
            author="VPN Simulator",
            description="带宽限制插件，限制网络链路的传输带宽",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "bandwidth_kbps": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000000,
                        "default": 1024,
                        "description": "带宽限制 (Kbps)",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["both", "upload", "download"],
                        "default": "both",
                        "description": "限制方向",
                    },
                },
                "required": ["bandwidth_kbps"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("带宽限制插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("带宽限制插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入带宽限制故障。

        Args:
            params: 故障参数，包含 bandwidth_kbps 和 direction。
        """
        params = params or {}
        self._bandwidth_kbps = params.get("bandwidth_kbps", 1024)
        self._direction = params.get("direction", "both")
        self._active = True

        if self._context:
            self._context.logger.info(
                f"带宽限制已注入: {self._bandwidth_kbps}Kbps, direction={self._direction}"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "bandwidth",
                "bandwidth_kbps": self._bandwidth_kbps,
                "direction": self._direction,
            })

    async def remove(self) -> None:
        """移除带宽限制故障。"""
        self._active = False
        self._bandwidth_kbps = 0
        self._direction = "both"

        if self._context:
            self._context.logger.info("带宽限制已移除")
            self._context.emit_event("fault.removed", {"fault_type": "bandwidth"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def bandwidth_kbps(self) -> int:
        """当前带宽限制 (Kbps)。"""
        return self._bandwidth_kbps

    @property
    def direction(self) -> str:
        """限制方向。"""
        return self._direction
