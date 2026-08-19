"""VPN config validation routes (F2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/validation")

_validation_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.validation import ValidationService


def get_validation_service() -> ValidationService:
    """懒加载单例 ValidationService。"""
    global _validation_service
    if _validation_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import get_database_manager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.validation import ValidationService

        _validation_service = ValidationService(EventBus(), ConfigManager(), get_database_manager())
    return _validation_service


class ValidateRequest(BaseModel):
    """Request to validate a VPN config."""

    protocol: str = Field(..., description="Protocol name (6 supported)")
    config: dict[str, Any] = Field(default_factory=dict, description="Config to validate")


class BatchRequest(BaseModel):
    """Request to batch-validate protocols."""

    protocols: list[str] | None = Field(None, description="Protocols to validate (default all 6)")
    configs: dict[str, dict[str, Any]] | None = Field(None, description="Per-protocol configs")


@router.post(
    "/validate",
    summary="Validate a VPN config",
    description="Run the 7-item config validation for a protocol (syntax/port/handshake/auth/tunnel/latency/throughput).",
)
async def validate(request: ValidateRequest) -> dict[str, Any]:
    """Validate a protocol config."""
    try:
        result = await get_validation_service().validate(request.protocol, request.config)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/results/{result_id}",
    summary="Get validation result",
    description="Retrieve a stored validation result by ID.",
)
async def get_result(result_id: str) -> dict[str, Any]:
    """Get a validation result."""
    result = await get_validation_service().get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Validation result {result_id} not found")
    return result


@router.get(
    "/history",
    summary="List validation history",
    description="List validation history, optionally filtered by protocol.",
)
async def history(
    protocol: str | None = Query(None, description="Filter by protocol"),
    limit: int = Query(50, ge=1, le=500, description="Max records"),
) -> list[dict[str, Any]]:
    """List validation history."""
    return await get_validation_service().history(protocol=protocol, limit=limit)


@router.post(
    "/batch",
    summary="Batch-validate protocols",
    description="Validate multiple protocols (default all 6) and return their results.",
)
async def batch(request: BatchRequest | None = None) -> list[dict[str, Any]]:
    """Batch-validate protocols."""
    protocols = request.protocols if request else None
    configs = request.configs if request else None
    return await get_validation_service().batch(protocols=protocols, configs=configs)
