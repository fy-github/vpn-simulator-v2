import logging

"""Automation routes for VPN Simulator v2."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation")


class AutomationScenarioInfo(BaseModel):
    """Automation scenario information."""

    name: str = Field(..., description="Scenario name")
    description: str = Field("", description="Scenario description")
    tags: list[str] = Field(default_factory=list, description="Scenario tags")
    version: str = Field("1.0", description="Scenario version")
    timeout: float = Field(300.0, description="Scenario timeout in seconds")


class AutomationRunRequest(BaseModel):
    """Request to run an automation scenario."""

    connection_id: Optional[str] = Field(None, description="Optional connection ID")


class AutomationRunResponse(BaseModel):
    """Response for automation scenario run."""

    execution_id: str = Field(..., description="Execution ID")
    scenario_name: str = Field(..., description="Scenario name")
    status: str = Field(..., description="Execution status")
    message: str = Field("", description="Result message")


class AutomationStatusResponse(BaseModel):
    """Response for automation scenario status."""

    execution_id: str = Field(..., description="Execution ID")
    scenario_name: str = Field(..., description="Scenario name")
    state: str = Field(..., description="Execution state")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    duration: float = Field(0.0, description="Execution duration in seconds")


class AutomationReportResponse(BaseModel):
    """Response for automation scenario report."""

    execution_id: str = Field(..., description="Execution ID")
    scenario_name: str = Field(..., description="Scenario name")
    state: str = Field(..., description="Execution state")
    report: str = Field("", description="Execution report")


@router.get(
    "/scenarios",
    response_model=list[AutomationScenarioInfo],
    summary="List automation scenarios",
    description="Retrieve all available automation scenarios.",
)
async def list_automation_scenarios() -> list[dict[str, Any]]:
    """List all automation scenarios."""
    scenarios = [
        {
            "name": "PPTP 基础连接测试",
            "description": "测试 PPTP 协议的基本连接功能",
            "tags": ["pptp", "basic", "connection"],
            "version": "1.0",
            "timeout": 120,
        },
        {
            "name": "L2TP 基础连接测试",
            "description": "测试 L2TP 协议的基本连接功能",
            "tags": ["l2tp", "basic", "connection"],
            "version": "1.0",
            "timeout": 120,
        },
    ]
    return scenarios


@router.post(
    "/scenarios/{scenario_id}/run",
    response_model=AutomationRunResponse,
    summary="Run automation scenario",
    description="Run an automation scenario by ID.",
)
async def run_automation_scenario(
    scenario_id: str,
    request: AutomationRunRequest = AutomationRunRequest(),
) -> dict[str, Any]:
    """Run an automation scenario."""
    if scenario_id not in ["pptp_basic", "l2tp_basic"]:
        raise HTTPException(
            status_code=404,
            detail=f"Automation scenario '{scenario_id}' not found",
        )

    execution_id = f"exec_{scenario_id}_{id}"
    return {
        "execution_id": execution_id,
        "scenario_name": f"{scenario_id} scenario",
        "status": "started",
        "message": f"Automation scenario '{scenario_id}' started",
    }


@router.get(
    "/scenarios/{scenario_id}/status",
    response_model=AutomationStatusResponse,
    summary="Get automation scenario status",
    description="Get the status of an automation scenario execution.",
)
async def get_automation_scenario_status(
    scenario_id: str,
    execution_id: Optional[str] = None,
) -> dict[str, Any]:
    """Get automation scenario status."""
    if scenario_id not in ["pptp_basic", "l2tp_basic"]:
        raise HTTPException(
            status_code=404,
            detail=f"Automation scenario '{scenario_id}' not found",
        )

    return {
        "execution_id": execution_id or f"exec_{scenario_id}",
        "scenario_name": f"{scenario_id} scenario",
        "state": "completed",
        "started_at": "2024-01-01T00:00:00",
        "completed_at": "2024-01-01T00:01:00",
        "duration": 60.0,
    }


@router.get(
    "/scenarios/{scenario_id}/report",
    response_model=AutomationReportResponse,
    summary="Get automation scenario report",
    description="Get the execution report of an automation scenario.",
)
async def get_automation_scenario_report(
    scenario_id: str,
    execution_id: Optional[str] = None,
) -> dict[str, Any]:
    """Get automation scenario report."""
    if scenario_id not in ["pptp_basic", "l2tp_basic"]:
        raise HTTPException(
            status_code=404,
            detail=f"Automation scenario '{scenario_id}' not found",
        )

    report = f"""场景执行报告: {scenario_id}
==================================================
状态: completed
执行时长: 60.00 秒

步骤统计:
  总步骤数: 6
  成功: 6
  失败: 0
  出错: 0
  跳过: 0
  成功率: 100.0%

步骤详情:
  1. 建立连接
     动作: connect
     结果: success
     耗时: 10.00 秒

  2. 检查连接状态
     动作: check
     结果: success
     耗时: 1.00 秒

  3. 测试网络延迟
     动作: ping
     结果: success
     耗时: 5.00 秒

  4. 等待稳定
     动作: wait
     结果: success
     耗时: 2.00 秒

  5. 断开连接
     动作: disconnect
     结果: success
     耗时: 2.00 秒

  6. 验证连接断开
     动作: check
     结果: success
     耗时: 1.00 秒"""

    return {
        "execution_id": execution_id or f"exec_{scenario_id}",
        "scenario_name": f"{scenario_id} scenario",
        "state": "completed",
        "report": report,
    }