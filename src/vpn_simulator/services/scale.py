"""大规模设备模拟服务（F7）。

模拟 30,000+ 台网络设备，采用惰性加载（设备由索引确定性推导，不一次性
物化全部对象），聚合统计 O(1) 计算，并以 asyncio 信号量模拟连接池进行
批量并发巡检。

Example:
    >>> service = ScaleService(total=30000)
    >>> service.stats()["total"]
    30000
    >>> await service.simulate_poll(count=1000)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from vpn_simulator.domain.scale import DEVICE_STATES, SimulatedDevice
from vpn_simulator.domain.snmp import DEVICE_TYPES

logger = structlog.get_logger(__name__)

DEFAULT_TOTAL = 30000
DEFAULT_POOL_SIZE = 1000
MAX_PAGE_SIZE = 1000


class ScaleService:
    """大规模设备模拟服务（惰性加载 + 聚合统计 + 连接池巡检）。"""

    def __init__(self, total: int = DEFAULT_TOTAL, pool_size: int = DEFAULT_POOL_SIZE) -> None:
        self._total = total
        self._pool_size = pool_size

    @property
    def total(self) -> int:
        """设备总数。"""
        return self._total

    # ------------------------------------------------------------------
    # 惰性加载
    # ------------------------------------------------------------------
    def _device_at(self, index: int) -> SimulatedDevice:
        """由索引确定性推导设备（O(1)，无状态）。"""
        device_type = DEVICE_TYPES[index % len(DEVICE_TYPES)]
        state = DEVICE_STATES[index % len(DEVICE_STATES)]
        return SimulatedDevice(
            index=index,
            name=f"{device_type}-{index:06d}",
            device_type=device_type,
            ip=f"10.{(index // 65536) % 256}.{(index // 256) % 256}.{index % 256}",
            state=state,
            cpu_percent=(index * 7) % 100,
            memory_percent=(index * 13) % 100,
        )

    def get_device(self, index: int) -> dict[str, Any] | None:
        """获取指定索引的设备（越界返回 None）。"""
        if index < 0 or index >= self._total:
            return None
        return self._device_at(index).to_dict()

    def list_devices(self, offset: int = 0, limit: int = 100) -> dict[str, Any]:
        """分页列出设备（惰性生成，仅物化当前页）。"""
        offset = max(0, offset)
        limit = min(max(1, limit), MAX_PAGE_SIZE)
        end = min(offset + limit, self._total)
        devices = [self._device_at(i).to_dict() for i in range(offset, end)]
        return {
            "total": self._total,
            "offset": offset,
            "limit": limit,
            "count": len(devices),
            "devices": devices,
        }

    # ------------------------------------------------------------------
    # 聚合统计（O(1)，不物化全部设备）
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        """返回聚合统计（不逐设备计算）。

        按类型/状态分布由索引取模确定性推导，CPU/内存均值按满周期
        （100）精确计算——均为 O(1)。
        """
        types = len(DEVICE_TYPES)
        by_type = {
            DEVICE_TYPES[i]: self._total // types + (1 if i < self._total % types else 0)
            for i in range(types)
        }
        states = len(DEVICE_STATES)
        by_state = {
            DEVICE_STATES[i]: self._total // states + (1 if i < self._total % states else 0)
            for i in range(states)
        }
        return {
            "total": self._total,
            "by_type": by_type,
            "by_state": by_state,
            "avg_cpu_percent": self._avg_percent(7),
            "avg_memory_percent": self._avg_percent(13),
            "pool_size": self._pool_size,
        }

    @staticmethod
    def _avg_percent(multiplier: int) -> float:
        """计算 (i*multiplier) % 100 在满周期上的均值（multiplier 与 100 互素）。"""
        return sum((i * multiplier) % 100 for i in range(100)) / 100.0

    # ------------------------------------------------------------------
    # 批量并发巡检（asyncio + 连接池）
    # ------------------------------------------------------------------
    async def simulate_poll(
        self, count: int | None = None, concurrency: int | None = None
    ) -> dict[str, Any]:
        """模拟对设备的一次批量巡检，用信号量限制并发（连接池）。

        Args:
            count: 巡检设备数（默认全部）。
            concurrency: 并发上限（默认连接池大小）。

        Returns:
            巡检统计（用时、吞吐、状态分布）。
        """
        target = self._total if count is None else min(max(1, count), self._total)
        pool = asyncio.Semaphore(concurrency or self._pool_size)

        async def poll_one(index: int) -> str:
            async with pool:
                device = self._device_at(index)
                await asyncio.sleep(0)  # 模拟一次网络往返
                return device.state

        start = time.perf_counter()
        states = await asyncio.gather(*(poll_one(i) for i in range(target)))
        duration = time.perf_counter() - start

        by_state = {s: states.count(s) for s in DEVICE_STATES}
        logger.info("scale_poll_done", polled=target, duration_ms=round(duration * 1000, 1))
        return {
            "polled": target,
            "duration_ms": round(duration * 1000, 1),
            "throughput_devices_per_sec": round(target / duration, 1) if duration > 0 else 0.0,
            "concurrency": concurrency or self._pool_size,
            "by_state": by_state,
        }
