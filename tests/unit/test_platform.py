"""Tests for platform module - cross-platform adapter layer."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from vpn_simulator.core.platform import (
    PlatformInfo,
    get_platform_adapter,
    LinuxAdapter,
    MacOSAdapter,
    WindowsAdapter,
)


class TestPlatformInfo:
    def test_platform_info_creation(self):
        info = PlatformInfo(
            os="linux",
            arch="x86_64",
            version="5.15.0",
            is_admin=False,
            python_version="3.12.0",
        )
        assert info.os == "linux"
        assert info.arch == "x86_64"
        assert info.version == "5.15.0"
        assert info.is_admin is False
        assert info.python_version == "3.12.0"


class TestGetPlatformAdapter:
    def test_returns_adapter_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            adapter = get_platform_adapter()
            assert isinstance(adapter, LinuxAdapter)

    def test_returns_adapter_on_darwin(self):
        with patch("platform.system", return_value="Darwin"):
            adapter = get_platform_adapter()
            assert isinstance(adapter, MacOSAdapter)

    def test_returns_adapter_on_windows(self):
        with patch("platform.system", return_value="Windows"):
            adapter = get_platform_adapter()
            assert isinstance(adapter, WindowsAdapter)

    def test_raises_on_unsupported(self):
        with patch("platform.system", return_value="FreeBSD"):
            with pytest.raises(ValueError, match="Unsupported platform"):
                get_platform_adapter()


class TestLinuxAdapter:
    @pytest.fixture
    def adapter(self):
        return LinuxAdapter()

    def test_get_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "linux"
        assert info.arch != ""
        assert info.python_version != ""

    @pytest.mark.asyncio
    async def test_check_privileges(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        interfaces = await adapter.get_network_interfaces()
        assert isinstance(interfaces, list)

    @pytest.mark.asyncio
    async def test_manage_service_invalid(self, adapter):
        result = await adapter.manage_service("status", "nonexistent_service")
        assert isinstance(result, bool)


class TestMacOSAdapter:
    @pytest.fixture
    def adapter(self):
        return MacOSAdapter()

    def test_get_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "darwin"
        assert info.arch != ""

    @pytest.mark.asyncio
    async def test_check_privileges(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        interfaces = await adapter.get_network_interfaces()
        assert isinstance(interfaces, list)


class TestWindowsAdapter:
    @pytest.fixture
    def adapter(self):
        return WindowsAdapter()

    def test_get_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "windows"
        assert info.arch != ""

    @pytest.mark.asyncio
    async def test_check_privileges_returns_bool(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        interfaces = await adapter.get_network_interfaces()
        assert isinstance(interfaces, list)
