"""Tests for ScaleService - large-scale device simulation (F7)."""

from __future__ import annotations

import pytest
from vpn_simulator.services.scale import DEFAULT_TOTAL, ScaleService


def test_default_total_is_30k_plus():
    service = ScaleService()
    assert service.total == DEFAULT_TOTAL == 30000


def test_list_devices_paginates_lazily():
    service = ScaleService(total=1000)
    page = service.list_devices(offset=100, limit=50)
    assert page["total"] == 1000
    assert page["count"] == 50
    assert page["devices"][0]["index"] == 100
    assert page["devices"][-1]["index"] == 149


def test_list_devices_clamps_page_size():
    service = ScaleService(total=1000)
    page = service.list_devices(offset=0, limit=9999)
    assert page["count"] == 1000  # 全部（clamp 到上限 1000）


def test_get_device_deterministic():
    service = ScaleService()
    d1 = service.get_device(123)
    d2 = service.get_device(123)
    assert d1 == d2
    assert d1 is not None
    assert d1["index"] == 123
    assert d1["ip"].startswith("10.")


def test_get_device_out_of_range():
    service = ScaleService(total=100)
    assert service.get_device(99) is not None
    assert service.get_device(100) is None
    assert service.get_device(-1) is None


def test_stats_aggregate():
    service = ScaleService(total=30000)
    stats = service.stats()
    assert stats["total"] == 30000
    assert sum(stats["by_type"].values()) == 30000
    assert sum(stats["by_state"].values()) == 30000
    assert stats["avg_cpu_percent"] == pytest.approx(49.5, abs=0.1)
    assert stats["avg_memory_percent"] == pytest.approx(49.5, abs=0.1)


@pytest.mark.asyncio
async def test_simulate_poll_with_connection_pool():
    service = ScaleService(total=10000, pool_size=200)
    result = await service.simulate_poll(count=1000, concurrency=100)
    assert result["polled"] == 1000
    assert result["concurrency"] == 100
    assert sum(result["by_state"].values()) == 1000
    assert result["duration_ms"] >= 0
    assert result["throughput_devices_per_sec"] > 0
