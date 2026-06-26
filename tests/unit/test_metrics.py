"""Tests for MetricsService - performance metrics collection."""

from __future__ import annotations

import pytest

from vpn_simulator.services.metrics import MetricsService


@pytest.fixture
def service() -> MetricsService:
    return MetricsService()


class TestMetricsServiceInit:
    def test_service_creation(self, service: MetricsService):
        assert service is not None
        assert hasattr(service, "_start_time")
        assert service._start_time > 0


class TestThroughputData:
    def test_default_throughput(self, service: MetricsService):
        result = service.get_throughput_data()
        assert "timestamps" in result
        assert "values" in result
        assert result["unit"] == "Mbps"
        assert result["time_range"] == "5m"
        assert result["protocol"] == "all"
        assert len(result["timestamps"]) == len(result["values"])
        assert len(result["values"]) > 0

    def test_throughput_1m_range(self, service: MetricsService):
        result = service.get_throughput_data(time_range="1m")
        assert result["time_range"] == "1m"
        assert len(result["values"]) == 30

    def test_throughput_15m_range(self, service: MetricsService):
        result = service.get_throughput_data(time_range="15m")
        assert result["time_range"] == "15m"
        assert len(result["values"]) == 60

    def test_throughput_1h_range(self, service: MetricsService):
        result = service.get_throughput_data(time_range="1h")
        assert result["time_range"] == "1h"
        assert len(result["values"]) == 60

    def test_throughput_invalid_range_defaults_5m(self, service: MetricsService):
        result = service.get_throughput_data(time_range="invalid")
        assert result["time_range"] == "invalid"
        assert len(result["values"]) == 60

    def test_throughput_specific_protocol(self, service: MetricsService):
        result = service.get_throughput_data(protocol="wireguard")
        assert result["protocol"] == "wireguard"
        assert len(result["values"]) > 0
        for val in result["values"]:
            assert val >= 0

    def test_throughput_unknown_protocol_aggregates(self, service: MetricsService):
        result = service.get_throughput_data(protocol="unknown")
        assert result["protocol"] == "unknown"
        assert len(result["values"]) > 0

    def test_throughput_all_protocols(self, service: MetricsService):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            result = service.get_throughput_data(protocol=proto)
            assert result["protocol"] == proto
            assert len(result["values"]) > 0

    def test_throughput_values_non_negative(self, service: MetricsService):
        result = service.get_throughput_data()
        for val in result["values"]:
            assert val >= 0


class TestLatencyData:
    def test_default_latency(self, service: MetricsService):
        result = service.get_latency_data()
        assert "timestamps" in result
        assert "values" in result
        assert "min_values" in result
        assert "max_values" in result
        assert result["unit"] == "ms"
        assert result["time_range"] == "5m"
        assert result["protocol"] == "all"

    def test_latency_specific_protocol(self, service: MetricsService):
        result = service.get_latency_data(protocol="wireguard")
        assert result["protocol"] == "wireguard"
        for val in result["values"]:
            assert val >= 1.0

    def test_latency_min_leq_avg_leq_max(self, service: MetricsService):
        result = service.get_latency_data()
        for mn, avg, mx in zip(result["min_values"], result["values"], result["max_values"]):
            assert mn <= avg or abs(mn - avg) < 0.1
            assert avg <= mx or abs(avg - mx) < 0.1

    def test_latency_values_positive(self, service: MetricsService):
        result = service.get_latency_data()
        for val in result["values"]:
            assert val >= 1.0


class TestPacketLossData:
    def test_default_packet_loss(self, service: MetricsService):
        result = service.get_packet_loss_data()
        assert "timestamps" in result
        assert "values" in result
        assert result["unit"] == "%"
        assert result["time_range"] == "5m"
        assert result["protocol"] == "all"

    def test_packet_loss_specific_protocol(self, service: MetricsService):
        result = service.get_packet_loss_data(protocol="ipsec")
        assert result["protocol"] == "ipsec"
        for val in result["values"]:
            assert 0.0 <= val <= 100.0

    def test_packet_loss_bounds(self, service: MetricsService):
        result = service.get_packet_loss_data()
        for val in result["values"]:
            assert 0.0 <= val <= 100.0

    def test_packet_loss_all_protocols(self, service: MetricsService):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            result = service.get_packet_loss_data(protocol=proto)
            assert result["protocol"] == proto


class TestConnectionsData:
    def test_default_connections(self, service: MetricsService):
        result = service.get_connections_data()
        assert "timestamps" in result
        assert "total" in result
        assert "protocols" in result
        assert result["unit"] == "connections"
        assert result["time_range"] == "5m"

    def test_connections_has_all_protocols(self, service: MetricsService):
        result = service.get_connections_data()
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            assert proto in result["protocols"]

    def test_connections_total_equals_sum(self, service: MetricsService):
        result = service.get_connections_data()
        for i in range(len(result["total"])):
            proto_sum = sum(result["protocols"][p][i] for p in result["protocols"])
            assert result["total"][i] == proto_sum

    def test_connections_non_negative(self, service: MetricsService):
        result = service.get_connections_data()
        for val in result["total"]:
            assert val >= 0


class TestProtocolDistribution:
    def test_distribution_structure(self, service: MetricsService):
        result = service.get_protocol_distribution()
        assert "protocols" in result
        assert "counts" in result
        assert "percentages" in result
        assert "total" in result

    def test_distribution_has_all_protocols(self, service: MetricsService):
        result = service.get_protocol_distribution()
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            assert proto in result["protocols"]

    def test_distribution_percentages_sum_to_100(self, service: MetricsService):
        result = service.get_protocol_distribution()
        total_pct = sum(result["percentages"])
        assert abs(total_pct - 100.0) < 0.5

    def test_distribution_counts_non_negative(self, service: MetricsService):
        result = service.get_protocol_distribution()
        for count in result["counts"]:
            assert count >= 0


class TestStatistics:
    def test_statistics_structure(self, service: MetricsService):
        result = service.get_statistics()
        assert "throughput" in result
        assert "latency" in result
        assert "packet_loss" in result
        assert "connections" in result
        assert "time_range" in result
        assert "protocol" in result
        assert "data_points" in result

    def test_statistics_has_stats_fields(self, service: MetricsService):
        result = service.get_statistics()
        for metric in ["throughput", "latency", "packet_loss"]:
            stats = result[metric]["stats"]
            for field in ["min", "max", "avg", "p50", "p95", "p99"]:
                assert field in stats

    def test_statistics_connections_fields(self, service: MetricsService):
        result = service.get_statistics()
        conn = result["connections"]
        assert "current" in conn
        assert "peak" in conn
        assert "average" in conn

    def test_statistics_specific_protocol(self, service: MetricsService):
        result = service.get_statistics(protocol="wireguard")
        assert result["protocol"] == "wireguard"

    def test_statistics_data_points_positive(self, service: MetricsService):
        result = service.get_statistics()
        assert result["data_points"] > 0
