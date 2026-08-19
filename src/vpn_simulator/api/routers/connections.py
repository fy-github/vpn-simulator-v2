"""Connection management routes for VPN Simulator v2."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections")

_connection_service = None


def get_connection_service():
    global _connection_service
    if _connection_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.connection import ConnectionService

        _connection_service = ConnectionService(EventBus(), ConfigManager(), get_database_manager())
    return _connection_service


class ConnectionInfo(BaseModel):
    """Connection information."""

    id: str = Field(..., description="Connection ID")
    protocol: str = Field(..., description="Protocol name")
    state: str = Field(..., description="Connection state")
    local_address: str = Field("", description="Local address")
    local_port: int = Field(0, description="Local port")
    remote_address: str = Field("", description="Remote address")
    remote_port: int = Field(0, description="Remote port")
    created_at: str = Field("", description="Creation timestamp")
    connected_at: str | None = Field(None, description="Connection established timestamp")
    bytes_sent: int = Field(0, description="Bytes sent")
    bytes_received: int = Field(0, description="Bytes received")
    packets_sent: int = Field(0, description="Packets sent")
    packets_received: int = Field(0, description="Packets received")


class ConnectionActionResponse(BaseModel):
    """Response for connection actions."""

    connection_id: str = Field(..., description="Connection ID")
    status: str = Field(..., description="Action result status")
    message: str = Field("", description="Result message")


@router.get(
    "",
    response_model=list[ConnectionInfo],
    summary="List all connections",
    description="Retrieve all active connections, optionally filtered by protocol and state.",
)
async def list_connections(
    protocol: str | None = None,
    state: str | None = None,
) -> list[dict[str, Any]]:
    from vpn_simulator.api.routers.protocols import _active_connections

    try:
        service = get_connection_service()
        connections = await service.list_connections(protocol=protocol, state=state)
        result = [
            {
                "id": c.get("id", ""),
                "protocol": c.get("protocol", ""),
                "state": c.get("state", "disconnected"),
                "local_address": c.get("local_address", ""),
                "local_port": c.get("local_port", 0),
                "remote_address": c.get("remote_address", ""),
                "remote_port": c.get("remote_port", 0),
                "created_at": c.get("created_at", ""),
                "connected_at": c.get("connected_at"),
                "bytes_sent": c.get("bytes_sent", 0),
                "bytes_received": c.get("bytes_received", 0),
                "packets_sent": c.get("packets_sent", 0),
                "packets_received": c.get("packets_received", 0),
            }
            for c in connections
        ]
        for conn in _active_connections.values():
            if protocol and conn["protocol"] != protocol:
                continue
            if state and conn["state"] != state:
                continue
            result.append(conn)
        return result
    except Exception as e:
        logger.warning("Failed to list connections: %s", e)
        return list(_active_connections.values())


@router.get(
    "/{connection_id}",
    response_model=ConnectionInfo,
    summary="Get connection details",
    description="Get detailed information about a specific connection.",
)
async def get_connection(connection_id: str) -> dict[str, Any]:
    """Get connection details."""
    try:
        service = get_connection_service()
        conn = await service.get_connection(connection_id)
        if conn is None:
            raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
        return {
            "id": conn.get("id", connection_id),
            "protocol": conn.get("protocol", ""),
            "state": conn.get("state", "disconnected"),
            "local_address": conn.get("local_address", ""),
            "local_port": conn.get("local_port", 0),
            "remote_address": conn.get("remote_address", ""),
            "remote_port": conn.get("remote_port", 0),
            "created_at": conn.get("created_at", ""),
            "connected_at": conn.get("connected_at"),
            "bytes_sent": conn.get("bytes_sent", 0),
            "bytes_received": conn.get("bytes_received", 0),
            "packets_sent": conn.get("packets_sent", 0),
            "packets_received": conn.get("packets_received", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Failed to get connection %s: %s", connection_id, e)
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")


@router.delete(
    "/{connection_id}",
    response_model=ConnectionActionResponse,
    summary="Disconnect connection",
    description="Disconnect and remove an active connection.",
)
async def disconnect_connection(connection_id: str) -> dict[str, str]:
    """Disconnect a connection."""
    from vpn_simulator.api.routers.protocols import _active_connections

    removed = False

    # 移除协议 start 时在路由器内存中伪造的连接
    if connection_id in _active_connections:
        del _active_connections[connection_id]
        removed = True

    # 移除 service 管理的连接（若存在）
    try:
        service = get_connection_service()
        if await service.disconnect_connection(connection_id):
            removed = True
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning("Failed to disconnect connection %s: %s", connection_id, e)

    if not removed:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")

    return {
        "connection_id": connection_id,
        "status": "disconnected",
        "message": f"Connection {connection_id} disconnected",
    }
