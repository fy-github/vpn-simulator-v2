"""Tests for scenario CLI commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from vpn_simulator.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestScenarioCommands:
    def test_scenario_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "list"])
        assert result.exit_code == 0

    def test_scenario_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "scenario", "list"])
        assert result.exit_code == 0

    def test_scenario_list_with_category(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "list", "--category", "mobile"])
        assert result.exit_code == 0

    def test_scenario_show(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "show", "3g"])
        assert result.exit_code == 0

    def test_scenario_show_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "show", "nonexistent"])
        assert result.exit_code == 0

    def test_scenario_show_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "scenario", "show", "3g"])
        assert result.exit_code == 0

    def test_scenario_apply(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "apply", "3g"])
        assert result.exit_code == 0

    def test_scenario_remove(self, runner: CliRunner):
        result = runner.invoke(cli, ["scenario", "remove", "3g"])
        assert result.exit_code == 0


class TestAutomationCommands:
    def test_automation_list(self, runner: CliRunner):
        result = runner.invoke(cli, ["automation", "list"])
        assert result.exit_code == 0

    def test_automation_list_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "automation", "list"])
        assert result.exit_code == 0

    def test_automation_run(self, runner: CliRunner):
        result = runner.invoke(cli, ["automation", "run", "pptp_basic"])
        assert result.exit_code == 0

    def test_automation_run_not_found(self, runner: CliRunner):
        result = runner.invoke(cli, ["automation", "run", "nonexistent"])
        assert result.exit_code == 0

    def test_automation_status(self, runner: CliRunner):
        result = runner.invoke(cli, ["automation", "status", "pptp_basic"])
        assert result.exit_code == 0

    def test_automation_status_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "automation", "status", "pptp_basic"])
        assert result.exit_code == 0


class TestBenchmarkCommands:
    def test_benchmark_results(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "results"])
        assert result.exit_code == 0

    def test_benchmark_results_json(self, runner: CliRunner):
        result = runner.invoke(cli, ["--json", "benchmark", "results"])
        assert result.exit_code == 0

    def test_benchmark_run(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
        assert result.exit_code == 0

    def test_benchmark_run_invalid_type(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "run", "invalid", "-p", "pptp"])
        assert result.exit_code != 0

    def test_benchmark_run_invalid_protocol(self, runner: CliRunner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "invalid"])
        assert result.exit_code != 0
