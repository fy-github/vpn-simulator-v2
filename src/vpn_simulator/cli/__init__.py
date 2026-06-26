"""VPN Simulator CLI - Command-line interface for VPN Simulator v2."""

import logging
import sys

import click
import structlog
from rich.console import Console

structlog.configure(
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logging.basicConfig(
    format="%(message)s",
    stream=sys.stderr,
    level=logging.WARNING,
)

from vpn_simulator.cli.commands.attacks import attacks_group
from vpn_simulator.cli.commands.automation import automation_group
from vpn_simulator.cli.commands.benchmark import benchmark_group
from vpn_simulator.cli.commands.config import config_group
from vpn_simulator.cli.commands.connections import connections_group
from vpn_simulator.cli.commands.faults import faults_group
from vpn_simulator.cli.commands.protocols import protocols_group
from vpn_simulator.cli.commands.scenario import scenario_group
from vpn_simulator.cli.commands.server import server_group

console = Console()


@click.group()
@click.version_option(version="2.0.0", prog_name="vpn-simulator")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, json_output: bool) -> None:
    """VPN Simulator - Multi-protocol VPN server simulator for teaching, testing, and research."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["json_output"] = json_output


cli.add_command(server_group)
cli.add_command(protocols_group)
cli.add_command(connections_group)
cli.add_command(faults_group)
cli.add_command(attacks_group)
cli.add_command(benchmark_group)
cli.add_command(config_group)
cli.add_command(scenario_group)
cli.add_command(automation_group)


def main() -> None:
    """Entry point for the CLI."""
    cli()


__all__ = ["cli", "main"]
