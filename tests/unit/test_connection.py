"""Unit tests for the connection model module.

Tests cover:
- ConnectionInfo creation and defaults
- ConnectionState enum values
- ConnectionInfo.to_dict() serialization
- ConnectionInfo.duration property
- ConnectionManager CRUD operations
- Connection state transitions
"""

from __future__ import annotations

from datetime import datetime

import pytest

from vpn_simulator.domain.connection import (
    ConnectionInfo,
    ConnectionManager,
    ConnectionState,
    ConnectionType,
)


class TestConnectionState:
    """Tests for the ConnectionState enum."""

    def test_state_values(self):
        """Verify all connection state values."""
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.DISCONNECTING.value == "disconnecting"
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.ERROR.value == "error"

    def test_state_count(self):
        """Verify the number of connection states."""
        assert len(ConnectionState) == 5


class TestConnectionType:
    """Tests for the ConnectionType enum."""

    def test_type_values(self):
        """Verify connection type values."""
        assert ConnectionType.CLIENT.value == "client"
        assert ConnectionType.SERVER.value == "server"


class TestConnectionInfo:
    """Tests for the ConnectionInfo data class."""

    def test_creation_with_defaults(self):
        """Verify ConnectionInfo is created with expected defaults."""
        conn = ConnectionInfo()
        assert conn.id is not None
        assert len(conn.id) == 36  # UUID
        assert conn.protocol == ""
        assert conn.state == ConnectionState.CONNECTING
        assert conn.connection_type == ConnectionType.CLIENT
        assert conn.local_address == ""
        assert conn.local_port == 0
        assert conn.remote_address == ""
        assert conn.remote_port == 0
        assert conn.bytes_sent == 0
        assert conn.bytes_received == 0
        assert conn.packets_sent == 0
        assert conn.packets_received == 0
        assert conn.protocol_data == {}
        assert conn.error_message is None
        assert conn.error_code is None

    def test_creation_with_custom_values(self):
        """Verify ConnectionInfo accepts custom values."""
        conn = ConnectionInfo(
            id="custom-id",
            protocol="pptp",
            state=ConnectionState.CONNECTED,
            local_address="10.0.0.1",
            local_port=1723,
            remote_address="192.168.1.1",
            remote_port=54321,
        )
        assert conn.id == "custom-id"
        assert conn.protocol == "pptp"
        assert conn.state == ConnectionState.CONNECTED
        assert conn.local_address == "10.0.0.1"
        assert conn.local_port == 1723

    def test_to_dict(self, sample_connection: ConnectionInfo):
        """Verify to_dict returns correct dictionary."""
        data = sample_connection.to_dict()

        assert data["id"] == "test-conn-001"
        assert data["protocol"] == "pptp"
        assert data["state"] == "connecting"
        assert data["connection_type"] == "client"
        assert data["local_address"] == "127.0.0.1"
        assert data["local_port"] == 1723
        assert data["remote_address"] == "192.168.1.100"
        assert data["remote_port"] == 54321
        assert data["bytes_sent"] == 0
        assert data["bytes_received"] == 0

    def test_to_dict_datetime_serialization(self):
        """Verify datetime fields are serialized to ISO format."""
        conn = ConnectionInfo(
            connected_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        data = conn.to_dict()
        assert data["connected_at"] == "2024-01-01T12:00:00"

    def test_to_dict_none_datetime(self):
        """Verify None datetime fields are serialized as None."""
        conn = ConnectionInfo()
        data = conn.to_dict()
        assert data["connected_at"] is None
        assert data["disconnected_at"] is None

    def test_duration_before_connection(self):
        """Verify duration is None before connection is established."""
        conn = ConnectionInfo()
        assert conn.duration is None

    def test_duration_after_connection(self):
        """Verify duration is calculated after connection is established."""
        conn = ConnectionInfo()
        conn.connected_at = datetime(2024, 1, 1, 12, 0, 0)
        # Duration depends on current time, so just verify it's not None
        assert conn.duration is not None
        assert conn.duration >= 0

    def test_duration_after_disconnection(self):
        """Verify duration is fixed after disconnection."""
        conn = ConnectionInfo()
        conn.connected_at = datetime(2024, 1, 1, 12, 0, 0)
        conn.disconnected_at = datetime(2024, 1, 1, 12, 5, 0)
        assert conn.duration == 300.0  # 5 minutes


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_create_connection(self, connection_manager: ConnectionManager):
        """Verify connection creation."""
        conn = await connection_manager.create_connection("pptp")
        assert conn.protocol == "pptp"
        assert conn.state == ConnectionState.CONNECTING
        assert conn.id is not None

    @pytest.mark.asyncio
    async def test_create_connection_with_kwargs(self, connection_manager: ConnectionManager):
        """Verify connection creation with extra kwargs."""
        conn = await connection_manager.create_connection(
            "l2tp", local_port=1701, remote_address="10.0.0.1"
        )
        assert conn.protocol == "l2tp"
        assert conn.local_port == 1701
        assert conn.remote_address == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_get_connection(self, connection_manager: ConnectionManager):
        """Verify connection retrieval by ID."""
        conn = await connection_manager.create_connection("pptp")
        retrieved = await connection_manager.get_connection(conn.id)
        assert retrieved is conn

    @pytest.mark.asyncio
    async def test_get_nonexistent_connection(self, connection_manager: ConnectionManager):
        """Verify None is returned for nonexistent connection."""
        retrieved = await connection_manager.get_connection("nonexistent-id")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_state(self, connection_manager: ConnectionManager):
        """Verify connection state update."""
        conn = await connection_manager.create_connection("pptp")
        event = await connection_manager.update_state(
            conn.id, ConnectionState.CONNECTED
        )

        assert conn.state == ConnectionState.CONNECTED
        assert conn.connected_at is not None
        assert event.old_state == ConnectionState.CONNECTING
        assert event.new_state == ConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_update_state_to_disconnected(self, connection_manager: ConnectionManager):
        """Verify disconnected_at is set when state changes to DISCONNECTED."""
        conn = await connection_manager.create_connection("pptp")
        await connection_manager.update_state(conn.id, ConnectionState.CONNECTED)
        await connection_manager.update_state(conn.id, ConnectionState.DISCONNECTED)

        assert conn.disconnected_at is not None

    @pytest.mark.asyncio
    async def test_update_state_nonexistent_raises(self, connection_manager: ConnectionManager):
        """Verify updating nonexistent connection raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await connection_manager.update_state("nonexistent", ConnectionState.CONNECTED)

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, connection_manager: ConnectionManager):
        """Verify empty connection list."""
        connections = await connection_manager.list_connections()
        assert connections == []

    @pytest.mark.asyncio
    async def test_list_connections(self, connection_manager: ConnectionManager):
        """Verify listing all connections."""
        await connection_manager.create_connection("pptp")
        await connection_manager.create_connection("l2tp")
        await connection_manager.create_connection("openvpn")

        connections = await connection_manager.list_connections()
        assert len(connections) == 3

    @pytest.mark.asyncio
    async def test_list_connections_by_protocol(self, connection_manager: ConnectionManager):
        """Verify filtering connections by protocol."""
        await connection_manager.create_connection("pptp")
        await connection_manager.create_connection("pptp")
        await connection_manager.create_connection("l2tp")

        pptp_connections = await connection_manager.list_connections(protocol="pptp")
        assert len(pptp_connections) == 2
        assert all(c.protocol == "pptp" for c in pptp_connections)

    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_manager: ConnectionManager):
        """Verify connection removal."""
        conn = await connection_manager.create_connection("pptp")
        result = await connection_manager.remove_connection(conn.id)
        assert result is True

        retrieved = await connection_manager.get_connection(conn.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(self, connection_manager: ConnectionManager):
        """Verify removing nonexistent connection returns False."""
        result = await connection_manager.remove_connection("nonexistent-id")
        assert result is False
