"""Tests for CLI commands with httpx mocking - automation, scenario, benchmark."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from vpn_simulator.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestAutomationCLI:
    def test_list_api_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"name": "test", "description": "test scenario", "tags": ["test"], "version": "1.0", "timeout": 120}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["automation", "list"])
            assert result.exit_code == 0

    def test_list_api_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "list"])
            assert result.exit_code == 0

    def test_list_connection_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["automation", "list"])
            assert result.exit_code == 0

    def test_list_json_output(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["--json", "automation", "list"])
            assert result.exit_code == 0

    def test_run_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "started"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            result = runner.invoke(cli, ["automation", "run", "test_scenario"])
            assert result.exit_code == 0

    def test_run_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "run", "nonexistent"])
            assert result.exit_code == 0

    def test_run_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "run", "test"])
            assert result.exit_code == 0

    def test_run_connection_error(self, runner):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["automation", "run", "test"])
            assert result.exit_code == 0

    def test_status_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"scenario_name": "test", "execution_id": "123", "state": "completed", "started_at": "2025-01-01", "completed_at": "2025-01-01", "duration": 1.5}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["automation", "status", "test"])
            assert result.exit_code == 0

    def test_status_json(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"scenario_name": "test", "execution_id": "123", "state": "completed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["--json", "automation", "status", "test"])
            assert result.exit_code == 0

    def test_status_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "status", "nonexistent"])
            assert result.exit_code == 0

    def test_status_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "status", "test"])
            assert result.exit_code == 0

    def test_status_connection_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["automation", "status", "test"])
            assert result.exit_code == 0

    def test_report_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"scenario_name": "test", "execution_id": "123", "state": "completed", "report": "All steps passed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["automation", "report", "test"])
            assert result.exit_code == 0

    def test_report_json(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"scenario_name": "test", "report": "All steps passed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["--json", "automation", "report", "test"])
            assert result.exit_code == 0

    def test_report_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "report", "nonexistent"])
            assert result.exit_code == 0

    def test_report_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["automation", "report", "test"])
            assert result.exit_code == 0

    def test_report_connection_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["automation", "report", "test"])
            assert result.exit_code == 0

    def test_static_scenarios(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["automation", "list"])
            assert result.exit_code == 0


class TestScenarioCLI:
    def test_list_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "3g", "name": "3G", "category": "mobile", "faults": {"latency": {"delay_ms": 200}, "packet_loss": {"loss_rate": 0.02}}, "active": False}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "list"])
            assert result.exit_code == 0

    def test_list_json(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["--json", "scenario", "list"])
            assert result.exit_code == 0

    def test_list_with_category(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "list", "--category", "mobile"])
            assert result.exit_code == 0

    def test_list_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "list"])
            assert result.exit_code == 0

    def test_show_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "3g", "name": "3G", "category": "mobile", "description": "3G network", "faults": {"latency": {"delay_ms": 200, "jitter_ms": 50}, "packet_loss": {"loss_rate": 0.02}}, "active": False}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "show", "3g"])
            assert result.exit_code == 0

    def test_show_json(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "3g", "name": "3G"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["--json", "scenario", "show", "3g"])
            assert result.exit_code == 0

    def test_show_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "show", "nonexistent"])
            assert result.exit_code == 0

    def test_show_connection_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "show", "3g"])
            assert result.exit_code == 0

    def test_show_fallback_found(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "show", "3g"])
            assert result.exit_code == 0

    def test_show_fallback_not_found(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "show", "nonexistent"])
            assert result.exit_code == 0

    def test_apply_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "Scenario applied"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "apply", "3g"])
            assert result.exit_code == 0

    def test_apply_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "apply", "nonexistent"])
            assert result.exit_code == 0

    def test_apply_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "apply", "3g"])
            assert result.exit_code == 0

    def test_apply_connection_error(self, runner):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "apply", "3g"])
            assert result.exit_code == 0

    def test_remove_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "Scenario removed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.delete", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "remove", "3g"])
            assert result.exit_code == 0

    def test_remove_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.delete", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "remove", "nonexistent"])
            assert result.exit_code == 0

    def test_remove_not_active(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "not active"
        with patch("httpx.delete", side_effect=httpx.HTTPStatusError("bad request", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "remove", "3g"])
            assert result.exit_code == 0

    def test_remove_server_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.delete", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["scenario", "remove", "3g"])
            assert result.exit_code == 0

    def test_remove_connection_error(self, runner):
        import httpx
        with patch("httpx.delete", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["scenario", "remove", "3g"])
            assert result.exit_code == 0

    def test_format_bandwidth_gbps(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "test", "name": "Test", "category": "test", "faults": {"bandwidth": {"bandwidth_kbps": 1000000}}, "active": False}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "list"])
            assert result.exit_code == 0

    def test_format_bandwidth_mbps(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "test", "name": "Test", "category": "test", "faults": {"bandwidth": {"bandwidth_kbps": 50000}}, "active": False}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "list"])
            assert result.exit_code == 0

    def test_format_bandwidth_kbps(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "test", "name": "Test", "category": "test", "faults": {"bandwidth": {"bandwidth_kbps": 500}}, "active": False}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["scenario", "list"])
            assert result.exit_code == 0


class TestBenchmarkCLI:
    def test_run_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "bench-1", "test_type": "handshake", "protocol": "pptp", "status": "completed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
            assert result.exit_code == 0

    def test_run_json(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "bench-1", "status": "completed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            result = runner.invoke(cli, ["--json", "benchmark", "run", "handshake", "-p", "pptp"])
            assert result.exit_code == 0

    def test_run_with_params(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "bench-1", "status": "completed"}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp", "-P", "iterations=50"])
            assert result.exit_code == 0

    def test_run_invalid_type(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "invalid", "-p", "pptp"])
        assert result.exit_code != 0

    def test_run_invalid_protocol(self, runner):
        result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "invalid"])
        assert result.exit_code != 0

    def test_run_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
            assert result.exit_code == 0

    def test_run_connection_error(self, runner):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["benchmark", "run", "handshake", "-p", "pptp"])
            assert result.exit_code == 0

    def test_results_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "bench-1", "status": "completed"}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["benchmark", "results"])
            assert result.exit_code == 0

    def test_results_json(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "bench-1"}]
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["--json", "benchmark", "results"])
            assert result.exit_code == 0

    def test_results_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["benchmark", "results"])
            assert result.exit_code == 0

    def test_compare_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"baseline": {}, "current": {}, "changes": {}}
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            result = runner.invoke(cli, ["benchmark", "compare", "-b", "bench-1", "-c", "bench-2"])
            assert result.exit_code == 0

    def test_compare_not_found(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["benchmark", "compare", "-b", "bench-1", "-c", "bench-2"])
            assert result.exit_code == 0

    def test_compare_error(self, runner):
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)):
            result = runner.invoke(cli, ["benchmark", "compare", "-b", "bench-1", "-c", "bench-2"])
            assert result.exit_code == 0

    def test_compare_connection_error(self, runner):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = runner.invoke(cli, ["benchmark", "compare", "-b", "bench-1", "-c", "bench-2"])
            assert result.exit_code == 0
