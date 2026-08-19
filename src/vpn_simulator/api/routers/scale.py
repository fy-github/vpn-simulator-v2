"""Large-scale device simulation routes (F7)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scale")

_scale_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.scale import ScaleService


def get_scale_service() -> ScaleService:
    """懒加载单例 ScaleService。"""
    global _scale_service
    if _scale_service is None:
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.services.scale import ScaleService

        _scale_service = ScaleService(db_manager=get_database_manager())
    return _scale_service


class PollRequest(BaseModel):
    """Request to run a bulk device poll."""

    count: int | None = Field(None, description="Devices to poll (default all)")
    concurrency: int = Field(1000, ge=1, description="Concurrency limit (connection pool)")


@router.get(
    "/devices",
    summary="List devices (paginated)",
    description="Lazily list simulated devices with pagination.",
)
async def list_devices(
    offset: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
) -> dict[str, Any]:
    """List devices."""
    return get_scale_service().list_devices(offset, limit)


@router.get(
    "/devices/{index}",
    summary="Get a device",
    description="Get a simulated device by index.",
)
async def get_device(index: int) -> dict[str, Any]:
    """Get a device."""
    device = get_scale_service().get_device(index)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device index {index} out of range")
    return device


@router.get(
    "/stats",
    summary="Get aggregate stats",
    description="Get aggregate device statistics (computed without materializing all devices).",
)
async def stats() -> dict[str, Any]:
    """Get aggregate stats."""
    return get_scale_service().stats()


@router.post(
    "/poll",
    summary="Run bulk poll",
    description="Simulate a bulk device health poll with a connection pool.",
)
async def poll(request: PollRequest) -> dict[str, Any]:
    """Run a bulk poll."""
    return await get_scale_service().simulate_poll(request.count, request.concurrency)


@router.post(
    "/persist",
    summary="Persist aggregate snapshot",
    description="Persist one aggregate snapshot row (not per-device rows).",
)
async def persist() -> dict[str, Any]:
    """Persist aggregate snapshot."""
    return await get_scale_service().persist_snapshot()


@router.get(
    "/snapshots",
    summary="Get latest aggregate snapshot",
    description="Get the most recent aggregate snapshot.",
)
async def latest_snapshot() -> dict[str, Any]:
    """Get latest snapshot."""
    snapshot = await get_scale_service().latest_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No snapshot persisted yet")
    return snapshot
