import logging

"""Packet management routes for VPN Simulator v2."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ...domain.packet import PacketDirection, PacketType
from ...services.packet_parser import packet_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/packets")


class PacketFieldInfo(BaseModel):
    """Packet field information."""

    name: str = Field(..., description="Field name")
    offset: int = Field(..., description="Field offset in bytes")
    length: int = Field(..., description="Field length in bytes")
    value: str = Field(..., description="Field value")
    description: str = Field("", description="Field description")
    field_type: str = Field("bytes", description="Field type")


class PacketInfo(BaseModel):
    """Packet information."""

    id: str = Field(..., description="Packet ID")
    timestamp: str = Field(..., description="Packet timestamp")
    direction: str = Field(..., description="Packet direction (incoming/outgoing)")
    packet_type: str = Field(..., description="Packet type (control/data/error)")
    protocol: str = Field(..., description="Protocol name")
    src_ip: str = Field("", description="Source IP address")
    dst_ip: str = Field("", description="Destination IP address")
    src_port: int = Field(0, description="Source port")
    dst_port: int = Field(0, description="Destination port")
    raw_data_hex: str = Field("", description="Raw packet data in hex")
    fields: list[PacketFieldInfo] = Field(default_factory=list, description="Parsed fields")
    parsed: bool = Field(False, description="Whether packet is parsed")
    parse_error: Optional[str] = Field(None, description="Parse error message")
    connection_id: Optional[str] = Field(None, description="Associated connection ID")
    session_id: Optional[str] = Field(None, description="Associated session ID")


class PacketListResponse(BaseModel):
    """Packet list response."""

    packets: list[PacketInfo] = Field(..., description="Packet list")
    total: int = Field(..., description="Total packet count")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")


class PacketStatistics(BaseModel):
    """Packet statistics."""

    total: int = Field(..., description="Total packet count")
    by_protocol: dict[str, int] = Field(..., description="Count by protocol")
    by_direction: dict[str, int] = Field(..., description="Count by direction")
    by_type: dict[str, int] = Field(..., description="Count by type")


class ProtocolInfo(BaseModel):
    """Protocol information."""

    protocols: list[str] = Field(..., description="Supported protocols")
    message_types: dict[str, list[str]] = Field(..., description="Message types by protocol")


def _convert_packet(packet: Any) -> dict[str, Any]:
    """Convert PacketInfo to API response format."""
    return {
        "id": packet.id,
        "timestamp": packet.timestamp.isoformat(),
        "direction": packet.direction.value,
        "packet_type": packet.packet_type.value,
        "protocol": packet.protocol,
        "src_ip": packet.src_ip,
        "dst_ip": packet.dst_ip,
        "src_port": packet.src_port,
        "dst_port": packet.dst_port,
        "raw_data_hex": packet.raw_data.hex(),
        "fields": [
            {
                "name": f.name,
                "offset": f.offset,
                "length": f.length,
                "value": str(f.value),
                "description": f.description,
                "field_type": f.field_type,
            }
            for f in packet.fields
        ],
        "parsed": packet.parsed,
        "parse_error": packet.parse_error,
        "connection_id": packet.connection_id,
        "session_id": packet.session_id,
    }


@router.get(
    "",
    response_model=PacketListResponse,
    summary="List all packets",
    description="Retrieve all packets with optional filtering.",
)
async def list_packets(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    direction: Optional[str] = Query(None, description="Filter by direction (incoming/outgoing)"),
    packet_type: Optional[str] = Query(None, description="Filter by type (control/data/error)"),
    connection_id: Optional[str] = Query(None, description="Filter by connection ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of packets to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict[str, Any]:
    """List all packets with optional filtering."""
    # Convert string parameters to enums
    direction_enum = None
    if direction:
        try:
            direction_enum = PacketDirection(direction)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")

    type_enum = None
    if packet_type:
        try:
            type_enum = PacketType(packet_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid packet type: {packet_type}")

    packets = packet_parser.get_packets(
        protocol=protocol,
        direction=direction_enum,
        packet_type=type_enum,
        connection_id=connection_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )

    return {
        "packets": [_convert_packet(p) for p in packets],
        "total": packet_parser.get_packet_count(),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/search",
    response_model=list[PacketInfo],
    summary="Search packets",
    description="Search packets by query string in field names, descriptions, and values.",
)
async def search_packets(
    query: str = Query(..., min_length=1, description="Search query"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
) -> list[dict[str, Any]]:
    """Search packets by query string."""
    packets = packet_parser.search_packets(query=query, protocol=protocol, limit=limit)
    return [_convert_packet(p) for p in packets]


@router.get(
    "/statistics",
    response_model=PacketStatistics,
    summary="Get packet statistics",
    description="Get statistics about all packets.",
)
async def get_statistics() -> dict[str, Any]:
    """Get packet statistics."""
    return packet_parser.get_statistics()


@router.get(
    "/protocols",
    response_model=ProtocolInfo,
    summary="Get supported protocols",
    description="Get list of supported protocols and their message types.",
)
async def get_protocols() -> dict[str, Any]:
    """Get supported protocols and message types."""
    protocols = packet_parser.get_supported_protocols()
    message_types = {}
    for protocol in protocols:
        message_types[protocol] = packet_parser.get_message_types(protocol)

    return {
        "protocols": protocols,
        "message_types": message_types,
    }


@router.get(
    "/export/pcap",
    summary="Export packets to PCAP",
    description="Export packets to PCAP format with optional filtering.",
)
async def export_pcap(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    direction: Optional[str] = Query(None, description="Filter by direction"),
    packet_type: Optional[str] = Query(None, description="Filter by type"),
    connection_id: Optional[str] = Query(None, description="Filter by connection ID"),
) -> Response:
    """Export packets to PCAP format."""
    # Convert string parameters to enums
    direction_enum = None
    if direction:
        try:
            direction_enum = PacketDirection(direction)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")

    type_enum = None
    if packet_type:
        try:
            type_enum = PacketType(packet_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid packet type: {packet_type}")

    pcap_data = packet_parser.export_to_pcap(
        protocol=protocol,
        direction=direction_enum,
        packet_type=type_enum,
        connection_id=connection_id,
    )

    return Response(
        content=pcap_data,
        media_type="application/vnd.tcpdump.pcap",
        headers={"Content-Disposition": "attachment; filename=packets.pcap"},
    )


@router.post(
    "/samples",
    response_model=list[PacketInfo],
    summary="Generate sample packets",
    description="Generate sample packet data for testing.",
)
async def generate_samples() -> list[dict[str, Any]]:
    """Generate sample packet data."""
    packets = packet_parser.generate_sample_packets()
    return [_convert_packet(p) for p in packets]


@router.get(
    "/{packet_id}",
    response_model=PacketInfo,
    summary="Get packet details",
    description="Get detailed information about a specific packet.",
)
async def get_packet(packet_id: str) -> dict[str, Any]:
    """Get packet details."""
    packet = packet_parser.get_packet(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail=f"Packet {packet_id} not found")
    return _convert_packet(packet)


@router.delete(
    "",
    summary="Clear all packets",
    description="Clear all stored packets.",
)
async def clear_packets() -> dict[str, str]:
    """Clear all packets."""
    packet_parser.clear_packets()
    return {"status": "success", "message": "All packets cleared"}
