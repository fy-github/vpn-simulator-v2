"""Grafana integration routes (F6)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/grafana")

_grafana_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.grafana import GrafanaService


def get_grafana_service() -> GrafanaService:
    """懒加载单例 GrafanaService。"""
    global _grafana_service
    if _grafana_service is None:
        from vpn_simulator.services.grafana import GrafanaService

        _grafana_service = GrafanaService()
    return _grafana_service


@router.get(
    "/dashboards",
    summary="List built-in dashboards",
    description="List built-in Grafana dashboards.",
)
async def list_dashboards() -> list[dict[str, Any]]:
    """List dashboards."""
    return get_grafana_service().list_dashboards()


@router.get(
    "/dashboards/{name}",
    summary="Get a dashboard JSON",
    description="Get a built-in Grafana dashboard JSON definition for import.",
)
async def get_dashboard(name: str) -> dict[str, Any]:
    """Get a dashboard JSON."""
    dashboard = get_grafana_service().get_dashboard(name)
    if dashboard is None:
        raise HTTPException(status_code=404, detail=f"Dashboard '{name}' not found")
    return dashboard


@router.get(
    "/alert-rules",
    summary="List alert rules",
    description="List Prometheus alert rules.",
)
async def list_alert_rules() -> list[dict[str, Any]]:
    """List alert rules."""
    return get_grafana_service().list_alert_rules()
