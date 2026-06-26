"""协议降级攻击插件。

强制通信双方使用较弱的加密协议，模拟协议降级攻击。

Example:
    >>> plugin = DowngradePlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.start({"target_protocol": "pptp", "force_version": "v1"})
    >>> await plugin.stop()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("downgrade")
class DowngradePlugin(Plugin):
    """协议降级攻击插件。

    通过篡改协议协商过程，强制通信双方使用较弱的加密协议版本。
    用于演示协议降级攻击原理和防御方法。

    Attributes:
        _context: 插件上下文。
        _running: 是否正在运行。
        _target_protocol: 目标协议。
        _force_version: 强制使用的协议版本。
        _intercepted_handshakes: 已拦截的握手次数。
    """

    def __init__(self) -> None:
        """初始化协议降级攻击插件。"""
        self._context: PluginContext | None = None
        self._running: bool = False
        self._target_protocol: str = ""
        self._force_version: str = ""
        self._intercepted_handshakes: int = 0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="downgrade",
            version="1.0.0",
            author="VPN Simulator",
            description="协议降级攻击插件，强制使用较弱的加密协议",
            plugin_type=PluginType.ATTACK,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "target_protocol": {
                        "type": "string",
                        "enum": ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"],
                        "default": "pptp",
                        "description": "目标协议",
                    },
                    "force_version": {
                        "type": "string",
                        "default": "v1",
                        "description": "强制使用的协议版本",
                    },
                    "target_host": {
                        "type": "string",
                        "default": "",
                        "description": "目标主机地址（为空则拦截所有）",
                    },
                },
                "required": ["target_protocol"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("协议降级攻击插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._running:
            await self.stop()
        if self._context:
            self._context.logger.info("协议降级攻击插件已关闭")
        self._context = None

    async def start(self, params: dict[str, Any] | None = None) -> None:
        """启动协议降级攻击。

        Args:
            params: 攻击参数，包含 target_protocol 和 force_version。
        """
        params = params or {}
        self._target_protocol = params.get("target_protocol", "pptp")
        self._force_version = params.get("force_version", "v1")
        self._intercepted_handshakes = 0
        self._running = True

        if self._context:
            self._context.logger.info(
                f"协议降级攻击已启动: target={self._target_protocol}, "
                f"force_version={self._force_version}"
            )
            self._context.emit_event("attack.started", {
                "attack_type": "downgrade",
                "target_protocol": self._target_protocol,
                "force_version": self._force_version,
            })

    async def stop(self) -> None:
        """停止协议降级攻击。"""
        self._running = False

        if self._context:
            self._context.logger.info(
                f"协议降级攻击已停止，共拦截 {self._intercepted_handshakes} 次握手"
            )
            self._context.emit_event("attack.completed", {
                "attack_type": "downgrade",
                "intercepted_handshakes": self._intercepted_handshakes,
            })

    @property
    def is_running(self) -> bool:
        """攻击是否正在运行。"""
        return self._running

    @property
    def target_protocol(self) -> str:
        """目标协议。"""
        return self._target_protocol

    @property
    def force_version(self) -> str:
        """强制使用的协议版本。"""
        return self._force_version

    @property
    def intercepted_handshakes(self) -> int:
        """已拦截的握手次数。"""
        return self._intercepted_handshakes
