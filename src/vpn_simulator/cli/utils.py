"""CLI utility functions for VPN Simulator."""

from __future__ import annotations

import json
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()


def output_json(data: Any) -> None:
    """Output data as formatted JSON."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def output_table(
    title: str,
    columns: list[str],
    rows: list[list[str]],
    *,
    json_output: bool = False,
) -> None:
    """Output data as a Rich table or JSON."""
    if json_output:
        records = [dict(zip(columns, row)) for row in rows]
        output_json(records)
        return

    table = Table(title=title, show_lines=True)
    for col in columns:
        table.add_column(col, style="cyan")
    for row in rows:
        table.add_row(*row)
    console.print(table)


def handle_error(message: str, *, json_output: bool = False) -> None:
    """Display an error message."""
    if json_output:
        output_json({"error": message})
    else:
        console.print(f"[red]Error:[/red] {message}")


def handle_success(message: str, *, json_output: bool = False) -> None:
    """Display a success message."""
    if json_output:
        output_json({"status": "ok", "message": message})
    else:
        console.print(f"[green]Success:[/green] {message}")


def confirm_action(message: str, *, abort: bool = True) -> bool:
    """Prompt the user for confirmation."""
    return click.confirm(message, abort=abort)
