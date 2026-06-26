"""Connection management commands for VPN Simulator CLI."""

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
    from vpn_simulator.services.connection import ConnectionService
    return ConnectionService(EventBus(), ConfigManager(), DatabaseManager())


@click.group("connection")
def connections_group() -> None:
    """Manage VPN connections."""


@connections_group.command("list")
@click.option("--protocol", "-p", help="Filter by protocol name.")
@click.option("--state", "-s", help="Filter by connection state.")
@click.pass_context
def connection_list(ctx: click.Context, protocol: str | None, state: str | None) -> None:
    """List active connections."""
    json_output: bool = ctx.obj["json_output"]

    try:
        service = _get_service()
        connections = asyncio.run(service.list_connections(protocol=protocol, state=state))
    except Exception:
        connections = []

    if json_output:
        output_json(connections)
    else:
        if not connections:
            console.print("[dim]No active connections.[/dim]")
            return

        output_table(
            title="Active Connections",
            columns=["ID", "Protocol", "State", "Local", "Remote", "Created"],
            rows=[
                [
                    c.get("id", ""),
                    c.get("protocol", ""),
                    c.get("state", ""),
                    c.get("local_address", ""),
                    c.get("remote_address", ""),
                    c.get("created_at", ""),
                ]
                for c in connections
            ],
        )


@connections_group.command("disconnect")
@click.argument("connection_id")
@click.option("--force", "-f", is_flag=True, help="Force disconnect without confirmation.")
@click.pass_context
def connection_disconnect(
    ctx: click.Context, connection_id: str, force: bool
) -> None:
    """Disconnect a specific connection."""
    json_output: bool = ctx.obj["json_output"]

    if not force:
        if not click.confirm(f"Disconnect connection {connection_id}?"):
            return

    try:
        service = _get_service()
        asyncio.run(service.disconnect_connection(connection_id))
        handle_success(f"Connection {connection_id} disconnected", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to disconnect connection {connection_id}: {e}", json_output=json_output)
