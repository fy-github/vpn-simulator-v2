"""Tests for IoTService - IoT device simulation service."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from vpn_simulator.services.iot import (
    DeviceConfig,
    DeviceInstance,
    DeviceState,
    IoTService,
    NetworkProfile,
    TrafficPattern,
)


@pytest.fixture
def temp_devices_file(tmp_path: Path) -> Path:
    import yaml
    devices_data = {
        "devices": {
            "ip_camera": {
                "id": "ip_camera",
                "name": "IP Camera",
                "name_en": "IP Camera",
                "description": "Network camera",
                "icon": "videocam",
                "category": "security",
                "protocols": ["RTSP", "HTTP"],
                "traffic_pattern": "continuous",
                "default_params": {"bitrate_kbps": 4000},
                "network_profile": {
                    "upload_kbps": 4000,
                    "download_kbps": 100,
                    "packet_size_bytes": 1400,
                    "interval_ms": 33,
                },
            },
            "temp_sensor": {
                "id": "temp_sensor",
                "name": "Temperature Sensor",
                "name_en": "Temperature Sensor",
                "description": "Temperature sensor",
                "icon": "thermostat",
                "category": "sensor",
                "protocols": ["MQTT"],
                "traffic_pattern": "periodic",
                "default_params": {"interval_sec": 60},
                "network_profile": {
                    "upload_kbps": 1,
                    "download_kbps": 1,
                    "packet_size_bytes": 128,
                    "interval_ms": 60000,
                },
            },
            "smart_speaker": {
                "id": "smart_speaker",
                "name": "Smart Speaker",
                "name_en": "Smart Speaker",
                "description": "Voice assistant",
                "icon": "speaker",
                "category": "consumer",
                "protocols": ["HTTPS"],
                "traffic_pattern": "burst",
                "default_params": {},
                "network_profile": {
                    "upload_kbps": 64,
                    "download_kbps": 128,
                    "packet_size_bytes": 320,
                    "interval_ms": 20,
                },
            },
        },
        "traffic_patterns": {
            "continuous": {"description": "Continuous traffic"},
            "periodic": {"description": "Periodic traffic"},
            "burst": {"description": "Burst traffic"},
        },
        "categories": {
            "security": {"name": "Security"},
            "sensor": {"name": "Sensor"},
            "consumer": {"name": "Consumer"},
        },
    }
    devices_file = tmp_path / "devices.yaml"
    devices_file.write_text(yaml.dump(devices_data, allow_unicode=True))
    return devices_file


@pytest.fixture
def service(temp_devices_file: Path) -> IoTService:
    svc = IoTService(devices_path=temp_devices_file)
    svc.load_devices()
    return svc


@pytest.fixture
def empty_service(tmp_path: Path) -> IoTService:
    return IoTService(devices_path=tmp_path / "nonexistent.yaml")


class TestIoTServiceInit:
    def test_service_creation(self, service: IoTService):
        assert service is not None
        assert len(service._device_configs) == 3

    def test_service_creation_empty(self, empty_service: IoTService):
        empty_service.load_devices()
        assert len(empty_service._device_configs) == 0


class TestLoadDevices:
    def test_load_devices(self, service: IoTService):
        assert "ip_camera" in service._device_configs
        assert "temp_sensor" in service._device_configs
        assert "smart_speaker" in service._device_configs

    def test_load_devices_config_structure(self, service: IoTService):
        config = service._device_configs["ip_camera"]
        assert config.id == "ip_camera"
        assert config.name == "IP Camera"
        assert config.category == "security"
        assert config.traffic_pattern == TrafficPattern.CONTINUOUS

    def test_load_devices_network_profile(self, service: IoTService):
        config = service._device_configs["ip_camera"]
        assert config.network_profile.upload_kbps == 4000
        assert config.network_profile.packet_size_bytes == 1400

    def test_load_devices_traffic_patterns(self, service: IoTService):
        assert len(service._traffic_patterns) == 3

    def test_load_devices_categories(self, service: IoTService):
        assert len(service._categories) == 3

    def test_load_devices_nonexistent_file(self, empty_service: IoTService):
        empty_service.load_devices()
        assert len(empty_service._device_configs) == 0


class TestListDevices:
    def test_list_all_devices(self, service: IoTService):
        devices = service.list_devices()
        assert len(devices) == 3

    def test_list_devices_by_category(self, service: IoTService):
        devices = service.list_devices(category="security")
        assert len(devices) == 1
        assert devices[0]["id"] == "ip_camera"

    def test_list_devices_empty_category(self, service: IoTService):
        devices = service.list_devices(category="nonexistent")
        assert len(devices) == 0

    def test_list_devices_structure(self, service: IoTService):
        devices = service.list_devices()
        device = devices[0]
        assert "id" in device
        assert "name" in device
        assert "category" in device
        assert "protocols" in device
        assert "traffic_pattern" in device
        assert "network_profile" in device
        assert "state" in device

    def test_list_devices_default_state(self, service: IoTService):
        devices = service.list_devices()
        assert all(d["state"] == "offline" for d in devices)


class TestGetDevice:
    def test_get_device(self, service: IoTService):
        device = service.get_device("ip_camera")
        assert device is not None
        assert device["id"] == "ip_camera"
        assert device["name"] == "IP Camera"

    def test_get_device_not_found(self, service: IoTService):
        device = service.get_device("nonexistent")
        assert device is None

    def test_get_device_structure(self, service: IoTService):
        device = service.get_device("ip_camera")
        assert "id" in device
        assert "name" in device
        assert "category" in device
        assert "state" in device
        assert "stats" in device


class TestStartDevice:
    @pytest.mark.asyncio
    async def test_start_device(self, service: IoTService):
        result = await service.start_device("ip_camera")
        assert result["device_id"] == "ip_camera"
        assert result["state"] == "online"
        assert "instance_id" in result

    @pytest.mark.asyncio
    async def test_start_device_not_found(self, service: IoTService):
        with pytest.raises(ValueError, match="not found"):
            await service.start_device("nonexistent")

    @pytest.mark.asyncio
    async def test_start_device_already_running(self, service: IoTService):
        await service.start_device("ip_camera")
        with pytest.raises(ValueError, match="already running"):
            await service.start_device("ip_camera")

    @pytest.mark.asyncio
    async def test_start_device_with_params(self, service: IoTService):
        result = await service.start_device("ip_camera", params={"bitrate_kbps": 8000})
        assert result["state"] == "online"

    @pytest.mark.asyncio
    async def test_start_device_creates_instance(self, service: IoTService):
        await service.start_device("ip_camera")
        assert len(service._instances) == 1


class TestStopDevice:
    @pytest.mark.asyncio
    async def test_stop_device(self, service: IoTService):
        await service.start_device("ip_camera")
        instances = list(service._instances.values())
        result = await service.stop_device(instances[0].instance_id)
        assert result["state"] == "offline"

    @pytest.mark.asyncio
    async def test_stop_device_not_found(self, service: IoTService):
        with pytest.raises(ValueError, match="not found"):
            await service.stop_device("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_device_removes_instance(self, service: IoTService):
        await service.start_device("ip_camera")
        instances = list(service._instances.values())
        await service.stop_device(instances[0].instance_id)
        assert service._instances[instances[0].instance_id].state == DeviceState.OFFLINE


class TestGetDeviceStatus:
    @pytest.mark.asyncio
    async def test_get_device_status(self, service: IoTService):
        await service.start_device("ip_camera")
        instances = list(service._instances.values())
        status = await service.get_device_status(instances[0].instance_id)
        assert status is not None
        assert status["state"] == "online"

    @pytest.mark.asyncio
    async def test_get_device_status_not_found(self, service: IoTService):
        status = await service.get_device_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_device_status_structure(self, service: IoTService):
        await service.start_device("ip_camera")
        instances = list(service._instances.values())
        status = await service.get_device_status(instances[0].instance_id)
        assert "instance_id" in status
        assert "device_id" in status
        assert "state" in status
        assert "stats" in status


class TestGetTrafficStats:
    @pytest.mark.asyncio
    async def test_get_traffic_stats_empty(self, service: IoTService):
        stats = await service.get_traffic_stats()
        assert stats["total_devices"] == 0
        assert stats["online_devices"] == 0

    @pytest.mark.asyncio
    async def test_get_traffic_stats_with_devices(self, service: IoTService):
        await service.start_device("ip_camera")
        await service.start_device("temp_sensor")
        stats = await service.get_traffic_stats()
        assert stats["total_devices"] == 2
        assert stats["online_devices"] == 2

    @pytest.mark.asyncio
    async def test_get_traffic_stats_structure(self, service: IoTService):
        await service.start_device("ip_camera")
        stats = await service.get_traffic_stats()
        assert "total_devices" in stats
        assert "online_devices" in stats
        assert "total_packets_sent" in stats
        assert "by_pattern" in stats
        assert "by_category" in stats


class TestStopAllDevices:
    @pytest.mark.asyncio
    async def test_stop_all_devices(self, service: IoTService):
        await service.start_device("ip_camera")
        await service.start_device("temp_sensor")
        result = await service.stop_all_devices()
        assert result["stopped_count"] == 2

    @pytest.mark.asyncio
    async def test_stop_all_devices_empty(self, service: IoTService):
        result = await service.stop_all_devices()
        assert result["stopped_count"] == 0


class TestGetTrafficPatterns:
    def test_get_traffic_patterns(self, service: IoTService):
        patterns = service.get_traffic_patterns()
        assert len(patterns) == 3
        assert "continuous" in patterns
        assert "periodic" in patterns
        assert "burst" in patterns


class TestGetCategories:
    def test_get_categories(self, service: IoTService):
        categories = service.get_categories()
        assert len(categories) == 3
        assert "security" in categories
        assert "sensor" in categories
        assert "consumer" in categories


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_devices_different_types(self, service: IoTService):
        await service.start_device("ip_camera")
        await service.start_device("temp_sensor")
        await service.start_device("smart_speaker")
        assert len(service._instances) == 3

    @pytest.mark.asyncio
    async def test_device_state_transitions(self, service: IoTService):
        result = await service.start_device("ip_camera")
        assert result["state"] == "online"
        
        instances = list(service._instances.values())
        await service.stop_device(instances[0].instance_id)
        assert instances[0].state == DeviceState.OFFLINE

    @pytest.mark.asyncio
    async def test_traffic_pattern_types(self, service: IoTService):
        for pattern in ["continuous", "periodic", "burst", "idle"]:
            config = service._device_configs.get("ip_camera")
            if config:
                config.traffic_pattern = TrafficPattern(pattern)
                result = await service.start_device("ip_camera")
                assert result["state"] == "online"
                await service.stop_device(result["instance_id"])
