"""Benchmark testing commands for VPN Simulator CLI."""

from __future__ import annotations

import asyncio
import click
from rich.console import Console

from vpn_simulator.cli.utils import handle_error, handle_success, output_json, output_table

console = Console()

BENCHMARK_TYPES = ["handshake", "throughput", "memory", "concurrency"]
PROTOCOLS = ["pptp", "l2tp", "openvpn", "ipsec", "ikev2", "wireguard"]


@click.group("benchmark")
def benchmark_group() -> None:
    """Run and manage benchmark tests."""


@benchmark_group.command("run")
@click.argument("test_type", type=click.Choice(BENCHMARK_TYPES))
@click.option("--protocol", "-p", required=True, type=click.Choice(PROTOCOLS), help="Protocol to benchmark.")
@click.option("--param", "-P", multiple=True, help="Test parameter in key=value format.")
@click.pass_context
def benchmark_run(
    ctx: click.Context,
    test_type: str,
    protocol: str,
    param: tuple[str, ...],
) -> None:
    """Run a benchmark test."""
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
        console.print(f"[dim]Running {test_type} benchmark on {protocol} with params {params}[/dim]")

    # Run the benchmark
    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    async def _run() -> dict:
        service = BenchmarkService(ConfigManager())
        return await service.run_benchmark(
            test_type=test_type,
            protocol=protocol,
            params=params,
        )

    try:
        result = asyncio.run(_run())
    except ValueError as e:
        handle_error(str(e), json_output=json_output)
        return
    except Exception as e:
        handle_error(f"Benchmark failed: {e}", json_output=json_output)
        return

    if json_output:
        output_json(result)
    else:
        console.print(f"[green]Benchmark completed![/green]")
        console.print(f"  ID: {result.get('id', 'N/A')}")
        console.print(f"  Type: {result.get('test_type', 'N/A')}")
        console.print(f"  Protocol: {result.get('protocol', 'N/A')}")
        console.print(f"  Status: {result.get('status', 'N/A')}")

        if result.get("result") and result["result"].get("metrics"):
            metrics = result["result"]["metrics"]
            console.print(f"\n[bold]Metrics:[/bold]")
            if test_type == "handshake":
                console.print(f"  Handshake Time: {metrics.get('handshake_time_ms', 0):.2f} ms")
            elif test_type == "throughput":
                console.print(f"  Throughput: {metrics.get('throughput_mbps', 0):.2f} Mbps")
            elif test_type == "memory":
                console.print(f"  Memory Usage: {metrics.get('memory_mb', 0):.2f} MB")
            elif test_type == "concurrency":
                console.print(f"  Concurrent Connections: {metrics.get('concurrent_connections', 0)}")
            console.print(f"  CPU Usage: {metrics.get('cpu_percent', 0):.1f}%")


@benchmark_group.command("results")
@click.option("--limit", "-l", default=10, help="Maximum number of results to show.")
@click.pass_context
def benchmark_results(ctx: click.Context, limit: int) -> None:
    """Show benchmark results."""
    json_output: bool = ctx.obj["json_output"]

    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    async def _get_results() -> list[dict]:
        service = BenchmarkService(ConfigManager())
        return await service.get_results(limit=limit)

    try:
        results = asyncio.run(_get_results())
    except Exception as e:
        handle_error(f"Failed to get results: {e}", json_output=json_output)
        return

    if json_output:
        output_json(results)
    else:
        if not results:
            console.print("[dim]No benchmark results available.[/dim]")
            return

        rows = []
        for r in results:
            metrics = r.get("result", {}).get("metrics", {})
            rows.append([
                r.get("id", "")[:8],
                r.get("test_type", ""),
                r.get("protocol", ""),
                r.get("status", ""),
                f"{metrics.get('handshake_time_ms', 0):.1f}" if r.get("test_type") == "handshake" else "-",
                f"{metrics.get('throughput_mbps', 0):.1f}" if r.get("test_type") == "throughput" else "-",
                f"{metrics.get('memory_mb', 0):.1f}" if r.get("test_type") == "memory" else "-",
                str(metrics.get("concurrent_connections", 0)) if r.get("test_type") == "concurrency" else "-",
            ])

        output_table(
            title="Benchmark Results",
            columns=["ID", "Type", "Protocol", "Status", "Handshake(ms)", "Throughput(Mbps)", "Memory(MB)", "Connections"],
            rows=rows,
        )


@benchmark_group.command("compare")
@click.option("--baseline", "-b", required=True, help="Baseline benchmark ID.")
@click.option("--current", "-c", required=True, help="Current benchmark ID.")
@click.pass_context
def benchmark_compare(ctx: click.Context, baseline: str, current: str) -> None:
    """Compare two benchmark results."""
    json_output: bool = ctx.obj["json_output"]

    from vpn_simulator.core.config import ConfigManager
    from vpn_simulator.services.benchmark import BenchmarkService

    async def _compare() -> dict:
        service = BenchmarkService(ConfigManager())
        return await service.compare_results(
            baseline_id=baseline,
            current_id=current,
        )

    try:
        result = asyncio.run(_compare())
    except ValueError as e:
        handle_error(str(e), json_output=json_output)
        return
    except Exception as e:
        handle_error(f"Comparison failed: {e}", json_output=json_output)
        return

    if json_output:
        output_json(result)
    else:
        console.print("[green]Comparison completed![/green]\n")

        baseline_info = result.get("baseline", {})
        current_info = result.get("current", {})

        console.print(f"[bold]Baseline:[/bold] {baseline_info.get('id', 'N/A')} ({baseline_info.get('protocol', 'N/A')})")
        console.print(f"[bold]Current:[/bold]  {current_info.get('id', 'N/A')} ({current_info.get('protocol', 'N/A')})")

        changes = result.get("changes", {})
        if changes:
            console.print("\n[bold]Changes:[/bold]")
            for metric, change in changes.items():
                absolute = change.get("absolute", 0)
                percent = change.get("percent", 0)
                direction = "+" if absolute > 0 else ""
                console.print(f"  {metric}: {direction}{absolute:.2f} ({direction}{percent:.1f}%)")
