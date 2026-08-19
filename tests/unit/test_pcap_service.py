"""Tests for PcapService - PCAP replay (F3)."""

from __future__ import annotations

import os
import tempfile

import pytest
from scapy.all import ICMP, IP, TCP, UDP, wrpcap
from vpn_simulator.core.config import ConfigManager
from vpn_simulator.services.pcap import PcapService
from vpn_simulator.services.traffic import get_traffic_service


def _make_pcap_bytes() -> bytes:
    """生成含 udp/tcp/icmp 三报文、时间跨度 1 秒的 PCAP。"""
    pkts = [
        IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=1234, dport=53) / b"AAAA",
        IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=5000, dport=80) / b"BBBB",
        IP(src="10.0.0.1", dst="10.0.0.2") / ICMP() / b"CCCC",
    ]
    pkts[0].time = 100.0
    pkts[1].time = 100.5
    pkts[2].time = 101.0

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcap")
    try:
        wrpcap(tmp.name, pkts)
        tmp.close()
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)


class TestUpload:
    @pytest.mark.asyncio
    async def test_upload_parses_pcap(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")
        assert info.packet_count == 3
        assert set(info.protocols) == {"udp", "tcp", "icmp"}
        assert info.duration_seconds == pytest.approx(1.0, abs=0.05)
        assert info.size_bytes > 0

    @pytest.mark.asyncio
    async def test_upload_invalid_data_raises(self):
        service = PcapService(ConfigManager())
        with pytest.raises(ValueError):
            await service.upload(b"not a pcap file", "bad.pcap")

    @pytest.mark.asyncio
    async def test_stats_by_protocol(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")
        stats = service.stats(info.id)
        assert stats is not None
        assert stats["by_protocol"] == {"udp": 1, "tcp": 1, "icmp": 1}


class TestReplay:
    @pytest.mark.asyncio
    async def test_replay_injects_into_traffic(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")
        traffic = get_traffic_service()
        before = traffic.packet_count

        session = await service.start_replay(info.id, speed=10.0)
        await service.wait_for_completion(session.id)
        status = service.status(session.id)

        assert status is not None
        assert status["status"] == "completed"
        assert status["packets_replayed"] == 3
        assert traffic.packet_count == before + 3

    @pytest.mark.asyncio
    async def test_replay_protocol_filter(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")

        session = await service.start_replay(info.id, speed=10.0, protocol_filter="tcp")
        await service.wait_for_completion(session.id)
        status = service.status(session.id)

        assert status is not None
        assert status["total_packets"] == 1
        assert status["packets_replayed"] == 1

    @pytest.mark.asyncio
    async def test_replay_invalid_speed(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")
        with pytest.raises(ValueError, match="speed"):
            await service.start_replay(info.id, speed=100.0)

    @pytest.mark.asyncio
    async def test_stop_replay(self):
        service = PcapService(ConfigManager())
        info = await service.upload(_make_pcap_bytes(), "test.pcap")
        session = await service.start_replay(info.id, speed=0.5)
        result = await service.stop_replay(session.id)
        assert result is not None
        assert result["status"] == "stopped"
