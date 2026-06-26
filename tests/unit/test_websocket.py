"""Tests for WebSocket manager - covering all uncovered lines."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from vpn_simulator.api.websocket import WebSocketManager, websocket_endpoint


@pytest.fixture
def manager() -> WebSocketManager:
    return WebSocketManager()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"action": "ping"}')
    return ws


class TestWebSocketManagerInit:
    def test_init(self, manager: WebSocketManager):
        assert manager._connections == {}
        assert manager.connection_count == 0
        assert manager.channels == []


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_default_channel(self, manager: WebSocketManager, mock_ws):
        await manager.connect(mock_ws)
        mock_ws.accept.assert_called_once()
        assert "default" in manager._connections
        assert mock_ws in manager._connections["default"]

    @pytest.mark.asyncio
    async def test_connect_custom_channel(self, manager: WebSocketManager, mock_ws):
        await manager.connect(mock_ws, channel="test")
        assert "test" in manager._connections
        assert mock_ws in manager._connections["test"]

    @pytest.mark.asyncio
    async def test_connect_multiple(self, manager: WebSocketManager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, channel="ch1")
        await manager.connect(ws2, channel="ch1")
        assert len(manager._connections["ch1"]) == 2


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect(self, manager: WebSocketManager, mock_ws):
        await manager.connect(mock_ws)
        await manager.disconnect(mock_ws)
        assert mock_ws not in manager._connections.get("default", set())

    @pytest.mark.asyncio
    async def test_disconnect_removes_empty_channel(self, manager: WebSocketManager, mock_ws):
        await manager.connect(mock_ws)
        await manager.disconnect(mock_ws)
        assert "default" not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager: WebSocketManager, mock_ws):
        await manager.disconnect(mock_ws, channel="nonexistent")


class TestDisconnectAll:
    @pytest.mark.asyncio
    async def test_disconnect_all(self, manager: WebSocketManager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1, channel="ch1")
        await manager.connect(ws2, channel="ch2")
        await manager.disconnect_all()
        assert manager.connection_count == 0
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self, manager: WebSocketManager):
        await manager.disconnect_all()
        assert manager.connection_count == 0


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast(self, manager: WebSocketManager, mock_ws):
        await manager.connect(mock_ws)
        await manager.broadcast("test_event", {"key": "value"})
        mock_ws.send_text.assert_called_once()
        message = json.loads(mock_ws.send_text.call_args[0][0])
        assert message["event"] == "test_event"
        assert message["data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_broadcast_no_channel(self, manager: WebSocketManager):
        await manager.broadcast("test_event", {"key": "value"}, channel="nonexistent")

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self, manager: WebSocketManager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock(side_effect=Exception("disconnected"))
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.broadcast("test", {})
        assert ws1 in manager._connections["default"]
        assert ws2 not in manager._connections["default"]


class TestSendTo:
    @pytest.mark.asyncio
    async def test_send_to(self, manager: WebSocketManager, mock_ws):
        await manager.send_to(mock_ws, "test_event", {"key": "value"})
        mock_ws.send_text.assert_called_once()
        message = json.loads(mock_ws.send_text.call_args[0][0])
        assert message["event"] == "test_event"


class TestConnectionCount:
    def test_empty(self, manager: WebSocketManager):
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_with_connections(self, manager: WebSocketManager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)
        assert manager.connection_count == 2


class TestChannels:
    def test_empty(self, manager: WebSocketManager):
        assert manager.channels == []

    @pytest.mark.asyncio
    async def test_with_channels(self, manager: WebSocketManager):
        ws = AsyncMock()
        await manager.connect(ws, channel="ch1")
        await manager.connect(ws, channel="ch2")
        assert set(manager.channels) == {"ch1", "ch2"}
