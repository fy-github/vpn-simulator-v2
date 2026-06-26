"""Voice API routes for VPN Simulator v2.

Provides endpoints for VoIP call simulation, quality metrics,
and real-time monitoring.
"""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice")


class StartCallRequest(BaseModel):
    """Request model for starting a voice call."""
    codec: str = Field("g711", description="Voice codec (g711, g729, opus)")
    caller_ip: str = Field("192.168.1.100", description="Caller IP address")
    callee_ip: str = Field("10.0.0.50", description="Callee IP address")
    latency_ms: float = Field(50.0, ge=0, le=5000, description="Network latency in ms")
    jitter_ms: float = Field(10.0, ge=0, le=1000, description="Network jitter in ms")
    packet_loss_percent: float = Field(0.0, ge=0, le=100, description="Packet loss percentage")
    bandwidth_kbps: float = Field(1000.0, ge=1, le=100000, description="Available bandwidth in kbps")


class UpdateConditionsRequest(BaseModel):
    """Request model for updating network conditions."""
    latency_ms: Optional[float] = Field(None, ge=0, le=5000, description="Network latency in ms")
    jitter_ms: Optional[float] = Field(None, ge=0, le=1000, description="Network jitter in ms")
    packet_loss_percent: Optional[float] = Field(None, ge=0, le=100, description="Packet loss percentage")
    bandwidth_kbps: Optional[float] = Field(None, ge=1, le=100000, description="Available bandwidth in kbps")


class CallResponse(BaseModel):
    """Response model for call operations."""
    call_id: Optional[str] = None
    codec: Optional[str] = None
    caller_ip: Optional[str] = None
    callee_ip: Optional[str] = None
    state: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None


def _get_service():
    from vpn_simulator.services.voice import get_voice_service
    return get_voice_service()


@router.get(
    "/codecs",
    summary="List supported codecs",
    description="Get list of supported voice codecs with their configurations.",
)
async def list_codecs() -> dict[str, Any]:
    """List supported voice codecs."""
    service = _get_service()
    return {
        "codecs": service.list_codecs(),
        "count": len(service.list_codecs()),
    }


@router.post(
    "/calls",
    summary="Start voice call",
    description="Start a simulated VoIP call with specified codec and network conditions.",
)
async def start_call(request: StartCallRequest) -> dict[str, Any]:
    """Start a simulated voice call."""
    service = _get_service()
    try:
        result = await service.start_call(
            codec=request.codec,
            caller_ip=request.caller_ip,
            callee_ip=request.callee_ip,
            latency_ms=request.latency_ms,
            jitter_ms=request.jitter_ms,
            packet_loss_percent=request.packet_loss_percent,
            bandwidth_kbps=request.bandwidth_kbps,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/calls/{call_id}/status",
    summary="Get call status",
    description="Get the current status and metrics of a voice call.",
)
async def get_call_status(call_id: str) -> dict[str, Any]:
    """Get call status."""
    service = _get_service()
    result = await service.get_call_status(call_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found")
    return result


@router.post(
    "/calls/{call_id}/stop",
    summary="Stop voice call",
    description="Stop an active voice call and return final metrics.",
)
async def stop_call(call_id: str) -> dict[str, Any]:
    """Stop a voice call."""
    service = _get_service()
    try:
        result = await service.stop_call(call_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/calls/{call_id}/quality",
    summary="Get call quality metrics",
    description="Get real-time quality metrics for an active call.",
)
async def get_call_quality(call_id: str) -> dict[str, Any]:
    """Get call quality metrics."""
    service = _get_service()
    result = await service.get_call_quality(call_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Call '{call_id}' not found")
    return result


@router.put(
    "/calls/{call_id}/conditions",
    summary="Update network conditions",
    description="Update network conditions for an active call.",
)
async def update_network_conditions(call_id: str, request: UpdateConditionsRequest) -> dict[str, Any]:
    """Update network conditions for a call."""
    service = _get_service()
    try:
        result = service.update_network_conditions(
            call_id=call_id,
            latency_ms=request.latency_ms,
            jitter_ms=request.jitter_ms,
            packet_loss_percent=request.packet_loss_percent,
            bandwidth_kbps=request.bandwidth_kbps,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/calls",
    summary="List active calls",
    description="Get list of all active voice calls.",
)
async def list_calls() -> dict[str, Any]:
    """List all active calls."""
    service = _get_service()
    stats = await service.get_statistics()
    return {
        "active_calls": stats["active_call_list"],
        "count": stats["active_calls"],
    }


@router.get(
    "/statistics",
    summary="Get voice statistics",
    description="Get overall voice simulation statistics.",
)
async def get_statistics() -> dict[str, Any]:
    """Get voice simulation statistics."""
    service = _get_service()
    return await service.get_statistics()
