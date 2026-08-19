"""Retention policy routes (packets / state_transitions cleanup)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/retention")

_retention_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.retention import RetentionService


def get_retention_service() -> RetentionService:
    """懒加载单例 RetentionService。"""
    global _retention_service
    if _retention_service is None:
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.services.retention import RetentionService

        _retention_service = RetentionService(get_database_manager())
    return _retention_service


class CleanupRequest(BaseModel):
    """Request to run retention cleanup with optional overrides."""

    max_packets: int | None = Field(None, description="packets 最大保留行数（默认 100000）")
    packet_ttl_seconds: int | None = Field(None, description="packets 最大保留秒数（默认 7 天）")
    max_transitions: int | None = Field(
        None, description="state_transitions 最大保留行数（默认 50000）"
    )
    transition_ttl_seconds: int | None = Field(
        None, description="state_transitions 最大保留秒数（默认 30 天）"
    )


@router.get(
    "/status",
    summary="Get retention status",
    description="Get current packets / state_transitions row counts.",
)
async def status() -> dict[str, int]:
    """Get row counts."""
    return await get_retention_service().counts()


@router.post(
    "/cleanup",
    summary="Run retention cleanup",
    description="Prune expired/overflowing packets and state_transitions rows.",
)
async def cleanup(request: CleanupRequest | None = None) -> dict[str, Any]:
    """Run cleanup."""
    if request is None:
        return await get_retention_service().cleanup()
    return await get_retention_service().cleanup(
        max_packets=request.max_packets,
        packet_ttl_seconds=request.packet_ttl_seconds,
        max_transitions=request.max_transitions,
        transition_ttl_seconds=request.transition_ttl_seconds,
    )
