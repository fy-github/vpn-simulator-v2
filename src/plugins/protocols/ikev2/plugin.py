"""IKEv2 协议插件入口。

提供 IKEv2 协议的插件实现，包含插件注册、生命周期管理和状态机初始化。

RFC 7296: Internet Key Exchange Protocol Version 2 (IKEv2)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.ikev2.state_machine import IKEv2StateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("ikev2")
class IKEv2Plugin(Plugin):
    """IKEv2 协议插件。

    提供 IKEv2/IPSec VPN 协议的服务端模拟功能。IKEv2 使用两阶段
    交换: IKE_SA_INIT (2 消息) 和 IKE_AUTH (2 消息)，比 IKEv1 更
    简洁高效。建立 Child SA 后通过 ESP 隧道传输数据。

    插件生命周期:
    1. 注册: @plugin("ikev2") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 IKEv2 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: IKEv2 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 IKEv2 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: IKEv2StateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 IKEv2 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="ikev2",
            version="1.0.0",
            author="VPN Simulator",
            description="IKEv2/IPSec 协议实现 - "
                        "IKE_SA_INIT (2步) + IKE_AUTH (2步) + Child SA + ESP 隧道",
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
                    "auth_method": {
                        "type": "string",
                        "default": "psk",
                        "enum": ["psk", "certificate", "eap-mschapv2"],
                        "description": "认证方式",
                    },
                    "psk": {
                        "type": "string",
                        "default": "",
                        "description": "Pre-Shared Key",
                    },
                    "cipher": {
                        "type": "string",
                        "default": "AES-256-GCM",
                        "description": "加密算法",
                    },
                    "prf": {
                        "type": "string",
                        "default": "HMAC-SHA256",
                        "description": "PRF 算法",
                    },
                    "dh_group": {
                        "type": "integer",
                        "default": 14,
                        "description": "DH 组",
                    },
                    "ip_pool_start": {
                        "type": "string",
                        "default": "10.0.0.100",
                        "description": "客户端 IP 池起始地址",
                    },
                    "ip_pool_end": {
                        "type": "string",
                        "default": "10.0.0.200",
                        "description": "客户端 IP 池结束地址",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 IKEv2 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("ikev2")
        self._state_machine = IKEv2StateMachine()

        self._logger.info("IKEv2 plugin initialized")

    async def shutdown(self) -> None:
        """关闭 IKEv2 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("IKEv2 plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> IKEv2StateMachine | None:
        """获取 IKEv2 状态机实例。"""
        return self._state_machine
