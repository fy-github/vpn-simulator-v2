"""Attack management commands for VPN Simulator CLI."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

ATTACK_TYPES = ["mitm", "replay", "brute_force", "downgrade", "traffic_analysis"]


def _get_service():
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.core.database import DatabaseManager
    from vpn_simulator.core.events import EventBus
    from vpn_simulator.services.attack import AttackService
    return AttackService(EventBus(), ConfigManager(), DatabaseManager())


@click.group("attack")
def attacks_group() -> None:
    """Manage attack simulations."""


@attacks_group.command("list")
@click.pass_context
def attack_list(ctx: click.Context) -> None:
    """List all attacks."""
    json_output: bool = ctx.obj["json_output"]

    try:
        service = _get_service()
        attacks = asyncio.run(service.list_attacks())
    except Exception:
        attacks = []

    if json_output:
        output_json(attacks)
    else:
        if not attacks:
            console.print("[dim]No attacks running.[/dim]")
            return

        output_table(
            title="Attacks",
            columns=["ID", "Type", "Target", "Status", "Started"],
            rows=[
                [
                    a.get("id", ""),
                    a.get("type", ""),
                    a.get("target", ""),
                    a.get("status", ""),
                    a.get("started_at", ""),
                ]
                for a in attacks
            ],
        )


@attacks_group.command("start")
@click.argument("type", type=click.Choice(ATTACK_TYPES))
@click.option("--target", "-t", required=True, help="Target protocol or connection.")
@click.option("--param", "-p", multiple=True, help="Attack parameter in key=value format.")
@click.pass_context
def attack_start(ctx: click.Context, type: str, target: str, param: tuple[str, ...]) -> None:
    """Start an attack simulation."""
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
        console.print(f"[dim]Starting {type} attack on {target} with params {params}[/dim]")

    try:
        service = _get_service()
        asyncio.run(service.start_attack(attack_type=type, target=target, params=params))
        handle_success(f"Attack {type} started on {target}", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to start attack: {e}", json_output=json_output)


@attacks_group.command("stop")
@click.argument("attack_id")
@click.option("--force", "-f", is_flag=True, help="Stop without confirmation.")
@click.pass_context
def attack_stop(ctx: click.Context, attack_id: str, force: bool) -> None:
    """Stop a running attack."""
    json_output: bool = ctx.obj["json_output"]

    if not force:
        if not click.confirm(f"Stop attack {attack_id}?"):
            return

    try:
        service = _get_service()
        asyncio.run(service.stop_attack(attack_id))
        handle_success(f"Attack {attack_id} stopped", json_output=json_output)
    except Exception as e:
        handle_error(f"Failed to stop attack {attack_id}: {e}", json_output=json_output)
