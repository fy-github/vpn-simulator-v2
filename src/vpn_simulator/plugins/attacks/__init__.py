"""攻击模拟插件包。

包含 5 种攻击模拟插件：
- mitm: 中间人攻击
- replay: 重放攻击
- brute_force: 暴力破解
- downgrade: 协议降级
- traffic_analysis: 流量分析
"""

from vpn_simulator.plugins.attacks.brute_force.plugin import BruteForcePlugin
from vpn_simulator.plugins.attacks.downgrade.plugin import DowngradePlugin
from vpn_simulator.plugins.attacks.mitm.plugin import MITMPlugin
from vpn_simulator.plugins.attacks.replay.plugin import ReplayPlugin
from vpn_simulator.plugins.attacks.traffic_analysis.plugin import TrafficAnalysisPlugin

__all__ = [
    "MITMPlugin",
    "ReplayPlugin",
    "BruteForcePlugin",
    "DowngradePlugin",
    "TrafficAnalysisPlugin",
]
