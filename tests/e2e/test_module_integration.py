"""End-to-end tests for VPN Simulator v2 - module integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vpn_simulator.api.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


class TestModuleIntegration:
    def test_health_endpoint(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_protocols_flow(self, client: TestClient):
        r = client.get("/api/v1/protocols")
        assert r.status_code == 200

    def test_connections_flow(self, client: TestClient):
        r = client.get("/api/v1/connections")
        assert r.status_code == 200

    def test_faults_flow(self, client: TestClient):
        r = client.get("/api/v1/faults")
        assert r.status_code == 200

    def test_attacks_flow(self, client: TestClient):
        r = client.get("/api/v1/attacks")
        assert r.status_code == 200

    def test_dpi_protocols(self, client: TestClient):
        r = client.get("/api/v1/dpi/protocols")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_iot_devices(self, client: TestClient):
        r = client.get("/api/v1/iot/devices")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_voice_codecs(self, client: TestClient):
        r = client.get("/api/v1/voice/codecs")
        assert r.status_code == 200

    def test_obfuscation_techniques(self, client: TestClient):
        r = client.get("/api/v1/obfuscation/techniques")
        assert r.status_code == 200

    def test_metrics_throughput(self, client: TestClient):
        r = client.get("/api/v1/metrics/throughput")
        assert r.status_code == 200

    def test_traffic_status(self, client: TestClient):
        r = client.get("/api/v1/traffic/status")
        assert r.status_code == 200

    def test_learning_rfc(self, client: TestClient):
        r = client.get("/api/v1/learning/rfc")
        assert r.status_code == 200

    def test_tutorials_list(self, client: TestClient):
        r = client.get("/api/v1/tutorials")
        assert r.status_code == 200

    def test_scenarios_list(self, client: TestClient):
        r = client.get("/api/v1/scenarios")
        assert r.status_code == 200

    def test_vendor_cli_vendors(self, client: TestClient):
        r = client.get("/api/v1/vendor-cli/vendors")
        assert r.status_code == 200

    def test_packets_list(self, client: TestClient):
        r = client.get("/api/v1/packets")
        assert r.status_code == 200

    def test_stats(self, client: TestClient):
        r = client.get("/api/v1/stats")
        assert r.status_code == 200

    def test_logs(self, client: TestClient):
        r = client.get("/api/v1/logs")
        assert r.status_code == 200

    def test_config(self, client: TestClient):
        r = client.get("/api/v1/config")
        assert r.status_code == 200

    def test_topology(self, client: TestClient):
        r = client.get("/api/v1/topology/topology")
        assert r.status_code == 200
