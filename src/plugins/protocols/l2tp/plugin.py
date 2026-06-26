"""L2TP 协议插件入口。

提供 L2TP (Layer 2 Tunneling Protocol) 协议的插件实现，
包含插件注册、生命周期管理和状态机初始化。

RFC 2661: Layer Two Tunneling Protocol "L2TP"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.l2tp.state_machine import L2TPStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("l2tp")
class L2TPPlugin(Plugin):
    """L2TP 协议插件。

    提供 L2TP VPN 协议的服务端模拟功能。L2TP 使用 UDP 1701 进行
    控制通道和数据通道通信，通常与 IPSec 结合使用。

    插件生命周期:
    1. 注册: @plugin("l2tp") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 L2TP 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: L2TP 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 L2TP 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: L2TPStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 L2TP 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="l2tp",
            version="1.0.0",
            author="VPN Simulator",
            description="L2TP (Layer 2 Tunneling Protocol) 协议实现 - "
                        "使用 UDP 1701 控制/数据通道 + PPP 封装",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 1701,
                        "description": "L2TP 控制端口",
                    },
                    "secret": {
                        "type": "string",
                        "default": "",
                        "description": "L2TP 共享密钥",
                    },
                    "max_sessions": {
                        "type": "integer",
                        "default": 100,
                        "description": "最大会话数",
                    },
                    "ipsec_enabled": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否启用 IPSec 保护",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 L2TP 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("l2tp")
        self._state_machine = L2TPStateMachine()

        self._logger.info("L2TP plugin initialized")

    async def shutdown(self) -> None:
        """关闭 L2TP 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("L2TP plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> L2TPStateMachine | None:
        """获取 L2TP 状态机实例。"""
        return self._state_machine
