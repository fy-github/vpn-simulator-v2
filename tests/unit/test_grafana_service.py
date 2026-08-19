"""Tests for GrafanaService - dashboards and alert rules (F6)."""

from __future__ import annotations

from vpn_simulator.services.grafana import GrafanaService


def test_list_dashboards():
    service = GrafanaService()
    dashboards = service.list_dashboards()
    assert len(dashboards) >= 1
    overview = next(d for d in dashboards if d["name"] == "vpn_simulator_overview")
    assert overview["uid"] == "vpn-simulator-overview"
    assert overview["title"] == "VPN Simulator Overview"


def test_get_dashboard_json():
    service = GrafanaService()
    dashboard = service.get_dashboard("vpn_simulator_overview")
    assert dashboard is not None
    assert dashboard["uid"] == "vpn-simulator-overview"
    assert len(dashboard["panels"]) >= 4
    assert {p["type"] for p in dashboard["panels"]} >= {"timeseries", "stat", "gauge"}


def test_get_unknown_dashboard_returns_none():
    service = GrafanaService()
    assert service.get_dashboard("does-not-exist") is None


def test_list_alert_rules():
    service = GrafanaService()
    groups = service.list_alert_rules()
    assert len(groups) >= 1
    rules = groups[0]["rules"]
    assert len(rules) >= 3
    names = {r["alert"] for r in rules}
    assert names >= {"HighLatency", "HighPacketLoss", "NoMetrics"}
    # 告警表达式应引用 /metrics 端点导出的真实指标名
    exprs = " ".join(r["expr"] for r in rules)
    assert "vpn_simulator_latency_ms" in exprs
    assert "vpn_simulator_packet_loss_percent" in exprs
