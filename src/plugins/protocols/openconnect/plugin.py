"""OpenConnect 协议插件入口。

提供 OpenConnect SSL VPN 协议的插件实现，
包含插件注册、生命周期管理和状态机初始化。

OpenConnect 是一个开源的 SSL VPN 协议，兼容 Cisco AnyConnect。
通过 HTTPS (TCP 443) 建立 TLS 隧道，使用 CSTP 协议传输 PPP 帧。
支持可选的 DTLS (UDP) 数据通道以提升性能。
默认端口 443。

Reference:
    OpenConnect Protocol Documentation
    https://www.infradead.org/openconnect/protocol.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.openconnect.state_machine import OpenConnectStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("openconnect")
class OpenConnectPlugin(Plugin):
    """OpenConnect 协议插件。

    提供 OpenConnect SSL VPN 协议的服务端模拟功能。OpenConnect 使用
    HTTPS (TCP 443) 建立 TLS 隧道，通过 CSTP (Connect Secure Tunnel Protocol)
    传输 PPP 帧。握手流程包括 TLS 握手、CSTP 协商、可选 DTLS 握手、
    PPP 三阶段协商 (LCP -> 认证 -> IPCP)。

    插件生命周期:
    1. 注册: @plugin("openconnect") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 OpenConnect 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: OpenConnect 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 OpenConnect 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: OpenConnectStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 OpenConnect 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="openconnect",
            version="1.0.0",
            author="VPN Simulator",
            description="OpenConnect SSL VPN 协议实现 - "
            "HTTPS (TCP 443) TLS 隧道 + CSTP 传输 PPP 帧，"
            "兼容 Cisco AnyConnect，支持可选 DTLS 数据通道",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 443,
                        "description": "OpenConnect 监听端口 (HTTPS)",
                    },
                    "dtls_port": {
                        "type": "integer",
                        "default": 443,
                        "description": "DTLS 监听端口 (UDP)",
                    },
                    "tls_version": {
                        "type": "string",
                        "default": "1.3",
                        "enum": ["1.2", "1.3"],
                        "description": "TLS 版本",
                    },
                    "dtls_enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "是否启用 DTLS 数据通道",
                    },
                    "max_connections": {
                        "type": "integer",
                        "default": 100,
                        "description": "最大并发连接数",
                    },
                    "ppp_mru": {
                        "type": "integer",
                        "default": 1406,
                        "description": "PPP MRU (Maximum Receive Unit)",
                    },
                    "auth_method": {
                        "type": "string",
                        "default": "MS-CHAPv2",
                        "enum": ["MS-CHAPv2", "EAP-TLS", "Certificate"],
                        "description": "PPP 认证方式",
                    },
                    "ip_pool_start": {
                        "type": "string",
                        "default": "192.168.210.10",
                        "description": "客户端 IP 池起始地址",
                    },
                    "ip_pool_end": {
                        "type": "string",
                        "default": "192.168.210.200",
                        "description": "客户端 IP 池结束地址",
                    },
                    "dns_server": {
                        "type": "string",
                        "default": "8.8.8.8",
                        "description": "分配给客户端的 DNS 服务器",
                    },
                    "cstp_keepalive": {
                        "type": "integer",
                        "default": 30,
                        "description": "CSTP 心跳间隔 (秒)",
                    },
                    "dpd_interval": {
                        "type": "integer",
                        "default": 30,
                        "description": "Dead Peer Detection 间隔 (秒)",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 OpenConnect 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("openconnect")
        self._state_machine = OpenConnectStateMachine()

        self._logger.info("OpenConnect plugin initialized")

    async def shutdown(self) -> None:
        """关闭 OpenConnect 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("OpenConnect plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> OpenConnectStateMachine | None:
        """获取 OpenConnect 状态机实例。"""
        return self._state_machine
