"""Tests for benchmark CLI commands with full coverage."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from vpn_simulator.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestBenchmarkRun:
    def test_run_handshake(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
        assert result.exit_code == 0

    def test_run_throughput(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "throughput", "-p", "wireguard"])
        assert result.exit_code == 0

    def test_run_memory(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "memory", "-p", "openvpn"])
        assert result.exit_code == 0

    def test_run_concurrency(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "concurrency", "-p", "ipsec"])
        assert result.exit_code == 0

    def test_run_with_params(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp", "-P", "iterations=50"])
        assert result.exit_code == 0

    def test_run_with_invalid_param(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp", "-P", "invalid"])
        assert result.exit_code == 0

    def test_run_json_output(self, runner):
        result = runner.invoke(cli, ["--json", "benchmark", "run", "handshake", "-p", "pptp"])
        assert result.exit_code == 0

    def test_run_verbose(self, runner):
        result = runner.invoke(cli, ["--verbose", "benchmark", "run", "handshake", "-p", "pptp"])
        assert result.exit_code == 0

    def test_run_invalid_type(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "invalid", "-p", "pptp"])
        assert result.exit_code != 0

    def test_run_invalid_protocol(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "invalid"])
        assert result.exit_code != 0

    def test_run_all_protocols(self, runner):
        for proto in ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]:
            result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", proto])
            assert result.exit_code == 0

    def test_run_all_types(self, runner):
        for test_type in ["handshake", "throughput", "memory", "concurrency"]:
            result = runner.invoke(cli, ["benchmark", "run", test_type, "-p", "pptp"])
            assert result.exit_code == 0


class TestBenchmarkResults:
    def test_results_default(self, runner):
        result = runner.invoke(cli, ["benchmark", "results"])
        assert result.exit_code == 0

    def test_results_json(self, runner):
        result = runner.invoke(cli, ["--json", "benchmark", "results"])
        assert result.exit_code == 0

    def test_results_with_limit(self, runner):
        result = runner.invoke(cli, ["benchmark", "results", "--limit", "5"])
        assert result.exit_code == 0

    def test_results_after_run(self, runner):
        runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
        result = runner.invoke(cli, ["benchmark", "results"])
        assert result.exit_code == 0


class TestBenchmarkCompare:
    def test_compare_after_runs(self, runner):
        r1 = runner.invoke(cli, ["--json", "benchmark", "run", "handshake", "-p", "pptp"])
        r2 = runner.invoke(cli, ["--json", "benchmark", "run", "handshake", "-p", "pptp"])
        import json
        try:
            id1 = json.loads(r1.output).get("id", "bench-1")
            id2 = json.loads(r2.output).get("id", "bench-2")
        except:
            id1, id2 = "bench-1", "bench-2"
        result = runner.invoke(cli, ["benchmark", "compare", "-b", id1, "-c", id2])
        assert result.exit_code == 0

    def test_compare_not_found(self, runner):
        result = runner.invoke(cli, ["benchmark", "compare", "-b", "nonexistent", "-c", "nonexistent2"])
        assert result.exit_code == 0

    def test_compare_json(self, runner):
        result = runner.invoke(cli, ["--json", "benchmark", "compare", "-b", "bench-1", "-c", "bench-2"])
        assert result.exit_code == 0
