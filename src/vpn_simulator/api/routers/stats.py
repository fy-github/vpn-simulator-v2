import logging
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats")

_start_time = time.time()
_last_cpu_percent = 0.0


class ProtocolStats(BaseModel):
    """Per-protocol statistics."""

    name: str = Field(..., description="Protocol name")
    connections_total: int = Field(0, description="Total connections")
    connections_active: int = Field(0, description="Active connections")
    bytes_sent: int = Field(0, description="Total bytes sent")
    bytes_received: int = Field(0, description="Total bytes received")
    packets_sent: int = Field(0, description="Total packets sent")
    packets_received: int = Field(0, description="Total packets received")
    errors: int = Field(0, description="Error count")


class SystemStats(BaseModel):
    """System-wide statistics."""

    uptime_seconds: float = Field(0, description="System uptime in seconds")
    cpu_percent: float = Field(0, description="CPU usage percentage")
    memory_percent: float = Field(0, description="Memory usage percentage")
    memory_used_mb: float = Field(0, description="Memory used in MB")
    memory_total_mb: float = Field(0, description="Total memory in MB")
    total_connections: int = Field(0, description="Total connections")
    active_connections: int = Field(0, description="Active connections")
    total_bytes_sent: int = Field(0, description="Total bytes sent")
    total_bytes_received: int = Field(0, description="Total bytes received")
    total_packets_sent: int = Field(0, description="Total packets sent")
    total_packets_received: int = Field(0, description="Total packets received")
    active_faults: int = Field(0, description="Active fault count")
    active_attacks: int = Field(0, description="Active attack count")
    protocols: list[ProtocolStats] = Field(default_factory=list, description="Per-protocol stats")


def _get_system_metrics() -> dict[str, float]:
    """Collect real system metrics using psutil."""
    global _last_cpu_percent
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0)
        if cpu == 0.0 and _last_cpu_percent == 0.0:
            cpu = psutil.cpu_percent(interval=0.1)
        _last_cpu_percent = cpu
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(mem.percent, 1),
            "memory_used_mb": round(mem.used / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
        }
    except ImportError:
        logger.warning("psutil not installed, returning zero metrics")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_used_mb": 0.0,
            "memory_total_mb": 0.0,
        }


def _get_connection_stats() -> dict[str, int]:
    """Get connection statistics from protocol service."""
    try:
        from vpn_simulator.api.routers.protocols import _started_protocols
        active = len(_started_protocols)
        return {
            "total_connections": active,
            "active_connections": active,
        }
    except Exception:
        return {"total_connections": 0, "active_connections": 0}


@router.get(
    "",
    response_model=SystemStats,
    summary="Get statistics",
    description="Retrieve system-wide and per-protocol statistics.",
)
async def get_stats() -> dict[str, Any]:
    """Get system statistics with real CPU/memory data."""
    uptime = time.time() - _start_time
    sys_metrics = _get_system_metrics()
    conn_stats = _get_connection_stats()

    return {
        "uptime_seconds": round(uptime, 1),
        **sys_metrics,
        **conn_stats,
        "total_bytes_sent": 0,
        "total_bytes_received": 0,
        "total_packets_sent": 0,
        "total_packets_received": 0,
        "active_faults": 0,
        "active_attacks": 0,
        "protocols": [],
    }
