"""Integration tests for API routers - comprehensive coverage."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vpn_simulator.api.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


class TestTrafficEndpoints:
    def test_get_status(self, client: TestClient):
        response = client.get("/api/v1/traffic/status")
        assert response.status_code == 200
        data = response.json()
        assert "capturing" in data
        assert "packet_count" in data

    def test_get_statistics(self, client: TestClient):
        response = client.get("/api/v1/traffic/statistics")
        assert response.status_code == 200

    def test_get_packets(self, client: TestClient):
        response = client.get("/api/v1/traffic/packets")
        assert response.status_code == 200
        data = response.json()
        assert "packets" in data
        assert "count" in data

    def test_start_capture(self, client: TestClient):
        response = client.post("/api/v1/traffic/capture", json={})
        assert response.status_code == 200

    def test_stop_capture(self, client: TestClient):
        response = client.post("/api/v1/traffic/stop")
        assert response.status_code == 200


class TestMetricsEndpoints:
    def test_throughput(self, client: TestClient):
        response = client.get("/api/v1/metrics/throughput")
        assert response.status_code == 200
        data = response.json()
        assert "timestamps" in data
        assert "values" in data

    def test_latency(self, client: TestClient):
        response = client.get("/api/v1/metrics/latency")
        assert response.status_code == 200

    def test_packet_loss(self, client: TestClient):
        response = client.get("/api/v1/metrics/packet-loss")
        assert response.status_code == 200

    def test_connections(self, client: TestClient):
        response = client.get("/api/v1/metrics/connections")
        assert response.status_code == 200

    def test_distribution(self, client: TestClient):
        response = client.get("/api/v1/metrics/distribution")
        assert response.status_code == 200

    def test_statistics(self, client: TestClient):
        response = client.get("/api/v1/metrics/statistics")
        assert response.status_code == 200


class TestPacketsEndpoints:
    def test_list_packets(self, client: TestClient):
        response = client.get("/api/v1/packets")
        assert response.status_code == 200

    def test_search_packets(self, client: TestClient):
        response = client.get("/api/v1/packets/search?query=test")
        assert response.status_code == 200

    def test_statistics(self, client: TestClient):
        response = client.get("/api/v1/packets/statistics")
        assert response.status_code == 200

    def test_protocols(self, client: TestClient):
        response = client.get("/api/v1/packets/protocols")
        assert response.status_code == 200

    def test_generate_samples(self, client: TestClient):
        response = client.post("/api/v1/packets/samples")
        assert response.status_code == 200

    def test_clear(self, client: TestClient):
        response = client.delete("/api/v1/packets")
        assert response.status_code == 200


class TestIoTEndpoints:
    def test_list_devices(self, client: TestClient):
        response = client.get("/api/v1/iot/devices")
        assert response.status_code == 200

    def test_traffic_patterns(self, client: TestClient):
        response = client.get("/api/v1/iot/traffic-patterns")
        assert response.status_code == 200

    def test_categories(self, client: TestClient):
        response = client.get("/api/v1/iot/categories")
        assert response.status_code == 200


class TestVoiceEndpoints:
    def test_codecs(self, client: TestClient):
        response = client.get("/api/v1/voice/codecs")
        assert response.status_code == 200
        data = response.json()
        assert "codecs" in data
        assert "count" in data

    def test_statistics(self, client: TestClient):
        response = client.get("/api/v1/voice/statistics")
        assert response.status_code == 200

    def test_calls(self, client: TestClient):
        response = client.get("/api/v1/voice/calls")
        assert response.status_code == 200


class TestVendorCLIEndpoints:
    def test_supported_vendors(self, client: TestClient):
        response = client.get("/api/v1/vendor-cli/vendors")
        assert response.status_code == 200

    def test_commands(self, client: TestClient):
        response = client.get("/api/v1/vendor-cli/commands?vendor=cisco")
        assert response.status_code == 200


class TestDPIEndpoints:
    def test_protocols(self, client: TestClient):
        response = client.get("/api/v1/dpi/protocols")
        assert response.status_code == 200

    def test_statistics(self, client: TestClient):
        response = client.get("/api/v1/dpi/statistics")
        assert response.status_code == 200

    def test_classification(self, client: TestClient):
        response = client.get("/api/v1/dpi/classification")
        assert response.status_code == 200

    def test_distribution(self, client: TestClient):
        response = client.get("/api/v1/dpi/distribution")
        assert response.status_code == 200

    def test_anomalies(self, client: TestClient):
        response = client.get("/api/v1/dpi/anomalies")
        assert response.status_code == 200

    def test_results(self, client: TestClient):
        response = client.get("/api/v1/dpi/results")
        assert response.status_code == 200

    def test_generate_samples(self, client: TestClient):
        response = client.post("/api/v1/dpi/samples")
        assert response.status_code == 200

    def test_clear(self, client: TestClient):
        response = client.delete("/api/v1/dpi")
        assert response.status_code == 200


class TestObfuscationEndpoints:
    def test_techniques(self, client: TestClient):
        response = client.get("/api/v1/obfuscation/techniques")
        assert response.status_code == 200

    def test_results(self, client: TestClient):
        response = client.get("/api/v1/obfuscation/results")
        assert response.status_code == 200

    def test_comparison(self, client: TestClient):
        response = client.get("/api/v1/obfuscation/comparison")
        assert response.status_code == 200

    def test_clear(self, client: TestClient):
        response = client.delete("/api/v1/obfuscation")
        assert response.status_code == 200


class TestLearningEndpoints:
    def test_rfc(self, client: TestClient):
        response = client.get("/api/v1/learning/rfc")
        assert response.status_code == 200

    def test_faq(self, client: TestClient):
        response = client.get("/api/v1/learning/faq")
        assert response.status_code == 200

    def test_faq_categories(self, client: TestClient):
        response = client.get("/api/v1/learning/faq/categories")
        assert response.status_code == 200

    def test_paths(self, client: TestClient):
        response = client.get("/api/v1/learning/paths")
        assert response.status_code == 200


class TestTutorialsEndpoints:
    def test_list_tutorials(self, client: TestClient):
        response = client.get("/api/v1/tutorials")
        assert response.status_code == 200


class TestScenariosEndpoints:
    def test_list_scenarios(self, client: TestClient):
        response = client.get("/api/v1/scenarios")
        assert response.status_code == 200


class TestComparisonEndpoints:
    def test_protocols(self, client: TestClient):
        response = client.get("/api/v1/compare/protocols")
        assert response.status_code == 200

    def test_compare(self, client: TestClient):
        response = client.get("/api/v1/compare?protocol1=pptp&protocol2=l2tp")
        assert response.status_code == 200


class TestBenchmarkEndpoints:
    def test_results(self, client: TestClient):
        response = client.get("/api/v1/benchmark/results")
        assert response.status_code == 200


class TestConfigEndpoints:
    def test_get_config(self, client: TestClient):
        response = client.get("/api/v1/config")
        assert response.status_code == 200


class TestStatsEndpoints:
    def test_get_stats(self, client: TestClient):
        response = client.get("/api/v1/stats")
        assert response.status_code == 200


class TestLogsEndpoints:
    def test_get_logs(self, client: TestClient):
        response = client.get("/api/v1/logs")
        assert response.status_code == 200


class TestTopologyEndpoints:
    def test_get_topology(self, client: TestClient):
        response = client.get("/api/v1/topology/topology")
        assert response.status_code == 200
