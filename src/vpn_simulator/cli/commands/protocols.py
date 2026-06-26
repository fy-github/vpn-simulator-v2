"""Protocol management commands for VPN Simulator CLI."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()


def _get_service():
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.database import DatabaseManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.services.protocol import ProtocolService
    return ProtocolService(EventBus(), ConfigManager(), DatabaseManager())


@click.group("protocol")
def protocols_group() -> None:
    """Manage VPN protocols."""


@protocols_group.command("list")
@click.pass_context
def protocol_list(ctx: click.Context) -> None:
    """List all available protocols."""
    json_output: bool = ctx.obj["json_output"]

    try:
        service = _get_service()
        protocols = asyncio.run(service.list_protocols())
        protocol_list = [
            {"name": p.get("name", ""), "state": "stopped", "port": 0, "connections": 0}
            for p in protocols
        ]
    except Exception:
        protocol_list = []

    if not protocol_list:
        protocol_list = [
            {"name": "PPTP", "state": "stopped", "port": 1723, "connections": 0},
            {"name": "L2TP", "state": "stopped", "port": 1701, "connections": 0},
            {"name": "OpenVPN", "state": "stopped", "port": 1194, "connections": 0},
            {"name": "IPSec", "state": "stopped", "port": 500, "connections": 0},
            {"name": "IKEv2", "state": "stopped", "port": 500, "connections": 0},
            {"name": "WireGuard", "state": "stopped", "port": 51820, "connections": 0},
        ]

    if json_output:
        output_json(protocol_list)
    else:
        output_table(
            title="Available Protocols",
            columns=["Name", "State", "Port", "Connections"],
            rows=[
                [p["name"], p["state"], str(p["port"]), str(p["connections"])]
                for p in protocol_list
            ],
        )


@protocols_group.command("start")
@click.argument("name")
@click.option("--port", "-p", type=int, help="Override default port.")
@click.pass_context
def protocol_start(ctx: click.Context, name: str, port: int | None) -> None:
    """Start a VPN protocol server."""
    json_output: bool = ctx.obj["json_output"]
    verbose: bool = ctx.obj["verbose"]

    if verbose:
        console.print(f"[dim]Starting {name} protocol...[/dim]")

    try:
        service = _get_service()
        asyncio.run(service.start_protocol(name=name, port=port))
        handle_success(f"Protocol {name} started", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to start protocol {name}: {e}", json_output=json_output)


@protocols_group.command("stop")
@click.argument("name")
@click.pass_context
def protocol_stop(ctx: click.Context, name: str) -> None:
    """Stop a VPN protocol server."""
    json_output: bool = ctx.obj["json_output"]

    try:
        service = _get_service()
        asyncio.run(service.stop_protocol(name))
        handle_success(f"Protocol {name} stopped", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to stop protocol {name}: {e}", json_output=json_output)
