"""基准测试服务。

提供 VPN 协议性能基准测试的创建、查询、执行和结果管理。
使用模拟数据生成基准测试结果。

Example:
    >>> from vpn_simulator.core import ConfigManager
    >>> service = BenchmarkService(config_manager)
    >>> result = await service.run_benchmark("handshake", "pptp")
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.domain.benchmark import (
    BenchmarkInfo,
    BenchmarkManager,
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkType,
)

logger = structlog.get_logger(__name__)

_SIMULATED_DATA: dict[str, dict[str, dict[str, Any]]] = {
    "handshake": {
        "pptp": {"min_ms": 15.0, "max_ms": 45.0},
        "l2tp": {"min_ms": 20.0, "max_ms": 55.0},
        "openvpn": {"min_ms": 100.0, "max_ms": 350.0},
        "ipsec": {"min_ms": 80.0, "max_ms": 250.0},
        "ikev2": {"min_ms": 60.0, "max_ms": 180.0},
        "wireguard": {"min_ms": 5.0, "max_ms": 15.0},
    },
    "throughput": {
        "pptp": {"min_mbps": 50.0, "max_mbps": 150.0},
        "l2tp": {"min_mbps": 45.0, "max_mbps": 140.0},
        "openvpn": {"min_mbps": 80.0, "max_mbps": 300.0},
        "ipsec": {"min_mbps": 100.0, "max_mbps": 400.0},
        "ikev2": {"min_mbps": 120.0, "max_mbps": 450.0},
        "wireguard": {"min_mbps": 200.0, "max_mbps": 800.0},
    },
    "memory": {
        "pptp": {"min_mb": 10.0, "max_mb": 25.0},
        "l2tp": {"min_mb": 12.0, "max_mb": 28.0},
        "openvpn": {"min_mb": 25.0, "max_mb": 60.0},
        "ipsec": {"min_mb": 20.0, "max_mb": 50.0},
        "ikev2": {"min_mb": 18.0, "max_mb": 45.0},
        "wireguard": {"min_mb": 5.0, "max_mb": 15.0},
    },
    "concurrency": {
        "pptp": {"min_conn": 50, "max_conn": 200},
        "l2tp": {"min_conn": 45, "max_conn": 180},
        "openvpn": {"min_conn": 100, "max_conn": 500},
        "ipsec": {"min_conn": 80, "max_conn": 400},
        "ikev2": {"min_conn": 90, "max_conn": 450},
        "wireguard": {"min_conn": 200, "max_conn": 1000},
    },
}

_RESULTS_DIR = Path("benchmark_results")


class BenchmarkService:
    """基准测试服务。"""

    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager
        self._benchmark_manager = BenchmarkManager()
        self._results_dir = _RESULTS_DIR
        self._results_dir.mkdir(parents=True, exist_ok=True)

    async def run_benchmark(
        self,
        test_type: str,
        protocol: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            bt = BenchmarkType(test_type)
        except ValueError:
            raise ValueError(
                f"Invalid benchmark type '{test_type}'. "
                f"Valid types: {[t.value for t in BenchmarkType]}"
            )

        valid_protocols = ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]
        if protocol.lower() not in valid_protocols:
            raise ValueError(
                f"Invalid protocol '{protocol}'. Valid protocols: {valid_protocols}"
            )

        benchmark = await self._benchmark_manager.create_benchmark(
            test_type=bt, protocol=protocol.lower(), params=params or {},
        )
        await self._benchmark_manager.start_benchmark(benchmark.id)

        result = self._generate_simulated_result(test_type, protocol.lower())
        await self._benchmark_manager.complete_benchmark(benchmark.id, result)
        await self._save_result(benchmark)

        logger.info(
            "benchmark_completed",
            benchmark_id=benchmark.id,
            test_type=test_type,
            protocol=protocol,
        )
        return benchmark.to_dict()

    async def get_benchmark(self, benchmark_id: str) -> Optional[dict[str, Any]]:
        benchmark = await self._benchmark_manager.get_benchmark(benchmark_id)
        if benchmark is None:
            return None
        return benchmark.to_dict()

    async def list_benchmarks(
        self,
        test_type: Optional[str] = None,
        protocol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        bt = BenchmarkType(test_type) if test_type else None
        bs = BenchmarkStatus(status) if status else None
        benchmarks = await self._benchmark_manager.list_benchmarks(
            test_type=bt, protocol=protocol, status=bs,
        )
        return [b.to_dict() for b in benchmarks]

    async def get_results(self, limit: int = 10) -> list[dict[str, Any]]:
        results = []
        for filepath in sorted(self._results_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(filepath.read_text())
                results.append(data)
            except Exception:
                continue
            if len(results) >= limit:
                break
        return results

    async def compare_results(
        self, baseline_id: str, current_id: str,
    ) -> dict[str, Any]:
        baseline_data = self._load_result_from_file(baseline_id)
        current_data = self._load_result_from_file(current_id)

        if baseline_data is None:
            raise ValueError(f"Baseline benchmark '{baseline_id}' not found")
        if current_data is None:
            raise ValueError(f"Current benchmark '{current_id}' not found")

        if baseline_data.get("result") is None:
            raise ValueError(f"Baseline benchmark '{baseline_id}' has no results")
        if current_data.get("result") is None:
            raise ValueError(f"Current benchmark '{current_id}' has no results")

        baseline_metrics = baseline_data["result"]["metrics"]
        current_metrics = current_data["result"]["metrics"]

        def _calc_change(baseline_val: float, current_val: float) -> dict[str, Any]:
            if baseline_val == 0:
                return {"absolute": current_val, "percent": 0.0}
            change = current_val - baseline_val
            percent = (change / baseline_val) * 100
            return {"absolute": change, "percent": percent}

        return {
            "baseline": baseline_data,
            "current": current_data,
            "changes": {
                "handshake_time_ms": _calc_change(
                    baseline_metrics.get("handshake_time_ms", 0),
                    current_metrics.get("handshake_time_ms", 0),
                ),
                "throughput_mbps": _calc_change(
                    baseline_metrics.get("throughput_mbps", 0),
                    current_metrics.get("throughput_mbps", 0),
                ),
                "memory_mb": _calc_change(
                    baseline_metrics.get("memory_mb", 0),
                    current_metrics.get("memory_mb", 0),
                ),
                "cpu_percent": _calc_change(
                    baseline_metrics.get("cpu_percent", 0),
                    current_metrics.get("cpu_percent", 0),
                ),
                "concurrent_connections": _calc_change(
                    float(baseline_metrics.get("concurrent_connections", 0)),
                    float(current_metrics.get("concurrent_connections", 0)),
                ),
            },
        }

    def _load_result_from_file(self, benchmark_id: str) -> Optional[dict[str, Any]]:
        for filepath in self._results_dir.glob("*.json"):
            if filepath.stem.startswith(benchmark_id):
                try:
                    return json.loads(filepath.read_text())
                except Exception:
                    continue
        return None

    def _generate_simulated_result(
        self, test_type: str, protocol: str,
    ) -> BenchmarkResult:
        data = _SIMULATED_DATA.get(test_type, {}).get(protocol, {})
        if not data:
            data = {"min_ms": 10.0, "max_ms": 50.0}

        duration = random.uniform(1.0, 5.0)
        iterations = random.randint(10, 100)

        real_cpu = self._get_real_cpu()
        real_mem = self._get_real_memory()

        metrics = BenchmarkMetrics()
        if test_type == "handshake":
            metrics.handshake_time_ms = random.uniform(data["min_ms"], data["max_ms"])
            metrics.cpu_percent = real_cpu
        elif test_type == "throughput":
            metrics.throughput_mbps = random.uniform(data["min_mbps"], data["max_mbps"])
            metrics.cpu_percent = real_cpu
        elif test_type == "memory":
            metrics.memory_mb = real_mem
            metrics.cpu_percent = real_cpu
        elif test_type == "concurrency":
            metrics.concurrent_connections = random.randint(data["min_conn"], data["max_conn"])
            metrics.cpu_percent = real_cpu

        return BenchmarkResult(
            metrics=metrics,
            duration_seconds=duration,
            iterations=iterations,
            details={
                "test_type": test_type,
                "protocol": protocol,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _get_real_cpu(self) -> float:
        try:
            import psutil
            return round(psutil.cpu_percent(interval=0.1), 1)
        except (ImportError, Exception):
            return 0.0

    def _get_real_memory(self) -> float:
        try:
            import psutil
            return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
        except (ImportError, Exception):
            return 0.0

    async def _save_result(self, benchmark: BenchmarkInfo) -> None:
        filename = f"{benchmark.id}_{benchmark.test_type.value}_{benchmark.protocol}.json"
        filepath = self._results_dir / filename

        result_data = {
            "id": benchmark.id,
            "test_type": benchmark.test_type.value,
            "protocol": benchmark.protocol,
            "status": benchmark.status.value,
            "started_at": benchmark.started_at.isoformat() if benchmark.started_at else None,
            "completed_at": benchmark.completed_at.isoformat() if benchmark.completed_at else None,
            "result": benchmark.result.to_dict() if benchmark.result else None,
        }

        filepath.write_text(json.dumps(result_data, indent=2, ensure_ascii=False))
