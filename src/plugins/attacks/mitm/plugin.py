"""中间人攻击插件。

拦截和篡改通信双方的数据流，模拟中间人攻击场景。

Example:
    >>> plugin = MITMPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.start({"proxy_port": 8888, "target_host": "10.0.0.1"})
    >>> await plugin.stop()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("mitm")
class MITMPlugin(Plugin):
    """中间人攻击插件。

    通过代理方式拦截通信双方的数据流，支持数据篡改和记录。
    用于演示中间人攻击原理和防御方法。

    Attributes:
        _context: 插件上下文。
        _running: 是否正在运行。
        _proxy_port: 代理监听端口。
        _target_host: 目标主机地址。
        _intercepted_packets: 已拦截的报文计数。
    """

    def __init__(self) -> None:
        """初始化中间人攻击插件。"""
        self._context: PluginContext | None = None
        self._running: bool = False
        self._proxy_port: int = 0
        self._target_host: str = ""
        self._intercepted_packets: int = 0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="mitm",
            version="1.0.0",
            author="VPN Simulator",
            description="中间人攻击插件，拦截和篡改通信双方的数据流",
            plugin_type=PluginType.ATTACK,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "proxy_port": {
                        "type": "integer",
                        "minimum": 1024,
                        "maximum": 65535,
                        "default": 8888,
                        "description": "代理监听端口",
                    },
                    "target_host": {
                        "type": "string",
                        "default": "10.0.0.1",
                        "description": "目标主机地址",
                    },
                    "target_port": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                        "default": 443,
                        "description": "目标端口",
                    },
                    "enable tampering": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否启用数据篡改",
                    },
                },
                "required": ["proxy_port", "target_host"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("中间人攻击插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._running:
            await self.stop()
        if self._context:
            self._context.logger.info("中间人攻击插件已关闭")
        self._context = None

    async def start(self, params: dict[str, Any] | None = None) -> None:
        """启动中间人攻击。

        Args:
            params: 攻击参数，包含 proxy_port、target_host 等。
        """
        params = params or {}
        self._proxy_port = params.get("proxy_port", 8888)
        self._target_host = params.get("target_host", "10.0.0.1")
        self._intercepted_packets = 0
        self._running = True

        if self._context:
            self._context.logger.info(
                f"中间人攻击已启动: proxy=:{self._proxy_port}, "
                f"target={self._target_host}"
            )
            self._context.emit_event("attack.started", {
                "attack_type": "mitm",
                "proxy_port": self._proxy_port,
                "target_host": self._target_host,
            })

    async def stop(self) -> None:
        """停止中间人攻击。"""
        self._running = False

        if self._context:
            self._context.logger.info(
                f"中间人攻击已停止，共拦截 {self._intercepted_packets} 个报文"
            )
            self._context.emit_event("attack.completed", {
                "attack_type": "mitm",
                "intercepted_packets": self._intercepted_packets,
            })

    @property
    def is_running(self) -> bool:
        """攻击是否正在运行。"""
        return self._running

    @property
    def proxy_port(self) -> int:
        """代理监听端口。"""
        return self._proxy_port

    @property
    def target_host(self) -> str:
        """目标主机地址。"""
        return self._target_host

    @property
    def intercepted_packets(self) -> int:
        """已拦截的报文数量。"""
        return self._intercepted_packets
