"""OpenVPN 协议插件入口。

提供 OpenVPN 协议的插件实现，包含插件注册、生命周期管理和状态机初始化。

OpenVPN 使用 TLS over UDP (或 TCP) 进行控制通道协商，
默认端口 1194。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.openvpn.state_machine import OpenVPNStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("openvpn")
class OpenVPNPlugin(Plugin):
    """OpenVPN 协议插件。

    提供 OpenVPN 协议的服务端模拟功能。OpenVPN 使用 TLS over UDP
    (或 TCP) 进行控制通道协商，支持多种加密算法和认证方式。

    插件生命周期:
    1. 注册: @plugin("openvpn") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 OpenVPN 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: OpenVPN 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 OpenVPN 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: OpenVPNStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 OpenVPN 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="openvpn",
            version="1.0.0",
            author="VPN Simulator",
            description="OpenVPN 协议实现 - "
                        "TLS over UDP/TCP 控制通道 + PUSH_REPLY 下发配置",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 1194,
                        "description": "OpenVPN 监听端口",
                    },
                    "protocol": {
                        "type": "string",
                        "default": "udp",
                        "enum": ["udp", "tcp"],
                        "description": "传输协议",
                    },
                    "cipher": {
                        "type": "string",
                        "default": "AES-256-GCM",
                        "description": "加密算法",
                    },
                    "tls_version": {
                        "type": "string",
                        "default": "1.3",
                        "description": "TLS 版本",
                    },
                    "max_clients": {
                        "type": "integer",
                        "default": 100,
                        "description": "最大客户端数",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 OpenVPN 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("openvpn")
        self._state_machine = OpenVPNStateMachine()

        self._logger.info("OpenVPN plugin initialized")

    async def shutdown(self) -> None:
        """关闭 OpenVPN 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("OpenVPN plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> OpenVPNStateMachine | None:
        """获取 OpenVPN 状态机实例。"""
        return self._state_machine
