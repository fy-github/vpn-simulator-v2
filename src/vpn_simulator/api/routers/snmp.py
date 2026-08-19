"""SNMP device simulation routes (F4)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, Query

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/snmp")

_snmp_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.snmp import SnmpService


def get_snmp_service() -> SnmpService:
    """懒加载单例 SnmpService。"""
    global _snmp_service
    if _snmp_service is None:
        from vpn_simulator.services.snmp import SnmpService

        _snmp_service = SnmpService()
    return _snmp_service


@router.get(
    "/devices",
    summary="List SNMP devices",
    description="List simulated SNMP devices (12 device types, v2c/v3).",
)
async def list_devices() -> list[dict[str, Any]]:
    """List SNMP devices."""
    return get_snmp_service().list_devices()


@router.get(
    "/oids",
    summary="List MIB OIDs",
    description="List supported MIB-II base OIDs.",
)
async def list_oids() -> list[dict[str, str]]:
    """List supported OIDs."""
    return get_snmp_service().list_oids()


@router.get(
    "/devices/{device_id}",
    summary="Get SNMP device",
    description="Get a simulated SNMP device by ID.",
)
async def get_device(device_id: str) -> dict[str, Any]:
    """Get a device."""
    device = get_snmp_service().get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return device


@router.get(
    "/devices/{device_id}/get",
    summary="SNMP GET",
    description="Simulate an SNMP GET for an OID (v2c/v3).",
)
async def snmp_get(
    device_id: str,
    oid: str = Query(..., description="OID to get (e.g. 1.3.6.1.2.1.1.5.0)"),
    version: str = Query("2c", description="SNMP version (2c or 3)"),
) -> dict[str, Any]:
    """Simulate SNMP GET."""
    try:
        return get_snmp_service().get_oid(device_id, oid, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/devices/{device_id}/walk",
    summary="SNMP WALK",
    description="Simulate an SNMP WALK (subtree traversal) for an OID prefix (v2c/v3).",
)
async def snmp_walk(
    device_id: str,
    oid: str = Query("1.3.6.1.2.1", description="OID prefix to walk"),
    version: str = Query("2c", description="SNMP version (2c or 3)"),
) -> list[dict[str, Any]]:
    """Simulate SNMP WALK."""
    try:
        return get_snmp_service().walk_oid(device_id, oid, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
