"""Tests for VendorCLIService - multi-vendor CLI service."""

from __future__ import annotations

import pytest

from vpn_simulator.services.vendor_cli import (
    CommandMapping,
    CommandMode,
    CommandResult,
    VendorCLIService,
    VendorType,
)


@pytest.fixture
def service() -> VendorCLIService:
    return VendorCLIService()


class TestVendorCLIServiceInit:
    def test_service_creation(self, service: VendorCLIService):
        assert service is not None
        assert len(service._cisco_commands) > 0
        assert len(service._huawei_commands) > 0
        assert len(service._history) == 0


class TestGetSupportedCommands:
    def test_cisco_commands(self, service: VendorCLIService):
        commands = service.get_supported_commands(VendorType.CISCO)
        assert len(commands) > 0
        assert any(c["command"] == "show ip interface brief" for c in commands)

    def test_huawei_commands(self, service: VendorCLIService):
        commands = service.get_supported_commands(VendorType.HUAWEI)
        assert len(commands) > 0
        assert any(c["command"] == "display ip interface brief" for c in commands)

    def test_command_structure(self, service: VendorCLIService):
        commands = service.get_supported_commands(VendorType.CISCO)
        cmd = commands[0]
        assert "command" in cmd
        assert "description" in cmd
        assert "mode" in cmd
        assert "aliases" in cmd


class TestExecuteCommand:
    def test_cisco_show_interfaces(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "show ip interface brief")
        assert result.success is True
        assert "Interface" in result.output or "lo" in result.output

    def test_cisco_show_routes(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "show ip route")
        assert result.success is True
        assert "via" in result.output or "Gateway" in result.output

    def test_cisco_show_interfaces_detail(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "show interfaces")
        assert result.success is True
        assert "lo" in result.output or "eth0" in result.output or "GigabitEthernet" in result.output

    def test_cisco_show_running_config(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "show running-config")
        assert result.success is True
        assert "VPN-Simulator" in result.output

    def test_cisco_configure_terminal(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "configure terminal")
        assert result.success is True
        assert "configuration commands" in result.output.lower()

    def test_cisco_write_memory(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "write memory")
        assert result.success is True
        assert "saved" in result.output.lower()

    def test_cisco_ping(self, service: VendorCLIService):
        result = service.execute_command(
            VendorType.CISCO, "ping", params={"target": "10.0.0.1"}
        )
        assert result.success is True
        assert "10.0.0.1" in result.output

    def test_cisco_traceroute(self, service: VendorCLIService):
        result = service.execute_command(
            VendorType.CISCO, "traceroute", params={"target": "8.8.8.8"}
        )
        assert result.success is True
        assert "traceroute" in result.output.lower() or "ms" in result.output

    def test_huawei_display_interfaces(self, service: VendorCLIService):
        result = service.execute_command(VendorType.HUAWEI, "display ip interface brief")
        assert result.success is True
        assert "Interface" in result.output or "lo" in result.output

    def test_huawei_display_routes(self, service: VendorCLIService):
        result = service.execute_command(VendorType.HUAWEI, "display ip routing-table")
        assert result.success is True

    def test_huawei_system_view(self, service: VendorCLIService):
        result = service.execute_command(VendorType.HUAWEI, "system-view")
        assert result.success is True

    def test_huawei_save(self, service: VendorCLIService):
        result = service.execute_command(VendorType.HUAWEI, "save")
        assert result.success is True

    def test_unknown_command(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "unknown command")
        assert result.success is False
        assert "Unknown command" in result.output

    def test_alias_command(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "sh ip int br")
        assert result.success is True
        assert "Interface" in result.output or "lo" in result.output


class TestGetHistory:
    def test_history_empty(self, service: VendorCLIService):
        history = service.get_history()
        assert len(history) == 0

    def test_history_after_commands(self, service: VendorCLIService):
        service.execute_command(VendorType.CISCO, "show ip interface brief")
        service.execute_command(VendorType.CISCO, "show ip route")
        history = service.get_history()
        assert len(history) == 2
        assert history[0]["command"] == "show ip interface brief"

    def test_history_structure(self, service: VendorCLIService):
        service.execute_command(VendorType.CISCO, "ping")
        history = service.get_history()
        entry = history[0]
        assert "command" in entry
        assert "output" in entry
        assert "success" in entry
        assert "timestamp" in entry

    def test_history_with_limit(self, service: VendorCLIService):
        for i in range(10):
            service.execute_command(VendorType.CISCO, f"ping")
        history = service.get_history(limit=5)
        assert len(history) == 5


class TestEdgeCases:
    def test_multiple_vendors(self, service: VendorCLIService):
        cisco_result = service.execute_command(VendorType.CISCO, "show ip interface brief")
        huawei_result = service.execute_command(VendorType.HUAWEI, "display ip interface brief")
        assert cisco_result.success is True
        assert huawei_result.success is True

    def test_command_result_structure(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "ping")
        assert hasattr(result, "command")
        assert hasattr(result, "output")
        assert hasattr(result, "success")
        assert hasattr(result, "timestamp")

    def test_alias_resolution(self, service: VendorCLIService):
        result = service.execute_command(VendorType.CISCO, "sh ip int br")
        assert result.success is True

    def test_huawei_alias(self, service: VendorCLIService):
        result = service.execute_command(VendorType.HUAWEI, "dis ip int br")
        assert result.success is True


class TestGlobalInstance:
    def test_get_vendor_cli_service(self):
        from vpn_simulator.services.vendor_cli import get_vendor_cli_service
        service = get_vendor_cli_service()
        assert service is not None
        assert isinstance(service, VendorCLIService)
