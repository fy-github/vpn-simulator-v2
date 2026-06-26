"""WebSocket manager for VPN Simulator v2."""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """WebSocket connection manager with channel-based pub/sub."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default") -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)

    async def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        """Remove a WebSocket connection."""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        for channel in list(self._connections.keys()):
            for ws in list(self._connections[channel]):
                try:
                    await ws.close()
                except Exception:
                    pass
            self._connections[channel].clear()
        self._connections.clear()

    async def broadcast(self, event: str, data: dict[str, Any], channel: str = "default") -> None:
        """Broadcast a message to all connections on a channel."""
        if channel not in self._connections:
            return

        message = json.dumps(
            {
                "event": event,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        disconnected: set[WebSocket] = set()
        for websocket in self._connections[channel]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        self._connections[channel] -= disconnected

    async def send_to(self, websocket: WebSocket, event: str, data: dict[str, Any]) -> None:
        """Send a message to a specific WebSocket connection."""
        message = json.dumps(
            {
                "event": event,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await websocket.send_text(message)

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def channels(self) -> list[str]:
        """Get list of active channels."""
        return list(self._connections.keys())


ws_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, channel: str = "default") -> None:
    """WebSocket endpoint handler."""
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            action = message.get("action")
            if action == "subscribe":
                new_channel = message.get("channel", "default")
                await ws_manager.disconnect(websocket, channel)
                channel = new_channel
                await ws_manager.connect(websocket, channel)
            elif action == "unsubscribe":
                await ws_manager.disconnect(websocket, channel)
                await ws_manager.connect(websocket, "default")
                channel = "default"
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)
