"""Tests for the time-varying impairment domain model (5 change types)."""

from __future__ import annotations

import pytest
from vpn_simulator.domain.impairment import ChangeType, Impairment


def _imp(**kwargs) -> Impairment:
    defaults = dict(
        fault_type="latency",
        param="delay_ms",
        change_type=ChangeType.LINEAR,
        start_value=0.0,
        end_value=100.0,
        duration_seconds=60.0,
    )
    defaults.update(kwargs)
    return Impairment(**defaults)


def test_linear_curve():
    imp = _imp(change_type=ChangeType.LINEAR, start_value=0.0, end_value=300.0)
    assert imp.value_at(0.0) == 0.0
    assert imp.value_at(30.0) == pytest.approx(150.0)
    assert imp.value_at(60.0) == 300.0
    assert imp.value_at(120.0) == 300.0  # clamp after duration


def test_exponential_curve():
    imp = _imp(change_type=ChangeType.EXPONENTIAL, start_value=10.0, end_value=500.0)
    assert imp.value_at(0.0) == 10.0
    assert imp.value_at(60.0) == pytest.approx(500.0)
    # 指数曲线先缓后陡：前半段增速小于后半段
    assert imp.value_at(15.0) - 10.0 < (500.0 - 10.0) / 2.0
    assert imp.value_at(45.0) > imp.value_at(15.0)


def test_step_curve_default_midpoint():
    imp = _imp(change_type=ChangeType.STEP, start_value=0.0, end_value=0.3)
    assert imp.value_at(0.0) == 0.0
    assert imp.value_at(29.9) == 0.0
    assert imp.value_at(30.0) == 0.3
    assert imp.value_at(60.0) == 0.3


def test_step_curve_custom_time():
    imp = _imp(change_type=ChangeType.STEP, start_value=0.0, end_value=1.0, step_at_seconds=10.0)
    assert imp.value_at(9.99) == 0.0
    assert imp.value_at(10.0) == 1.0


def test_sine_curve_bounded_and_periodic():
    imp = _imp(
        change_type=ChangeType.SINE,
        start_value=100.0,
        end_value=1000.0,
        duration_seconds=60.0,
        period_seconds=20.0,
    )
    for t in (0.0, 5.0, 10.0, 15.0, 20.0, 60.0):
        assert 100.0 <= imp.value_at(t) <= 1000.0
    # 正弦周期：t 与 t + period 取值相等
    assert imp.value_at(3.0) == pytest.approx(imp.value_at(23.0))


def test_random_curve_bounded():
    imp = _imp(change_type=ChangeType.RANDOM, start_value=0.0, end_value=50.0)
    for _ in range(100):
        assert 0.0 <= imp.value_at(1.0) <= 50.0


def test_timeline_samples():
    imp = _imp(change_type=ChangeType.LINEAR, start_value=0.0, end_value=100.0)
    timeline = imp.timeline(samples=5)
    assert len(timeline) == 5
    assert timeline[0]["t"] == 0.0
    assert timeline[0]["value"] == 0.0
    assert timeline[-1]["t"] == 60.0
    assert timeline[-1]["value"] == 100.0


def test_lifecycle_elapsed_and_current_value():
    imp = _imp(
        change_type=ChangeType.LINEAR,
        start_value=0.0,
        end_value=60.0,
        duration_seconds=60.0,
    )
    assert imp.current_value() is None  # not started
    imp.start()
    assert imp.active is True
    assert imp.current_value() is not None
    imp.stop()
    assert imp.active is False
    assert imp.elapsed_seconds() is not None
