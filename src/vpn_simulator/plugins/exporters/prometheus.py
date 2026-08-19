"""Prometheus 文本格式导出插件。

将 MetricsService.get_statistics() 的聚合指标渲染为 Prometheus 文本
格式（version 0.0.4），供 Prometheus/`/metrics` 抓取端点直接消费。
作为首个 exporter，为后续 F6（可观测性）铺路。

Example:
    >>> from vpn_simulator.plugins.exporters.prometheus import render_prometheus_text
    >>> text = render_prometheus_text(metrics)
"""

from __future__ import annotations

from typing import Any

from vpn_simulator.plugins import Plugin, PluginContext, PluginMeta, PluginType, plugin

_METRIC_DEFS: tuple[tuple[str, str, str], ...] = (
    # (统计段名, 指标名, HELP 文本)
    ("throughput", "vpn_simulator_throughput_mbps", "Simulated VPN throughput (Mbps)"),
    ("latency", "vpn_simulator_latency_ms", "Simulated VPN latency (ms)"),
    (
        "packet_loss",
        "vpn_simulator_packet_loss_percent",
        "Simulated VPN packet loss (%)",
    ),
)

_STAT_KEYS: tuple[str, ...] = ("min", "max", "avg", "p50", "p95", "p99")


def _escape_label_value(value: str) -> str:
    """转义 Prometheus 标签值中的特殊字符。"""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _emit_gauge(
    lines: list[str],
    name: str,
    help_text: str,
    value: float,
    labels: dict[str, str],
) -> None:
    """向 lines 追加一个 gauge 指标块（HELP/TYPE/样本）。"""
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} gauge")
    label_str = ",".join(
        f'{key}="{_escape_label_value(str(val))}"' for key, val in sorted(labels.items())
    )
    lines.append(f"{name}{{{label_str}}} {value}")


def render_prometheus_text(metrics: dict[str, Any]) -> str:
    """将 get_statistics() 的输出渲染为 Prometheus 文本格式。

    Args:
        metrics: MetricsService.get_statistics() 返回的聚合指标字典。

    Returns:
        Prometheus 文本格式（末尾含换行），无指标时返回空串。
    """
    lines: list[str] = []
    protocol = str(metrics.get("protocol", "all"))

    for section, metric_name, help_text in _METRIC_DEFS:
        stats = metrics.get(section, {}).get("stats", {})
        for stat in _STAT_KEYS:
            if stat in stats:
                _emit_gauge(
                    lines,
                    metric_name,
                    help_text,
                    float(stats[stat]),
                    {"stat": stat, "protocol": protocol},
                )

    connections = metrics.get("connections", {})
    for stat in ("current", "peak", "average"):
        if stat in connections:
            _emit_gauge(
                lines,
                "vpn_simulator_connections",
                "Simulated VPN connection count",
                float(connections[stat]),
                {"stat": stat},
            )

    return "\n".join(lines) + ("\n" if lines else "")


@plugin("prometheus")
class PrometheusExporter(Plugin):
    """Prometheus 文本格式导出插件。

    无状态导出器：把聚合指标渲染为 Prometheus 文本，供抓取端点使用。
    """

    def meta(self) -> PluginMeta:
        """返回插件元数据。"""
        return PluginMeta(
            name="prometheus",
            version="1.0.0",
            author="VPN Simulator",
            description="Prometheus 文本格式指标导出插件（首个 exporter）",
            plugin_type=PluginType.EXPORTER,
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {},
            },
        )

    async def initialize(self, context: PluginContext) -> None:
        """初始化导出插件（无状态，仅记录上下文）。"""
        self._context: PluginContext | None = context

    async def shutdown(self) -> None:
        """关闭导出插件。"""
        self._context = None

    def render(self, metrics: dict[str, Any]) -> str:
        """渲染指标为 Prometheus 文本格式。"""
        return render_prometheus_text(metrics)
