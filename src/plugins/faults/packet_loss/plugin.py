"""丢包模拟插件。

随机丢弃网络报文，模拟不可靠的网络连接。

Example:
    >>> plugin = PacketLossPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.inject({"loss_rate": 0.1})
    >>> await plugin.remove()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("packet_loss")
class PacketLossPlugin(Plugin):
    """丢包模拟插件。

    按照配置的概率随机丢弃网络报文，用于模拟丢包场景。
    支持配置丢包率和可选的突发丢包模式。

    Attributes:
        _context: 插件上下文。
        _active: 是否激活。
        _loss_rate: 丢包率 (0.0-1.0)。
        _burst_mode: 是否启用突发丢包模式。
    """

    def __init__(self) -> None:
        """初始化丢包插件。"""
        self._context: PluginContext | None = None
        self._active: bool = False
        self._loss_rate: float = 0.0
        self._burst_mode: bool = False

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="packet_loss",
            version="1.0.0",
            author="VPN Simulator",
            description="丢包模拟插件，随机丢弃网络报文模拟不可靠连接",
            plugin_type=PluginType.FAULT,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "loss_rate": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.05,
                        "description": "丢包率 (0.0-1.0)",
                    },
                    "burst_mode": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否启用突发丢包模式",
                    },
                },
                "required": ["loss_rate"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("丢包模拟插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._active:
            await self.remove()
        if self._context:
            self._context.logger.info("丢包模拟插件已关闭")
        self._context = None

    async def inject(self, params: dict[str, Any] | None = None) -> None:
        """注入丢包故障。

        Args:
            params: 故障参数，包含 loss_rate 和 burst_mode。
        """
        params = params or {}
        self._loss_rate = params.get("loss_rate", 0.05)
        self._burst_mode = params.get("burst_mode", False)
        self._active = True

        if self._context:
            self._context.logger.info(
                f"丢包故障已注入: rate={self._loss_rate}, burst={self._burst_mode}"
            )
            self._context.emit_event("fault.injected", {
                "fault_type": "packet_loss",
                "loss_rate": self._loss_rate,
                "burst_mode": self._burst_mode,
            })

    async def remove(self) -> None:
        """移除丢包故障。"""
        self._active = False
        self._loss_rate = 0.0
        self._burst_mode = False

        if self._context:
            self._context.logger.info("丢包故障已移除")
            self._context.emit_event("fault.removed", {"fault_type": "packet_loss"})

    @property
    def is_active(self) -> bool:
        """故障是否激活。"""
        return self._active

    @property
    def loss_rate(self) -> float:
        """当前丢包率。"""
        return self._loss_rate

    @property
    def burst_mode(self) -> bool:
        """是否启用突发丢包模式。"""
        return self._burst_mode
