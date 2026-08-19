"""PCAP replay routes (F3)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/pcap")

_pcap_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.pcap import PcapService


def get_pcap_service() -> PcapService:
    """懒加载单例 PcapService。"""
    global _pcap_service
    if _pcap_service is None:
        from vpn_simulator.core.config import ConfigManager
        from vpn_simulator.services.pcap import PcapService

        _pcap_service = PcapService(ConfigManager())
    return _pcap_service


class ReplayRequest(BaseModel):
    """Request to start a PCAP replay."""

    file_id: str = Field(..., description="PCAP file ID")
    speed: float = Field(1.0, ge=0.5, le=10.0, description="Replay speed (0.5x-10x)")
    protocol_filter: str | None = Field(None, description="Protocol filter (e.g. tcp)")


@router.post(
    "/upload",
    summary="Upload a PCAP file",
    description="Upload and parse a PCAP/PCAPNG file for replay.",
    status_code=201,
)
async def upload_pcap(file: UploadFile) -> dict[str, Any]:
    """Upload a PCAP file."""
    data = await file.read()
    try:
        info = await get_pcap_service().upload(data, file.filename or "capture.pcap")
        return info.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/files",
    summary="List PCAP files",
    description="List uploaded PCAP files.",
)
async def list_files() -> list[dict[str, Any]]:
    """List uploaded PCAP files."""
    return get_pcap_service().list_files()


@router.post(
    "/replay",
    summary="Start PCAP replay",
    description="Replay a PCAP file into the traffic stream at the given speed.",
    status_code=202,
)
async def start_replay(request: ReplayRequest) -> dict[str, Any]:
    """Start a replay session."""
    try:
        session = await get_pcap_service().start_replay(
            request.file_id, request.speed, request.protocol_filter
        )
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/status/{session_id}",
    summary="Get replay status",
    description="Get the status of a replay session.",
)
async def replay_status(session_id: str) -> dict[str, Any]:
    """Get replay status."""
    status = get_pcap_service().status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Replay session {session_id} not found")
    return status


@router.post(
    "/stop/{session_id}",
    summary="Stop replay",
    description="Stop a running replay session.",
)
async def stop_replay(session_id: str) -> dict[str, Any]:
    """Stop a replay session."""
    result = await get_pcap_service().stop_replay(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Replay session {session_id} not found")
    return result


@router.get(
    "/stats/{file_id}",
    summary="Get PCAP statistics",
    description="Get parsed statistics for an uploaded PCAP file.",
)
async def pcap_stats(file_id: str) -> dict[str, Any]:
    """Get PCAP statistics."""
    stats = get_pcap_service().stats(file_id)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"PCAP file {file_id} not found")
    return stats
