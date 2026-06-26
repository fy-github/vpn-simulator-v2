"""Scenario preset commands for VPN Simulator CLI."""

from __future__ import annotations

import click
import httpx
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

API_BASE = "http://localhost:8080/api/v1"


@click.group("scenario")
def scenario_group() -> None:
    """Manage network scenario presets."""


@scenario_group.command("list")
@click.option("--category", "-c", help="Filter by category (mobile, satellite, wifi, wired).")
@click.pass_context
def scenario_list(ctx: click.Context, category: str | None) -> None:
    """List all available scenario presets."""
    json_output: bool = ctx.obj["json_output"]

    try:
        params = {}
        if category:
            params["category"] = category

        resp = httpx.get(f"{API_BASE}/scenarios", params=params, timeout=5)
        resp.raise_for_status()
        scenarios = resp.json()
    except httpx.HTTPStatusError as e:
        handle_error(f"API error: {e.response.status_code} - {e.response.text}", json_output=json_output)
        return
    except httpx.RequestError:
        # Fallback to static data if API is not available
        scenarios = _get_static_scenarios()
        if category:
            scenarios = [s for s in scenarios if s.get("category") == category]

    if json_output:
        output_json(scenarios)
        return

    if not scenarios:
        console.print("[dim]No scenarios available.[/dim]")
        return

    output_table(
        title="Network Scenario Presets",
        columns=["ID", "Name", "Category", "Latency", "Loss", "Bandwidth", "Active"],
        rows=[
            [
                s.get("id", ""),
                s.get("name", ""),
                s.get("category", ""),
                f"{s.get('faults', {}).get('latency', {}).get('delay_ms', '-')}ms",
                f"{s.get('faults', {}).get('packet_loss', {}).get('loss_rate', 0) * 100:.1f}%",
                _format_bandwidth(s.get('faults', {}).get('bandwidth', {}).get('bandwidth_kbps', 0)),
                "Yes" if s.get("active") else "No",
            ]
            for s in scenarios
        ],
        json_output=json_output,
    )


@scenario_group.command("show")
@click.argument("scenario_id")
@click.pass_context
def scenario_show(ctx: click.Context, scenario_id: str) -> None:
    """Show details of a specific scenario."""
    json_output: bool = ctx.obj["json_output"]

    try:
        resp = httpx.get(f"{API_BASE}/scenarios/{scenario_id}", timeout=5)
        resp.raise_for_status()
        scenario = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Scenario '{scenario_id}' not found", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code}", json_output=json_output)
        return
    except httpx.RequestError:
        scenarios = _get_static_scenarios()
        scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
        if not scenario:
            handle_error(f"Scenario '{scenario_id}' not found", json_output=json_output)
            return

    if json_output:
        output_json(scenario)
        return

    console.print(f"\n[bold cyan]{scenario['name']}[/bold cyan]")
    console.print(f"  ID:          {scenario['id']}")
    console.print(f"  Category:    {scenario['category']}")
    console.print(f"  Description: {scenario['description']}")
    console.print(f"  Active:      {'Yes' if scenario.get('active') else 'No'}")
    console.print("\n  [bold]Fault Parameters:[/bold]")

    faults = scenario.get("faults", {})
    if "latency" in faults:
        console.print(f"    Latency:      {faults['latency'].get('delay_ms', 0)}ms (jitter: {faults['latency'].get('jitter_ms', 0)}ms)")
    if "packet_loss" in faults:
        console.print(f"    Packet Loss:  {faults['packet_loss'].get('loss_rate', 0) * 100:.1f}%")
    if "bandwidth" in faults:
        console.print(f"    Bandwidth:    {_format_bandwidth(faults['bandwidth'].get('bandwidth_kbps', 0))}")
    console.print()


@scenario_group.command("apply")
@click.argument("scenario_id")
@click.pass_context
def scenario_apply(ctx: click.Context, scenario_id: str) -> None:
    """Apply a network scenario preset."""
    json_output: bool = ctx.obj["json_output"]

    try:
        resp = httpx.post(f"{API_BASE}/scenarios/{scenario_id}/apply", timeout=5)
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Scenario '{scenario_id}' not found", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code} - {e.response.text}", json_output=json_output)
        return
    except httpx.RequestError:
        handle_error("API server not available. Start the server first.", json_output=json_output)
        return

    handle_success(result.get("message", f"Scenario '{scenario_id}' applied"), json_output=json_output)


@scenario_group.command("remove")
@click.argument("scenario_id")
@click.pass_context
def scenario_remove(ctx: click.Context, scenario_id: str) -> None:
    """Remove an applied network scenario."""
    json_output: bool = ctx.obj["json_output"]

    try:
        resp = httpx.delete(f"{API_BASE}/scenarios/{scenario_id}/remove", timeout=5)
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            handle_error(f"Scenario '{scenario_id}' not found", json_output=json_output)
        elif e.response.status_code == 400:
            handle_error(f"Scenario '{scenario_id}' is not currently active", json_output=json_output)
        else:
            handle_error(f"API error: {e.response.status_code} - {e.response.text}", json_output=json_output)
        return
    except httpx.RequestError:
        handle_error("API server not available. Start the server first.", json_output=json_output)
        return

    handle_success(result.get("message", f"Scenario '{scenario_id}' removed"), json_output=json_output)


def _format_bandwidth(kbps: int) -> str:
    """Format bandwidth for display."""
    if kbps >= 1000000:
        return f"{kbps / 1000000:.0f}Gbps"
    if kbps >= 1000:
        return f"{kbps / 1000:.0f}Mbps"
    return f"{kbps}Kbps"


def _get_static_scenarios() -> list[dict]:
    """Get static scenario data as fallback."""
    return [
        {
            "id": "3g",
            "name": "3G",
            "description": "3G mobile network - moderate latency, limited bandwidth",
            "category": "mobile",
            "faults": {
                "latency": {"delay_ms": 200, "jitter_ms": 50},
                "packet_loss": {"loss_rate": 0.02},
                "bandwidth": {"bandwidth_kbps": 2000},
            },
            "active": False,
        },
        {
            "id": "4g_lte",
            "name": "4G LTE",
            "description": "4G LTE mobile network - low latency, good bandwidth",
            "category": "mobile",
            "faults": {
                "latency": {"delay_ms": 50, "jitter_ms": 20},
                "packet_loss": {"loss_rate": 0.01},
                "bandwidth": {"bandwidth_kbps": 50000},
            },
            "active": False,
        },
        {
            "id": "satellite",
            "name": "Satellite",
            "description": "Traditional satellite connection - high latency, moderate bandwidth",
            "category": "satellite",
            "faults": {
                "latency": {"delay_ms": 600, "jitter_ms": 100},
                "packet_loss": {"loss_rate": 0.05},
                "bandwidth": {"bandwidth_kbps": 10000},
            },
            "active": False,
        },
        {
            "id": "starlink",
            "name": "Starlink",
            "description": "Starlink LEO satellite - low latency, high bandwidth",
            "category": "satellite",
            "faults": {
                "latency": {"delay_ms": 40, "jitter_ms": 15},
                "packet_loss": {"loss_rate": 0.005},
                "bandwidth": {"bandwidth_kbps": 100000},
            },
            "active": False,
        },
        {
            "id": "congested_wifi",
            "name": "Congested WiFi",
            "description": "Crowded WiFi network - high jitter, significant packet loss",
            "category": "wifi",
            "faults": {
                "latency": {"delay_ms": 100, "jitter_ms": 80},
                "packet_loss": {"loss_rate": 0.10},
                "bandwidth": {"bandwidth_kbps": 5000},
            },
            "active": False,
        },
        {
            "id": "fiber",
            "name": "Fiber",
            "description": "Fiber optic connection - ultra-low latency, massive bandwidth",
            "category": "wired",
            "faults": {
                "latency": {"delay_ms": 5, "jitter_ms": 2},
                "packet_loss": {"loss_rate": 0.001},
                "bandwidth": {"bandwidth_kbps": 1000000},
            },
            "active": False,
        },
    ]
