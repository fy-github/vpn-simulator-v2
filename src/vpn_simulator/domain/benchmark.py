"""基准测试模型。

提供 VPN 协议性能基准测试的数据模型，支持 4 种测试类型：
握手性能、吞吐量、内存使用和并发性能。

每个基准测试实例跟踪其状态和执行结果。

Example:
    >>> benchmark = BenchmarkInfo(
    ...     id="bench-001",
    ...     test_type=BenchmarkType.HANDSHAKE,
    ...     protocol="pptp",
    ... )
    >>> benchmark.status
    BenchmarkStatus.PENDING
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class BenchmarkType(Enum):
    """基准测试类型枚举。

    Attributes:
        HANDSHAKE: 握手性能测试，测量协议握手时间。
        THROUGHPUT: 吞吐量测试，测量数据传输速率。
        MEMORY: 内存使用测试，测量协议内存占用。
        CONCURRENCY: 并发性能测试，测量并发连接处理能力。
    """

    HANDSHAKE = "handshake"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"


class BenchmarkStatus(Enum):
    """基准测试状态枚举。

    Attributes:
        PENDING: 等待执行。
        RUNNING: 正在执行。
        COMPLETED: 执行完成。
        FAILED: 执行失败。
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BenchmarkMetrics:
    """基准测试指标数据类。

    Attributes:
        handshake_time_ms: 握手时间（毫秒）。
        throughput_mbps: 吞吐量（Mbps）。
        memory_mb: 内存占用（MB）。
        cpu_percent: CPU 使用率（%）。
        concurrent_connections: 并发连接数。
    """

    handshake_time_ms: float = 0.0
    throughput_mbps: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    concurrent_connections: int = 0

    def to_dict(self) -> dict[str, Any]:
        """将指标转换为字典。

        Returns:
            包含所有指标的字典。
        """
        return {
            "handshake_time_ms": self.handshake_time_ms,
            "throughput_mbps": self.throughput_mbps,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "concurrent_connections": self.concurrent_connections,
        }


@dataclass
class BenchmarkResult:
    """基准测试结果数据类。

    Attributes:
        metrics: 测试指标。
        duration_seconds: 测试持续时间（秒）。
        iterations: 测试迭代次数。
        details: 详细测试数据。
    """

    metrics: BenchmarkMetrics = field(default_factory=BenchmarkMetrics)
    duration_seconds: float = 0.0
    iterations: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将结果转换为字典。

        Returns:
            包含所有结果信息的字典。
        """
        return {
            "metrics": self.metrics.to_dict(),
            "duration_seconds": self.duration_seconds,
            "iterations": self.iterations,
            "details": self.details,
        }


@dataclass
class BenchmarkInfo:
    """基准测试信息数据类。

    封装一个基准测试实例的完整信息。

    Attributes:
        id: 测试唯一标识符（UUID）。
        test_type: 测试类型。
        protocol: 协议名称。
        status: 测试状态。
        params: 测试参数。
        started_at: 开始时间。
        completed_at: 完成时间。
        result: 测试结果。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    test_type: BenchmarkType = BenchmarkType.HANDSHAKE
    protocol: str = ""
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    params: dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[BenchmarkResult] = None

    def to_dict(self) -> dict[str, Any]:
        """将测试信息转换为字典。

        Returns:
            包含所有测试信息的字典。
        """
        return {
            "id": self.id,
            "test_type": self.test_type.value,
            "protocol": self.protocol,
            "status": self.status.value,
            "params": self.params,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
        }

    def mark_running(self) -> None:
        """将测试标记为正在执行。"""
        self.status = BenchmarkStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self, result: BenchmarkResult) -> None:
        """将测试标记为完成。

        Args:
            result: 测试结果。
        """
        self.status = BenchmarkStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """将测试标记为失败。

        Args:
            error: 错误信息。
        """
        self.status = BenchmarkStatus.FAILED
        self.completed_at = datetime.now()
        self.result = BenchmarkResult(
            details={"error": error},
        )


class BenchmarkManager:
    """基准测试管理器。

    负责基准测试的创建、查询、状态更新和移除。
    """

    def __init__(self) -> None:
        """初始化基准测试管理器。"""
        self._benchmarks: dict[str, BenchmarkInfo] = {}

    async def create_benchmark(
        self,
        test_type: BenchmarkType,
        protocol: str,
        params: Optional[dict[str, Any]] = None,
    ) -> BenchmarkInfo:
        """创建一个基准测试实例。

        Args:
            test_type: 测试类型。
            protocol: 协议名称。
            params: 测试参数。

        Returns:
            新创建的测试信息。
        """
        benchmark = BenchmarkInfo(
            test_type=test_type,
            protocol=protocol,
            params=params or {},
        )
        self._benchmarks[benchmark.id] = benchmark
        return benchmark

    async def get_benchmark(self, benchmark_id: str) -> Optional[BenchmarkInfo]:
        """获取指定基准测试。

        Args:
            benchmark_id: 测试 ID。

        Returns:
            测试信息，不存在返回 None。
        """
        return self._benchmarks.get(benchmark_id)

    async def list_benchmarks(
        self,
        test_type: Optional[BenchmarkType] = None,
        protocol: Optional[str] = None,
        status: Optional[BenchmarkStatus] = None,
    ) -> list[BenchmarkInfo]:
        """列出基准测试。

        Args:
            test_type: 可选的测试类型过滤。
            protocol: 可选的协议名称过滤。
            status: 可选的测试状态过滤。

        Returns:
            测试信息列表。
        """
        benchmarks = list(self._benchmarks.values())
        if test_type:
            benchmarks = [b for b in benchmarks if b.test_type == test_type]
        if protocol:
            benchmarks = [b for b in benchmarks if b.protocol == protocol]
        if status:
            benchmarks = [b for b in benchmarks if b.status == status]
        return benchmarks

    async def remove_benchmark(self, benchmark_id: str) -> bool:
        """移除基准测试。

        Args:
            benchmark_id: 测试 ID。

        Returns:
            True 表示成功移除，False 表示测试不存在。
        """
        if benchmark_id in self._benchmarks:
            del self._benchmarks[benchmark_id]
            return True
        return False

    async def start_benchmark(self, benchmark_id: str) -> Optional[BenchmarkInfo]:
        """启动基准测试。

        Args:
            benchmark_id: 测试 ID。

        Returns:
            更新后的测试信息，不存在返回 None。
        """
        benchmark = self._benchmarks.get(benchmark_id)
        if benchmark:
            benchmark.mark_running()
        return benchmark

    async def complete_benchmark(
        self, benchmark_id: str, result: BenchmarkResult
    ) -> Optional[BenchmarkInfo]:
        """完成基准测试。

        Args:
            benchmark_id: 测试 ID。
            result: 测试结果。

        Returns:
            更新后的测试信息，不存在返回 None。
        """
        benchmark = self._benchmarks.get(benchmark_id)
        if benchmark:
            benchmark.mark_completed(result)
        return benchmark

    async def fail_benchmark(
        self, benchmark_id: str, error: str
    ) -> Optional[BenchmarkInfo]:
        """标记基准测试失败。

        Args:
            benchmark_id: 测试 ID。
            error: 错误信息。

        Returns:
            更新后的测试信息，不存在返回 None。
        """
        benchmark = self._benchmarks.get(benchmark_id)
        if benchmark:
            benchmark.mark_failed(error)
        return benchmark
