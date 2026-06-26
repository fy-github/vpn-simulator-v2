"""Integration tests for the FastAPI API endpoints.

Tests cover:
- Health check endpoint
- Protocol management endpoints
- Connection management endpoints
- Fault injection endpoints
- Attack management endpoints
- Request/response models
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vpn_simulator.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Verify health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"


class TestProtocolEndpoints:
    """Tests for protocol management endpoints."""

    def test_list_protocols(self, client: TestClient):
        """Verify listing protocols returns a list."""
        response = client.get("/api/v1/protocols")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_start_protocol(self, client: TestClient):
        """Verify starting a protocol."""
        response = client.post(
            "/api/v1/protocols/pptp/start",
            json={"port": 1723, "config": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pptp"
        assert data["status"] == "started"

    def test_stop_protocol(self, client: TestClient):
        """Verify stopping a protocol."""
        response = client.post("/api/v1/protocols/pptp/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pptp"
        assert data["status"] == "stopped"

    def test_get_protocol_status(self, client: TestClient):
        """Verify getting protocol status."""
        response = client.get("/api/v1/protocols/pptp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "pptp"
        assert "state" in data
        assert "port" in data
        assert "connections" in data


class TestConnectionEndpoints:
    """Tests for connection management endpoints."""

    def test_list_connections(self, client: TestClient):
        """Verify listing connections returns a list."""
        response = client.get("/api/v1/connections")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_connections_with_filter(self, client: TestClient):
        """Verify listing connections with protocol filter."""
        response = client.get("/api/v1/connections?protocol=pptp")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_connection(self, client: TestClient):
        """Verify getting nonexistent connection returns 404."""
        response = client.get("/api/v1/connections/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_disconnect_connection(self, client: TestClient):
        """Verify disconnecting a connection."""
        response = client.delete("/api/v1/connections/test-conn-001")
        assert response.status_code == 200
        data = response.json()
        assert data["connection_id"] == "test-conn-001"
        assert data["status"] == "disconnected"


class TestFaultEndpoints:
    """Tests for fault injection endpoints."""

    def test_list_faults(self, client: TestClient):
        """Verify listing faults returns a list."""
        response = client.get("/api/v1/faults")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_fault(self, client: TestClient):
        """Verify adding a fault injection."""
        response = client.post(
            "/api/v1/faults",
            json={
                "type": "latency",
                "params": {"delay_ms": 100},
                "target": "pptp",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "latency"
        assert data["params"] == {"delay_ms": 100}
        assert data["active"] is True

    def test_add_fault_invalid_type(self, client: TestClient):
        """Verify adding fault with invalid type fails validation."""
        response = client.post(
            "/api/v1/faults",
            json={"type": "invalid_type", "params": {}},
        )
        assert response.status_code == 422

    def test_remove_fault(self, client: TestClient):
        """Verify removing a fault injection."""
        response = client.delete("/api/v1/faults/fault-001")
        assert response.status_code == 200
        data = response.json()
        assert data["fault_id"] == "fault-001"
        assert data["status"] == "removed"


class TestAttackEndpoints:
    """Tests for attack management endpoints."""

    def test_list_attacks(self, client: TestClient):
        """Verify listing attacks returns a list."""
        response = client.get("/api/v1/attacks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_start_attack(self, client: TestClient):
        """Verify starting an attack with invalid service call returns error."""
        response = client.post(
            "/api/v1/attacks",
            json={
                "type": "mitm",
                "target": "pptp",
                "params": {"proxy_port": 8888},
            },
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_start_attack_invalid_type(self, client: TestClient):
        """Verify starting attack with invalid type fails validation."""
        response = client.post(
            "/api/v1/attacks",
            json={"type": "invalid_attack", "target": "pptp"},
        )
        assert response.status_code == 422

    def test_stop_attack(self, client: TestClient):
        """Verify stopping a non-existent attack returns error."""
        response = client.delete("/api/v1/attacks/attack-001")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAPIModels:
    """Tests for API request/response models."""

    def test_protocol_info_model(self):
        """Verify ProtocolInfo model structure."""
        from vpn_simulator.api.routers.protocols import ProtocolInfo

        info = ProtocolInfo(name="pptp", state="running", port=1723, connections=5)
        assert info.name == "pptp"
        assert info.state == "running"
        assert info.port == 1723
        assert info.connections == 5

    def test_connection_info_model(self):
        """Verify ConnectionInfo model structure."""
        from vpn_simulator.api.routers.connections import ConnectionInfo

        info = ConnectionInfo(
            id="conn-001",
            protocol="pptp",
            state="connected",
            local_address="127.0.0.1",
            local_port=1723,
        )
        assert info.id == "conn-001"
        assert info.protocol == "pptp"

    def test_fault_info_model(self):
        """Verify FaultInfo model structure."""
        from vpn_simulator.api.routers.faults import FaultInfo

        info = FaultInfo(
            id="fault-001",
            type="latency",
            params={"delay_ms": 100},
            target="pptp",
            active=True,
        )
        assert info.id == "fault-001"
        assert info.type == "latency"

    def test_attack_info_model(self):
        """Verify AttackInfo model structure."""
        from vpn_simulator.api.routers.attacks import AttackInfo

        info = AttackInfo(
            id="atk-001",
            type="mitm",
            status="running",
            target="pptp",
        )
        assert info.id == "atk-001"
        assert info.type == "mitm"
