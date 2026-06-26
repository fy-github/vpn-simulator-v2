"""Comprehensive tests for platform adapters - Windows, macOS, Linux."""

from __future__ import annotations

import socket
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from vpn_simulator.core.platform import (
    LinuxAdapter,
    MacOSAdapter,
    PlatformInfo,
    WindowsAdapter,
    get_platform_adapter,
)


class TestPlatformInfo:
    def test_fields(self):
        info = PlatformInfo(os="linux", arch="x86_64", version="5.15", is_admin=False, python_version="3.12")
        assert info.os == "linux"
        assert info.arch == "x86_64"
        assert info.version == "5.15"
        assert info.is_admin is False
        assert info.python_version == "3.12"


class TestGetPlatformAdapter:
    def test_linux(self):
        with patch("platform.system", return_value="Linux"):
            assert isinstance(get_platform_adapter(), LinuxAdapter)

    def test_darwin(self):
        with patch("platform.system", return_value="Darwin"):
            assert isinstance(get_platform_adapter(), MacOSAdapter)

    def test_windows(self):
        with patch("platform.system", return_value="Windows"):
            assert isinstance(get_platform_adapter(), WindowsAdapter)

    def test_unsupported(self):
        with patch("platform.system", return_value="FreeBSD"):
            with pytest.raises(ValueError, match="Unsupported"):
                get_platform_adapter()


class TestWindowsAdapter:
    @pytest.fixture
    def adapter(self):
        return WindowsAdapter()

    def test_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "windows"
        assert info.arch != ""
        assert info.python_version != ""

    @pytest.mark.asyncio
    async def test_check_privileges(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_create_raw_socket(self, adapter):
        with patch("socket.socket") as mock_sock:
            mock_instance = MagicMock()
            mock_sock.return_value = mock_instance
            sock = await adapter.create_raw_socket(socket.IPPROTO_TCP)
            assert sock is mock_instance

    @pytest.mark.asyncio
    async def test_configure_firewall_no_port(self, adapter):
        result = await adapter.configure_firewall({"name": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_success(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.configure_firewall({"name": "test", "port": 8080})
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_firewall_failure(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            result = await adapter.configure_firewall({"name": "test", "port": 8080})
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_exception(self, adapter):
        with patch("subprocess.run", side_effect=OSError("fail")):
            result = await adapter.configure_firewall({"name": "test", "port": 8080})
            assert result is False

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        with patch("psutil.net_if_addrs", return_value={"eth0": [MagicMock(address="192.168.1.1")]}):
            interfaces = await adapter.get_network_interfaces()
            assert len(interfaces) == 1
            assert interfaces[0]["name"] == "eth0"

    @pytest.mark.asyncio
    async def test_get_network_interfaces_no_psutil(self, adapter):
        with patch.dict("sys.modules", {"psutil": None}):
            interfaces = await adapter.get_network_interfaces()
            assert interfaces == []

    @pytest.mark.asyncio
    async def test_manage_service_success(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.manage_service("start", "vpn_service")
            assert result is True

    @pytest.mark.asyncio
    async def test_manage_service_failure(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = await adapter.manage_service("stop", "vpn_service")
            assert result is False

    @pytest.mark.asyncio
    async def test_manage_service_exception(self, adapter):
        with patch("subprocess.run", side_effect=OSError("fail")):
            result = await adapter.manage_service("start", "vpn_service")
            assert result is False


class TestMacOSAdapter:
    @pytest.fixture
    def adapter(self):
        return MacOSAdapter()

    def test_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "darwin"
        assert info.arch != ""

    @pytest.mark.asyncio
    async def test_check_privileges(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_create_raw_socket(self, adapter):
        with patch("socket.socket") as mock_sock:
            mock_instance = MagicMock()
            mock_sock.return_value = mock_instance
            sock = await adapter.create_raw_socket(socket.IPPROTO_TCP)
            assert sock is mock_instance

    @pytest.mark.asyncio
    async def test_configure_firewall_no_pf_rule(self, adapter):
        result = await adapter.configure_firewall({"name": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_success(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.configure_firewall({"pf_rule": "pass in on en0"})
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_firewall_failure(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            result = await adapter.configure_firewall({"pf_rule": "bad rule"})
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_exception(self, adapter):
        with patch("subprocess.run", side_effect=OSError("fail")):
            result = await adapter.configure_firewall({"pf_rule": "rule"})
            assert result is False

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        with patch("psutil.net_if_addrs", return_value={"en0": [MagicMock(address="192.168.1.1")]}):
            interfaces = await adapter.get_network_interfaces()
            assert len(interfaces) == 1

    @pytest.mark.asyncio
    async def test_manage_service_start(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.manage_service("start", "com.vpn.service")
            assert result is True

    @pytest.mark.asyncio
    async def test_manage_service_stop(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.manage_service("stop", "com.vpn.service")
            assert result is True

    @pytest.mark.asyncio
    async def test_manage_service_status(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.manage_service("status", "com.vpn.service")
            assert result is True

    @pytest.mark.asyncio
    async def test_manage_service_unsupported_action(self, adapter):
        result = await adapter.manage_service("restart", "com.vpn.service")
        assert result is False


class TestLinuxAdapter:
    @pytest.fixture
    def adapter(self):
        return LinuxAdapter()

    def test_platform_info(self, adapter):
        info = adapter.get_platform_info()
        assert info.os == "linux"
        assert info.arch != ""

    @pytest.mark.asyncio
    async def test_check_privileges(self, adapter):
        result = await adapter.check_privileges()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_create_raw_socket(self, adapter):
        with patch("socket.socket") as mock_sock:
            mock_instance = MagicMock()
            mock_sock.return_value = mock_instance
            sock = await adapter.create_raw_socket(socket.IPPROTO_TCP)
            assert sock is mock_instance

    @pytest.mark.asyncio
    async def test_configure_firewall_no_port(self, adapter):
        result = await adapter.configure_firewall({"action": "-A"})
        assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_success(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.configure_firewall({"action": "-A", "port": 8080})
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_firewall_failure(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            result = await adapter.configure_firewall({"action": "-A", "port": 8080})
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_firewall_exception(self, adapter):
        with patch("subprocess.run", side_effect=OSError("fail")):
            result = await adapter.configure_firewall({"action": "-A", "port": 8080})
            assert result is False

    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, adapter):
        with patch("psutil.net_if_addrs", return_value={"eth0": [MagicMock(address="192.168.1.1")]}):
            interfaces = await adapter.get_network_interfaces()
            assert len(interfaces) == 1

    @pytest.mark.asyncio
    async def test_manage_service_success(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = await adapter.manage_service("start", "vpn_service")
            assert result is True

    @pytest.mark.asyncio
    async def test_manage_service_failure(self, adapter):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = await adapter.manage_service("stop", "vpn_service")
            assert result is False

    @pytest.mark.asyncio
    async def test_manage_service_exception(self, adapter):
        with patch("subprocess.run", side_effect=OSError("fail")):
            result = await adapter.manage_service("start", "vpn_service")
            assert result is False
