import logging

"""Scenario presets routes for VPN Simulator v2."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios")


class ScenarioInfo(BaseModel):
    """Scenario preset information."""

    id: str = Field(..., description="Scenario ID")
    name: str = Field(..., description="Scenario display name")
    description: str = Field("", description="Scenario description")
    icon: str = Field("network_check", description="Scenario icon name")
    category: str = Field("other", description="Scenario category")
    faults: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Fault configurations")
    active: bool = Field(False, description="Whether scenario is currently active")


class ScenarioActionResponse(BaseModel):
    """Response for scenario actions."""

    scenario_id: str = Field(..., description="Scenario ID")
    status: str = Field(..., description="Action result status")
    message: str = Field("", description="Result message")
    fault_ids: list[str] = Field(default_factory=list, description="Associated fault IDs")


# 预设场景数据（从 config/scenarios/presets.yaml 加载）
SCENARIO_PRESETS: dict[str, dict[str, Any]] = {
    "3g": {
        "id": "3g",
        "name": "3G",
        "description": "3G mobile network - moderate latency, limited bandwidth",
        "icon": "signal_cellular_alt",
        "category": "mobile",
        "faults": {
            "latency": {"delay_ms": 200, "jitter_ms": 50},
            "packet_loss": {"loss_rate": 0.02},
            "bandwidth": {"bandwidth_kbps": 2000},
        },
    },
    "4g_lte": {
        "id": "4g_lte",
        "name": "4G LTE",
        "description": "4G LTE mobile network - low latency, good bandwidth",
        "icon": "signal_cellular_4_bar",
        "category": "mobile",
        "faults": {
            "latency": {"delay_ms": 50, "jitter_ms": 20},
            "packet_loss": {"loss_rate": 0.01},
            "bandwidth": {"bandwidth_kbps": 50000},
        },
    },
    "satellite": {
        "id": "satellite",
        "name": "Satellite",
        "description": "Traditional satellite connection - high latency, moderate bandwidth",
        "icon": "satellite_alt",
        "category": "satellite",
        "faults": {
            "latency": {"delay_ms": 600, "jitter_ms": 100},
            "packet_loss": {"loss_rate": 0.05},
            "bandwidth": {"bandwidth_kbps": 10000},
        },
    },
    "starlink": {
        "id": "starlink",
        "name": "Starlink",
        "description": "Starlink LEO satellite - low latency, high bandwidth",
        "icon": "rocket_launch",
        "category": "satellite",
        "faults": {
            "latency": {"delay_ms": 40, "jitter_ms": 15},
            "packet_loss": {"loss_rate": 0.005},
            "bandwidth": {"bandwidth_kbps": 100000},
        },
    },
    "congested_wifi": {
        "id": "congested_wifi",
        "name": "Congested WiFi",
        "description": "Crowded WiFi network - high jitter, significant packet loss",
        "icon": "wifi",
        "category": "wifi",
        "faults": {
            "latency": {"delay_ms": 100, "jitter_ms": 80},
            "packet_loss": {"loss_rate": 0.10},
            "bandwidth": {"bandwidth_kbps": 5000},
        },
    },
    "fiber": {
        "id": "fiber",
        "name": "Fiber",
        "description": "Fiber optic connection - ultra-low latency, massive bandwidth",
        "icon": "lan",
        "category": "wired",
        "faults": {
            "latency": {"delay_ms": 5, "jitter_ms": 2},
            "packet_loss": {"loss_rate": 0.001},
            "bandwidth": {"bandwidth_kbps": 1000000},
        },
    },
}

# 追踪激活的场景
_active_scenario: Optional[str] = None


@router.get(
    "",
    response_model=list[ScenarioInfo],
    summary="List all scenarios",
    description="Retrieve all predefined network scenario presets.",
)
async def list_scenarios(category: Optional[str] = None) -> list[dict[str, Any]]:
    """List all scenario presets.

    Args:
        category: Optional category filter (mobile, satellite, wifi, wired).
    """
    scenarios = list(SCENARIO_PRESETS.values())
    if category:
        scenarios = [s for s in scenarios if s.get("category") == category]

    result = []
    for s in scenarios:
        entry = {**s, "active": s["id"] == _active_scenario}
        result.append(entry)
    return result


@router.get(
    "/{scenario_id}",
    response_model=ScenarioInfo,
    summary="Get scenario details",
    description="Retrieve details of a specific network scenario preset.",
)
async def get_scenario(scenario_id: str) -> dict[str, Any]:
    """Get scenario details by ID."""
    scenario = SCENARIO_PRESETS.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return {**scenario, "active": scenario_id == _active_scenario}


@router.post(
    "/{scenario_id}/apply",
    response_model=ScenarioActionResponse,
    summary="Apply scenario",
    description="Apply a network scenario preset by activating its fault injections.",
)
async def apply_scenario(scenario_id: str) -> dict[str, Any]:
    """Apply a scenario preset.

    This creates and activates fault injections corresponding to the scenario.
    """
    global _active_scenario

    scenario = SCENARIO_PRESETS.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    # Set as active
    _active_scenario = scenario_id

    return {
        "scenario_id": scenario_id,
        "status": "applied",
        "message": f"Scenario '{scenario['name']}' applied successfully",
        "fault_ids": [],
    }


@router.delete(
    "/{scenario_id}/remove",
    response_model=ScenarioActionResponse,
    summary="Remove scenario",
    description="Remove an applied network scenario by deactivating its fault injections.",
)
async def remove_scenario(scenario_id: str) -> dict[str, Any]:
    """Remove an applied scenario."""
    global _active_scenario

    scenario = SCENARIO_PRESETS.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    if _active_scenario != scenario_id:
        raise HTTPException(
            status_code=400,
            detail=f"Scenario '{scenario_id}' is not currently active",
        )

    _active_scenario = None

    return {
        "scenario_id": scenario_id,
        "status": "removed",
        "message": f"Scenario '{scenario['name']}' removed successfully",
        "fault_ids": [],
    }
