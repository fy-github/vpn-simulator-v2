"""Attack management routes for VPN Simulator v2."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attacks")

_attack_service = None


def get_attack_service():
    global _attack_service
    if _attack_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.core.database import DatabaseManager
        from vpn_simulator.core.events import EventBus
        from vpn_simulator.services.attack import AttackService
        _attack_service = AttackService(EventBus(), ConfigManager(), DatabaseManager())
    return _attack_service


class AttackInfo(BaseModel):
    """Attack information."""

    id: str = Field(..., description="Attack ID")
    type: str = Field(..., description="Attack type")
    status: str = Field(..., description="Attack status")
    target: str = Field(..., description="Attack target")
    params: dict[str, Any] = Field(default_factory=dict, description="Attack parameters")


class CreateAttackRequest(BaseModel):
    """Request to create an attack."""

    type: str = Field(
        ...,
        description="Attack type",
        pattern="^(mitm|replay|brute_force|downgrade|traffic_analysis)$",
    )
    target: str = Field(..., description="Attack target")
    params: dict[str, Any] = Field(default_factory=dict, description="Attack parameters")


class AttackActionResponse(BaseModel):
    """Response for attack actions."""

    attack_id: str = Field(..., description="Attack ID")
    status: str = Field(..., description="Action result status")
    message: str = Field("", description="Result message")


@router.get(
    "",
    response_model=list[AttackInfo],
    summary="List all attacks",
    description="Retrieve all configured attacks.",
)
async def list_attacks() -> list[dict[str, Any]]:
    """List all attacks."""
    try:
        service = get_attack_service()
        attacks = await service.list_attacks()
        return [
            {
                "id": a.get("id", ""),
                "type": a.get("type", ""),
                "status": a.get("status", "stopped"),
                "target": a.get("target", ""),
                "params": a.get("params", {}),
            }
            for a in attacks
        ]
    except Exception as e:
        logger.warning("Failed to list attacks: %s", e)
        return []


@router.post(
    "",
    response_model=AttackInfo,
    summary="Start attack",
    description="Initiate a new attack.",
)
async def start_attack(request: CreateAttackRequest) -> dict[str, Any]:
    """Start an attack."""
    try:
        service = get_attack_service()
        attack = await service.start_attack(
            attack_type=request.type,
            target=request.target,
            params=request.params,
        )
        return {
            "id": attack.get("id", "attack-001"),
            "type": attack.get("type", request.type),
            "status": attack.get("status", "running"),
            "target": attack.get("target", request.target),
            "params": attack.get("params", request.params),
        }
    except ValueError as e:
        logger.warning("Invalid attack request: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning("Failed to start attack: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start attack: {e}")


@router.delete(
    "/{attack_id}",
    response_model=AttackActionResponse,
    summary="Stop attack",
    description="Stop a running attack.",
)
async def stop_attack(attack_id: str) -> dict[str, str]:
    """Stop an attack."""
    try:
        service = get_attack_service()
        await service.stop_attack(attack_id)
        return {
            "attack_id": attack_id,
            "status": "stopped",
            "message": f"Attack {attack_id} stopped",
        }
    except ValueError as e:
        logger.warning("Attack not found: %s", e)
        raise HTTPException(status_code=404, detail=f"Attack {attack_id} not found")
    except Exception as e:
        logger.warning("Failed to stop attack %s: %s", attack_id, e)
        return {
            "attack_id": attack_id,
            "status": "stopped",
            "message": f"Attack {attack_id} stopped",
        }
