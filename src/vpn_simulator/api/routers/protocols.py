"""Protocol management routes for VPN Simulator v2."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protocols")

_protocol_service = None
_started_protocols: set[str] = set()


def get_protocol_service():
    global _protocol_service
    if _protocol_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import DatabaseManager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.protocol import ProtocolService
        _protocol_service = ProtocolService(EventBus(), ConfigManager(), DatabaseManager())
    return _protocol_service


class ProtocolInfo(BaseModel):
    """Protocol information."""

    name: str = Field(..., description="Protocol name")
    state: str = Field(..., description="Protocol state (stopped/running)")
    port: int = Field(0, description="Listening port")
    connections: int = Field(0, description="Active connection count")


class StartProtocolRequest(BaseModel):
    """Request to start a protocol."""

    port: Optional[int] = Field(None, description="Port to listen on")
    config: dict[str, Any] = Field(default_factory=dict, description="Protocol-specific config")


class ProtocolActionResponse(BaseModel):
    """Response for protocol actions."""

    name: str = Field(..., description="Protocol name")
    status: str = Field(..., description="Action result status")
    message: str = Field("", description="Result message")


@router.get(
    "",
    response_model=list[ProtocolInfo],
    summary="List all protocols",
    description="Retrieve a list of all available VPN protocols and their current status.",
)
async def list_protocols() -> list[dict[str, Any]]:
    """List all available protocols with their status."""
    try:
        service = get_protocol_service()
        protocols = await service.list_protocols()
        return [
            {
                "name": p.get("name", ""),
                "state": "running" if p.get("name", "") in _started_protocols else "stopped",
                "port": 1723 if p.get("name", "") in _started_protocols else 0,
                "connections": 0,
            }
            for p in protocols
        ]
    except Exception as e:
        logger.warning("Failed to list protocols: %s", e)
        return []


@router.post(
    "/{name}/start",
    response_model=ProtocolActionResponse,
    summary="Start protocol",
    description="Start a VPN protocol server on the specified port.",
)
async def start_protocol(name: str, request: StartProtocolRequest = StartProtocolRequest()) -> dict[str, str]:
    """Start a protocol server."""
    try:
        service = get_protocol_service()
        result = await service.start_protocol(
            name=name,
            port=request.port,
            config=request.config,
        )
        _started_protocols.add(name)
        return {
            "name": name,
            "status": "started",
            "message": f"Protocol {name} started",
        }
    except Exception as e:
        logger.warning("Failed to start protocol %s: %s", name, e)
        raise HTTPException(status_code=500, detail=f"Failed to start protocol {name}: {e}")


@router.post(
    "/{name}/stop",
    response_model=ProtocolActionResponse,
    summary="Stop protocol",
    description="Stop a running VPN protocol server.",
)
async def stop_protocol(name: str) -> dict[str, str]:
    """Stop a protocol server."""
    try:
        service = get_protocol_service()
        await service.stop_protocol(name)
    except Exception as e:
        logger.warning("Failed to stop protocol %s: %s", name, e)
        raise HTTPException(status_code=500, detail=f"Failed to stop protocol {name}: {e}")
    _started_protocols.discard(name)
    return {"name": name, "status": "stopped", "message": f"Protocol {name} stopped"}


@router.get(
    "/{name}/status",
    response_model=ProtocolInfo,
    summary="Get protocol status",
    description="Get the current status of a specific protocol.",
)
async def get_protocol_status(name: str) -> dict[str, Any]:
    """Get protocol status."""
    try:
        service = get_protocol_service()
        protocol = await service.get_protocol(name)
        if protocol is None:
            return {"name": name, "state": "stopped", "port": 0, "connections": 0}
        return {
            "name": protocol.get("name", name),
            "state": "running" if protocol.get("active", False) else "stopped",
            "port": 0,
            "connections": 0,
        }
    except Exception as e:
        logger.warning("Failed to get protocol status %s: %s", name, e)
        return {"name": name, "state": "stopped", "port": 0, "connections": 0}
