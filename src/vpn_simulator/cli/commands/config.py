"""Configuration management commands for VPN Simulator CLI."""

from __future__ import annotations

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json

console = Console()


def _get_config_manager():
    from vpn_simulator.core.config import ConfigManager
    return ConfigManager()


@click.group("config")
def config_group() -> None:
    """Manage VPN Simulator configuration."""


@config_group.command("get")
@click.argument("key", required=False)
@click.pass_context
def config_get(ctx: click.Context, key: str | None) -> None:
    """Get configuration value(s)."""
    json_output: bool = ctx.obj["json_output"]

    try:
        config_manager = _get_config_manager()
        config = config_manager.config

        if key:
            value = getattr(config, key, None)
            if json_output:
                output_json({key: value})
            else:
                console.print(f"{key} = {value}")
        else:
            config_dict = config_manager._config_to_dict(config)
            if json_output:
                output_json(config_dict)
            else:
                for k, v in config_dict.items():
                    if isinstance(v, dict):
                        for kk, vv in v.items():
                            console.print(f"{k}.{kk} = {vv}")
                    else:
                        console.print(f"{k} = {v}")
    except Exception as e:
        handle_error(str(e), json_output=json_output)


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value."""
    json_output: bool = ctx.obj["json_output"]
    verbose: bool = ctx.obj["verbose"]

    if verbose:
        console.print(f"[dim]Setting {key} = {value}[/dim]")

    try:
        config_manager = _get_config_manager()
        config = config_manager.config

        if hasattr(config, key):
            setattr(config, key, value)
            config_manager.save(config)
            handle_success(f"Configuration updated: {key} = {value}", json_output=json_output)
        else:
            handle_error(f"Unknown configuration key: {key}", json_output=json_output)
    except Exception as e:
        handle_error(str(e), json_output=json_output)
