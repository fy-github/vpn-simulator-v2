"""Tests for ConnectionService - connection management service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.services.connection import ConnectionService


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def mock_db_manager():
    dm = MagicMock(spec=DatabaseManager)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    dm.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    dm.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return dm


@pytest.fixture
def service(mock_event_bus, mock_config_manager, mock_db_manager) -> ConnectionService:
    return ConnectionService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


class TestConnectionServiceInit:
    def test_service_creation(self, service: ConnectionService):
        assert service is not None
        assert service._connection_manager is not None


class TestCreateConnection:
    @pytest.mark.asyncio
    async def test_create_connection_client(self, service: ConnectionService):
        result = await service.create_connection("pptp", remote_address="10.0.0.1")
        assert result is not None
        assert result["protocol"] == "pptp"
        assert result["connection_type"] == "client"
        assert result["remote_address"] == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_create_connection_server(self, service: ConnectionService):
        result = await service.create_connection("l2tp", connection_type="server")
        assert result["connection_type"] == "server"

    @pytest.mark.asyncio
    async def test_create_connection_with_params(self, service: ConnectionService):
        result = await service.create_connection(
            "openvpn",
            local_address="192.168.1.1",
            local_port=1194,
            remote_address="10.0.0.1",
            remote_port=54321,
        )
        assert result["local_address"] == "192.168.1.1"
        assert result["local_port"] == 1194

    @pytest.mark.asyncio
    async def test_create_connection_with_protocol_data(self, service: ConnectionService):
        result = await service.create_connection(
            "wireguard",
            protocol_data={"public_key": "abc123"},
        )
        assert result["protocol_data"]["public_key"] == "abc123"

    @pytest.mark.asyncio
    async def test_create_connection_emits_event(self, service: ConnectionService, mock_event_bus):
        await service.create_connection("pptp")
        assert mock_event_bus.emit.called


class TestGetConnection:
    @pytest.mark.asyncio
    async def test_get_connection(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        result = await service.get_connection(created["id"])
        assert result is not None
        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, service: ConnectionService):
        result = await service.get_connection("nonexistent")
        assert result is None


class TestListConnections:
    @pytest.mark.asyncio
    async def test_list_connections_empty(self, service: ConnectionService):
        connections = await service.list_connections()
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_list_connections_with_data(self, service: ConnectionService):
        await service.create_connection("pptp")
        await service.create_connection("l2tp")
        connections = await service.list_connections()
        assert len(connections) == 2

    @pytest.mark.asyncio
    async def test_list_connections_by_protocol(self, service: ConnectionService):
        await service.create_connection("pptp")
        await service.create_connection("l2tp")
        connections = await service.list_connections(protocol="pptp")
        assert len(connections) == 1

    @pytest.mark.asyncio
    async def test_list_connections_by_state(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        await service.update_connection_state(created["id"], "connected")
        connections = await service.list_connections(state="connected")
        assert len(connections) == 1


class TestUpdateConnectionState:
    @pytest.mark.asyncio
    async def test_update_to_connected(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        result = await service.update_connection_state(created["id"], "connected")
        assert result["new_state"] == "connected"

    @pytest.mark.asyncio
    async def test_update_to_disconnected(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        await service.update_connection_state(created["id"], "connected")
        result = await service.update_connection_state(created["id"], "disconnected")
        assert result["new_state"] == "disconnected"

    @pytest.mark.asyncio
    async def test_update_to_error(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        result = await service.update_connection_state(created["id"], "error")
        assert result["new_state"] == "error"

    @pytest.mark.asyncio
    async def test_update_state_emits_event(self, service: ConnectionService, mock_event_bus):
        created = await service.create_connection("pptp")
        await service.update_connection_state(created["id"], "connected")
        assert mock_event_bus.emit.call_count >= 2


class TestUpdateConnectionStats:
    @pytest.mark.asyncio
    async def test_update_stats(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        await service.update_connection_stats(
            created["id"],
            bytes_sent=1024,
            bytes_received=2048,
            packets_sent=10,
            packets_received=20,
        )
        conn = await service.get_connection(created["id"])
        assert conn["bytes_sent"] == 1024
        assert conn["bytes_received"] == 2048

    @pytest.mark.asyncio
    async def test_update_stats_not_found(self, service: ConnectionService):
        await service.update_connection_stats("nonexistent", bytes_sent=100)


class TestRemoveConnection:
    @pytest.mark.asyncio
    async def test_remove_connection(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        result = await service.remove_connection(created["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_connection_not_found(self, service: ConnectionService):
        result = await service.remove_connection("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_connected_disconnects_first(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        await service.update_connection_state(created["id"], "connected")
        result = await service.remove_connection(created["id"])
        assert result is True


class TestGetConnectionStats:
    @pytest.mark.asyncio
    async def test_get_stats_empty(self, service: ConnectionService):
        stats = await service.get_connection_stats()
        assert stats["total"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_connections(self, service: ConnectionService):
        await service.create_connection("pptp")
        await service.create_connection("l2tp")
        stats = await service.get_connection_stats()
        assert stats["total"] == 2
        assert "by_state" in stats
        assert "by_protocol" in stats


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, service: ConnectionService):
        created = await service.create_connection("pptp")
        assert created["state"] == "connecting"

        await service.update_connection_state(created["id"], "connected")
        conn = await service.get_connection(created["id"])
        assert conn["state"] == "connected"

        await service.update_connection_stats(created["id"], bytes_sent=1024)
        conn = await service.get_connection(created["id"])
        assert conn["bytes_sent"] == 1024

        await service.remove_connection(created["id"])

    @pytest.mark.asyncio
    async def test_multiple_protocols(self, service: ConnectionService):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            result = await service.create_connection(proto)
            assert result["protocol"] == proto

    @pytest.mark.asyncio
    async def test_connection_types(self, service: ConnectionService):
        client = await service.create_connection("pptp", connection_type="client")
        server = await service.create_connection("pptp", connection_type="server")
        assert client["connection_type"] == "client"
        assert server["connection_type"] == "server"
