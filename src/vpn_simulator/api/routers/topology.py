import logging

"""Topology management routes for VPN Simulator v2."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topology")


class TopologyNode(BaseModel):
    """Topology node."""

    id: str = Field(..., description="Node ID")
    type: str = Field(..., description="Node type (server/client/router)")
    label: str = Field("", description="Display label")
    address: str = Field("", description="Network address")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class TopologyEdge(BaseModel):
    """Topology edge."""

    id: str = Field(..., description="Edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str = Field("", description="Display label")
    properties: dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class Topology(BaseModel):
    """Network topology."""

    nodes: list[TopologyNode] = Field(default_factory=list, description="Topology nodes")
    edges: list[TopologyEdge] = Field(default_factory=list, description="Topology edges")


@router.get(
    "/topology",
    response_model=Topology,
    summary="Get topology",
    description="Retrieve the current network topology.",
)
async def get_topology() -> dict[str, list[Any]]:
    """Get the current topology."""
    return {"nodes": [], "edges": []}


@router.put(
    "/topology",
    response_model=Topology,
    summary="Update topology",
    description="Update the network topology configuration.",
)
async def update_topology(topology: Topology) -> dict[str, list[Any]]:
    """Update the topology."""
    return {"nodes": [n.model_dump() for n in topology.nodes], "edges": [e.model_dump() for e in topology.edges]}
