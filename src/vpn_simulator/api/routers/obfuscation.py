import logging

"""流量混淆测试 API 路由。"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.obfuscation import obfuscation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obfuscation")


class ObfuscationTestRequest(BaseModel):
    """混淆测试请求。"""
    technique: str = Field(..., description="混淆技术名称")
    packet_count: int = Field(1000, ge=100, le=10000, description="模拟数据包数量")
    duration_seconds: float = Field(10.0, ge=1.0, le=60.0, description="模拟测试时长（秒）")


class TechniqueInfoResponse(BaseModel):
    """混淆技术信息响应。"""
    name: str
    technique: str
    description: str
    transport_protocol: str
    default_port: int
    encryption: str
    resistance_level: str
    use_cases: list[str]


class TrafficFeaturesResponse(BaseModel):
    """流量特征响应。"""
    avg_packet_size: float
    packet_size_std: float
    avg_interval_ms: float
    interval_std_ms: float
    burst_ratio: float
    protocol_distribution: dict[str, float]
    port_distribution: dict[str, float]


class ShannonEntropyResponse(BaseModel):
    """Shannon 熵响应。"""
    payload_entropy: float
    header_entropy: float
    overall_entropy: float
    randomness_score: float


class ObfuscationTestResultResponse(BaseModel):
    """混淆测试结果响应。"""
    id: str
    timestamp: str
    technique: str
    detection_rate: float
    false_positive_rate: float
    traffic_features: TrafficFeaturesResponse
    shannon_entropy: ShannonEntropyResponse
    detection_difficulty: str
    detection_score: float
    packets_analyzed: int
    duration_seconds: float
    metadata: dict[str, Any]


class ComparisonMetrics(BaseModel):
    """对比指标。"""
    avg_detection_rate: float
    avg_false_positive_rate: float
    avg_detection_score: float
    avg_entropy: float
    test_count: int


class RankingItem(BaseModel):
    """排名项。"""
    rank: int
    technique: str
    score: float


class ComparisonResponse(BaseModel):
    """对比结果响应。"""
    techniques: list[str]
    metrics: dict[str, ComparisonMetrics]
    rankings: dict[str, list[RankingItem]]


@router.get(
    "/techniques",
    response_model=list[TechniqueInfoResponse],
    summary="获取支持的混淆技术",
    description="返回所有支持的混淆技术信息。",
)
async def get_techniques() -> list[dict[str, Any]]:
    """获取支持的混淆技术列表。"""
    return obfuscation_service.get_supported_techniques()


@router.post(
    "/test",
    response_model=ObfuscationTestResultResponse,
    summary="运行混淆测试",
    description="对指定的混淆技术进行测试评估。",
)
async def run_test(request: ObfuscationTestRequest) -> dict[str, Any]:
    """运行混淆测试。"""
    try:
        return obfuscation_service.run_test(
            technique=request.technique,
            packet_count=request.packet_count,
            duration_seconds=request.duration_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/results",
    response_model=list[ObfuscationTestResultResponse],
    summary="获取测试结果",
    description="返回最近的混淆测试结果。",
)
async def get_results(
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
) -> list[dict[str, Any]]:
    """获取测试结果。"""
    return obfuscation_service.get_results(limit=limit)


@router.get(
    "/comparison",
    response_model=ComparisonResponse,
    summary="获取对比结果",
    description="返回混淆技术的对比分析结果。",
)
async def get_comparison() -> dict[str, Any]:
    """获取对比结果。"""
    return obfuscation_service.get_comparison()


@router.delete(
    "",
    summary="清除测试数据",
    description="清除所有混淆测试结果。",
)
async def clear_data() -> dict[str, str]:
    """清除所有测试数据。"""
    obfuscation_service.clear()
    return {"status": "success", "message": "Obfuscation test data cleared"}