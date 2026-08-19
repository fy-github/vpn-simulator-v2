"""Tests for the Prometheus text-format exporter."""

from __future__ import annotations

from vpn_simulator.plugins.exporters.prometheus import render_prometheus_text

SAMPLE_METRICS = {
    "throughput": {"stats": {"min": 10.0, "avg": 20.0}, "unit": "Mbps"},
    "latency": {"stats": {"avg": 15.5}, "unit": "ms"},
    "packet_loss": {"stats": {"avg": 0.5}, "unit": "%"},
    "connections": {"current": 100, "peak": 120, "average": 110.5},
    "time_range": "5m",
    "protocol": "all",
}


def test_render_prometheus_text_contains_gauges():
    text = render_prometheus_text(SAMPLE_METRICS)

    assert "# HELP vpn_simulator_throughput_mbps Simulated VPN throughput (Mbps)" in text
    assert "# TYPE vpn_simulator_throughput_mbps gauge" in text
    assert 'vpn_simulator_throughput_mbps{protocol="all",stat="avg"} 20.0' in text
    assert 'vpn_simulator_latency_ms{protocol="all",stat="avg"} 15.5' in text
    assert 'vpn_simulator_packet_loss_percent{protocol="all",stat="avg"} 0.5' in text
    assert 'vpn_simulator_connections{stat="current"} 100.0' in text
    assert 'vpn_simulator_connections{stat="peak"} 120.0' in text
    assert 'vpn_simulator_connections{stat="average"} 110.5' in text


def test_render_prometheus_text_empty():
    assert render_prometheus_text({}) == ""
    assert render_prometheus_text({"connections": {}}) == ""


def test_render_prometheus_text_escapes_label_values():
    metrics = {
        "throughput": {"stats": {"avg": 1.0}, "unit": "Mbps"},
        "latency": {"stats": {}, "unit": "ms"},
        "packet_loss": {"stats": {}, "unit": "%"},
        "connections": {},
        "protocol": 'we"ird\\name',
    }
    text = render_prometheus_text(metrics)
    assert 'protocol="we\\"ird\\\\name"' in text
