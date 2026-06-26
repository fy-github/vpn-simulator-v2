"""Metrics API routes for VPN Simulator v2.

Provides endpoints for performance visualization data including
throughput, latency, packet loss, and connection statistics.
"""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics")

_VALID_PROTOCOLS = ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]
_VALID_TIME_RANGES = ["1m", "5m", "15m", "1h"]


def _get_service():
    from vpn_simulator.services.metrics import MetricsService
    return MetricsService()


def _validate_protocol(protocol: Optional[str]) -> Optional[str]:
    if protocol is None:
        return None
    if protocol.lower() not in _VALID_PROTOCOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid protocol '{protocol}'. Valid: {_VALID_PROTOCOLS}",
        )
    return protocol.lower()


def _validate_time_range(time_range: str) -> str:
    if time_range not in _VALID_TIME_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time_range '{time_range}'. Valid: {_VALID_TIME_RANGES}",
        )
    return time_range


@router.get(
    "/throughput",
    summary="Get throughput data",
    description="Retrieve throughput time series data for visualization.",
)
async def get_throughput(
    time_range: str = Query("5m", description="Time range (1m, 5m, 15m, 1h)"),
    protocol: Optional[str] = Query(None, description="Protocol filter"),
) -> dict[str, Any]:
    """Get throughput time series data."""
    _validate_time_range(time_range)
    _validate_protocol(protocol)
    service = _get_service()
    return service.get_throughput_data(time_range=time_range, protocol=protocol)


@router.get(
    "/latency",
    summary="Get latency data",
    description="Retrieve latency time series data for visualization.",
)
async def get_latency(
    time_range: str = Query("5m", description="Time range (1m, 5m, 15m, 1h)"),
    protocol: Optional[str] = Query(None, description="Protocol filter"),
) -> dict[str, Any]:
    """Get latency time series data."""
    _validate_time_range(time_range)
    _validate_protocol(protocol)
    service = _get_service()
    return service.get_latency_data(time_range=time_range, protocol=protocol)


@router.get(
    "/packet-loss",
    summary="Get packet loss data",
    description="Retrieve packet loss time series data for visualization.",
)
async def get_packet_loss(
    time_range: str = Query("5m", description="Time range (1m, 5m, 15m, 1h)"),
    protocol: Optional[str] = Query(None, description="Protocol filter"),
) -> dict[str, Any]:
    """Get packet loss time series data."""
    _validate_time_range(time_range)
    _validate_protocol(protocol)
    service = _get_service()
    return service.get_packet_loss_data(time_range=time_range, protocol=protocol)


@router.get(
    "/connections",
    summary="Get connections data",
    description="Retrieve connection count time series data for visualization.",
)
async def get_connections(
    time_range: str = Query("5m", description="Time range (1m, 5m, 15m, 1h)"),
) -> dict[str, Any]:
    """Get connection count time series data."""
    _validate_time_range(time_range)
    service = _get_service()
    return service.get_connections_data(time_range=time_range)


@router.get(
    "/distribution",
    summary="Get protocol distribution",
    description="Retrieve current connection distribution across protocols.",
)
async def get_protocol_distribution() -> dict[str, Any]:
    """Get protocol distribution data for pie chart."""
    service = _get_service()
    return service.get_protocol_distribution()


@router.get(
    "/statistics",
    summary="Get metrics statistics",
    description="Retrieve aggregated statistics for the given time range.",
)
async def get_statistics(
    time_range: str = Query("5m", description="Time range (1m, 5m, 15m, 1h)"),
    protocol: Optional[str] = Query(None, description="Protocol filter"),
) -> dict[str, Any]:
    """Get aggregated metrics statistics."""
    _validate_time_range(time_range)
    _validate_protocol(protocol)
    service = _get_service()
    return service.get_statistics(time_range=time_range, protocol=protocol)
