"""Time-varying network impairment routes (F1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/impairments")

_impairment_service = None

_VALID_CHANGE_TYPES = ["linear", "exponential", "step", "sine", "random"]
_VALID_FAULT_TYPES = [
    "latency",
    "packet_loss",
    "bandwidth",
    "reorder",
    "duplicate",
    "corrupt",
]


if TYPE_CHECKING:
    from vpn_simulator.services.impairment import ImpairmentService


def get_impairment_service() -> ImpairmentService:
    """懒加载单例 ImpairmentService。"""
    global _impairment_service
    if _impairment_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.impairment import ImpairmentService

        _impairment_service = ImpairmentService(EventBus(), ConfigManager(), get_database_manager())
    return _impairment_service


class CreateImpairmentRequest(BaseModel):
    """Request to create a time-varying impairment."""

    fault_type: str = Field(..., description="Fault type (one of 6 fault types)")
    param: str = Field(..., description="Fault parameter to vary (e.g. delay_ms)")
    change_type: str = Field(..., description="linear | exponential | step | sine | random")
    start_value: float = Field(..., description="Start value")
    end_value: float = Field(..., description="End value")
    duration_seconds: float = Field(..., gt=0, description="Duration in seconds")
    period_seconds: float = Field(0.0, ge=0, description="Sine period in seconds")
    step_at_seconds: float | None = Field(None, description="Step time in seconds")
    target: str = Field("", description="Target protocol or connection")
    name: str = Field("", description="Display name")


@router.get(
    "/presets",
    summary="List impairment presets",
    description="List built-in time-varying impairment presets.",
)
async def list_presets() -> list[dict[str, Any]]:
    """List impairment presets."""
    return get_impairment_service().list_presets()


@router.post(
    "/presets/{name}/apply",
    summary="Apply a preset",
    description="Apply a built-in impairment preset, creating an impairment instance.",
    status_code=201,
)
async def apply_preset(name: str) -> dict[str, Any]:
    """Apply a preset by name."""
    try:
        return await get_impairment_service().apply_preset(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "",
    summary="List impairments",
    description="List all created impairment instances.",
)
async def list_impairments() -> list[dict[str, Any]]:
    """List impairments."""
    return get_impairment_service().list_impairments()


@router.post(
    "",
    summary="Create impairment",
    description="Create a time-varying impairment instance.",
    status_code=201,
)
async def create_impairment(request: CreateImpairmentRequest) -> dict[str, Any]:
    """Create an impairment."""
    if request.change_type not in _VALID_CHANGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid change_type '{request.change_type}'. Valid: {_VALID_CHANGE_TYPES}",
        )
    if request.fault_type not in _VALID_FAULT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fault_type '{request.fault_type}'. Valid: {_VALID_FAULT_TYPES}",
        )
    impairment = await get_impairment_service().create_impairment(
        fault_type=request.fault_type,
        param=request.param,
        change_type=request.change_type,
        start_value=request.start_value,
        end_value=request.end_value,
        duration_seconds=request.duration_seconds,
        period_seconds=request.period_seconds,
        step_at_seconds=request.step_at_seconds,
        target=request.target,
        name=request.name,
    )
    return impairment.to_dict()


@router.post(
    "/{impairment_id}/start",
    summary="Start impairment",
    description="Start a time-varying impairment (records start time).",
)
async def start_impairment(impairment_id: str) -> dict[str, Any]:
    """Start an impairment."""
    result = await get_impairment_service().start(impairment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Impairment {impairment_id} not found")
    return result


@router.post(
    "/{impairment_id}/stop",
    summary="Stop impairment",
    description="Stop a time-varying impairment (freezes progress).",
)
async def stop_impairment(impairment_id: str) -> dict[str, Any]:
    """Stop an impairment."""
    result = await get_impairment_service().stop(impairment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Impairment {impairment_id} not found")
    return result


@router.get(
    "/{impairment_id}/status",
    summary="Get impairment status",
    description="Get current value, progress and lifecycle status of an impairment.",
)
async def get_impairment_status(impairment_id: str) -> dict[str, Any]:
    """Get impairment status."""
    result = await get_impairment_service().status(impairment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Impairment {impairment_id} not found")
    return result


@router.get(
    "/{impairment_id}/timeline",
    summary="Get impairment timeline",
    description="Get evenly-sampled time series of the impairment curve.",
)
async def get_impairment_timeline(
    impairment_id: str,
    samples: int = Query(60, ge=2, le=500, description="Number of samples"),
) -> list[dict[str, Any]]:
    """Get impairment timeline samples."""
    service = get_impairment_service()
    if service.get_impairment(impairment_id) is None:
        raise HTTPException(status_code=404, detail=f"Impairment {impairment_id} not found")
    return service.timeline(impairment_id, samples)


@router.delete(
    "/{impairment_id}",
    summary="Remove impairment",
    description="Remove an impairment instance.",
)
async def remove_impairment(impairment_id: str) -> dict[str, str]:
    """Remove an impairment."""
    removed = await get_impairment_service().remove(impairment_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Impairment {impairment_id} not found")
    return {"impairment_id": impairment_id, "status": "removed"}
