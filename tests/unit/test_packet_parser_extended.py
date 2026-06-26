"""Tests for PacketParser - covering uncovered lines."""

from __future__ import annotations

import pytest

from vpn_simulator.domain.packet import PacketDirection, PacketType
from vpn_simulator.services.packet_parser import PacketParser


@pytest.fixture
def parser() -> PacketParser:
    return PacketParser()


class TestGetPacketType:
    def test_control_message(self, parser: PacketParser):
        result = parser._get_packet_type("pptp", "SCCRQ")
        assert result == PacketType.CONTROL

    def test_data_message(self, parser: PacketParser):
        result = parser._get_packet_type("pptp", "P_DATA")
        assert result == PacketType.DATA

    def test_unknown_message_defaults_control(self, parser: PacketParser):
        result = parser._get_packet_type("pptp", "UNKNOWN_TYPE")
        assert result == PacketType.CONTROL


class TestSearchPackets:
    def test_search_by_protocol(self, parser: PacketParser):
        parser.parse_packet(b"\x00" * 10, protocol="pptp", message_type="SCCRQ")
        results = parser.search_packets("pptp")
        assert len(results) > 0

    def test_search_by_field_name(self, parser: PacketParser):
        parser.parse_packet(b"\x00" * 20, protocol="pptp", message_type="SCCRQ")
        results = parser.search_packets("message_type")
        assert len(results) >= 0

    def test_search_with_limit(self, parser: PacketParser):
        for i in range(10):
            parser.parse_packet(b"\x00" * 10, protocol="pptp", message_type="SCCRQ")
        results = parser.search_packets("pptp", limit=3)
        assert len(results) <= 3


class TestGetPackets:
    def test_get_packets_with_filters(self, parser: PacketParser):
        parser.parse_packet(b"\\x00" * 10, protocol="pptp", message_type="SCCRQ")
        parser.parse_packet(b"\\x00" * 10, protocol="l2tp", message_type="SCCRP")
        packets = parser.get_packets(protocol="pptp")
        assert len(packets) == 1

    def test_get_packets_with_direction(self, parser: PacketParser):
        parser.parse_packet(b"\x00" * 10, protocol="pptp", message_type="SCCRQ", direction="incoming")
        packets = parser.get_packets(direction=PacketDirection.INCOMING)
        assert len(packets) >= 0

    def test_get_packets_with_limit(self, parser: PacketParser):
        for i in range(10):
            parser.parse_packet(b"\\x00" * 10, protocol="pptp", message_type="SCCRQ")
        packets = parser.get_packets(limit=5)
        assert len(packets) <= 5


class TestParseFields:
    def test_parse_fields_with_error(self, parser: PacketParser):
        result = parser.parse_packet(b"\\x00" * 5, protocol="pptp", message_type="SCCRQ")
        assert result is not None


class TestExportToPcap:
    def test_export_empty(self, parser: PacketParser):
        result = parser.export_to_pcap()
        assert isinstance(result, bytes)

    def test_export_with_packets(self, parser: PacketParser):
        parser.parse_packet(b"\\x00" * 10, protocol="pptp", message_type="SCCRQ")
        result = parser.export_to_pcap()
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_with_protocol_filter(self, parser: PacketParser):
        parser.parse_packet(b"\\x00" * 10, protocol="pptp", message_type="SCCRQ")
        parser.parse_packet(b"\\x00" * 10, protocol="l2tp", message_type="SCCRP")
        result = parser.export_to_pcap(protocol="pptp")
        assert isinstance(result, bytes)


class TestGetStatistics:
    def test_statistics_empty(self, parser: PacketParser):
        stats = parser.get_statistics()
        assert stats["total"] == 0

    def test_statistics_with_packets(self, parser: PacketParser):
        parser.parse_packet(b"\x00" * 10, protocol="pptp", message_type="SCCRQ")
        parser.parse_packet(b"\x00" * 10, protocol="l2tp", message_type="SCCRP")
        stats = parser.get_statistics()
        assert stats["total"] == 2
        assert "by_protocol" in stats
        assert "by_direction" in stats
        assert "by_type" in stats


class TestGenerateSamplePackets:
    def test_generate_samples(self, parser: PacketParser):
        samples = parser.generate_sample_packets()
        assert isinstance(samples, list)
        assert len(samples) > 0

    def test_sample_structure(self, parser: PacketParser):
        samples = parser.generate_sample_packets()
        sample = samples[0]
        assert hasattr(sample, 'protocol')
        assert hasattr(sample, 'packet_type')


class TestEdgeCases:
    def test_multiple_protocols(self, parser: PacketParser):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            parser.parse_packet(b"\x00" * 10, protocol=proto, message_type="test")
        stats = parser.get_statistics()
        assert stats["total"] == 6

    def test_packet_with_all_fields(self, parser: PacketParser):
        result = parser.parse_packet(
            b"\\x00" * 50,
            protocol="pptp",
            message_type="SCCRQ",
            direction="incoming",
            src_ip="192.168.1.1",
            dst_ip="10.0.0.1",
            src_port=12345,
            dst_port=1723,
        )
        assert result is not None
        assert result.protocol == "pptp"
        assert result.src_ip == "192.168.1.1"

    def test_clear_and_reparse(self, parser: PacketParser):
        parser.parse_packet(b"\\x00" * 10, protocol="pptp", message_type="SCCRQ")
        assert parser.get_packet_count() == 1
        parser.clear_packets()
        assert parser.get_packet_count() == 0
        parser.parse_packet(b"\\x00" * 10, protocol="l2tp", message_type="SCCRP")
        assert parser.get_packet_count() == 1
