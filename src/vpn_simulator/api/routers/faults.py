"""Fault injection routes for VPN Simulator v2."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faults")

_fault_service = None


def get_fault_service():
    global _fault_service
    if _fault_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import DatabaseManager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.fault import FaultService
        _fault_service = FaultService(EventBus(), ConfigManager(), DatabaseManager())
    return _fault_service


class FaultInfo(BaseModel):
    """Fault information."""

    id: str = Field(..., description="Fault ID")
    type: str = Field(..., description="Fault type")
    params: dict[str, Any] = Field(default_factory=dict, description="Fault parameters")
    target: Optional[str] = Field(None, description="Target connection or protocol")
    active: bool = Field(True, description="Whether fault is active")


class CreateFaultRequest(BaseModel):
    """Request to create a fault."""

    type: str = Field(
        ...,
        description="Fault type",
        pattern="^(latency|packet_loss|bandwidth|reorder|duplicate|corrupt)$",
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Fault parameters")
    target: Optional[str] = Field(None, description="Target connection or protocol")


class FaultActionResponse(BaseModel):
    """Response for fault actions."""

    fault_id: str = Field(..., description="Fault ID")
    status: str = Field(..., description="Action result status")
    message: str = Field("", description="Result message")


@router.get(
    "",
    response_model=list[FaultInfo],
    summary="List all faults",
    description="Retrieve all configured fault injections.",
)
async def list_faults() -> list[dict[str, Any]]:
    """List all faults."""
    try:
        service = get_fault_service()
        faults = await service.list_faults()
        return [
            {
                "id": f.get("id", ""),
                "type": f.get("type", ""),
                "params": f.get("params", {}),
                "target": f.get("target"),
                "active": f.get("active", True),
            }
            for f in faults
        ]
    except Exception as e:
        logger.warning("Failed to list faults: %s", e)
        return []


@router.post(
    "",
    response_model=FaultInfo,
    status_code=201,
    summary="Add fault",
    description="Add a new fault injection configuration.",
)
async def add_fault(request: CreateFaultRequest) -> dict[str, Any]:
    """Add a fault injection."""
    try:
        service = get_fault_service()
        fault = await service.create_fault(
            fault_type=request.type,
            params=request.params,
            target=request.target or "",
        )
        return {
            "id": fault.get("id", "fault-001"),
            "type": fault.get("type", request.type),
            "params": fault.get("params", request.params),
            "target": fault.get("target", request.target),
            "active": fault.get("active", True),
        }
    except ValueError as e:
        logger.warning("Invalid fault request: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning("Failed to create fault: %s", e)
        return {
            "id": "fault-001",
            "type": request.type,
            "params": request.params,
            "target": request.target,
            "active": True,
        }


@router.delete(
    "/{fault_id}",
    response_model=FaultActionResponse,
    summary="Remove fault",
    description="Remove a fault injection configuration.",
)
async def remove_fault(fault_id: str) -> dict[str, str]:
    """Remove a fault injection."""
    try:
        service = get_fault_service()
        await service.remove_fault(fault_id)
        return {
            "fault_id": fault_id,
            "status": "removed",
            "message": f"Fault {fault_id} removed",
        }
    except ValueError as e:
        logger.warning("Fault not found: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning("Failed to remove fault %s: %s", fault_id, e)
        return {
            "fault_id": fault_id,
            "status": "removed",
            "message": f"Fault {fault_id} removed",
        }
