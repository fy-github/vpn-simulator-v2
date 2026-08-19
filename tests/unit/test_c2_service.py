"""Tests for C2Service - C2 attack scenarios (F8)."""

from __future__ import annotations

from vpn_simulator.services.c2 import C2Service


def test_list_scenarios_covers_5_plus():
    service = C2Service()
    scenarios = service.list_scenarios()
    assert len(scenarios) >= 5
    ids = {s["id"] for s in scenarios}
    assert {
        "dns_c2",
        "http_beacon",
        "https_sliver",
        "icmp_tunnel",
        "websocket_c2",
        "dga_fallback",
    } <= ids


def test_get_scenario():
    service = C2Service()
    scenario = service.get_scenario("dns_c2")
    assert scenario is not None
    assert scenario["channel"] == "dns"
    assert scenario["mitre_attck_id"] == "T1071.004"
    assert service.get_scenario("missing") is None


def test_simulate_returns_steps_and_indicators():
    service = C2Service()
    result = service.simulate("http_beacon")
    assert result is not None
    assert result.scenario_id == "http_beacon"
    assert len(result.steps) >= 4
    stages = {s["stage"] for s in result.steps}
    assert {"staging", "beacon", "c2_channel", "command"} <= stages
    assert len(result.detected_indicators) >= 3


def test_simulate_unknown_returns_none():
    service = C2Service()
    assert service.simulate("missing") is None


def test_detection_features():
    service = C2Service()
    features = service.detection_features("https_sliver")
    assert features is not None
    assert features["channel"] == "https"
    assert features["mitre_attck_id"] == "T1071.001"
    assert "TLS JA3" in " ".join(features["indicators"])
    assert service.detection_features("missing") is None


def test_ethics_declaration():
    service = C2Service()
    ethics = service.ethics()
    assert "title" in ethics
    assert "purpose" in ethics
    assert len(ethics["restrictions"]) >= 2
    assert any("授权" in r for r in ethics["restrictions"]) or "authorization" in ethics
