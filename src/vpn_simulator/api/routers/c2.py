"""C2 attack scenario routes (F8)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/c2")

_c2_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.c2 import C2Service


def get_c2_service() -> C2Service:
    """懒加载单例 C2Service。"""
    global _c2_service
    if _c2_service is None:
        from vpn_simulator.services.c2 import C2Service

        _c2_service = C2Service()
    return _c2_service


@router.get(
    "/scenarios",
    summary="List C2 scenarios",
    description="List simulated C2 attack scenarios (educational/defensive only).",
)
async def list_scenarios() -> list[dict[str, Any]]:
    """List C2 scenarios."""
    return get_c2_service().list_scenarios()


@router.get(
    "/ethics",
    summary="Get ethics declaration",
    description="Get the ethics declaration for C2 simulation.",
)
async def ethics() -> dict[str, Any]:
    """Get ethics declaration."""
    return get_c2_service().ethics()


@router.get(
    "/scenarios/{scenario_id}",
    summary="Get a C2 scenario",
    description="Get a C2 scenario by ID.",
)
async def get_scenario(scenario_id: str) -> dict[str, Any]:
    """Get a scenario."""
    scenario = get_c2_service().get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return scenario


@router.post(
    "/scenarios/{scenario_id}/simulate",
    summary="Simulate a C2 scenario",
    description="Simulate a C2 scenario's behavior and return detection indicators.",
)
async def simulate(scenario_id: str) -> dict[str, Any]:
    """Simulate a C2 scenario."""
    result = get_c2_service().simulate(scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return result.to_dict()


@router.get(
    "/scenarios/{scenario_id}/detection",
    summary="Get detection features",
    description="Get detection features (IOCs) for a C2 scenario.",
)
async def detection(scenario_id: str) -> dict[str, Any]:
    """Get detection features."""
    features = get_c2_service().detection_features(scenario_id)
    if features is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return features
