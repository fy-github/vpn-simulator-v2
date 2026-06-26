"""Protocol comparison routes for VPN Simulator v2."""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from vpn_simulator.services.comparison import ComparisonService, PhaseCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compare")

comparison_service = ComparisonService()


class StateInfoResponse(BaseModel):
    """State information with phase category."""

    name: str = Field(..., description="State name")
    description: str = Field(..., description="State description")
    phase: str = Field(..., description="Phase category")
    is_initial: bool = Field(False, description="Is initial state")
    is_final: bool = Field(False, description="Is final state")


class TransitionInfoResponse(BaseModel):
    """Transition information with phase category."""

    from_state: str = Field(..., alias="from_state", description="Source state")
    to_state: str = Field(..., alias="to_state", description="Target state")
    event: str = Field(..., description="Trigger event")
    description: str = Field("", description="Transition description")
    phase: str = Field(..., description="Phase category")

    model_config = {"populate_by_name": True}


class ProtocolStateDataResponse(BaseModel):
    """Protocol state machine data."""

    name: str = Field(..., description="Protocol name")
    description: str = Field("", description="Protocol description")
    states: list[StateInfoResponse] = Field(default_factory=list, description="States list")
    transitions: list[TransitionInfoResponse] = Field(default_factory=list, description="Transitions list")


class ComparisonResponse(BaseModel):
    """Comparison result for two protocols."""

    protocol1: ProtocolStateDataResponse = Field(..., description="First protocol data")
    protocol2: ProtocolStateDataResponse = Field(..., description="Second protocol data")
    common_phases: list[str] = Field(default_factory=list, description="Common phase categories")
    different_phases: list[str] = Field(default_factory=list, description="Different phase categories")


class ProtocolOption(BaseModel):
    """Available protocol option."""

    name: str = Field(..., description="Protocol name")
    description: str = Field("", description="Protocol description")


@router.get(
    "/protocols",
    response_model=list[ProtocolOption],
    summary="List comparable protocols",
    description="Retrieve a list of all protocols available for comparison.",
)
async def list_comparable_protocols() -> list[dict[str, Any]]:
    """List all protocols available for comparison."""
    return comparison_service.get_available_protocols()


@router.get(
    "",
    response_model=ComparisonResponse,
    summary="Compare two protocols",
    description="Compare the state machines of two VPN protocols side by side.",
)
async def compare_protocols(
    protocol1: str = Query(..., description="First protocol name (e.g., pptp)"),
    protocol2: str = Query(..., description="Second protocol name (e.g., l2tp)"),
) -> dict[str, Any]:
    """Compare two protocol state machines.

    Returns detailed state machine data for both protocols with phase
    categorization for highlighting similarities and differences.
    """
    try:
        result = await comparison_service.compare(protocol1, protocol2)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    def _state_to_dict(s: Any) -> dict[str, Any]:
        return {
            "name": s.name,
            "description": s.description,
            "phase": s.phase.value,
            "is_initial": s.is_initial,
            "is_final": s.is_final,
        }

    def _transition_to_dict(t: Any) -> dict[str, Any]:
        return {
            "from_state": t.from_state,
            "to_state": t.to_state,
            "event": t.event,
            "description": t.description,
            "phase": t.phase.value,
        }

    return {
        "protocol1": {
            "name": result.protocol1.name,
            "description": result.protocol1.description,
            "states": [_state_to_dict(s) for s in result.protocol1.states],
            "transitions": [_transition_to_dict(t) for t in result.protocol1.transitions],
        },
        "protocol2": {
            "name": result.protocol2.name,
            "description": result.protocol2.description,
            "states": [_state_to_dict(s) for s in result.protocol2.states],
            "transitions": [_transition_to_dict(t) for t in result.protocol2.transitions],
        },
        "common_phases": [p.value for p in result.common_phases],
        "different_phases": [p.value for p in result.different_phases],
    }
