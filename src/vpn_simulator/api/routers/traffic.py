"""Traffic API routes for VPN Simulator v2.

Provides endpoints for traffic capture control, statistics,
and real-time packet streaming via WebSocket.
"""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traffic")

_VALID_PROTOCOLS = ["tcp", "udp", "icmp", "arp"]


class CaptureRequest(BaseModel):
    """Request model for starting capture."""
    protocols: Optional[list[str]] = None


class CaptureResponse(BaseModel):
    """Response model for capture operations."""
    status: str
    message: str
    protocols: Optional[list[str] | str] = None
    statistics: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None


def _get_service():
    from vpn_simulator.services.traffic import get_traffic_service
    return get_traffic_service()


def _validate_protocols(protocols: Optional[list[str]]) -> Optional[list[str]]:
    if protocols is None:
        return None
    validated = []
    for p in protocols:
        if p.lower() not in _VALID_PROTOCOLS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid protocol '{p}'. Valid: {_VALID_PROTOCOLS}",
            )
        validated.append(p.lower())
    return validated


@router.post(
    "/capture",
    summary="Start traffic capture",
    description="Start capturing simulated network traffic with optional protocol filtering.",
    response_model=CaptureResponse,
)
async def start_capture(request: CaptureRequest) -> CaptureResponse:
    """Start traffic capture with optional protocol filtering."""
    service = _get_service()
    validated_protocols = _validate_protocols(request.protocols)
    result = await service.start_capture(protocols=validated_protocols)
    return CaptureResponse(**result)


@router.post(
    "/stop",
    summary="Stop traffic capture",
    description="Stop the current traffic capture and return final statistics.",
    response_model=CaptureResponse,
)
async def stop_capture() -> CaptureResponse:
    """Stop the current traffic capture."""
    service = _get_service()
    result = await service.stop_capture()
    return CaptureResponse(**result)


@router.get(
    "/statistics",
    summary="Get traffic statistics",
    description="Retrieve current traffic statistics including PPS, BPS, and protocol counts.",
)
async def get_statistics() -> dict[str, Any]:
    """Get current traffic statistics."""
    service = _get_service()
    return service.get_statistics()


@router.get(
    "/packets",
    summary="Get recent packets",
    description="Retrieve a list of recently captured packets.",
)
async def get_recent_packets(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of packets to return"),
) -> dict[str, Any]:
    """Get recent packets."""
    service = _get_service()
    packets = service.get_recent_packets(limit=limit)
    return {
        "packets": packets,
        "count": len(packets),
        "total": service.packet_count,
    }


@router.websocket("/stream")
async def traffic_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time traffic streaming.

    Streams packet data in real-time to connected clients.
    Each message is a JSON object with packet data.
    """
    await websocket.accept()
    service = _get_service()

    try:
        # Start capture if not already capturing
        if not service.is_capturing:
            await service.start_capture()

        # Stream packets
        async for packet_data in service.get_packet_stream():
            try:
                await websocket.send_json(packet_data)
            except WebSocketDisconnect:
                break
            except Exception:
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get(
    "/status",
    summary="Get capture status",
    description="Check if traffic capture is currently active.",
)
async def get_capture_status() -> dict[str, Any]:
    """Get current capture status."""
    service = _get_service()
    return {
        "capturing": service.is_capturing,
        "packet_count": service.packet_count,
    }
