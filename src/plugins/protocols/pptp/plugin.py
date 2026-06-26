"""PPTP 协议插件入口。

提供 PPTP (Point-to-Point Tunneling Protocol) 协议的插件实现，
包含插件注册、生命周期管理和状态机初始化。

RFC 2637: Point-to-Point Tunneling Protocol (PPTP)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.pptp.state_machine import PPTPStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("pptp")
class PPTPPlugin(Plugin):
    """PPTP 协议插件。

    提供 PPTP VPN 协议的服务端模拟功能。PPTP 使用 TCP 1723 进行
    控制通道协商，GRE (协议号 47) 封装 PPP 数据帧。

    插件生命周期:
    1. 注册: @plugin("pptp") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 PPTP 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: PPTP 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 PPTP 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: PPTPStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 PPTP 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="pptp",
            version="1.0.0",
            author="VPN Simulator",
            description="PPTP (Point-to-Point Tunneling Protocol) 协议实现 - "
                        "使用 TCP 1723 控制通道 + GRE 隧道封装 PPP",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 1723,
                        "description": "PPTP 控制通道端口",
                    },
                    "gre_protocol": {
                        "type": "integer",
                        "default": 47,
                        "description": "GRE 协议号",
                    },
                    "max_connections": {
                        "type": "integer",
                        "default": 100,
                        "description": "最大并发连接数",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 PPTP 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("pptp")
        self._state_machine = PPTPStateMachine()

        self._logger.info("PPTP plugin initialized")

    async def shutdown(self) -> None:
        """关闭 PPTP 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("PPTP plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> PPTPStateMachine | None:
        """获取 PPTP 状态机实例。"""
        return self._state_machine
