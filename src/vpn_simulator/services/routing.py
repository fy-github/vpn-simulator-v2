"""路由协议模拟服务（F5）。

模拟多台路由器的 OSPF/BGP 邻居建立（有限状态机推进）与路由表查询。
纯 Python 状态机实现，不发送真实路由协议报文（真实报文层可后续接入）。

Example:
    >>> service = RoutingService()
    >>> service.establish_neighbor("r1", "r2", "ospf")
    >>> service.get_routing_table("r1")
"""

from __future__ import annotations

from typing import Any

import structlog

from vpn_simulator.domain.routing import RoutingEntry, RoutingNeighbor, RoutingProtocol

logger = structlog.get_logger(__name__)

# 模拟路由器拓扑：每台路由器的直连网段（connected）
_ROUTERS: list[dict[str, Any]] = [
    {"id": "r1", "name": "core-router-1", "router_id": "10.0.0.1", "asn": 65001, "area": "0.0.0.0"},
    {"id": "r2", "name": "core-router-2", "router_id": "10.0.0.2", "asn": 65001, "area": "0.0.0.0"},
    {"id": "r3", "name": "edge-router-1", "router_id": "10.0.0.3", "asn": 65002, "area": "0.0.0.1"},
    {"id": "r4", "name": "edge-router-2", "router_id": "10.0.0.4", "asn": 65002, "area": "0.0.0.1"},
]

_CONNECTED: dict[str, list[RoutingEntry]] = {
    "r1": [
        RoutingEntry("10.0.0.0/30", "0.0.0.0", 0, "connected", "C"),
        RoutingEntry("192.168.1.0/24", "0.0.0.0", 0, "connected", "C"),
    ],
    "r2": [
        RoutingEntry("10.0.0.4/30", "0.0.0.0", 0, "connected", "C"),
        RoutingEntry("192.168.2.0/24", "0.0.0.0", 0, "connected", "C"),
    ],
    "r3": [
        RoutingEntry("172.16.1.0/24", "0.0.0.0", 0, "connected", "C"),
        RoutingEntry("192.168.3.0/24", "0.0.0.0", 0, "connected", "C"),
    ],
    "r4": [
        RoutingEntry("172.16.2.0/24", "0.0.0.0", 0, "connected", "C"),
        RoutingEntry("192.168.4.0/24", "0.0.0.0", 0, "connected", "C"),
    ],
}

# 邻居关系（本端, 对端, 协议）
_NEIGHBOR_LINKS: list[tuple[str, str, str]] = [
    ("r1", "r2", "ospf"),
    ("r2", "r3", "ospf"),
    ("r1", "r3", "bgp"),
    ("r3", "r4", "bgp"),
]


class RoutingService:
    """路由协议模拟服务。"""

    def __init__(self) -> None:
        self._routers = {r["id"]: dict(r) for r in _ROUTERS}
        self._neighbors: dict[tuple[str, str, str], RoutingNeighbor] = {}
        for local, remote, proto in _NEIGHBOR_LINKS:
            protocol = RoutingProtocol(proto)
            key = (local, remote, proto)
            self._neighbors[key] = RoutingNeighbor(
                router_id=local, neighbor_id=remote, protocol=protocol
            )

    # ------------------------------------------------------------------
    # 路由器
    # ------------------------------------------------------------------
    def list_routers(self) -> list[dict[str, Any]]:
        """列出模拟路由器。"""
        return list(self._routers.values())

    # ------------------------------------------------------------------
    # 邻居
    # ------------------------------------------------------------------
    def list_neighbors(self, router_id: str, protocol: str | None = None) -> list[dict[str, Any]]:
        """列出指定路由器的邻居（可按协议过滤）。"""
        result = []
        for (local, _remote, proto), n in self._neighbors.items():
            if local != router_id:
                continue
            if protocol and proto != protocol:
                continue
            result.append(n.to_dict())
        return result

    def get_neighbor(
        self, router_id: str, neighbor_id: str, protocol: str
    ) -> RoutingNeighbor | None:
        """获取指定邻居关系。"""
        return self._neighbors.get((router_id, neighbor_id, protocol))

    def advance_neighbor(
        self, router_id: str, neighbor_id: str, protocol: str
    ) -> dict[str, Any] | None:
        """推进邻居状态机一步。"""
        neighbor = self.get_neighbor(router_id, neighbor_id, protocol)
        if neighbor is None:
            return None
        neighbor.advance()
        return neighbor.to_dict()

    def establish_neighbor(
        self, router_id: str, neighbor_id: str, protocol: str
    ) -> dict[str, Any] | None:
        """将邻居状态机推进到完全邻接/会话建立状态。"""
        neighbor = self.get_neighbor(router_id, neighbor_id, protocol)
        if neighbor is None:
            return None
        for _ in range(len(neighbor.states())):
            if neighbor.is_established():
                break
            neighbor.advance()
        logger.info(
            "neighbor_established",
            router=router_id,
            neighbor=neighbor_id,
            protocol=protocol,
            state=neighbor.state,
        )
        return neighbor.to_dict()

    # ------------------------------------------------------------------
    # 路由表
    # ------------------------------------------------------------------
    def get_routing_table(self, router_id: str) -> list[dict[str, Any]]:
        """返回指定路由器的路由表（直连 + 已建立邻居学到的路由）。"""
        entries: list[RoutingEntry] = list(_CONNECTED.get(router_id, []))

        for (local, remote, proto), neighbor in self._neighbors.items():
            if local != router_id or not neighbor.is_established():
                continue
            for learned in _CONNECTED.get(remote, []):
                protocol_name = neighbor.protocol.value
                entries.append(
                    RoutingEntry(
                        prefix=learned.prefix,
                        next_hop=self._routers[remote]["router_id"],
                        metric=10 if protocol_name == "ospf" else 100,
                        protocol=protocol_name,
                        route_type="O" if protocol_name == "ospf" else "B",
                    )
                )

        # 去重（相同前缀保留 metric 更小者）
        deduped: dict[str, RoutingEntry] = {}
        for e in entries:
            existing = deduped.get(e.prefix)
            if existing is None or e.metric < existing.metric:
                deduped[e.prefix] = e
        return [e.to_dict() for e in deduped.values()]
