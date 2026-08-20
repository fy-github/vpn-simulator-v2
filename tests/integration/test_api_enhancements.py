"""HTTP integration tests for the F1-F8 + retention API routers.

Covers the 9 feature routers added after Phase 0/1:
impairment, validation, pcap, snmp, routing, grafana, scale, c2, retention.

Uses the FastAPI TestClient against the real application (in-process).
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


class TestImpairmentEndpoints:
    """F1 — time-varying network impairment."""

    def test_list_presets(self, client: TestClient) -> None:
        response = client.get("/api/v1/impairments/presets")
        assert response.status_code == 200
        presets = response.json()
        assert isinstance(presets, list)
        assert len(presets) >= 1

    def test_create_impairment_lifecycle(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/impairments",
            json={
                "fault_type": "latency",
                "param": "delay_ms",
                "change_type": "linear",
                "start_value": 0,
                "end_value": 300,
                "duration_seconds": 60,
            },
        )
        assert response.status_code == 201
        created = response.json()
        assert created["fault_type"] == "latency"
        assert created["change_type"] == "linear"

        impairment_id = created["id"]
        assert client.get(f"/api/v1/impairments/{impairment_id}/status").status_code == 200
        assert client.post(f"/api/v1/impairments/{impairment_id}/start").status_code == 200
        assert client.post(f"/api/v1/impairments/{impairment_id}/stop").status_code == 200

        timeline = client.get(f"/api/v1/impairments/{impairment_id}/timeline").json()
        assert isinstance(timeline, list)
        assert len(timeline) >= 2

        assert client.delete(f"/api/v1/impairments/{impairment_id}").status_code == 200

    def test_create_impairment_invalid_change_type(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/impairments",
            json={
                "fault_type": "latency",
                "param": "delay_ms",
                "change_type": "bogus",
                "start_value": 0,
                "end_value": 100,
                "duration_seconds": 60,
            },
        )
        assert response.status_code == 400

    def test_apply_preset(self, client: TestClient) -> None:
        presets = client.get("/api/v1/impairments/presets").json()
        name = presets[0]["name"]
        response = client.post(f"/api/v1/impairments/presets/{name}/apply")
        assert response.status_code == 201
        assert response.json()["name"] == name


class TestValidationEndpoints:
    """F2 — config validation."""

    def test_validate_wireguard(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/validation/validate",
            json={"protocol": "wireguard", "config": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["protocol"] == "wireguard"
        assert data["status"] in ("pass", "fail")
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) >= 1

    def test_validate_unsupported_protocol(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/validation/validate",
            json={"protocol": "nope", "config": {}},
        )
        assert response.status_code == 400

    def test_history(self, client: TestClient) -> None:
        response = client.get("/api/v1/validation/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_batch(self, client: TestClient) -> None:
        response = client.post("/api/v1/validation/batch", json={})
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) == 9


class TestPcapEndpoints:
    """F3 — PCAP replay."""

    def test_list_files_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/pcap/files")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_upload_invalid_data(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/pcap/upload",
            files={"file": ("bad.pcap", b"not-a-pcap", "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_replay_missing_file(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/pcap/replay",
            json={"file_id": "does-not-exist", "speed": 1.0},
        )
        assert response.status_code == 400

    def test_status_and_stats_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/pcap/status/missing").status_code == 404
        assert client.get("/api/v1/pcap/stats/missing").status_code == 404


class TestSnmpEndpoints:
    """F4 — SNMP device simulation."""

    def test_list_devices(self, client: TestClient) -> None:
        response = client.get("/api/v1/snmp/devices")
        assert response.status_code == 200
        devices = response.json()
        assert isinstance(devices, list)
        assert len(devices) >= 12

    def test_list_oids(self, client: TestClient) -> None:
        response = client.get("/api/v1/snmp/oids")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_oid(self, client: TestClient) -> None:
        devices = client.get("/api/v1/snmp/devices").json()
        device_id = devices[0]["id"]
        response = client.get(
            f"/api/v1/snmp/devices/{device_id}/get",
            params={"oid": "1.3.6.1.2.1.1.5.0", "version": "2c"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["oid"] == "1.3.6.1.2.1.1.5.0"
        assert "value" in data

    def test_walk_oid(self, client: TestClient) -> None:
        devices = client.get("/api/v1/snmp/devices").json()
        device_id = devices[0]["id"]
        response = client.get(
            f"/api/v1/snmp/devices/{device_id}/walk",
            params={"oid": "1.3.6.1.2.1", "version": "2c"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_invalid_oid(self, client: TestClient) -> None:
        devices = client.get("/api/v1/snmp/devices").json()
        device_id = devices[0]["id"]
        response = client.get(
            f"/api/v1/snmp/devices/{device_id}/get",
            params={"oid": "not-an-oid", "version": "2c"},
        )
        assert response.status_code == 404

    def test_get_missing_device(self, client: TestClient) -> None:
        assert client.get("/api/v1/snmp/devices/missing").status_code == 404


class TestRoutingEndpoints:
    """F5 — routing protocol simulation."""

    def test_list_routers(self, client: TestClient) -> None:
        response = client.get("/api/v1/routing/routers")
        assert response.status_code == 200
        routers = response.json()
        assert isinstance(routers, list)
        assert len(routers) == 4

    def test_list_neighbors(self, client: TestClient) -> None:
        response = client.get("/api/v1/routing/r1/neighbors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_establish_neighbor(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/routing/r1/neighbors/r2/establish",
            params={"protocol": "ospf"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "full"

    def test_establish_missing_neighbor(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/routing/r1/neighbors/nope/establish",
            params={"protocol": "ospf"},
        )
        assert response.status_code == 404

    def test_get_routes(self, client: TestClient) -> None:
        response = client.get("/api/v1/routing/r1/routes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestGrafanaEndpoints:
    """F6 — Grafana dashboards / alert rules."""

    def test_list_dashboards(self, client: TestClient) -> None:
        response = client.get("/api/v1/grafana/dashboards")
        assert response.status_code == 200
        dashboards = response.json()
        assert isinstance(dashboards, list)
        assert len(dashboards) >= 1

    def test_get_dashboard_json(self, client: TestClient) -> None:
        dashboards = client.get("/api/v1/grafana/dashboards").json()
        name = dashboards[0]["name"]
        response = client.get(f"/api/v1/grafana/dashboards/{name}")
        assert response.status_code == 200
        assert "title" in response.json()

    def test_get_dashboard_missing(self, client: TestClient) -> None:
        assert client.get("/api/v1/grafana/dashboards/nope").status_code == 404

    def test_list_alert_rules(self, client: TestClient) -> None:
        response = client.get("/api/v1/grafana/alert-rules")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestScaleEndpoints:
    """F7 — large-scale device simulation."""

    def test_stats(self, client: TestClient) -> None:
        response = client.get("/api/v1/scale/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 30000
        assert data["pool_size"] == 1000

    def test_list_devices_paginated(self, client: TestClient) -> None:
        response = client.get("/api/v1/scale/devices", params={"offset": 0, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 30000
        assert data["count"] == 10
        assert len(data["devices"]) == 10

    def test_get_device(self, client: TestClient) -> None:
        response = client.get("/api/v1/scale/devices/0")
        assert response.status_code == 200
        assert response.json()["index"] == 0

    def test_get_device_out_of_range(self, client: TestClient) -> None:
        assert client.get("/api/v1/scale/devices/999999").status_code == 404

    def test_poll(self, client: TestClient) -> None:
        response = client.post("/api/v1/scale/poll", json={"count": 100, "concurrency": 50})
        assert response.status_code == 200
        data = response.json()
        assert data["polled"] == 100
        assert "duration_ms" in data


class TestC2Endpoints:
    """F8 — C2 attack scenarios."""

    def test_list_scenarios(self, client: TestClient) -> None:
        response = client.get("/api/v1/c2/scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 6

    def test_ethics(self, client: TestClient) -> None:
        response = client.get("/api/v1/c2/ethics")
        assert response.status_code == 200
        assert "purpose" in response.json()

    def test_get_scenario(self, client: TestClient) -> None:
        response = client.get("/api/v1/c2/scenarios/dns_c2")
        assert response.status_code == 200
        assert response.json()["channel"] == "dns"

    def test_simulate(self, client: TestClient) -> None:
        response = client.post("/api/v1/c2/scenarios/dns_c2/simulate")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_id"] == "dns_c2"
        assert len(data["steps"]) >= 1

    def test_detection(self, client: TestClient) -> None:
        response = client.get("/api/v1/c2/scenarios/dns_c2/detection")
        assert response.status_code == 200
        assert "indicators" in response.json()

    def test_get_missing_scenario(self, client: TestClient) -> None:
        assert client.get("/api/v1/c2/scenarios/nope").status_code == 404


class TestRetentionEndpoints:
    """Retention policy."""

    def test_status(self, client: TestClient) -> None:
        response = client.get("/api/v1/retention/status")
        assert response.status_code == 200
        data = response.json()
        assert "packets" in data
        assert "state_transitions" in data

    def test_cleanup(self, client: TestClient) -> None:
        response = client.post("/api/v1/retention/cleanup", json={})
        assert response.status_code == 200
        data = response.json()
        assert "deleted_packets" in data
        assert "deleted_state_transitions" in data
        assert "remaining_packets" in data
        assert "remaining_state_transitions" in data
