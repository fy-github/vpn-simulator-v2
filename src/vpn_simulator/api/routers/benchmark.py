"""Benchmark testing routes for VPN Simulator v2."""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark")


class BenchmarkRunRequest(BaseModel):
    """Request to run a benchmark test."""

    test_type: str = Field(
        ...,
        description="Benchmark test type (handshake, throughput, memory, concurrency)",
    )
    protocol: str = Field(
        ...,
        description="Protocol name (pptp, l2tp, openvpn, ipsec, ikev2, wireguard)",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional test parameters",
    )


class BenchmarkMetricsResponse(BaseModel):
    """Benchmark metrics response."""

    handshake_time_ms: float = Field(0.0, description="Handshake time in milliseconds")
    throughput_mbps: float = Field(0.0, description="Throughput in Mbps")
    memory_mb: float = Field(0.0, description="Memory usage in MB")
    cpu_percent: float = Field(0.0, description="CPU usage percentage")
    concurrent_connections: int = Field(0, description="Number of concurrent connections")


class BenchmarkResultResponse(BaseModel):
    """Benchmark result response."""

    metrics: BenchmarkMetricsResponse = Field(
        default_factory=BenchmarkMetricsResponse,
        description="Benchmark metrics",
    )
    duration_seconds: float = Field(0.0, description="Test duration in seconds")
    iterations: int = Field(0, description="Number of test iterations")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed test data")


class BenchmarkInfoResponse(BaseModel):
    """Benchmark information response."""

    id: str = Field(..., description="Benchmark ID")
    test_type: str = Field(..., description="Test type")
    protocol: str = Field(..., description="Protocol name")
    status: str = Field(..., description="Test status")
    params: dict[str, Any] = Field(default_factory=dict, description="Test parameters")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    result: Optional[BenchmarkResultResponse] = Field(None, description="Test result")


class CompareRequest(BaseModel):
    """Request to compare benchmark results."""

    baseline_id: str = Field(..., description="Baseline benchmark ID")
    current_id: str = Field(..., description="Current benchmark ID")


class MetricChangeResponse(BaseModel):
    """Metric change response."""

    absolute: float = Field(..., description="Absolute change")
    percent: float = Field(..., description="Percentage change")


class CompareResponse(BaseModel):
    """Comparison result response."""

    baseline: BenchmarkInfoResponse = Field(..., description="Baseline benchmark")
    current: BenchmarkInfoResponse = Field(..., description="Current benchmark")
    changes: dict[str, MetricChangeResponse] = Field(
        ...,
        description="Metric changes",
    )


@router.post(
    "/run",
    response_model=BenchmarkInfoResponse,
    summary="Run benchmark test",
    description="Run a benchmark test for a specific protocol.",
)
async def run_benchmark(request: BenchmarkRunRequest) -> dict[str, Any]:
    """Run a benchmark test."""
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    service = BenchmarkService(ConfigManager())

    try:
        return await service.run_benchmark(
            test_type=request.test_type,
            protocol=request.protocol,
            params=request.params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/results",
    response_model=list[BenchmarkInfoResponse],
    summary="Get benchmark results",
    description="Retrieve benchmark test results.",
)
async def get_results(
    limit: int = Query(10, description="Maximum number of results to return"),
) -> list[dict[str, Any]]:
    """Get benchmark results."""
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    service = BenchmarkService(ConfigManager())
    return await service.get_results(limit=limit)


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare benchmark results",
    description="Compare two benchmark test results.",
)
async def compare_results(
    baseline: str = Query(..., description="Baseline benchmark ID"),
    current: str = Query(..., description="Current benchmark ID"),
) -> dict[str, Any]:
    """Compare benchmark results."""
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    service = BenchmarkService(ConfigManager())

    try:
        return await service.compare_results(
            baseline_id=baseline,
            current_id=current,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
