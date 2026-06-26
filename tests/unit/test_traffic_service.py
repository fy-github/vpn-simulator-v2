"""Tests for TrafficService - traffic capture and simulation service."""

from __future__ import annotations

import pytest

from vpn_simulator.services.traffic import (
    Packet,
    Protocol,
    TrafficService,
    TrafficStats,
)


@pytest.fixture
def service() -> TrafficService:
    return TrafficService()


class TestTrafficServiceInit:
    def test_service_creation(self, service: TrafficService):
        assert service is not None
        assert service._capturing is False
        assert len(service._packets) == 0


class TestStartCapture:
    @pytest.mark.asyncio
    async def test_start_capture(self, service: TrafficService):
        result = await service.start_capture()
        assert result["status"] == "started"
        assert service._capturing is True
        await service.stop_capture()

    @pytest.mark.asyncio
    async def test_start_capture_already_capturing(self, service: TrafficService):
        await service.start_capture()
        result = await service.start_capture()
        assert result["status"] == "already_capturing"
        await service.stop_capture()

    @pytest.mark.asyncio
    async def test_start_capture_with_protocols(self, service: TrafficService):
        result = await service.start_capture(protocols=["tcp", "udp"])
        assert result["status"] == "started"
        assert service._protocol_filter is not None
        await service.stop_capture()

    @pytest.mark.asyncio
    async def test_start_capture_resets_state(self, service: TrafficService):
        await service.start_capture()
        await service.stop_capture()
        await service.start_capture()
        assert len(service._packets) == 0
        await service.stop_capture()


class TestStopCapture:
    @pytest.mark.asyncio
    async def test_stop_capture(self, service: TrafficService):
        await service.start_capture()
        result = await service.stop_capture()
        assert result["status"] == "stopped"
        assert service._capturing is False

    @pytest.mark.asyncio
    async def test_stop_capture_not_capturing(self, service: TrafficService):
        result = await service.stop_capture()
        assert result["status"] == "not_capturing"

    @pytest.mark.asyncio
    async def test_stop_capture_returns_stats(self, service: TrafficService):
        await service.start_capture()
        result = await service.stop_capture()
        assert "statistics" in result
        assert "total_packets" in result["statistics"]


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_not_capturing(self, service: TrafficService):
        assert service.is_capturing is False
        assert service.packet_count == 0

    @pytest.mark.asyncio
    async def test_get_status_capturing(self, service: TrafficService):
        await service.start_capture()
        assert service.is_capturing is True
        await service.stop_capture()


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, service: TrafficService):
        stats = service.get_statistics()
        assert "capturing" in stats
        assert "statistics" in stats
        assert stats["statistics"]["total_packets"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_data(self, service: TrafficService):
        await service.start_capture()
        await asyncio.sleep(0.5)
        await service.stop_capture()
        stats = service.get_statistics()
        assert stats["statistics"]["total_packets"] > 0


class TestGetRecentPackets:
    @pytest.mark.asyncio
    async def test_get_recent_packets_empty(self, service: TrafficService):
        packets = service.get_recent_packets()
        assert len(packets) == 0

    @pytest.mark.asyncio
    async def test_get_recent_packets_with_data(self, service: TrafficService):
        await service.start_capture()
        await asyncio.sleep(0.5)
        await service.stop_capture()
        packets = service.get_recent_packets()
        assert len(packets) > 0

    @pytest.mark.asyncio
    async def test_get_recent_packets_with_limit(self, service: TrafficService):
        await service.start_capture()
        await asyncio.sleep(1)
        await service.stop_capture()
        packets = service.get_recent_packets(limit=5)
        assert len(packets) <= 5


class TestPacketGeneration:
    def test_generate_packet(self, service: TrafficService):
        packet = service._generate_packet()
        assert packet is not None
        assert packet.protocol in [Protocol.TCP, Protocol.UDP, Protocol.ICMP, Protocol.ARP]
        assert packet.size > 0
        assert packet.src_ip != ""
        assert packet.dst_ip != ""

    def test_generate_packet_structure(self, service: TrafficService):
        packet = service._generate_packet()
        packet_dict = packet.to_dict()
        assert "id" in packet_dict
        assert "timestamp" in packet_dict
        assert "protocol" in packet_dict
        assert "src_ip" in packet_dict
        assert "dst_ip" in packet_dict

    def test_generate_random_ip(self, service: TrafficService):
        ip = service._generate_random_ip()
        assert ip.startswith(("192.168.1.", "10.0.0.", "172.16.0.", "100.64.0."))


class TestProtocolFilter:
    @pytest.mark.asyncio
    async def test_protocol_filter_tcp(self, service: TrafficService):
        await service.start_capture(protocols=["tcp"])
        await asyncio.sleep(0.5)
        await service.stop_capture()
        packets = service.get_recent_packets()
        for p in packets:
            assert p["protocol"] == "tcp"

    @pytest.mark.asyncio
    async def test_protocol_filter_udp(self, service: TrafficService):
        await service.start_capture(protocols=["udp"])
        await asyncio.sleep(0.5)
        await service.stop_capture()
        packets = service.get_recent_packets()
        for p in packets:
            assert p["protocol"] == "udp"


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_start_stop(self, service: TrafficService):
        for _ in range(3):
            await service.start_capture()
            await asyncio.sleep(0.1)
            await service.stop_capture()

    @pytest.mark.asyncio
    async def test_packet_buffer_limit(self, service: TrafficService):
        await service.start_capture()
        await asyncio.sleep(2)
        await service.stop_capture()
        assert len(service._recent_packets) <= service._max_recent_packets

    def test_packet_to_dict(self, service: TrafficService):
        packet = Packet(
            protocol=Protocol.TCP,
            src_ip="192.168.1.1",
            dst_ip="10.0.0.1",
            src_port=80,
            dst_port=12345,
            size=128,
        )
        d = packet.to_dict()
        assert d["protocol"] == "tcp"
        assert d["src_ip"] == "192.168.1.1"
        assert d["size"] == 128


import asyncio
