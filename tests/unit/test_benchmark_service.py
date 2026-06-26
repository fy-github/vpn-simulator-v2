"""Tests for BenchmarkService - benchmark testing service."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.services.benchmark import BenchmarkService


@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def service(mock_config_manager, tmp_path) -> BenchmarkService:
    svc = BenchmarkService(config_manager=mock_config_manager)
    svc._results_dir = tmp_path / "results"
    svc._results_dir.mkdir(parents=True, exist_ok=True)
    return svc


class TestBenchmarkServiceInit:
    def test_service_creation(self, service: BenchmarkService):
        assert service is not None
        assert service._config_manager is not None
        assert service._benchmark_manager is not None


class TestRunBenchmark:
    @pytest.mark.asyncio
    async def test_run_handshake_benchmark(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "pptp")
        assert result is not None
        assert result["test_type"] == "handshake"
        assert result["protocol"] == "pptp"
        assert result["status"] == "completed"
        assert result["result"] is not None

    @pytest.mark.asyncio
    async def test_run_throughput_benchmark(self, service: BenchmarkService):
        result = await service.run_benchmark("throughput", "wireguard")
        assert result["test_type"] == "throughput"
        assert result["protocol"] == "wireguard"

    @pytest.mark.asyncio
    async def test_run_memory_benchmark(self, service: BenchmarkService):
        result = await service.run_benchmark("memory", "ipsec")
        assert result["test_type"] == "memory"
        assert result["protocol"] == "ipsec"

    @pytest.mark.asyncio
    async def test_run_concurrency_benchmark(self, service: BenchmarkService):
        result = await service.run_benchmark("concurrency", "openvpn")
        assert result["test_type"] == "concurrency"
        assert result["protocol"] == "openvpn"

    @pytest.mark.asyncio
    async def test_run_benchmark_invalid_type(self, service: BenchmarkService):
        with pytest.raises(ValueError, match="Invalid benchmark type"):
            await service.run_benchmark("invalid", "pptp")

    @pytest.mark.asyncio
    async def test_run_benchmark_invalid_protocol(self, service: BenchmarkService):
        with pytest.raises(ValueError, match="Invalid protocol"):
            await service.run_benchmark("handshake", "invalid")

    @pytest.mark.asyncio
    async def test_run_benchmark_with_params(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "pptp", params={"iterations": 50})
        assert result is not None

    @pytest.mark.asyncio
    async def test_run_benchmark_all_protocols(self, service: BenchmarkService):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            result = await service.run_benchmark("handshake", proto)
            assert result["protocol"] == proto

    @pytest.mark.asyncio
    async def test_run_benchmark_all_types(self, service: BenchmarkService):
        for test_type in ["handshake", "throughput", "memory", "concurrency"]:
            result = await service.run_benchmark(test_type, "pptp")
            assert result["test_type"] == test_type


class TestGetBenchmark:
    @pytest.mark.asyncio
    async def test_get_benchmark(self, service: BenchmarkService):
        created = await service.run_benchmark("handshake", "pptp")
        result = await service.get_benchmark(created["id"])
        assert result is not None
        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_benchmark_not_found(self, service: BenchmarkService):
        result = await service.get_benchmark("nonexistent")
        assert result is None


class TestListBenchmarks:
    @pytest.mark.asyncio
    async def test_list_benchmarks_empty(self, service: BenchmarkService):
        benchmarks = await service.list_benchmarks()
        assert len(benchmarks) == 0

    @pytest.mark.asyncio
    async def test_list_benchmarks_with_results(self, service: BenchmarkService):
        await service.run_benchmark("handshake", "pptp")
        await service.run_benchmark("throughput", "wireguard")
        benchmarks = await service.list_benchmarks()
        assert len(benchmarks) == 2

    @pytest.mark.asyncio
    async def test_list_benchmarks_by_type(self, service: BenchmarkService):
        await service.run_benchmark("handshake", "pptp")
        await service.run_benchmark("throughput", "wireguard")
        benchmarks = await service.list_benchmarks(test_type="handshake")
        assert len(benchmarks) == 1

    @pytest.mark.asyncio
    async def test_list_benchmarks_by_protocol(self, service: BenchmarkService):
        await service.run_benchmark("handshake", "pptp")
        await service.run_benchmark("handshake", "wireguard")
        benchmarks = await service.list_benchmarks(protocol="pptp")
        assert len(benchmarks) == 1


class TestGetResults:
    @pytest.mark.asyncio
    async def test_get_results_empty(self, service: BenchmarkService):
        results = await service.get_results()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_results_with_data(self, service: BenchmarkService):
        await service.run_benchmark("handshake", "pptp")
        results = await service.get_results()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_results_with_limit(self, service: BenchmarkService):
        for i in range(5):
            await service.run_benchmark("handshake", "pptp")
        results = await service.get_results(limit=3)
        assert len(results) == 3


class TestCompareResults:
    @pytest.mark.asyncio
    async def test_compare_results(self, service: BenchmarkService):
        baseline = await service.run_benchmark("handshake", "pptp")
        current = await service.run_benchmark("handshake", "pptp")
        result = await service.compare_results(baseline["id"], current["id"])
        assert "baseline" in result
        assert "current" in result
        assert "changes" in result

    @pytest.mark.asyncio
    async def test_compare_results_baseline_not_found(self, service: BenchmarkService):
        current = await service.run_benchmark("handshake", "pptp")
        with pytest.raises(ValueError, match="not found"):
            await service.compare_results("nonexistent", current["id"])

    @pytest.mark.asyncio
    async def test_compare_results_current_not_found(self, service: BenchmarkService):
        baseline = await service.run_benchmark("handshake", "pptp")
        with pytest.raises(ValueError, match="not found"):
            await service.compare_results(baseline["id"], "nonexistent")


class TestSimulatedData:
    @pytest.mark.asyncio
    async def test_handshake_metrics(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "wireguard")
        metrics = result["result"]["metrics"]
        assert metrics["handshake_time_ms"] >= 5.0
        assert metrics["handshake_time_ms"] <= 15.0

    @pytest.mark.asyncio
    async def test_throughput_metrics(self, service: BenchmarkService):
        result = await service.run_benchmark("throughput", "wireguard")
        metrics = result["result"]["metrics"]
        assert metrics["throughput_mbps"] >= 200.0
        assert metrics["throughput_mbps"] <= 800.0

    @pytest.mark.asyncio
    async def test_memory_metrics(self, service: BenchmarkService):
        result = await service.run_benchmark("memory", "wireguard")
        metrics = result["result"]["metrics"]
        assert metrics["memory_mb"] >= 5.0
        assert metrics["memory_mb"] <= 15.0

    @pytest.mark.asyncio
    async def test_concurrency_metrics(self, service: BenchmarkService):
        result = await service.run_benchmark("concurrency", "wireguard")
        metrics = result["result"]["metrics"]
        assert metrics["concurrent_connections"] >= 200
        assert metrics["concurrent_connections"] <= 1000


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_benchmark_result_structure(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "pptp")
        assert "id" in result
        assert "test_type" in result
        assert "protocol" in result
        assert "status" in result
        assert "result" in result
        assert "started_at" in result
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_benchmark_result_metrics(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "pptp")
        metrics = result["result"]["metrics"]
        assert "handshake_time_ms" in metrics
        assert "cpu_percent" in metrics

    @pytest.mark.asyncio
    async def test_benchmark_result_details(self, service: BenchmarkService):
        result = await service.run_benchmark("handshake", "pptp")
        details = result["result"]["details"]
        assert details["test_type"] == "handshake"
        assert details["protocol"] == "pptp"
        assert details["simulated"] is True
