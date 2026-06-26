"""Integration tests for CLI commands - comprehensive coverage."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from vpn_simulator.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestServerCommands:
    def test_server_start(self, runner: CliRunner):
        result = runner.invoke(cli, ["server", "start"])
        assert result.exit_code == 0
        assert "Success" in result.output or "started" in result.output.lower()

    def test_server_start_with_options(self, runner: CliRunner):
        result = runner.invoke(cli, ["server", "start", "--host", "127.0.0.1", "--port", "9090"])
        assert result.exit_code == 0

    def test_server_stop(self, runner: CliRunner):
        result = runner.invoke(cli, ["server", "stop"])
        assert result.exit_code == 0

    def test_server_status(self, runner: CliRunner):
        result = runner.invoke(cli, ["server", "status"])
        assert result.exit_code == 0

    def test_server_status_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "server", "status"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "state" in data


class TestProtocolCommands:
    def test_protocol_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["protocol", "list"])
        assert result.exit_code == 0

    def test_protocol_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "protocol", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_protocol_start(self, runner: CliRunner):
        result = runner.invoke(cli, ["protocol", "start", "pptp"])
        assert result.exit_code == 0

    def test_protocol_start_with_port(self, runner: CliRunner):
        result = runner.invoke(cli, ["protocol", "start", "pptp", "--port", "1723"])
        assert result.exit_code == 0

    def test_protocol_stop(self, runner: CliRunner):
        result = runner.invoke(cli, ["protocol", "stop", "pptp"])
        assert result.exit_code == 0


class TestConnectionCommands:
    def test_connection_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["connection", "list"])
        assert result.exit_code == 0

    def test_connection_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "connection", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_connection_disconnect(self, runner: CliRunner):
        result = runner.invoke(cli, ["connection", "disconnect", "test-conn", "--force"])
        assert result.exit_code == 0


class TestFaultCommands:
    def test_fault_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["fault", "list"])
        assert result.exit_code == 0

    def test_fault_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "fault", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_fault_add(self, runner: CliRunner):
        result = runner.invoke(cli, ["fault", "add", "latency", "--target", "pptp", "-p", "delay_ms=100"])
        assert result.exit_code == 0

    def test_fault_add_invalid_param(self, runner: CliRunner):
        result = runner.invoke(cli, ["fault", "add", "latency", "--target", "pptp", "-p", "invalid"])
        assert result.exit_code == 0

    def test_fault_remove(self, runner: CliRunner):
        result = runner.invoke(cli, ["fault", "remove", "fault-001", "--force"])
        assert result.exit_code == 0


class TestAttackCommands:
    def test_attack_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["attack", "list"])
        assert result.exit_code == 0

    def test_attack_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "attack", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_attack_start(self, runner: CliRunner):
        result = runner.invoke(cli, ["attack", "start", "mitm", "--target", "pptp"])
        assert result.exit_code == 0

    def test_attack_start_with_params(self, runner: CliRunner):
        result = runner.invoke(cli, ["attack", "start", "mitm", "--target", "pptp", "-p", "port=8080"])
        assert result.exit_code == 0

    def test_attack_stop(self, runner: CliRunner):
        result = runner.invoke(cli, ["attack", "stop", "attack-001", "--force"])
        assert result.exit_code == 0


class TestConfigCommands:
    def test_config_get(self, runner: CliRunner):
        result = runner.invoke(cli, ["config", "get"])
        assert result.exit_code == 0

    def test_config_get_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "config", "get"])
        assert result.exit_code == 0

    def test_config_set(self, runner: CliRunner):
        result = runner.invoke(cli, ["config", "set", "log_level", "DEBUG"])
        assert result.exit_code == 0


class TestBenchmarkCommands:
    def test_benchmark_run(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
        assert result.exit_code == 0

    def test_benchmark_results(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "results"])
        assert result.exit_code == 0

    def test_benchmark_results_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "benchmark", "results"])
        assert result.exit_code == 0


class TestScenarioCommands:
    def test_scenario_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "list"])
        assert result.exit_code == 0


class TestAutomationCommands:
    def test_automation_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["automation", "list"])
        assert result.exit_code == 0


class TestCLIGlobalOptions:
    def test_verbose_output(self, runner: CliRunner):
        result = runner.invoke(cli, ["--verbose", "protocol", "list"])
        assert result.exit_code == 0

    def test_json_output(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "protocol", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "VPN Simulator" in result.output

    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
