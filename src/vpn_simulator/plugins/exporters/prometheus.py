"""Prometheus 文本格式导出插件。

将 MetricsService.get_statistics() 的聚合指标渲染为 Prometheus 文本
格式（version 0.0.4），供 Prometheus/`/metrics` 抓取端点直接消费。
渲染底层复用官方 `prometheus-client` 库（F6 收尾），保证转义、浮点
格式与标签排序与 Prometheus 生态一致。

Example:
    >>> from vpn_simulator.plugins.exporters.prometheus import render_prometheus_text
    >>> text = render_prometheus_text(metrics)
"""

from __future__ import annotations

from typing import Any

from prometheus_client import CollectorRegistry, Gauge, generate_latest

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


def render_prometheus_text(metrics: dict[str, Any]) -> str:
    """将 get_statistics() 的输出渲染为 Prometheus 文本格式。

    Args:
        metrics: MetricsService.get_statistics() 返回的聚合指标字典。

    Returns:
        Prometheus 文本格式（末尾含换行），无指标时返回空串。
    """
    registry = CollectorRegistry()
    protocol = str(metrics.get("protocol", "all"))
    gauges: dict[str, Gauge] = {}

    def get_gauge(name: str, help_text: str, labelnames: list[str]) -> Gauge:
        """复用同一指标名的 Gauge 对象（不同标签组合走 .labels()）。"""
        if name not in gauges:
            gauges[name] = Gauge(name, help_text, labelnames, registry=registry)
        return gauges[name]

    for section, metric_name, help_text in _METRIC_DEFS:
        stats = metrics.get(section, {}).get("stats", {})
        samples = [(stat, float(stats[stat])) for stat in _STAT_KEYS if stat in stats]
        if not samples:
            continue
        gauge = get_gauge(metric_name, help_text, ["stat", "protocol"])
        for stat, value in samples:
            gauge.labels(stat=stat, protocol=protocol).set(value)

    connections = metrics.get("connections", {})
    conn_samples = [
        (stat, float(connections[stat]))
        for stat in ("current", "peak", "average")
        if stat in connections
    ]
    if conn_samples:
        gauge = get_gauge("vpn_simulator_connections", "Simulated VPN connection count", ["stat"])
        for stat, value in conn_samples:
            gauge.labels(stat=stat).set(value)

    return generate_latest(registry).decode("utf-8")


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
