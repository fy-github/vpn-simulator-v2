"""Tests for DPIService - deep packet inspection service."""

from __future__ import annotations

import pytest

from vpn_simulator.services.dpi import (
    AnomalyDetection,
    DPIResult,
    DPIService,
    ProtocolCategory,
    ProtocolFingerprint,
    ProtocolStatistics,
    ThreatLevel,
)


@pytest.fixture
def service() -> DPIService:
    return DPIService()


class TestDPIServiceInit:
    def test_service_creation(self, service: DPIService):
        assert service is not None
        assert len(service._fingerprints) > 0
        assert len(service._results) == 0

    def test_loads_fingerprints(self, service: DPIService):
        protocols = service.get_supported_protocols()
        assert len(protocols) > 0
        assert any(p["name"] == "HTTP" for p in protocols)
        assert any(p["name"] == "HTTPS" for p in protocols)
        assert any(p["name"] == "DNS" for p in protocols)


class TestGetSupportedProtocols:
    def test_returns_list(self, service: DPIService):
        protocols = service.get_supported_protocols()
        assert isinstance(protocols, list)

    def test_protocol_structure(self, service: DPIService):
        protocols = service.get_supported_protocols()
        proto = protocols[0]
        assert "name" in proto
        assert "category" in proto
        assert "default_ports" in proto
        assert "description" in proto
        assert "threat_level" in proto
        assert "is_encrypted" in proto

    def test_categories_present(self, service: DPIService):
        protocols = service.get_supported_protocols()
        categories = {p["category"] for p in protocols}
        assert "application" in categories
        assert "vpn" in categories


class TestAnalyzePacket:
    def test_analyze_http(self, service: DPIService):
        payload = b"GET / HTTP/1.1\r\nHost: example.com\r\n"
        result = service.analyze_packet(payload, dst_port=80)
        assert result.protocol == "HTTP"
        assert result.category == ProtocolCategory.APPLICATION

    def test_analyze_port_match(self, service: DPIService):
        result = service.analyze_packet(b"test", src_port=54321, dst_port=443)
        assert result.protocol is not None
        assert result.src_port == 54321
        assert result.dst_port == 443
        assert result.confidence > 0

    def test_analyze_dns(self, service: DPIService):
        payload = b"\x00" * 28
        result = service.analyze_packet(payload, dst_port=53)
        assert result.protocol == "DNS"

    def test_analyze_unknown(self, service: DPIService):
        payload = b"\x00" * 10
        result = service.analyze_packet(payload, src_port=12345, dst_port=54321)
        assert result.protocol == "Unknown"
        assert result.confidence < 0.1

    def test_analyze_with_ips(self, service: DPIService):
        payload = b"GET / HTTP/1.1\r\n"
        result = service.analyze_packet(
            payload,
            src_ip="192.168.1.1",
            dst_ip="10.0.0.1",
            dst_port=80,
        )
        assert result.src_ip == "192.168.1.1"
        assert result.dst_ip == "10.0.0.1"

    def test_analyze_result_structure(self, service: DPIService):
        result = service.analyze_packet(b"test", dst_port=80)
        d = result.to_dict()
        assert "id" in d
        assert "timestamp" in d
        assert "protocol" in d
        assert "confidence" in d
        assert "category" in d
        assert "threat_level" in d

    def test_analyze_updates_statistics(self, service: DPIService):
        service.analyze_packet(b"test", dst_port=80)
        stats = service.get_statistics()
        assert stats["total_packets"] == 1

    def test_analyze_stores_results(self, service: DPIService):
        service.analyze_packet(b"test", dst_port=80)
        results = service.get_recent_results()
        assert len(results) == 1


class TestGetStatistics:
    def test_statistics_empty(self, service: DPIService):
        stats = service.get_statistics()
        assert stats["total_packets"] == 0
        assert stats["total_bytes"] == 0

    def test_statistics_after_analysis(self, service: DPIService):
        service.analyze_packet(b"GET / HTTP/1.1", dst_port=80)
        service.analyze_packet(b"\x16\x03\x01", dst_port=443)
        stats = service.get_statistics()
        assert stats["total_packets"] == 2
        assert stats["total_bytes"] > 0
        assert "protocol_counts" in stats
        assert "category_counts" in stats

    def test_statistics_structure(self, service: DPIService):
        stats = service.get_statistics()
        assert "total_packets" in stats
        assert "protocol_counts" in stats
        assert "category_counts" in stats
        assert "threat_counts" in stats
        assert "avg_confidence" in stats
        assert "anomaly_count" in stats


class TestGetTrafficClassification:
    def test_classification_empty(self, service: DPIService):
        classification = service.get_traffic_classification()
        assert isinstance(classification, list)
        assert len(classification) == 0

    def test_classification_with_data(self, service: DPIService):
        service.analyze_packet(b"GET /", dst_port=80)
        service.analyze_packet(b"\x16\x03\x01", dst_port=443)
        classification = service.get_traffic_classification()
        assert len(classification) > 0


class TestGetAnomalies:
    def test_anomalies_empty(self, service: DPIService):
        anomalies = service.get_anomalies()
        assert isinstance(anomalies, list)

    def test_anomalies_after_analysis(self, service: DPIService):
        service.analyze_packet(b"test", dst_port=80)
        anomalies = service.get_anomalies()
        assert isinstance(anomalies, list)


class TestGetProtocolDistribution:
    def test_distribution_empty(self, service: DPIService):
        dist = service.get_protocol_distribution()
        assert dist["total"] == 0
        assert isinstance(dist["protocols"], list)

    def test_distribution_with_data(self, service: DPIService):
        service.analyze_packet(b"GET /", dst_port=80)
        service.analyze_packet(b"\x16\x03\x01", dst_port=443)
        dist = service.get_protocol_distribution()
        assert dist["total"] > 0
        assert len(dist["protocols"]) > 0


class TestGetRecentResults:
    def test_results_empty(self, service: DPIService):
        results = service.get_recent_results()
        assert len(results) == 0

    def test_results_with_data(self, service: DPIService):
        service.analyze_packet(b"test", dst_port=80)
        results = service.get_recent_results()
        assert len(results) == 1

    def test_results_with_limit(self, service: DPIService):
        for _ in range(10):
            service.analyze_packet(b"test", dst_port=80)
        results = service.get_recent_results(limit=5)
        assert len(results) == 5


class TestGenerateSampleTraffic:
    def test_generate_samples(self, service: DPIService):
        samples = service.generate_sample_traffic(count=10)
        assert len(samples) == 10
        assert all(isinstance(s, dict) for s in samples)

    def test_sample_structure(self, service: DPIService):
        samples = service.generate_sample_traffic(count=1)
        sample = samples[0]
        assert "protocol" in sample
        assert "confidence" in sample


class TestClear:
    def test_clear(self, service: DPIService):
        service.analyze_packet(b"test", dst_port=80)
        assert len(service._results) > 0
        service.clear()
        assert len(service._results) == 0
        stats = service.get_statistics()
        assert stats["total_packets"] == 0


class TestEdgeCases:
    def test_multiple_analyses(self, service: DPIService):
        for port in [80, 443, 53, 22, 1194]:
            service.analyze_packet(b"test", dst_port=port)
        stats = service.get_statistics()
        assert stats["total_packets"] == 5

    def test_empty_payload(self, service: DPIService):
        result = service.analyze_packet(b"", dst_port=80)
        assert result.protocol is not None

    def test_large_payload(self, service: DPIService):
        payload = b"\x00" * 10000
        result = service.analyze_packet(payload, dst_port=80)
        assert result.payload_size == 10000

    def test_confidence_range(self, service: DPIService):
        for _ in range(100):
            result = service.analyze_packet(b"test", dst_port=80)
            assert 0.0 <= result.confidence <= 1.0
