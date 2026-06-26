"""VPN Simulator 核心模块

提供事件系统、配置管理、数据库管理和跨平台适配功能。

Example:
    >>> from vpn_simulator.core import EventBus, ConfigManager, DatabaseManager
    >>> from vpn_simulator.core import get_platform_adapter
"""

from vpn_simulator.core.config import Config, ConfigManager
from vpn_simulator.core.database import (
    AttackRecord,
    Base,
    ConfigHistoryRecord,
    ConnectionRecord,
    DatabaseManager,
    FaultRecord,
    PacketRecord,
    StateTransitionRecord,
    TopologyRecord,
)
from vpn_simulator.core.events import Event, EventBus, EventTypes
from vpn_simulator.core.platform import (
    LinuxAdapter,
    MacOSAdapter,
    PlatformAdapter,
    PlatformInfo,
    WindowsAdapter,
    get_platform_adapter,
)

__all__ = [
    # 事件系统
    "Event",
    "EventBus",
    "EventTypes",
    # 配置管理
    "Config",
    "ConfigManager",
    # 数据库
    "Base",
    "DatabaseManager",
    "ConnectionRecord",
    "PacketRecord",
    "StateTransitionRecord",
    "FaultRecord",
    "AttackRecord",
    "ConfigHistoryRecord",
    "TopologyRecord",
    # 平台适配
    "PlatformAdapter",
    "PlatformInfo",
    "WindowsAdapter",
    "MacOSAdapter",
    "LinuxAdapter",
    "get_platform_adapter",
]
