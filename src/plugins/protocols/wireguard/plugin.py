"""WireGuard 协议插件入口。

提供 WireGuard 协议的插件实现，包含插件注册、生命周期管理和状态机初始化。

WireGuard 使用 Noise_IKpsk2 协议进行密钥交换，
默认端口 51820/UDP。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.wireguard.state_machine import WireGuardStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("wireguard")
class WireGuardPlugin(Plugin):
    """WireGuard 协议插件。

    提供 WireGuard VPN 协议的服务端模拟功能。WireGuard 使用
    Noise_IKpsk2 协议进行密钥交换，握手仅需 2 个消息
    (Initiation 52B + Response 92B)，之后通过 ChaCha20-Poly1305
    加密数据通道传输。

    插件生命周期:
    1. 注册: @plugin("wireguard") 装饰器自动注册
    2. 初始化: initialize() 创建状态机和资源
    3. 运行: 通过状态机管理 WireGuard 握手流程
    4. 关闭: shutdown() 释放资源

    Attributes:
        _context: 插件上下文，提供事件总线、配置等服务。
        _state_machine: WireGuard 协议状态机实例。
        _logger: 插件专用日志记录器。
    """

    def __init__(self) -> None:
        """初始化 WireGuard 插件实例。"""
        self._context: PluginContext | None = None
        self._state_machine: WireGuardStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        """返回 WireGuard 插件元数据。

        Returns:
            包含插件名称、版本、描述等信息的 PluginMeta。
        """
        return PluginMeta(
            name="wireguard",
            version="1.0.0",
            author="VPN Simulator",
            description="WireGuard 协议实现 - "
                        "Noise_IKpsk2 握手 (Initiation 52B + Response 92B) + "
                        "ChaCha20-Poly1305 数据通道",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "default": 51820,
                        "description": "WireGuard 监听端口",
                    },
                    "private_key": {
                        "type": "string",
                        "default": "",
                        "description": "服务端私钥 (Base64)",
                    },
                    "public_key": {
                        "type": "string",
                        "default": "",
                        "description": "服务端公钥 (Base64)",
                    },
                    "tunnel_ip": {
                        "type": "string",
                        "default": "10.0.0.1/24",
                        "description": "隧道 IP 地址",
                    },
                    "dns": {
                        "type": "string",
                        "default": "1.1.1.1",
                        "description": "DNS 服务器",
                    },
                    "max_peers": {
                        "type": "integer",
                        "default": 256,
                        "description": "最大对等端数",
                    },
                },
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化 WireGuard 插件。

        创建状态机实例，获取日志记录器，订阅相关事件。

        Args:
            context: 插件上下文，提供事件总线、配置、日志等服务。
        """
        self._context = context
        self._logger = context.create_child_logger("wireguard")
        self._state_machine = WireGuardStateMachine()

        self._logger.info("WireGuard plugin initialized")

    async def shutdown(self) -> None:
        """关闭 WireGuard 插件，释放所有资源。"""
        self._state_machine = None
        if self._logger:
            self._logger.info("WireGuard plugin shutdown")
        self._context = None

    @property
    def state_machine(self) -> WireGuardStateMachine | None:
        """获取 WireGuard 状态机实例。"""
        return self._state_machine
