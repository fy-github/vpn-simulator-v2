"""Tests for packet parser service."""

import pytest
from vpn_simulator.domain.packet import PacketDirection, PacketType
from vpn_simulator.domain.packet_fields import (
    FieldDefinition,
    FieldType,
    get_field_definitions,
    get_message_types,
    get_supported_protocols,
)
from vpn_simulator.services.packet_parser import PacketParser


def test_packet_parser_initialization():
    """Test PacketParser initialization."""
    parser = PacketParser()
    assert parser.get_packet_count() == 0


def test_parse_pptp_sccrq():
    """Test parsing PPTP SCCRQ packet."""
    parser = PacketParser()

    raw_data = bytes([
        0x00, 0x9C,  # length = 156
        0x00, 0x01,  # message_type = 1 (SCCRQ)
        0x1A, 0x2B, 0x3C, 0x4D,  # magic_cookie
        0x00, 0x01,  # control_message_type = 1
        0x00, 0x00,  # reserved
        0x01, 0x00,  # protocol_version = 256
        0x00, 0x00, 0x00, 0x03,  # framing_capabilities
        0x00, 0x00, 0x00, 0x03,  # bearer_capabilities
        0x00, 0x01,  # max_channels = 1
        0x01, 0x00,  # firmware_revision = 256
    ] + [0x00] * 136)  # padding

    packet = parser.parse_packet(
        raw_data,
        "pptp",
        "SCCRQ",
        direction=PacketDirection.INCOMING,
        src_ip="192.168.1.100",
        dst_ip="192.168.1.1",
        src_port=50000,
        dst_port=1723,
    )

    assert packet.protocol == "pptp"
    assert packet.direction == PacketDirection.INCOMING
    assert packet.packet_type == PacketType.CONTROL
    assert packet.parsed is True
    assert len(packet.fields) > 0
    assert packet.src_ip == "192.168.1.100"
    assert packet.dst_ip == "192.168.1.1"


def test_parse_l2tp_sccrq():
    """Test parsing L2TP SCCRQ packet."""
    parser = PacketParser()

    raw_data = bytes([
        0xC8, 0x02,  # flags
        0x00, 0x3C,  # length = 60
        0x00, 0x01,  # tunnel_id = 1
        0x00, 0x00,  # session_id = 0
        0x00, 0x00,  # ns = 0
        0x00, 0x00,  # nr = 0
        0x00, 0x00,  # offset_size = 0
    ] + [0x00] * 20)

    packet = parser.parse_packet(
        raw_data,
        "l2tp",
        "SCCRQ",
        direction=PacketDirection.INCOMING,
    )

    assert packet.protocol == "l2tp"
    assert packet.parsed is True


def test_parse_openvpn_p_control():
    """Test parsing OpenVPN P_CONTROL packet."""
    parser = PacketParser()

    raw_data = bytes([
        0x40,  # opcode = P_CONTROL_V1
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,  # session_id
        0x00, 0x00, 0x00, 0x01,  # message_id
        0x00,  # ack_length
        0x00, 0x10,  # payload_length
    ] + [0x00] * 16)

    packet = parser.parse_packet(
        raw_data,
        "openvpn",
        "P_CONTROL",
        direction=PacketDirection.INCOMING,
    )

    assert packet.protocol == "openvpn"
    assert packet.parsed is True


def test_parse_ipsec_ike_sa_init():
    """Test parsing IPSec IKE_SA_INIT packet."""
    parser = PacketParser()

    raw_data = bytes([
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,  # initiator_spi
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # responder_spi
        0x21,  # next_payload
        0x20,  # version
        0x22,  # exchange_type = IKE_SA_INIT
        0x08,  # flags
        0x00, 0x00, 0x00, 0x00,  # message_id
        0x00, 0x00, 0x00, 0x2C,  # length
    ] + [0x00] * 16)

    packet = parser.parse_packet(
        raw_data,
        "ipsec",
        "IKE_SA_INIT",
        direction=PacketDirection.INCOMING,
    )

    assert packet.protocol == "ipsec"
    assert packet.parsed is True


def test_get_packets():
    """Test getting packets list."""
    parser = PacketParser()

    # Generate sample packets
    parser.generate_sample_packets()

    # Get all packets
    packets = parser.get_packets()
    assert len(packets) > 0

    # Get packets by protocol
    pptp_packets = parser.get_packets(protocol="pptp")
    assert all(p.protocol == "pptp" for p in pptp_packets)

    # Get packets by direction
    incoming_packets = parser.get_packets(direction=PacketDirection.INCOMING)
    assert all(p.direction == PacketDirection.INCOMING for p in incoming_packets)


def test_search_packets():
    """Test searching packets."""
    parser = PacketParser()

    # Generate sample packets
    parser.generate_sample_packets()

    # Search by protocol name
    results = parser.search_packets("pptp")
    assert len(results) > 0
    assert all(p.protocol == "pptp" for p in results)

    # Search by IP address
    results = parser.search_packets("192.168.1.100")
    assert len(results) > 0


def test_export_to_pcap():
    """Test exporting packets to PCAP format."""
    parser = PacketParser()

    # Generate sample packets
    parser.generate_sample_packets()

    # Export to PCAP
    pcap_data = parser.export_to_pcap()

    # Check PCAP header
    assert len(pcap_data) > 0
    assert pcap_data[:4] == b'\xd4\xc3\xb2\xa1'  # PCAP magic number


def test_get_statistics():
    """Test getting packet statistics."""
    parser = PacketParser()

    # Generate sample packets
    parser.generate_sample_packets()

    stats = parser.get_statistics()

    assert stats["total"] > 0
    assert "by_protocol" in stats
    assert "by_direction" in stats
    assert "by_type" in stats


def test_get_supported_protocols():
    """Test getting supported protocols."""
    protocols = get_supported_protocols()

    assert "pptp" in protocols
    assert "l2tp" in protocols
    assert "openvpn" in protocols
    assert "ipsec" in protocols
    assert "ikev2" in protocols


def test_get_message_types():
    """Test getting message types for protocols."""
    pptp_types = get_message_types("pptp")
    assert "SCCRQ" in pptp_types
    assert "SCCRP" in pptp_types

    l2tp_types = get_message_types("l2tp")
    assert "SCCRQ" in l2tp_types

    openvpn_types = get_message_types("openvpn")
    assert "P_CONTROL" in openvpn_types
    assert "P_DATA" in openvpn_types


def test_get_field_definitions():
    """Test getting field definitions."""
    fields = get_field_definitions("pptp", "SCCRQ")
    assert fields is not None
    assert len(fields) > 0

    # Check field structure
    field = fields[0]
    assert field.name == "length"
    assert field.offset == 0
    assert field.length == 2
    assert field.field_type == FieldType.UINT16


def test_clear_packets():
    """Test clearing all packets."""
    parser = PacketParser()

    # Generate sample packets
    parser.generate_sample_packets()
    assert parser.get_packet_count() > 0

    # Clear packets
    parser.clear_packets()
    assert parser.get_packet_count() == 0


def test_packet_field_to_dict():
    """Test PacketField to_dict conversion."""
    parser = PacketParser()

    raw_data = bytes([
        0x00, 0x9C,  # length = 156
        0x00, 0x01,  # message_type = 1 (SCCRQ)
        0x1A, 0x2B, 0x3C, 0x4D,  # magic_cookie
        0x00, 0x01,  # control_message_type = 1
        0x00, 0x00,  # reserved
        0x01, 0x00,  # protocol_version = 256
        0x00, 0x00, 0x00, 0x03,  # framing_capabilities
        0x00, 0x00, 0x00, 0x03,  # bearer_capabilities
        0x00, 0x01,  # max_channels = 1
        0x01, 0x00,  # firmware_revision = 256
    ] + [0x00] * 136)

    packet = parser.parse_packet(raw_data, "pptp", "SCCRQ")

    # Check field to_dict
    field = packet.fields[0]
    field_dict = field.to_dict()

    assert "name" in field_dict
    assert "offset" in field_dict
    assert "length" in field_dict
    assert "value" in field_dict
    assert "description" in field_dict
    assert "field_type" in field_dict


def test_packet_info_to_dict():
    """Test PacketInfo to_dict conversion."""
    parser = PacketParser()

    raw_data = bytes([
        0x00, 0x9C,  # length = 156
        0x00, 0x01,  # message_type = 1 (SCCRQ)
        0x1A, 0x2B, 0x3C, 0x4D,  # magic_cookie
        0x00, 0x01,  # control_message_type = 1
        0x00, 0x00,  # reserved
        0x01, 0x00,  # protocol_version = 256
        0x00, 0x00, 0x00, 0x03,  # framing_capabilities
        0x00, 0x00, 0x00, 0x03,  # bearer_capabilities
        0x00, 0x01,  # max_channels = 1
        0x01, 0x00,  # firmware_revision = 256
    ] + [0x00] * 136)

    packet = parser.parse_packet(raw_data, "pptp", "SCCRQ")
    packet_dict = packet.to_dict()

    assert "id" in packet_dict
    assert "timestamp" in packet_dict
    assert "direction" in packet_dict
    assert "packet_type" in packet_dict
    assert "protocol" in packet_dict
    assert "raw_data_hex" in packet_dict
    assert "fields" in packet_dict
    assert "parsed" in packet_dict
