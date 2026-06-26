import logging

"""IoT 设备模拟 API 路由。"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iot")

# IoT 服务实例（单例）
_iot_service = None


def get_iot_service():
    """获取 IoT 服务实例。"""
    global _iot_service
    if _iot_service is None:
        from vpn_simulator.services.iot import IoTService
        _iot_service = IoTService()
        _iot_service.load_devices()
    return _iot_service


class DeviceInfo(BaseModel):
    """设备信息。"""
    id: str = Field(..., description="设备 ID")
    name: str = Field(..., description="设备名称")
    name_en: str = Field("", description="设备英文名称")
    description: str = Field("", description="设备描述")
    icon: str = Field("device_unknown", description="设备图标")
    category: str = Field("other", description="设备分类")
    protocols: list[str] = Field(default_factory=list, description="支持的协议")
    traffic_pattern: str = Field("periodic", description="流量模式")
    default_params: dict[str, Any] = Field(default_factory=dict, description="默认参数")
    network_profile: dict[str, Any] = Field(default_factory=dict, description="网络流量配置")
    instance_id: Optional[str] = Field(None, description="运行实例 ID")
    state: str = Field("offline", description="设备状态")


class DeviceStartRequest(BaseModel):
    """启动设备请求。"""
    device_id: str = Field(..., description="设备 ID")
    params: Optional[dict[str, Any]] = Field(None, description="设备参数覆盖")


class DeviceActionResponse(BaseModel):
    """设备操作响应。"""
    instance_id: Optional[str] = Field(None, description="实例 ID")
    device_id: str = Field(..., description="设备 ID")
    state: str = Field(..., description="设备状态")
    message: str = Field("", description="操作结果消息")


class DeviceStatusResponse(BaseModel):
    """设备状态响应。"""
    instance_id: str = Field(..., description="实例 ID")
    device_id: str = Field(..., description="设备 ID")
    device_name: str = Field(..., description="设备名称")
    state: str = Field(..., description="设备状态")
    started_at: Optional[float] = Field(None, description="启动时间戳")
    uptime_seconds: float = Field(0, description="运行时长(秒)")
    params: dict[str, Any] = Field(default_factory=dict, description="设备参数")
    stats: dict[str, Any] = Field(default_factory=dict, description="流量统计")
    traffic_pattern: str = Field("", description="流量模式")
    network_profile: dict[str, Any] = Field(default_factory=dict, description="网络配置")


class TrafficStatsResponse(BaseModel):
    """流量统计响应。"""
    total_devices: int = Field(0, description="总设备数")
    online_devices: int = Field(0, description="在线设备数")
    total_packets_sent: int = Field(0, description="总发送包数")
    total_packets_received: int = Field(0, description="总接收包数")
    total_bytes_sent: int = Field(0, description="总发送字节数")
    total_bytes_received: int = Field(0, description="总接收字节数")
    total_errors: int = Field(0, description="总错误数")
    by_pattern: dict[str, Any] = Field(default_factory=dict, description="按流量模式统计")
    by_category: dict[str, Any] = Field(default_factory=dict, description="按分类统计")
    devices: list[dict[str, Any]] = Field(default_factory=list, description="设备详情列表")


@router.get(
    "/devices",
    response_model=list[DeviceInfo],
    summary="列出所有 IoT 设备",
    description="获取所有可用的 IoT 设备配置和运行状态。",
)
async def list_devices(category: Optional[str] = None) -> list[dict[str, Any]]:
    """列出所有 IoT 设备。

    Args:
        category: 可选的设备分类过滤。
    """
    service = get_iot_service()
    return service.list_devices(category=category)


@router.get(
    "/devices/{device_id}",
    response_model=DeviceInfo,
    summary="获取设备详情",
    description="获取指定 IoT 设备的详细配置和状态。",
)
async def get_device(device_id: str) -> dict[str, Any]:
    """获取设备详情。

    Args:
        device_id: 设备 ID。
    """
    service = get_iot_service()
    device = service.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return device


@router.post(
    "/devices/start",
    response_model=DeviceActionResponse,
    summary="启动设备模拟",
    description="启动指定 IoT 设备的网络行为模拟。",
)
async def start_device(request: DeviceStartRequest) -> dict[str, Any]:
    """启动设备模拟。

    Args:
        request: 启动请求，包含设备 ID 和可选参数。
    """
    service = get_iot_service()
    try:
        result = await service.start_device(request.device_id, request.params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start device: {str(e)}")


@router.post(
    "/devices/{instance_id}/stop",
    response_model=DeviceActionResponse,
    summary="停止设备模拟",
    description="停止指定设备实例的网络行为模拟。",
)
async def stop_device(instance_id: str) -> dict[str, Any]:
    """停止设备模拟。

    Args:
        instance_id: 设备实例 ID。
    """
    service = get_iot_service()
    try:
        result = await service.stop_device(instance_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop device: {str(e)}")


@router.get(
    "/devices/{instance_id}/status",
    response_model=DeviceStatusResponse,
    summary="获取设备状态",
    description="获取运行中设备实例的详细状态和统计信息。",
)
async def get_device_status(instance_id: str) -> dict[str, Any]:
    """获取设备状态。

    Args:
        instance_id: 设备实例 ID。
    """
    service = get_iot_service()
    status = await service.get_device_status(instance_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Device instance '{instance_id}' not found")
    return status


@router.get(
    "/traffic",
    response_model=TrafficStatsResponse,
    summary="获取 IoT 流量统计",
    description="获取所有 IoT 设备的流量统计汇总。",
)
async def get_traffic_stats() -> dict[str, Any]:
    """获取 IoT 流量统计。"""
    service = get_iot_service()
    return await service.get_traffic_stats()


@router.post(
    "/devices/stop-all",
    summary="停止所有设备",
    description="停止所有运行中的 IoT 设备模拟。",
)
async def stop_all_devices() -> dict[str, Any]:
    """停止所有设备模拟。"""
    service = get_iot_service()
    return await service.stop_all_devices()


@router.get(
    "/traffic-patterns",
    summary="获取流量模式",
    description="获取所有可用的流量模式定义。",
)
async def get_traffic_patterns() -> dict[str, Any]:
    """获取流量模式定义。"""
    service = get_iot_service()
    return service.get_traffic_patterns()


@router.get(
    "/categories",
    summary="获取设备分类",
    description="获取所有设备分类定义。",
)
async def get_categories() -> dict[str, Any]:
    """获取设备分类定义。"""
    service = get_iot_service()
    return service.get_categories()
