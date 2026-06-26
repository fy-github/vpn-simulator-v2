from __future__ import annotations

from typing import TYPE_CHECKING

from vpn_simulator.plugins.registry import Plugin, PluginMeta, PluginType, plugin
from plugins.protocols.vxlan.state_machine import VXLANStateMachine

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext


@plugin("vxlan")
class VXLANPlugin(Plugin):
    """VXLAN 协议插件。

    VXLAN (Virtual Extensible LAN) 是一种网络虚拟化技术，
    使用 MAC-in-UDP 封装在三层网络上构建二层隧道。
    默认端口 4789/UDP，VNI (VXLAN Network Identifier) 标识虚拟网络。
    """

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._state_machine: VXLANStateMachine | None = None
        self._logger = None

    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="vxlan",
            version="1.0.0",
            author="VPN Simulator",
            description="VXLAN 协议实现 - MAC-in-UDP 封装 (端口 4789/UDP, VNI 隔离)",
            plugin_type=PluginType.PROTOCOL,
        )

    async def initialize(self, context: PluginContext) -> None:
        self._context = context
        self._state_machine = VXLANStateMachine()
        self._logger = context.create_child_logger("vxlan")
        self._logger.info("VXLAN plugin initialized")

    async def shutdown(self) -> None:
        if self._state_machine:
            self._state_machine = None
        if self._logger:
            self._logger.info("VXLAN plugin shutdown")
