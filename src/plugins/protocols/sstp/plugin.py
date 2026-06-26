"""SSTP 协议插件入口。

提供 SSTP (Secure Socket Tunneling Protocol) 协议的插件实现，
包含插件注册、生命周期管理和状态机初始化。

SSTP 通过 HTTPS (TCP 443) 传输 PPP 帧，由 Microsoft 开发。
默认端口 443。

Reference:
    [MS-SSTP]: Secure Socket Tunneling Protocol (SSTP)
    https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-sstp
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.sstp.state_machine import SSTPStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("sstp")
class SSTPPlugin(Plugin):
    """SSTP 协议插件。

    提供 SSTP VPN 协议的服务端模拟功能。SSTP 使用 HTTPS (TCP 443)
    传输 PPP 帧，握手流程包括 TLS 握手、SSTP 协商、PPP 三阶段
    协商 (LCP -> 认证 -> IPCP)。

    插件生命周期:
    1. 注册: @plugin("sstp") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 SSTP 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: SSTP 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 SSTP 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: SSTPStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 SSTP 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="sstp",
            version="1.0.0",
            author="VPN Simulator",
            description="SSTP (Secure Socket Tunneling Protocol) 协议实现 - "
            "HTTPS (TCP 443) 传输 PPP 帧，"
            "支持 MS-CHAPv2 认证",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 443,
                        "description": "SSTP 监听端口 (HTTPS)",
                    },
                    "tls_version": {
                        "type": "string",
                        "default": "1.2",
                        "enum": ["1.2", "1.3"],
                        "description": "TLS 版本",
                    },
                    "max_connections": {
                        "type": "integer",
                        "default": 100,
                        "description": "最大并发连接数",
                    },
                    "ppp_mru": {
                        "type": "integer",
                        "default": 1500,
                        "description": "PPP MRU (Maximum Receive Unit)",
                    },
                    "auth_method": {
                        "type": "string",
                        "default": "MS-CHAPv2",
                        "enum": ["MS-CHAPv2", "EAP-TLS"],
                        "description": "PPP 认证方式",
                    },
                    "ip_pool_start": {
                        "type": "string",
                        "default": "192.168.200.10",
                        "description": "客户端 IP 池起始地址",
                    },
                    "ip_pool_end": {
                        "type": "string",
                        "default": "192.168.200.200",
                        "description": "客户端 IP 池结束地址",
                    },
                    "dns_server": {
                        "type": "string",
                        "default": "8.8.8.8",
                        "description": "分配给客户端的 DNS 服务器",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 SSTP 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("sstp")
        self._state_machine = SSTPStateMachine()

        self._logger.info("SSTP plugin initialized")

    async def shutdown(self) -> None:
        """关闭 SSTP 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("SSTP plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> SSTPStateMachine | None:
        """获取 SSTP 状态机实例。"""
        return self._state_machine
