"""Protocol management routes for VPN Simulator v2."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/protocols")

_protocol_service = None
_active_connections: dict[str, dict[str, Any]] = {}


if TYPE_CHECKING:
    from vpn_simulator.services.protocol import ProtocolService


def get_protocol_service() -> ProtocolService:
    global _protocol_service
    if _protocol_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.protocol import ProtocolService

        _protocol_service = ProtocolService(EventBus(), ConfigManager(), get_database_manager())
    return _protocol_service


class ProtocolInfo(BaseModel):
    """Protocol information."""

    name: str = Field(..., description="Protocol name")
    state: str = Field(..., description="Protocol state (stopped/running)")
    port: int = Field(0, description="Listening port")
    connections: int = Field(0, description="Active connection count")


class StartProtocolRequest(BaseModel):
    """Request to start a protocol."""

    port: int | None = Field(None, description="Port to listen on")
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
                "state": "running" if p.get("active", False) else "stopped",
                "port": _get_default_port(p.get("name", "")) if p.get("active", False) else 0,
                "connections": 0,
            }
            for p in protocols
        ]
    except Exception as e:
        logger.warning("Failed to list protocols", error=str(e))
        return []


@router.post(
    "/{name}/start",
    response_model=ProtocolActionResponse,
    summary="Start protocol",
    description="Start a VPN protocol server on the specified port.",
)
async def start_protocol(
    name: str, request: StartProtocolRequest = StartProtocolRequest()
) -> dict[str, str]:
    try:
        service = get_protocol_service()
        await service.start_protocol(
            name=name,
            port=request.port,
            config=request.config,
        )
        conn_id = f"conn_{name}_{uuid.uuid4().hex[:8]}"
        _active_connections[conn_id] = {
            "id": conn_id,
            "protocol": name,
            "state": "connected",
            "local_address": "0.0.0.0",
            "local_port": request.port or _get_default_port(name),
            "remote_address": "127.0.0.1",
            "remote_port": 50000 + len(_active_connections),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "connected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "bytes_sent": 0,
            "bytes_received": 0,
            "packets_sent": 0,
            "packets_received": 0,
        }
        return {
            "name": name,
            "status": "started",
            "message": f"Protocol {name} started",
        }
    except Exception as e:
        logger.warning("Failed to start protocol", protocol=name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start protocol {name}: {e}")


def _get_default_port(name: str) -> int:
    ports = {
        "pptp": 1723,
        "l2tp": 1701,
        "openvpn": 1194,
        "ipsec": 500,
        "ikev2": 500,
        "wireguard": 51820,
        "sstp": 443,
        "openconnect": 443,
        "vxlan": 4789,
    }
    return ports.get(name, 0)


@router.post(
    "/{name}/stop",
    response_model=ProtocolActionResponse,
    summary="Stop protocol",
    description="Stop a running VPN protocol server.",
)
async def stop_protocol(name: str) -> dict[str, str]:
    try:
        service = get_protocol_service()
        await service.stop_protocol(name)
    except Exception as e:
        logger.warning("Failed to stop protocol", protocol=name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop protocol {name}: {e}")
    to_remove = [cid for cid, c in _active_connections.items() if c["protocol"] == name]
    for cid in to_remove:
        del _active_connections[cid]
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
        active = bool(protocol.get("active", False))
        return {
            "name": protocol.get("name", name),
            "state": "running" if active else "stopped",
            "port": _get_default_port(name) if active else 0,
            "connections": 0,
        }
    except Exception as e:
        logger.warning("Failed to get protocol status", protocol=name, error=str(e))
        return {"name": name, "state": "stopped", "port": 0, "connections": 0}
