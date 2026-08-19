"""Tests for RoutingService - OSPF/BGP simulation (F5)."""

from __future__ import annotations

from vpn_simulator.services.routing import RoutingService


def test_list_routers():
    service = RoutingService()
    routers = service.list_routers()
    assert len(routers) == 4
    assert {r["id"] for r in routers} == {"r1", "r2", "r3", "r4"}


def test_list_neighbors():
    service = RoutingService()
    neighbors = service.list_neighbors("r1")
    assert len(neighbors) == 2
    protocols = {n["protocol"] for n in neighbors}
    assert protocols == {"ospf", "bgp"}

    ospf_only = service.list_neighbors("r1", protocol="ospf")
    assert len(ospf_only) == 1
    assert ospf_only[0]["neighbor_id"] == "r2"


def test_advance_neighbor_state():
    service = RoutingService()
    first = service.advance_neighbor("r1", "r2", "ospf")
    assert first is not None
    assert first["state"] == "init"  # down -> init


def test_establish_ospf_neighbor():
    service = RoutingService()
    result = service.establish_neighbor("r1", "r2", "ospf")
    assert result is not None
    assert result["state"] == "full"


def test_establish_bgp_neighbor():
    service = RoutingService()
    result = service.establish_neighbor("r1", "r3", "bgp")
    assert result is not None
    assert result["state"] == "established"


def test_routing_table_learns_routes_after_adjacency():
    service = RoutingService()
    before = {e["prefix"] for e in service.get_routing_table("r1")}
    assert "192.168.1.0/24" in before  # 直连
    assert "192.168.2.0/24" not in before  # r2 的路由尚未学到

    service.establish_neighbor("r1", "r2", "ospf")
    after = service.get_routing_table("r1")
    prefixes = {e["prefix"] for e in after}
    assert "192.168.2.0/24" in prefixes  # 经 OSPF 学到 r2 直连
    learned = next(e for e in after if e["prefix"] == "192.168.2.0/24")
    assert learned["protocol"] == "ospf"
    assert learned["route_type"] == "O"
    assert learned["next_hop"] == "10.0.0.2"


def test_get_neighbor_unknown_returns_none():
    service = RoutingService()
    assert service.get_neighbor("r1", "r4", "ospf") is None
    assert service.advance_neighbor("r1", "r4", "ospf") is None
    assert service.establish_neighbor("r1", "r4", "ospf") is None
