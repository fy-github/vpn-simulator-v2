"""Server management commands for VPN Simulator CLI."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()


def _get_protocol_service():
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.database import DatabaseManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.services.protocol import ProtocolService
    return ProtocolService(EventBus(), ConfigManager(), DatabaseManager())


def _get_connection_service():
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.database import DatabaseManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.services.connection import ConnectionService
    return ConnectionService(EventBus(), ConfigManager(), DatabaseManager())


@click.group("server")
def server_group() -> None:
    """Manage the VPN Simulator server."""


@server_group.command("start")
@click.option("--host", "-h", default="0.0.0.0", help="Server bind address.")
@click.option("--port", "-p", default=8080, type=int, help="Server bind port.")
@click.option("--daemon", "-d", is_flag=True, help="Run as background daemon.")
@click.pass_context
def server_start(ctx: click.Context, host: str, port: int, daemon: bool) -> None:
    """Start the VPN Simulator server."""
    json_output: bool = ctx.obj["json_output"]
    verbose: bool = ctx.obj["verbose"]

    if verbose:
        console.print(f"[dim]Starting server on {host}:{port}[/dim]")

    handle_success(f"Server started on {host}:{port}", json_output=json_output)


@server_group.command("stop")
@click.pass_context
def server_stop(ctx: click.Context) -> None:
    """Stop the VPN Simulator server."""
    json_output: bool = ctx.obj["json_output"]
    handle_success("Server stopped", json_output=json_output)


@server_group.command("status")
@click.pass_context
def server_status(ctx: click.Context) -> None:
    """Show the current server status."""
    json_output: bool = ctx.obj["json_output"]

    try:
        protocol_service = _get_protocol_service()
        connection_service = _get_connection_service()

        protocols = asyncio.run(protocol_service.list_protocols())
        connections = asyncio.run(connection_service.list_connections())

        status = {
            "state": "running",
            "host": "0.0.0.0",
            "port": 8080,
            "uptime": "N/A",
            "active_protocols": len(protocols),
            "active_connections": len(connections),
        }
    except Exception as e:
        status = {
            "state": "unknown",
            "host": "0.0.0.0",
            "port": 8080,
            "uptime": "N/A",
            "active_protocols": 0,
            "active_connections": 0,
            "error": str(e),
        }

    if json_output:
        output_json(status)
    else:
        output_table(
            title="Server Status",
            columns=["Property", "Value"],
            rows=[[k, str(v)] for k, v in status.items()],
        )
