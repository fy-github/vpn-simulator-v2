"""IoT 设备模拟服务。

提供 IoT 设备的网络行为模拟，包括设备管理、流量生成和状态监控。

Example:
    >>> from vpn_simulator.services.iot import IoTService
    >>> service = IoTService()
    >>> service.load_devices()
    >>> await service.start_device("ip_camera")
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)

# 默认配置路径
DEFAULT_DEVICES_PATH = Path(__file__).parent.parent.parent.parent / "config" / "iot" / "devices.yaml"


class TrafficPattern(str, Enum):
    """流量模式枚举。"""
    CONTINUOUS = "continuous"
    PERIODIC = "periodic"
    BURST = "burst"
    IDLE = "idle"


class DeviceState(str, Enum):
    """设备状态枚举。"""
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    ERROR = "error"


@dataclass
class NetworkProfile:
    """网络流量配置。"""
    upload_kbps: float = 0.0
    download_kbps: float = 0.0
    packet_size_bytes: int = 64
    interval_ms: int = 1000


@dataclass
class DeviceConfig:
    """IoT 设备配置。"""
    id: str
    name: str
    name_en: str
    description: str
    icon: str
    category: str
    protocols: list[str]
    traffic_pattern: TrafficPattern
    default_params: dict[str, Any]
    network_profile: NetworkProfile


@dataclass
class DeviceInstance:
    """运行中的设备实例。"""
    instance_id: str
    device_id: str
    config: DeviceConfig
    state: DeviceState = DeviceState.OFFLINE
    started_at: Optional[float] = None
    params: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    _task: Optional[asyncio.Task] = field(default=None, repr=False)


class IoTService:
    """IoT 设备模拟服务。

    管理 IoT 设备的生命周期，模拟设备的网络流量行为。

    Attributes:
        _devices_path: 设备配置文件路径。
        _device_configs: 设备配置字典。
        _instances: 运行中的设备实例字典。
    """

    def __init__(self, devices_path: Optional[Path] = None) -> None:
        """初始化 IoT 服务。

        Args:
            devices_path: 设备配置文件路径，默认使用内置配置。
        """
        self._devices_path = devices_path or DEFAULT_DEVICES_PATH
        self._device_configs: dict[str, DeviceConfig] = {}
        self._instances: dict[str, DeviceInstance] = {}
        self._traffic_patterns: dict[str, dict[str, Any]] = {}
        self._categories: dict[str, dict[str, Any]] = {}

    def load_devices(self) -> None:
        """从 YAML 文件加载设备配置。"""
        if not self._devices_path.exists():
            logger.warning("devices_config_not_found", path=str(self._devices_path))
            return

        try:
            with open(self._devices_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 加载设备配置
            for device_id, device_data in data.get("devices", {}).items():
                network_profile = NetworkProfile(
                    upload_kbps=device_data.get("network_profile", {}).get("upload_kbps", 0),
                    download_kbps=device_data.get("network_profile", {}).get("download_kbps", 0),
                    packet_size_bytes=device_data.get("network_profile", {}).get("packet_size_bytes", 64),
                    interval_ms=device_data.get("network_profile", {}).get("interval_ms", 1000),
                )

                config = DeviceConfig(
                    id=device_data.get("id", device_id),
                    name=device_data.get("name", device_id),
                    name_en=device_data.get("name_en", device_id),
                    description=device_data.get("description", ""),
                    icon=device_data.get("icon", "device_unknown"),
                    category=device_data.get("category", "other"),
                    protocols=device_data.get("protocols", []),
                    traffic_pattern=TrafficPattern(device_data.get("traffic_pattern", "periodic")),
                    default_params=device_data.get("default_params", {}),
                    network_profile=network_profile,
                )
                self._device_configs[device_id] = config

            # 加载流量模式
            self._traffic_patterns = data.get("traffic_patterns", {})

            # 加载分类
            self._categories = data.get("categories", {})

            logger.info(
                "iot_devices_loaded",
                count=len(self._device_configs),
                path=str(self._devices_path),
            )
        except Exception as e:
            logger.error("iot_devices_load_error", path=str(self._devices_path), error=str(e))

    def list_devices(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """列出所有可用设备配置。

        Args:
            category: 可选的分类过滤。

        Returns:
            设备配置字典列表。
        """
        devices = list(self._device_configs.values())
        if category:
            devices = [d for d in devices if d.category == category]

        result = []
        for device in devices:
            instance = self._find_instance_by_device_id(device.id)
            result.append({
                "id": device.id,
                "name": device.name,
                "name_en": device.name_en,
                "description": device.description,
                "icon": device.icon,
                "category": device.category,
                "protocols": device.protocols,
                "traffic_pattern": device.traffic_pattern.value,
                "default_params": device.default_params,
                "network_profile": {
                    "upload_kbps": device.network_profile.upload_kbps,
                    "download_kbps": device.network_profile.download_kbps,
                    "packet_size_bytes": device.network_profile.packet_size_bytes,
                    "interval_ms": device.network_profile.interval_ms,
                },
                "instance_id": instance.instance_id if instance else None,
                "state": instance.state.value if instance else DeviceState.OFFLINE.value,
            })

        return result

    def get_device(self, device_id: str) -> Optional[dict[str, Any]]:
        """获取指定设备的详细信息。

        Args:
            device_id: 设备 ID。

        Returns:
            设备信息字典，不存在返回 None。
        """
        device = self._device_configs.get(device_id)
        if device is None:
            return None

        instance = self._find_instance_by_device_id(device_id)
        return {
            "id": device.id,
            "name": device.name,
            "name_en": device.name_en,
            "description": device.description,
            "icon": device.icon,
            "category": device.category,
            "protocols": device.protocols,
            "traffic_pattern": device.traffic_pattern.value,
            "default_params": device.default_params,
            "network_profile": {
                "upload_kbps": device.network_profile.upload_kbps,
                "download_kbps": device.network_profile.download_kbps,
                "packet_size_bytes": device.network_profile.packet_size_bytes,
                "interval_ms": device.network_profile.interval_ms,
            },
            "instance_id": instance.instance_id if instance else None,
            "state": instance.state.value if instance else DeviceState.OFFLINE.value,
            "started_at": instance.started_at if instance else None,
            "stats": instance.stats if instance else {},
        }

    async def start_device(
        self,
        device_id: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """启动设备模拟。

        Args:
            device_id: 设备 ID。
            params: 可选的设备参数覆盖。

        Returns:
            包含启动结果的字典。

        Raises:
            ValueError: 设备不存在或已在运行。
        """
        device_config = self._device_configs.get(device_id)
        if device_config is None:
            raise ValueError(f"Device '{device_id}' not found")

        # 检查是否已有运行实例
        existing = self._find_instance_by_device_id(device_id)
        if existing and existing.state in (DeviceState.ONLINE, DeviceState.STARTING):
            raise ValueError(f"Device '{device_id}' is already running")

        # 创建新实例
        instance_id = f"iot_{device_id}_{uuid.uuid4().hex[:8]}"
        merged_params = {**device_config.default_params, **(params or {})}

        instance = DeviceInstance(
            instance_id=instance_id,
            device_id=device_id,
            config=device_config,
            state=DeviceState.STARTING,
            params=merged_params,
            stats={
                "packets_sent": 0,
                "packets_received": 0,
                "bytes_sent": 0,
                "bytes_received": 0,
                "errors": 0,
            },
        )

        self._instances[instance_id] = instance

        # 启动模拟任务
        instance._task = asyncio.create_task(self._run_device_simulation(instance))
        instance.state = DeviceState.ONLINE
        instance.started_at = time.time()

        logger.info(
            "iot_device_started",
            instance_id=instance_id,
            device_id=device_id,
            pattern=device_config.traffic_pattern.value,
        )

        return {
            "instance_id": instance_id,
            "device_id": device_id,
            "state": instance.state.value,
            "message": f"Device '{device_config.name}' started successfully",
        }

    async def stop_device(self, instance_id: str) -> dict[str, Any]:
        """停止设备模拟。

        Args:
            instance_id: 设备实例 ID。

        Returns:
            包含停止结果的字典。

        Raises:
            ValueError: 实例不存在。
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            raise ValueError(f"Device instance '{instance_id}' not found")

        # 取消任务
        if instance._task and not instance._task.done():
            instance._task.cancel()
            try:
                await instance._task
            except asyncio.CancelledError:
                pass

        instance.state = DeviceState.OFFLINE
        instance._task = None

        logger.info(
            "iot_device_stopped",
            instance_id=instance_id,
            device_id=instance.device_id,
        )

        return {
            "instance_id": instance_id,
            "device_id": instance.device_id,
            "state": instance.state.value,
            "message": f"Device '{instance.config.name}' stopped successfully",
        }

    async def get_device_status(self, instance_id: str) -> Optional[dict[str, Any]]:
        """获取设备实例状态。

        Args:
            instance_id: 设备实例 ID。

        Returns:
            设备状态字典，不存在返回 None。
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        uptime = time.time() - instance.started_at if instance.started_at else 0

        return {
            "instance_id": instance.instance_id,
            "device_id": instance.device_id,
            "device_name": instance.config.name,
            "state": instance.state.value,
            "started_at": instance.started_at,
            "uptime_seconds": uptime,
            "params": instance.params,
            "stats": instance.stats,
            "traffic_pattern": instance.config.traffic_pattern.value,
            "network_profile": {
                "upload_kbps": instance.config.network_profile.upload_kbps,
                "download_kbps": instance.config.network_profile.download_kbps,
                "packet_size_bytes": instance.config.network_profile.packet_size_bytes,
                "interval_ms": instance.config.network_profile.interval_ms,
            },
        }

    async def get_traffic_stats(self) -> dict[str, Any]:
        """获取所有设备的流量统计。

        Returns:
            流量统计汇总字典。
        """
        total_stats = {
            "total_devices": len(self._instances),
            "online_devices": 0,
            "total_packets_sent": 0,
            "total_packets_received": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_errors": 0,
            "by_pattern": {},
            "by_category": {},
            "devices": [],
        }

        for instance in self._instances.values():
            if instance.state == DeviceState.ONLINE:
                total_stats["online_devices"] += 1

            total_stats["total_packets_sent"] += instance.stats.get("packets_sent", 0)
            total_stats["total_packets_received"] += instance.stats.get("packets_received", 0)
            total_stats["total_bytes_sent"] += instance.stats.get("bytes_sent", 0)
            total_stats["total_bytes_received"] += instance.stats.get("bytes_received", 0)
            total_stats["total_errors"] += instance.stats.get("errors", 0)

            # 按流量模式统计
            pattern = instance.config.traffic_pattern.value
            if pattern not in total_stats["by_pattern"]:
                total_stats["by_pattern"][pattern] = {
                    "count": 0,
                    "bytes_sent": 0,
                    "bytes_received": 0,
                }
            total_stats["by_pattern"][pattern]["count"] += 1
            total_stats["by_pattern"][pattern]["bytes_sent"] += instance.stats.get("bytes_sent", 0)
            total_stats["by_pattern"][pattern]["bytes_received"] += instance.stats.get("bytes_received", 0)

            # 按分类统计
            category = instance.config.category
            if category not in total_stats["by_category"]:
                total_stats["by_category"][category] = {
                    "count": 0,
                    "bytes_sent": 0,
                    "bytes_received": 0,
                }
            total_stats["by_category"][category]["count"] += 1
            total_stats["by_category"][category]["bytes_sent"] += instance.stats.get("bytes_sent", 0)
            total_stats["by_category"][category]["bytes_received"] += instance.stats.get("bytes_received", 0)

            # 设备详情
            total_stats["devices"].append({
                "instance_id": instance.instance_id,
                "device_id": instance.device_id,
                "device_name": instance.config.name,
                "state": instance.state.value,
                "traffic_pattern": pattern,
                "category": category,
                "stats": instance.stats,
            })

        return total_stats

    async def stop_all_devices(self) -> dict[str, Any]:
        """停止所有设备模拟。

        Returns:
            包含停止结果的字典。
        """
        stopped_count = 0
        for instance_id in list(self._instances.keys()):
            try:
                await self.stop_device(instance_id)
                stopped_count += 1
            except Exception as e:
                logger.error("iot_device_stop_error", instance_id=instance_id, error=str(e))

        return {
            "stopped_count": stopped_count,
            "message": f"Stopped {stopped_count} devices",
        }

    def get_traffic_patterns(self) -> dict[str, Any]:
        """获取流量模式信息。

        Returns:
            流量模式字典。
        """
        return self._traffic_patterns

    def get_categories(self) -> dict[str, Any]:
        """获取设备分类信息。

        Returns:
            设备分类字典。
        """
        return self._categories

    def _find_instance_by_device_id(self, device_id: str) -> Optional[DeviceInstance]:
        """根据设备 ID 查找运行中的实例。"""
        for instance in self._instances.values():
            if instance.device_id == device_id and instance.state in (DeviceState.ONLINE, DeviceState.STARTING):
                return instance
        return None

    async def _run_device_simulation(self, instance: DeviceInstance) -> None:
        """运行设备流量模拟。

        Args:
            instance: 设备实例。
        """
        pattern = instance.config.traffic_pattern
        profile = instance.config.network_profile

        try:
            while instance.state == DeviceState.ONLINE:
                if pattern == TrafficPattern.CONTINUOUS:
                    await self._simulate_continuous(instance, profile)
                elif pattern == TrafficPattern.PERIODIC:
                    await self._simulate_periodic(instance, profile)
                elif pattern == TrafficPattern.BURST:
                    await self._simulate_burst(instance, profile)
                elif pattern == TrafficPattern.IDLE:
                    await self._simulate_idle(instance, profile)
                else:
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.debug("iot_simulation_cancelled", instance_id=instance.instance_id)
        except Exception as e:
            logger.error(
                "iot_simulation_error",
                instance_id=instance.instance_id,
                error=str(e),
            )
            instance.state = DeviceState.ERROR
            instance.stats["errors"] += 1

    async def _simulate_continuous(self, instance: DeviceInstance, profile: NetworkProfile) -> None:
        """模拟持续流模式。"""
        interval = profile.interval_ms / 1000.0
        packet_size = profile.packet_size_bytes

        # 模拟数据包发送
        instance.stats["packets_sent"] += 1
        instance.stats["bytes_sent"] += packet_size
        instance.stats["packets_received"] += 1
        instance.stats["bytes_received"] += packet_size // 10  # 下行通常较小

        await asyncio.sleep(interval)

    async def _simulate_periodic(self, instance: DeviceInstance, profile: NetworkProfile) -> None:
        """模拟周期性模式。"""
        interval = profile.interval_ms / 1000.0
        packet_size = profile.packet_size_bytes

        # 模拟数据上报
        instance.stats["packets_sent"] += 1
        instance.stats["bytes_sent"] += packet_size

        # 模拟响应
        instance.stats["packets_received"] += 1
        instance.stats["bytes_received"] += 32  # ACK

        await asyncio.sleep(interval)

    async def _simulate_burst(self, instance: DeviceInstance, profile: NetworkProfile) -> None:
        """模拟突发性模式。"""
        # 大部分时间空闲
        idle_time = random.uniform(5, 30)
        await asyncio.sleep(idle_time)

        # 突发数据
        burst_count = random.randint(10, 100)
        packet_size = profile.packet_size_bytes

        for _ in range(burst_count):
            instance.stats["packets_sent"] += 1
            instance.stats["bytes_sent"] += packet_size
            instance.stats["packets_received"] += 1
            instance.stats["bytes_received"] += packet_size // 2
            await asyncio.sleep(profile.interval_ms / 1000.0)

    async def _simulate_idle(self, instance: DeviceInstance, profile: NetworkProfile) -> None:
        """模拟空闲模式。"""
        # 长时间空闲
        idle_time = random.uniform(60, 600)
        await asyncio.sleep(idle_time)

        # 偶尔心跳
        instance.stats["packets_sent"] += 1
        instance.stats["bytes_sent"] += profile.packet_size_bytes
        instance.stats["packets_received"] += 1
        instance.stats["bytes_received"] += 16  # 小响应
