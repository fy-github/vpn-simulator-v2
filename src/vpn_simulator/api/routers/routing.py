"""Routing protocol simulation routes (F5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, Query

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/routing")

_routing_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.routing import RoutingService


def get_routing_service() -> RoutingService:
    """懒加载单例 RoutingService。"""
    global _routing_service
    if _routing_service is None:
        from vpn_simulator.services.routing import RoutingService

        _routing_service = RoutingService()
    return _routing_service


@router.get(
    "/routers",
    summary="List routers",
    description="List simulated routers (OSPF/BGP topology).",
)
async def list_routers() -> list[dict[str, Any]]:
    """List routers."""
    return get_routing_service().list_routers()


@router.get(
    "/{router_id}/neighbors",
    summary="List neighbors",
    description="List a router's routing-protocol neighbors, optionally filtered by protocol.",
)
async def list_neighbors(
    router_id: str,
    protocol: str | None = Query(None, description="Filter by protocol (ospf/bgp)"),
) -> list[dict[str, Any]]:
    """List neighbors."""
    return get_routing_service().list_neighbors(router_id, protocol)


@router.post(
    "/{router_id}/neighbors/{neighbor_id}/establish",
    summary="Establish adjacency",
    description="Drive an OSPF/BGP neighbor state machine to full/established.",
)
async def establish_neighbor(
    router_id: str,
    neighbor_id: str,
    protocol: str = Query("ospf", description="Protocol (ospf/bgp)"),
) -> dict[str, Any]:
    """Establish a neighbor adjacency."""
    result = get_routing_service().establish_neighbor(router_id, neighbor_id, protocol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Neighbor {neighbor_id} not found")
    return result


@router.get(
    "/{router_id}/routes",
    summary="Get routing table",
    description="Get a router's routing table (connected + learned routes).",
)
async def get_routes(router_id: str) -> list[dict[str, Any]]:
    """Get routing table."""
    return get_routing_service().get_routing_table(router_id)
