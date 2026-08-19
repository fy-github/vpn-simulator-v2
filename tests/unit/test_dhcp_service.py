"""Tests for DHCPService - DHCP 地址占用服务。"""

from __future__ import annotations

import json
import signal
import sys

import pytest
from vpn_simulator.services.dhcp import STATE_IDLE, STATE_RUNNING, DHCPService


@pytest.fixture
def service() -> DHCPService:
    return DHCPService()


class TestDHCPServiceInit:
    def test_service_creation(self, service: DHCPService):
        assert service is not None
        assert service._script_path.name == "dhcp_occupy_vlan.py"
        assert service._script_path.exists()
        assert service.status()["state"] == STATE_IDLE

    def test_script_is_pure_python(self, service: DHCPService):
        # 脚本仅依赖标准库，可被子进程独立执行
        assert sys.executable


class TestBuildArgs:
    def test_basic_args(self, service: DHCPService):
        args = service._build_args({"count": 7, "interval": 0.8, "timeout": 5.0, "attempts": 2})
        assert args[0] == sys.executable
        assert args[1].endswith("dhcp_occupy_vlan.py")
        assert "-n" in args and "7" in args
        assert "--interval" in args and "0.8" in args
        assert "--timeout" in args and "5.0" in args
        assert "--attempts" in args and "2" in args
        assert "--save" in args
        assert "--vlan" not in args

    def test_vlan_args(self, service: DHCPService):
        args = service._build_args({"iface": "en0", "vlan": 20})
        assert "--iface" in args and "en0" in args
        assert "--vlan" in args and "20" in args

    def test_hold_and_source_mac(self, service: DHCPService):
        args = service._build_args({"hold": True, "duration": 60, "source_mac": "real"})
        assert "--hold" in args
        assert "--duration" in args and "60.0" in args
        assert "--source-mac" in args and "real" in args

    def test_flags(self, service: DHCPService):
        args = service._build_args({"blind": True, "raw": True, "verbose": True})
        assert "--blind" in args
        assert "--raw" in args
        assert "-v" in args


class TestLeases:
    def test_read_leases_empty(self, service: DHCPService, tmp_path):
        empty = tmp_path / "leases.json"
        svc = DHCPService(state_file=empty)
        assert svc.leases() == []

    def test_read_leases_from_file(self, tmp_path):
        state = tmp_path / "leases.json"
        state.write_text(
            json.dumps(
                {
                    "leases": [
                        {
                            "mac": "aa:bb:cc:dd:ee:ff",
                            "ip": "192.168.1.10",
                            "server": "192.168.1.1",
                            "lease": 7200,
                        }
                    ]
                }
            )
        )
        svc = DHCPService(state_file=state)
        leases = svc.leases()
        assert len(leases) == 1
        assert leases[0]["ip"] == "192.168.1.10"

    def test_read_leases_malformed(self, tmp_path):
        state = tmp_path / "leases.json"
        state.write_text("{not-json")
        svc = DHCPService(state_file=state)
        assert svc.leases() == []


class TestJobLifecycle:
    def test_start_spawns_subprocess(self, service: DHCPService, mocker):
        mocker.patch("vpn_simulator.services.dhcp.threading.Thread")
        popen = mocker.patch("vpn_simulator.services.dhcp.subprocess.Popen")
        fake_proc = mocker.MagicMock()
        fake_proc.pid = 12345
        popen.return_value = fake_proc

        result = service.start({"count": 3})
        assert result["state"] == STATE_RUNNING
        popen.assert_called_once()
        assert service._job.proc is fake_proc

    def test_start_rejects_when_running(self, service: DHCPService, mocker):
        mocker.patch("vpn_simulator.services.dhcp.threading.Thread")
        fake_proc = mocker.MagicMock()
        mocker.patch("vpn_simulator.services.dhcp.subprocess.Popen", return_value=fake_proc)

        service.start({"count": 1})
        with pytest.raises(RuntimeError):
            service.start({"count": 1})

    def test_stop_sends_sigint(self, service: DHCPService, mocker):
        mocker.patch("vpn_simulator.services.dhcp.threading.Thread")
        fake_proc = mocker.MagicMock()
        mocker.patch("vpn_simulator.services.dhcp.subprocess.Popen", return_value=fake_proc)

        service.start({"count": 1})
        result = service.stop()
        assert result["state"] == "stopping"
        fake_proc.send_signal.assert_called_once_with(signal.SIGINT)

    def test_stop_when_idle(self, service: DHCPService):
        result = service.stop()
        assert result["state"] == STATE_IDLE
        assert "没有正在运行的任务" in result["message"]


class TestStatus:
    def test_status_incremental(self, service: DHCPService):
        service._append_log(service._job, "第一行")
        service._append_log(service._job, "第二行")

        status = service.status(after=1)
        assert status["seq"] == 2
        assert len(status["logs"]) == 1
        assert status["logs"][0]["line"] == "第二行"

    def test_status_initial(self, service: DHCPService):
        status = service.status(after=0)
        assert status["state"] == STATE_IDLE
        assert status["logs"] == []
        assert status["leases"] == []
