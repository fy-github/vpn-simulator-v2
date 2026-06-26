"""多厂商 CLI API 路由模块。"""

from __future__ import annotations

import logging

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vpn_simulator.services.vendor_cli import VendorType, get_vendor_cli_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendor-cli", tags=["vendor-cli"])


class ExecuteCommandRequest(BaseModel):
    """执行命令请求。"""
    vendor: str
    command: str
    params: Optional[dict[str, Any]] = None


class ExecuteCommandResponse(BaseModel):
    """执行命令响应。"""
    command: str
    output: str
    success: bool
    timestamp: str


@router.get("/commands")
async def get_supported_commands(vendor: str = "cisco") -> dict[str, Any]:
    """获取支持的命令列表。

    Args:
        vendor: 厂商类型 (cisco/huawei)

    Returns:
        支持的命令列表
    """
    try:
        vendor_type = VendorType(vendor)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported vendor: {vendor}")

    service = get_vendor_cli_service()
    commands = service.get_supported_commands(vendor_type)

    return {
        "vendor": vendor,
        "commands": commands,
        "total": len(commands)
    }


@router.post("/execute")
async def execute_command(request: ExecuteCommandRequest) -> ExecuteCommandResponse:
    """执行厂商命令。

    Args:
        request: 执行命令请求

    Returns:
        命令执行结果
    """
    try:
        vendor_type = VendorType(request.vendor)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported vendor: {request.vendor}")

    service = get_vendor_cli_service()
    result = service.execute_command(vendor_type, request.command, request.params)

    return ExecuteCommandResponse(
        command=result.command,
        output=result.output,
        success=result.success,
        timestamp=result.timestamp.isoformat()
    )


@router.get("/history")
async def get_command_history(limit: int = 50) -> dict[str, Any]:
    """获取命令历史。

    Args:
        limit: 返回的最大记录数

    Returns:
        命令历史列表
    """
    service = get_vendor_cli_service()
    history = service.get_history(limit)

    return {
        "history": history,
        "total": len(history)
    }


@router.get("/vendors")
async def get_supported_vendors() -> dict[str, Any]:
    """获取支持的厂商列表。

    Returns:
        支持的厂商列表
    """
    return {
        "vendors": [
            {
                "id": "cisco",
                "name": "Cisco IOS",
                "description": "Cisco Internetwork Operating System"
            },
            {
                "id": "huawei",
                "name": "华为 VRP",
                "description": "华为通用路由平台"
            }
        ]
    }
