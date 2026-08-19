"""Server management commands for VPN Simulator CLI."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

_RUNTIME_DIR = Path.home() / ".vpn-simulator"
_PID_FILE = _RUNTIME_DIR / "server.pid"
_STATE_FILE = _RUNTIME_DIR / "server.json"


def _read_pid() -> int | None:
    """Read the daemon PID from the pid file, if present."""
    try:
        return int(_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


def _is_running(pid: int | None) -> bool:
    """Return True if a process with the given PID exists."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_state() -> dict[str, Any]:
    """Read the persisted server state (host/port/started_at)."""
    try:
        return cast(dict[str, Any], json.loads(_STATE_FILE.read_text()))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _write_state(host: str, port: int, pid: int, started_at: float) -> None:
    """Persist server state for later status/stop commands."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(pid))
    _STATE_FILE.write_text(
        json.dumps({"host": host, "port": port, "pid": pid, "started_at": started_at})
    )


def _clear_state() -> None:
    """Remove pid/state files after shutdown."""
    _PID_FILE.unlink(missing_ok=True)
    _STATE_FILE.unlink(missing_ok=True)


def _start_daemon(host: str, port: int) -> int:
    """Spawn the API server as a detached background process and return its pid."""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _RUNTIME_DIR / "server.log"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "vpn_simulator.api.app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    log_fh = log_file.open("ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    _write_state(host, port, proc.pid, time.time())
    return proc.pid


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    """Perform a best-effort HTTP GET and parse JSON, returning None on failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None


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

    if _is_running(_read_pid()):
        handle_success(f"Server already running (pid {_read_pid()})", json_output=json_output)
        return

    if daemon:
        pid = _start_daemon(host, port)
        handle_success(
            f"Server started in background on {host}:{port} (pid {pid})",
            json_output=json_output,
        )
        return

    if verbose:
        console.print(f"[dim]Starting server on {host}:{port}[/dim]")

    # 前台运行：直接阻塞在 uvicorn 上，直到收到 Ctrl-C。
    import uvicorn

    uvicorn.run("vpn_simulator.api.app:app", host=host, port=port)


@server_group.command("stop")
@click.pass_context
def server_stop(ctx: click.Context) -> None:
    """Stop the VPN Simulator server."""
    json_output: bool = ctx.obj["json_output"]

    pid = _read_pid()
    if pid is None or not _is_running(pid):
        _clear_state()
        handle_error("Server is not running", json_output=json_output)
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    _clear_state()
    handle_success(f"Server stopped (pid {pid})", json_output=json_output)


@server_group.command("status")
@click.pass_context
def server_status(ctx: click.Context) -> None:
    """Show the current server status."""
    json_output: bool = ctx.obj["json_output"]

    pid = _read_pid()
    running = _is_running(pid)
    state = _read_state()

    host = str(state.get("host", "0.0.0.0"))
    port = int(state.get("port", 8080))
    started_at = state.get("started_at")

    active_protocols = 0
    active_connections = 0

    if running:
        health = _http_get_json(f"http://{host}:{port}/health")
        if health is not None:
            protocols = _http_get_json(f"http://{host}:{port}/api/v1/protocols")
            connections = _http_get_json(f"http://{host}:{port}/api/v1/connections")
            if isinstance(protocols, list):
                active_protocols = len(protocols)
            if isinstance(connections, list):
                active_connections = len(connections)

    uptime = "N/A"
    if running and started_at:
        uptime = f"{int(time.time() - float(started_at))}s"

    status = {
        "state": "running" if running else "stopped",
        "host": host,
        "port": port,
        "pid": pid if running else None,
        "uptime": uptime,
        "active_protocols": active_protocols,
        "active_connections": active_connections,
    }

    if json_output:
        output_json(status)
    else:
        output_table(
            title="Server Status",
            columns=["Property", "Value"],
            rows=[[k, str(v)] for k, v in status.items()],
        )
