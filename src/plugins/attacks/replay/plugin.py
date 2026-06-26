"""重放攻击插件。

捕获合法网络报文并重新发送，模拟重放攻击场景。

Example:
    >>> plugin = ReplayPlugin()
    >>> await plugin.initialize(context)
    >>> await plugin.start({"capture_count": 100, "replay_delay_ms": 500})
    >>> await plugin.stop()
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin


@plugin("replay")
class ReplayPlugin(Plugin):
    """重放攻击插件。

    捕获合法的网络报文并按照配置重新发送，用于演示重放攻击原理。
    支持配置捕获数量、重放延迟和重放次数。

    Attributes:
        _context: 插件上下文。
        _running: 是否正在运行。
        _capture_count: 捕获报文数量。
        _replay_delay_ms: 重放延迟毫秒数。
        _replay_count: 重放次数。
        _captured_packets: 已捕获的报文数。
        _replayed_packets: 已重放的报文数。
    """

    def __init__(self) -> None:
        """初始化重放攻击插件。"""
        self._context: PluginContext | None = None
        self._running: bool = False
        self._capture_count: int = 0
        self._replay_delay_ms: int = 0
        self._replay_count: int = 1
        self._captured_packets: int = 0
        self._replayed_packets: int = 0

    def meta(self) -> PluginMeta:
        """返回插件元数据。

        Returns:
            PluginMeta 包含插件名称、版本、描述等信息。
        """
        return PluginMeta(
            name="replay",
            version="1.0.0",
            author="VPN Simulator",
            description="重放攻击插件，捕获并重放合法网络报文",
            plugin_type=PluginType.ATTACK,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "capture_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10000,
                        "default": 100,
                        "description": "捕获报文数量",
                    },
                    "replay_delay_ms": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 60000,
                        "default": 0,
                        "description": "重放延迟毫秒数",
                    },
                    "replay_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 1,
                        "description": "重放次数",
                    },
                },
                "required": ["capture_count"],
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化插件。

        Args:
            context: 插件上下文，提供事件总线、配置等服务。
        """
        self._context = context
        self._context.logger.info("重放攻击插件已初始化")

    async def shutdown(self) -> None:
        """关闭插件，清理资源。"""
        if self._running:
            await self.stop()
        if self._context:
            self._context.logger.info("重放攻击插件已关闭")
        self._context = None

    async def start(self, params: dict[str, Any] | None = None) -> None:
        """启动重放攻击。

        Args:
            params: 攻击参数，包含 capture_count、replay_delay_ms 等。
        """
        params = params or {}
        self._capture_count = params.get("capture_count", 100)
        self._replay_delay_ms = params.get("replay_delay_ms", 0)
        self._replay_count = params.get("replay_count", 1)
        self._captured_packets = 0
        self._replayed_packets = 0
        self._running = True

        if self._context:
            self._context.logger.info(
                f"重放攻击已启动: capture={self._capture_count}, "
                f"delay={self._replay_delay_ms}ms, replay={self._replay_count}次"
            )
            self._context.emit_event("attack.started", {
                "attack_type": "replay",
                "capture_count": self._capture_count,
                "replay_delay_ms": self._replay_delay_ms,
                "replay_count": self._replay_count,
            })

    async def stop(self) -> None:
        """停止重放攻击。"""
        self._running = False

        if self._context:
            self._context.logger.info(
                f"重放攻击已停止: captured={self._captured_packets}, "
                f"replayed={self._replayed_packets}"
            )
            self._context.emit_event("attack.completed", {
                "attack_type": "replay",
                "captured_packets": self._captured_packets,
                "replayed_packets": self._replayed_packets,
            })

    @property
    def is_running(self) -> bool:
        """攻击是否正在运行。"""
        return self._running

    @property
    def capture_count(self) -> int:
        """捕获报文数量。"""
        return self._capture_count

    @property
    def replay_delay_ms(self) -> int:
        """重放延迟毫秒数。"""
        return self._replay_delay_ms

    @property
    def replay_count(self) -> int:
        """重放次数。"""
        return self._replay_count

    @property
    def captured_packets(self) -> int:
        """已捕获的报文数。"""
        return self._captured_packets

    @property
    def replayed_packets(self) -> int:
        """已重放的报文数。"""
        return self._replayed_packets
