"""DHCP 模拟 API 路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dhcp")

# DHCP 服务实例（单例）
_dhcp_service = None


if TYPE_CHECKING:
    from vpn_simulator.services.dhcp import DHCPService


def get_dhcp_service() -> DHCPService:
    """获取 DHCP 服务实例。"""
    global _dhcp_service
    if _dhcp_service is None:
        from vpn_simulator.services.dhcp import DHCPService

        _dhcp_service = DHCPService()
    return _dhcp_service


class DHCPRunRequest(BaseModel):
    """启动 DHCP 模拟任务的请求参数。"""

    count: int = Field(5, ge=1, le=200, description="要获取的 DHCP 地址数量")
    interval: float = Field(0.5, ge=0, description="并发启动错峰间隔（秒）")
    timeout: float = Field(6.0, gt=0, description="单次请求等待回包秒数")
    attempts: int = Field(3, ge=1, description="获取失败后的重试次数")
    iface: str | None = Field(None, description="发送网卡名（如 en0）")
    vlan: int | None = Field(None, ge=1, le=4094, description="802.1Q VLAN ID")
    source_mac: str = Field(
        "random", pattern="^(random|real)$", description="chaddr 使用随机或真实 MAC"
    )
    hold: bool = Field(False, description="持续续期保持地址占用")
    duration: float = Field(0.0, ge=0, description="hold 模式运行秒数，0 表示直到手动停止")
    server: str | None = Field(None, description="DHCP 服务器 IP")
    pool: str | None = Field(None, description="DHCP 池区间（如 192.168.99.50-150）")
    blind: bool = Field(False, description="盲写模式（配合 pool/server）")
    raw: bool = Field(False, description="BPF 抓包接收回包")
    verbose: bool = Field(False, description="打印每个收发报文")


class DHCPReleaseRequest(BaseModel):
    """释放地址的请求参数。"""

    iface: str | None = Field(None, description="网卡名（VLAN 模式必填）")
    vlan: int | None = Field(None, ge=1, le=4094, description="VLAN ID")
    server: str | None = Field(None, description="DHCP 服务器 IP")


class DHCPActionResponse(BaseModel):
    """任务操作响应。"""

    state: str = Field(..., description="任务状态")
    message: str = Field("", description="操作结果消息")


@router.post(
    "/start",
    response_model=DHCPActionResponse,
    summary="启动 DHCP 模拟",
    description="伪造随机 MAC 并发获取指定数量的 DHCP 地址。",
)
async def start_dhcp(request: DHCPRunRequest) -> dict[str, str]:
    """启动 DHCP 模拟任务。"""
    try:
        service = get_dhcp_service()
        return service.start(request.model_dump())
    except RuntimeError as e:
        logger.warning("Failed to start DHCP job", error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.warning("Failed to start DHCP job", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start DHCP job: {e}")


@router.post(
    "/stop",
    response_model=DHCPActionResponse,
    summary="停止 DHCP 模拟",
    description="向当前模拟任务发送停止信号并触发清理。",
)
async def stop_dhcp() -> dict[str, str]:
    """停止当前 DHCP 模拟任务。"""
    service = get_dhcp_service()
    return service.stop()


@router.post(
    "/release",
    summary="释放模拟获取的地址",
    description="显式释放状态文件中保存的全部模拟地址。",
)
async def release_dhcp(request: DHCPReleaseRequest) -> dict[str, Any]:
    """释放之前模拟获取的全部 DHCP 地址。"""
    try:
        service = get_dhcp_service()
        result = await service.release(request.iface, request.vlan, request.server)
        return {
            "state": result["state"],
            "message": result["message"],
            "leases": result["leases"],
            "returncode": result["returncode"],
        }
    except Exception as e:
        logger.warning("Failed to release DHCP leases", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to release DHCP leases: {e}")


@router.get(
    "/status",
    summary="获取 DHCP 任务状态",
    description="获取当前任务状态、增量日志与租约结果。",
)
async def get_dhcp_status(after: int = 0) -> dict[str, Any]:
    """获取当前 DHCP 任务状态与增量日志。

    Args:
        after: 日志游标，仅返回序号大于该值的日志行。
    """
    service = get_dhcp_service()
    return service.status(after=after)


@router.get(
    "/leases",
    summary="获取当前租约",
    description="读取状态文件中的租约列表。",
)
async def get_dhcp_leases() -> list[dict[str, Any]]:
    """读取当前租约列表。"""
    service = get_dhcp_service()
    return service.leases()
