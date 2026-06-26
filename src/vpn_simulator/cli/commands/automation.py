"""Automation commands for VPN Simulator CLI."""

from __future__ import annotations

import click
import httpx
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

API_BASE = "http://localhost:8080/api/v1"


@click.group("automation")
def automation_group() -> None:
    """Manage automation scenarios."""


@automation_group.command("list")
@click.pass_context
def automation_list(ctx: click.Context) -> None:
    """List all available automation scenarios."""
    json_output: bool = ctx.obj["json_output"]

    try:
        resp = httpx.get(f"{API_BASE}/automation/scenarios", timeout=5)
        resp.raise_for_status()
        scenarios = resp.json()
    except httpx.HTTPStatusError as e:
        handle_error(f"API error: {e.response.status_code} - {e.response.text}", json_output=json_output)
        return
    except httpx.RequestError:
        scenarios = _get_static_scenarios()

    if json_output:
        output_json(scenarios)
        return

    if not scenarios:
        console.print("[dim]No automation scenarios available.[/dim]")
        return

    output_table(
        title="Automation Scenarios",
        columns=["Name", "Description", "Tags", "Version", "Timeout"],
        rows=[
            [
                s.get("name", ""),
                s.get("description", ""),
                ", ".join(s.get("tags", [])),
                s.get("version", ""),
                f"{s.get('timeout', 0)}s",
            ]
            for s in scenarios
        ],
    )


@automation_group.command("run")
@click.argument("scenario_id")
@click.option("--connection-id", "-c", help="Optional connection ID.")
@click.pass_context
def automation_run(ctx: click.Context, scenario_id: str, connection_id: str | None) -> None:
    """Run an automation scenario."""
    json_output: bool = ctx.obj["json_output"]

    try:
        data = {}
        if connection_id:
            data["connection_id"] = connection_id

        resp = httpx.post(
            f"{API_BASE}/automation/scenarios/{scenario_id}/run",
            json=data,
            timeout=5,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Automation scenario '{scenario_id}' not found", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code} - {e.response.text}", json_output=json_output)
        return
    except httpx.RequestError:
        handle_error("API server not available. Start the server first.", json_output=json_output)
        return

    handle_success(result.get("message", f"Automation scenario '{scenario_id}' started"), json_output=json_output)


@automation_group.command("status")
@click.argument("scenario_id")
@click.option("--execution-id", "-e", help="Execution ID.")
@click.pass_context
def automation_status(ctx: click.Context, scenario_id: str, execution_id: str | None) -> None:
    """Get status of an automation scenario execution."""
    json_output: bool = ctx.obj["json_output"]

    try:
        params = {}
        if execution_id:
            params["execution_id"] = execution_id

        resp = httpx.get(
            f"{API_BASE}/automation/scenarios/{scenario_id}/status",
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        status = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Automation scenario '{scenario_id}' not found", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code}", json_output=json_output)
        return
    except httpx.RequestError:
        handle_error("API server not available. Start the server first.", json_output=json_output)
        return

    if json_output:
        output_json(status)
        return

    console.print(f"\n[bold cyan]{status.get('scenario_name', scenario_id)}[/bold cyan]")
    console.print(f"  Execution ID: {status.get('execution_id', '')}")
    console.print(f"  State:        {status.get('state', '')}")
    console.print(f"  Started At:   {status.get('started_at', 'N/A')}")
    console.print(f"  Completed At: {status.get('completed_at', 'N/A')}")
    console.print(f"  Duration:     {status.get('duration', 0):.2f}s")
    console.print()


@automation_group.command("report")
@click.argument("scenario_id")
@click.option("--execution-id", "-e", help="Execution ID.")
@click.pass_context
def automation_report(ctx: click.Context, scenario_id: str, execution_id: str | None) -> None:
    """Get execution report of an automation scenario."""
    json_output: bool = ctx.obj["json_output"]

    try:
        params = {}
        if execution_id:
            params["execution_id"] = execution_id

        resp = httpx.get(
            f"{API_BASE}/automation/scenarios/{scenario_id}/report",
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        report_data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Automation scenario '{scenario_id}' not found", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code}", json_output=json_output)
        return
    except httpx.RequestError:
        handle_error("API server not available. Start the server first.", json_output=json_output)
        return

    if json_output:
        output_json(report_data)
        return

    console.print(f"\n[bold cyan]Automation Report: {report_data.get('scenario_name', scenario_id)}[/bold cyan]")
    console.print("=" * 60)
    console.print(f"Execution ID: {report_data.get('execution_id', '')}")
    console.print(f"State:        {report_data.get('state', '')}")
    console.print()
    console.print(report_data.get("report", "No report available"))
    console.print()


def _get_static_scenarios() -> list[dict]:
    """Get static automation scenario data as fallback."""
    return [
        {
            "name": "PPTP 基础连接测试",
            "description": "测试 PPTP 协议的基本连接功能",
            "tags": ["pptp", "basic", "connection"],
            "version": "1.0",
            "timeout": 120,
        },
        {
            "name": "L2TP 基础连接测试",
            "description": "测试 L2TP 协议的基本连接功能",
            "tags": ["l2tp", "basic", "connection"],
            "version": "1.0",
            "timeout": 120,
        },
    ]