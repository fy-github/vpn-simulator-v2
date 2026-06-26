"""Integration tests for the CLI commands.

Tests cover:
- CLI entry point and version
- Server commands (start, stop, status)
- Protocol commands (list, start, stop)
- Fault commands (list, add, remove)
- JSON output mode
- Verbose mode
"""

from __future__ import annotations

from click.testing import CliRunner

from vpn_simulator.cli import cli


class TestCLIBasic:
    """Tests for basic CLI functionality."""

    def test_cli_help(self, cli_runner: CliRunner):
        """Verify CLI shows help message."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "VPN Simulator" in result.output

    def test_cli_version(self, cli_runner: CliRunner):
        """Verify CLI shows version."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_cli_verbose_flag(self, cli_runner: CliRunner):
        """Verify CLI accepts verbose flag."""
        result = cli_runner.invoke(cli, ["--verbose", "server", "status"])
        assert result.exit_code == 0

    def test_cli_json_flag(self, cli_runner: CliRunner):
        """Verify CLI accepts JSON output flag."""
        result = cli_runner.invoke(cli, ["--json", "server", "status"])
        assert result.exit_code == 0


class TestServerCommands:
    """Tests for server management commands."""

    def test_server_help(self, cli_runner: CliRunner):
        """Verify server command shows help."""
        result = cli_runner.invoke(cli, ["server", "--help"])
        assert result.exit_code == 0
        assert "Manage the VPN Simulator server" in result.output

    def test_server_start(self, cli_runner: CliRunner):
        """Verify server start command."""
        result = cli_runner.invoke(cli, ["server", "start"])
        assert result.exit_code == 0
        assert "Success" in result.output or "started" in result.output.lower()

    def test_server_start_with_options(self, cli_runner: CliRunner):
        """Verify server start command with options."""
        result = cli_runner.invoke(
            cli, ["server", "start", "--host", "127.0.0.1", "--port", "9090"]
        )
        assert result.exit_code == 0

    def test_server_stop(self, cli_runner: CliRunner):
        """Verify server stop command."""
        result = cli_runner.invoke(cli, ["server", "stop"])
        assert result.exit_code == 0

    def test_server_status(self, cli_runner: CliRunner):
        """Verify server status command."""
        result = cli_runner.invoke(cli, ["server", "status"])
        assert result.exit_code == 0

    def test_server_status_json(self, cli_runner: CliRunner):
        """Verify server status command with JSON output."""
        result = cli_runner.invoke(cli, ["--json", "server", "status"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "state" in data
        assert "host" in data
        assert "port" in data


class TestProtocolCommands:
    """Tests for protocol management commands."""

    def test_protocol_help(self, cli_runner: CliRunner):
        """Verify protocol command shows help."""
        result = cli_runner.invoke(cli, ["protocol", "--help"])
        assert result.exit_code == 0
        assert "Manage VPN protocols" in result.output

    def test_protocol_list(self, cli_runner: CliRunner):
        """Verify protocol list command."""
        result = cli_runner.invoke(cli, ["protocol", "list"])
        assert result.exit_code == 0

    def test_protocol_list_json(self, cli_runner: CliRunner):
        """Verify protocol list command with JSON output."""
        result = cli_runner.invoke(cli, ["--json", "protocol", "list"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]

    def test_protocol_start(self, cli_runner: CliRunner):
        """Verify protocol start command."""
        result = cli_runner.invoke(cli, ["protocol", "start", "pptp"])
        assert result.exit_code == 0

    def test_protocol_start_with_port(self, cli_runner: CliRunner):
        """Verify protocol start command with port option."""
        result = cli_runner.invoke(cli, ["protocol", "start", "pptp", "--port", "1723"])
        assert result.exit_code == 0

    def test_protocol_stop(self, cli_runner: CliRunner):
        """Verify protocol stop command."""
        result = cli_runner.invoke(cli, ["protocol", "stop", "pptp"])
        assert result.exit_code == 0


class TestFaultCommands:
    """Tests for fault injection commands."""

    def test_fault_help(self, cli_runner: CliRunner):
        """Verify fault command shows help."""
        result = cli_runner.invoke(cli, ["fault", "--help"])
        assert result.exit_code == 0
        assert "Manage fault injection" in result.output

    def test_fault_list(self, cli_runner: CliRunner):
        """Verify fault list command."""
        result = cli_runner.invoke(cli, ["fault", "list"])
        assert result.exit_code == 0

    def test_fault_add(self, cli_runner: CliRunner):
        """Verify fault add command."""
        result = cli_runner.invoke(
            cli,
            ["fault", "add", "latency", "--target", "pptp", "--param", "delay_ms=100"],
        )
        assert result.exit_code == 0

    def test_fault_add_invalid_param(self, cli_runner: CliRunner):
        """Verify fault add command rejects invalid parameter format."""
        result = cli_runner.invoke(
            cli,
            ["fault", "add", "latency", "--target", "pptp", "--param", "invalid"],
        )
        assert result.exit_code == 0
        assert "Error" in result.output or "Invalid" in result.output

    def test_fault_add_invalid_type(self, cli_runner: CliRunner):
        """Verify fault add command rejects invalid fault type."""
        result = cli_runner.invoke(
            cli,
            ["fault", "add", "invalid_type", "--target", "pptp"],
        )
        assert result.exit_code != 0

    def test_fault_remove_with_force(self, cli_runner: CliRunner):
        """Verify fault remove command with force flag."""
        result = cli_runner.invoke(cli, ["fault", "remove", "fault-001", "--force"])
        assert result.exit_code == 0


class TestCLIGlobalOptions:
    """Tests for CLI global options."""

    def test_verbose_output(self, cli_runner: CliRunner):
        """Verify verbose flag enables detailed output."""
        result = cli_runner.invoke(cli, ["--verbose", "protocol", "start", "pptp"])
        assert result.exit_code == 0

    def test_json_output_format(self, cli_runner: CliRunner):
        """Verify JSON flag produces valid JSON output."""
        import json

        result = cli_runner.invoke(cli, ["--json", "protocol", "list"])
        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)
