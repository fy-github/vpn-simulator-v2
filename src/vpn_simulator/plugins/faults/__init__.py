"""故障注入插件包。

包含 6 种故障注入插件：
- latency: 延迟注入
- packet_loss: 丢包模拟
- bandwidth: 带宽限制
- reorder: 乱序注入
- duplicate: 重复注入
- corrupt: 数据损坏
"""

from vpn_simulator.plugins.faults.bandwidth.plugin import BandwidthPlugin
from vpn_simulator.plugins.faults.corrupt.plugin import CorruptPlugin
from vpn_simulator.plugins.faults.duplicate.plugin import DuplicatePlugin
from vpn_simulator.plugins.faults.latency.plugin import LatencyPlugin
from vpn_simulator.plugins.faults.packet_loss.plugin import PacketLossPlugin
from vpn_simulator.plugins.faults.reorder.plugin import ReorderPlugin

__all__ = [
    "LatencyPlugin",
    "PacketLossPlugin",
    "BandwidthPlugin",
    "ReorderPlugin",
    "DuplicatePlugin",
    "CorruptPlugin",
]
