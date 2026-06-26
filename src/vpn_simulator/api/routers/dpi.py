import logging

"""深度包检测 (DPI) API 路由。"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.dpi import dpi_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dpi")


class AnalyzeRequest(BaseModel):
    """分析请求。"""

    payload_hex: str = Field("", description="载荷数据 (十六进制)")
    src_ip: str = Field("", description="源 IP 地址")
    dst_ip: str = Field("", description="目的 IP 地址")
    src_port: int = Field(0, ge=0, le=65535, description="源端口")
    dst_port: int = Field(0, ge=0, le=65535, description="目的端口")


class ProtocolInfo(BaseModel):
    """协议信息。"""

    name: str
    category: str
    default_ports: list[int]
    description: str
    threat_level: str
    is_encrypted: bool
    common_domains: list[str]


class DPIResultResponse(BaseModel):
    """DPI 分析结果。"""

    id: str
    timestamp: str
    protocol: str
    category: str
    confidence: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    payload_size: int
    is_encrypted: bool
    threat_level: str
    metadata: dict[str, Any]
    matched_rules: list[str]


class StatisticsResponse(BaseModel):
    """统计响应。"""

    total_packets: int
    protocol_counts: dict[str, int]
    category_counts: dict[str, int]
    threat_counts: dict[str, int]
    total_bytes: int
    protocol_bytes: dict[str, int]
    avg_confidence: float
    anomaly_count: int


class ClassificationItem(BaseModel):
    """分类项。"""

    category: str
    protocols: list[str]
    packet_count: int
    byte_count: int
    percentage: float
    avg_confidence: float


class AnomalyItem(BaseModel):
    """异常项。"""

    id: str
    timestamp: str
    anomaly_type: str
    severity: str
    description: str
    source_ip: str
    protocol: str
    details: dict[str, Any]


class DistributionResponse(BaseModel):
    """协议分布响应。"""

    protocols: list[str]
    counts: list[int]
    percentages: list[float]
    total: int


@router.get(
    "/protocols",
    response_model=list[ProtocolInfo],
    summary="获取支持的协议列表",
    description="返回 DPI 服务支持识别的所有协议信息。",
)
async def get_protocols() -> list[dict[str, Any]]:
    """获取支持的协议列表。"""
    return dpi_service.get_supported_protocols()


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="获取协议统计",
    description="返回所有已分析数据包的统计信息。",
)
async def get_statistics() -> dict[str, Any]:
    """获取协议统计信息。"""
    return dpi_service.get_statistics()


@router.post(
    "/analyze",
    response_model=DPIResultResponse,
    summary="分析数据包",
    description="对单个数据包进行深度协议检测。",
)
async def analyze_packet(request: AnalyzeRequest) -> dict[str, Any]:
    """分析数据包。"""
    # 解析载荷
    if request.payload_hex:
        try:
            payload = bytes.fromhex(request.payload_hex)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex payload")
    else:
        payload = b""

    result = dpi_service.analyze_packet(
        payload=payload,
        src_ip=request.src_ip,
        dst_ip=request.dst_ip,
        src_port=request.src_port,
        dst_port=request.dst_port,
    )
    return result.to_dict()


@router.get(
    "/classification",
    response_model=list[ClassificationItem],
    summary="获取流量分类",
    description="按协议类别返回流量分类统计。",
)
async def get_classification() -> list[dict[str, Any]]:
    """获取流量分类。"""
    return dpi_service.get_traffic_classification()


@router.get(
    "/distribution",
    response_model=DistributionResponse,
    summary="获取协议分布",
    description="返回协议分布数据，适用于图表展示。",
)
async def get_distribution() -> dict[str, Any]:
    """获取协议分布。"""
    return dpi_service.get_protocol_distribution()


@router.get(
    "/anomalies",
    response_model=list[AnomalyItem],
    summary="获取异常检测结果",
    description="返回检测到的异常事件列表。",
)
async def get_anomalies(
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
) -> list[dict[str, Any]]:
    """获取异常检测结果。"""
    return dpi_service.get_anomalies(limit=limit)


@router.get(
    "/results",
    response_model=list[DPIResultResponse],
    summary="获取最近分析结果",
    description="返回最近的数据包分析结果。",
)
async def get_recent_results(
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
) -> list[dict[str, Any]]:
    """获取最近的分析结果。"""
    return dpi_service.get_recent_results(limit=limit)


@router.post(
    "/samples",
    response_model=list[DPIResultResponse],
    summary="生成模拟流量",
    description="生成模拟流量数据用于测试和演示。",
)
async def generate_samples(
    count: int = Query(50, ge=1, le=500, description="生成数量"),
) -> list[dict[str, Any]]:
    """生成模拟流量数据。"""
    return dpi_service.generate_sample_traffic(count=count)


@router.delete(
    "",
    summary="清除 DPI 数据",
    description="清除所有分析结果和统计数据。",
)
async def clear_data() -> dict[str, str]:
    """清除所有 DPI 数据。"""
    dpi_service.clear()
    return {"status": "success", "message": "DPI data cleared"}
