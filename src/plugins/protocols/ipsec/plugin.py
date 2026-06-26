"""IPSec 协议插件入口。

提供 IPSec (IKEv1) 协议的插件实现，包含插件注册、生命周期管理和状态机初始化。

RFC 2409: The Internet Key Exchange (IKE)
RFC 2401: Security Architecture for the Internet Protocol
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.ipsec.state_machine import IPSecStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("ipsec")
class IPSecPlugin(Plugin):
    """IPSec (IKEv1) 协议插件。

    提供 IPSec VPN 协议的服务端模拟功能。IPSec 使用 IKEv1 两阶段
    协商: Phase 1 Main Mode (6 消息) 建立 ISAKMP SA，Phase 2 Quick
    Mode (3 消息) 建立 IPSec SA，最终通过 ESP 隧道传输数据。

    插件生命周期:
    1. 注册: @plugin("ipsec") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 IPSec 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: IPSec 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 IPSec 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: IPSecStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 IPSec 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="ipsec",
            version="1.0.0",
            author="VPN Simulator",
            description="IPSec (IKEv1) 协议实现 - "
                        "Phase1 Main Mode (6步) + Phase2 Quick Mode (3步) + ESP 隧道",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 500,
                        "description": "IKE 协商端口",
                    },
                    "nat_t_port": {
                        "type": "integer",
                        "default": 4500,
                        "description": "NAT-T 端口",
                    },
                    "psk": {
                        "type": "string",
                        "default": "",
                        "description": "Pre-Shared Key",
                    },
                    "auth_method": {
                        "type": "string",
                        "default": "psk",
                        "enum": ["psk", "certificate"],
                        "description": "认证方式",
                    },
                    "phase1_cipher": {
                        "type": "string",
                        "default": "AES-256-CBC",
                        "description": "Phase 1 加密算法",
                    },
                    "phase1_hash": {
                        "type": "string",
                        "default": "SHA256",
                        "description": "Phase 1 哈希算法",
                    },
                    "phase1_dh_group": {
                        "type": "integer",
                        "default": 14,
                        "description": "Phase 1 DH 组",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 IPSec 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("ipsec")
        self._state_machine = IPSecStateMachine()

        self._logger.info("IPSec plugin initialized")

    async def shutdown(self) -> None:
        """关闭 IPSec 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("IPSec plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> IPSecStateMachine | None:
        """获取 IPSec 状态机实例。"""
        return self._state_machine
