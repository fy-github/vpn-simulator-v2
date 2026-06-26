"""Fault injection commands for VPN Simulator CLI."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

FAULT_TYPES = ["latency", "packet_loss", "bandwidth", "reorder", "duplicate", "corrupt"]


def _get_service():
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.database import DatabaseManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.services.fault import FaultService
    return FaultService(EventBus(), ConfigManager(), DatabaseManager())


@click.group("fault")
def faults_group() -> None:
    """Manage fault injection."""


@faults_group.command("list")
@click.pass_context
def fault_list(ctx: click.Context) -> None:
    """List all active faults."""
    json_output: bool = ctx.obj["json_output"]

    try:
        service = _get_service()
        faults = asyncio.run(service.list_faults())
    except Exception:
        faults = []

    if json_output:
        output_json(faults)
    else:
        if not faults:
            console.print("[dim]No active faults.[/dim]")
            return

        output_table(
            title="Active Faults",
            columns=["ID", "Type", "Target", "Params", "Active"],
            rows=[
                [
                    f.get("id", ""),
                    f.get("type", ""),
                    f.get("target", ""),
                    str(f.get("params", "")),
                    str(f.get("active", "")),
                ]
                for f in faults
            ],
        )


@faults_group.command("add")
@click.argument("type", type=click.Choice(FAULT_TYPES))
@click.option("--target", "-t", required=True, help="Target protocol or connection.")
@click.option("--param", "-p", multiple=True, help="Fault parameter in key=value format.")
@click.pass_context
def fault_add(ctx: click.Context, type: str, target: str, param: tuple[str, ...]) -> None:
    """Add a fault injection."""
    json_output: bool = ctx.obj["json_output"]
    verbose: bool = ctx.obj["verbose"]

    params: dict[str, str] = {}
    for p in param:
        if "=" not in p:
            handle_error(f"Invalid parameter format: {p}. Use key=value.", json_output=json_output)
            return
        key, value = p.split("=", 1)
        params[key] = value

    if verbose:
        console.print(f"[dim]Adding {type} fault to {target} with params {params}[/dim]")

    try:
        service = _get_service()
        asyncio.run(service.create_fault(fault_type=type, params=params, target=target))
        handle_success(f"Fault {type} added to {target}", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to add fault: {e}", json_output=json_output)


@faults_group.command("remove")
@click.argument("fault_id")
@click.option("--force", "-f", is_flag=True, help="Remove without confirmation.")
@click.pass_context
def fault_remove(ctx: click.Context, fault_id: str, force: bool) -> None:
    """Remove a fault injection."""
    json_output: bool = ctx.obj["json_output"]

    if not force:
        if not click.confirm(f"Remove fault {fault_id}?"):
            return

    try:
        service = _get_service()
        asyncio.run(service.remove_fault(fault_id))
        handle_success(f"Fault {fault_id} removed", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to remove fault {fault_id}: {e}", json_output=json_output)
