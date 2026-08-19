"""路由协议模拟模型（F5）。

模拟 OSPF 与 BGP 邻居建立的有限状态机，以及每台模拟路由器的路由表。
纯 Python 状态机实现（参考 FRR / BIRD / ExaBGP 的邻居状态语义）。

Example:
    >>> neighbor = RoutingNeighbor(router_id="r1", neighbor_id="r2", protocol=RoutingProtocol.OSPF)
    >>> neighbor.advance()  # down -> init
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RoutingProtocol(str, Enum):
    """路由协议。"""

    OSPF = "ospf"
    BGP = "bgp"


# 各协议的邻居状态序列
_STATE_SEQUENCES: dict[RoutingProtocol, list[str]] = {
    RoutingProtocol.OSPF: ["down", "init", "two_way", "exstart", "exchange", "loading", "full"],
    RoutingProtocol.BGP: ["idle", "connect", "open_sent", "open_confirm", "established"],
}


@dataclass
class RoutingNeighbor:
    """一个路由协议邻居（OSPF/BGP 邻居关系）。

    Attributes:
        id: 邻居关系唯一标识。
        router_id: 本端路由器 ID。
        neighbor_id: 对端路由器 ID。
        protocol: 路由协议。
        state: 当前邻居状态。
        last_transition: 最近一次状态变化时间。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    router_id: str = ""
    neighbor_id: str = ""
    protocol: RoutingProtocol = RoutingProtocol.OSPF
    state: str = "down"
    last_transition: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """确保初始状态合法：非法状态回退到协议的首个状态。"""
        seq = self.states()
        if self.state not in seq:
            self.state = seq[0]

    def states(self) -> list[str]:
        """返回该协议的完整状态序列。"""
        return list(_STATE_SEQUENCES[self.protocol])

    def advance(self) -> bool:
        """推进到下一个状态；已在终态时返回 False。"""
        seq = self.states()
        idx = seq.index(self.state) if self.state in seq else -1
        if idx < 0 or idx + 1 >= len(seq):
            return False
        self.state = seq[idx + 1]
        self.last_transition = datetime.now()
        return True

    def is_established(self) -> bool:
        """是否处于完全邻接/会话建立状态。"""
        return self.state == self.states()[-1]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "router_id": self.router_id,
            "neighbor_id": self.neighbor_id,
            "protocol": self.protocol.value,
            "state": self.state,
            "last_transition": self.last_transition.isoformat(),
        }


@dataclass
class RoutingEntry:
    """一条路由表项。

    Attributes:
        prefix: 目的网段（CIDR）。
        next_hop: 下一跳地址。
        metric: 路由度量值。
        protocol: 来源协议（ospf / bgp / static / connected）。
        route_type: 路由类型（O/B/S/C 等）。
    """

    prefix: str = ""
    next_hop: str = ""
    metric: int = 0
    protocol: str = "connected"
    route_type: str = "C"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "prefix": self.prefix,
            "next_hop": self.next_hop,
            "metric": self.metric,
            "protocol": self.protocol,
            "route_type": self.route_type,
        }
