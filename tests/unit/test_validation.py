"""Tests for the VPN config validation domain models."""

from __future__ import annotations

from vpn_simulator.domain.validation import StepStatus, ValidationResult, ValidationStep


def test_step_to_dict():
    step = ValidationStep("syntax", StepStatus.PASS, "ok", {"k": 1})
    assert step.to_dict() == {
        "name": "syntax",
        "status": "pass",
        "message": "ok",
        "metrics": {"k": 1},
    }


def test_result_status_pass():
    result = ValidationResult(
        protocol="wireguard",
        steps=[
            ValidationStep("syntax", StepStatus.PASS, "ok"),
            ValidationStep("handshake", StepStatus.SKIP, "skip"),
        ],
    )
    assert result.status == "pass"


def test_result_status_fail_on_any_fail():
    result = ValidationResult(
        protocol="wireguard",
        steps=[
            ValidationStep("syntax", StepStatus.PASS, "ok"),
            ValidationStep("auth", StepStatus.FAIL, "missing"),
        ],
    )
    assert result.status == "fail"


def test_result_metrics_merged():
    result = ValidationResult(
        protocol="wireguard",
        steps=[
            ValidationStep("latency", StepStatus.PASS, "", {"latency_ms": 1.2}),
            ValidationStep("throughput", StepStatus.PASS, "", {"throughput_mbps": 900.0}),
        ],
    )
    assert result.metrics == {"latency_ms": 1.2, "throughput_mbps": 900.0}


def test_result_to_dict():
    result = ValidationResult(
        protocol="pptp", steps=[ValidationStep("syntax", StepStatus.PASS, "ok")]
    )
    d = result.to_dict()
    assert d["protocol"] == "pptp"
    assert d["status"] == "pass"
    assert d["steps"][0]["name"] == "syntax"
