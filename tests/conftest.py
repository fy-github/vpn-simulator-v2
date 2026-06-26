"""Shared test fixtures and configuration for VPN Simulator v2 tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from vpn_simulator.core.config import Config, ConfigManager
from vpn_simulator.core.events import Event, EventBus, EventTypes
from vpn_simulator.domain.attack import AttackInfo, AttackManager, AttackType
from vpn_simulator.domain.connection import ConnectionInfo, ConnectionManager, ConnectionState
from vpn_simulator.domain.fault import FaultInfo, FaultManager, FaultParams, FaultType
from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition
from vpn_simulator.plugins.context import PluginContext
from vpn_simulator.plugins.registry import PluginMeta, PluginRegistry, PluginType


# ── Event System Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh EventBus instance for testing."""
    return EventBus(max_history=100)


@pytest.fixture
def sample_event() -> Event:
    """Create a sample event for testing."""
    return Event(
        name=EventTypes.CONNECTION_CREATED,
        data={"connection_id": "test-conn-001", "protocol": "pptp"},
        source="test",
    )


# ── Configuration Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def config() -> Config:
    """Create a default Config instance for testing."""
    return Config()


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with a temporary directory for testing."""
    return ConfigManager(config_dir=tmp_path)


@pytest.fixture
def config_with_custom_values() -> Config:
    """Create a Config with custom values for testing."""
    return Config(
        server_host="127.0.0.1",
        server_port=9090,
        log_level="DEBUG",
        log_format="text",
        locale="en-US",
        protocols={"pptp": {"port": 1723}, "l2tp": {"port": 1701}},
    )


# ── Connection Model Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def connection_manager() -> ConnectionManager:
    """Create a fresh ConnectionManager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def sample_connection() -> ConnectionInfo:
    """Create a sample ConnectionInfo for testing."""
    return ConnectionInfo(
        id="test-conn-001",
        protocol="pptp",
        state=ConnectionState.CONNECTING,
        local_address="127.0.0.1",
        local_port=1723,
        remote_address="192.168.1.100",
        remote_port=54321,
    )


# ── Fault Model Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def fault_manager() -> FaultManager:
    """Create a fresh FaultManager instance for testing."""
    return FaultManager()


@pytest.fixture
def sample_fault() -> FaultInfo:
    """Create a sample FaultInfo for testing."""
    return FaultInfo(
        id="test-fault-001",
        fault_type=FaultType.LATENCY,
        params={"delay_ms": 100, "jitter_ms": 20},
        target="pptp",
        active=True,
    )


@pytest.fixture
def fault_params() -> FaultParams:
    """Create a FaultParams instance for testing."""
    return FaultParams(
        delay_ms=100,
        jitter_ms=20,
        loss_rate=0.1,
        bandwidth_kbps=1000,
    )


# ── Attack Model Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def attack_manager() -> AttackManager:
    """Create a fresh AttackManager instance for testing."""
    return AttackManager()


@pytest.fixture
def sample_attack() -> AttackInfo:
    """Create a sample AttackInfo for testing."""
    return AttackInfo(
        id="test-attack-001",
        attack_type=AttackType.MITM,
        params={"proxy_port": 8888},
        target="pptp",
    )


# ── State Machine Fixtures ─────────────────────────────────────────────────────


class SimpleStateMachine(ProtocolStateMachine):
    """A simple state machine for testing purposes."""

    def __init__(self) -> None:
        super().__init__("TestProtocol")
        self.add_state(State("IDLE", "Idle state", is_initial=True))
        self.add_state(State("CONNECTING", "Connecting state"))
        self.add_state(State("CONNECTED", "Connected state", is_final=True))
        self.add_state(State("ERROR", "Error state"))

        self.add_transition(StateTransition("IDLE", "CONNECTING", "CONNECT"))
        self.add_transition(StateTransition("CONNECTING", "CONNECTED", "ESTABLISHED"))
        self.add_transition(StateTransition("CONNECTING", "ERROR", "FAIL"))
        self.add_transition(StateTransition("ERROR", "IDLE", "RESET"))
        self.add_transition(
            StateTransition(
                "CONNECTING",
                "CONNECTED",
                "ESTABLISHED_WITH_GUARD",
                guard=lambda ctx: ctx and ctx.get("authenticated", False),
            )
        )


@pytest.fixture
def state_machine() -> SimpleStateMachine:
    """Create a SimpleStateMachine for testing."""
    return SimpleStateMachine()


@pytest.fixture
def state_machine_with_actions() -> SimpleStateMachine:
    """Create a state machine with action callbacks for testing."""
    sm = SimpleStateMachine()
    sm._action_log: list[str] = []

    async def on_enter_connected(ctx):
        sm._action_log.append("enter_connected")

    async def on_exit_connecting(ctx):
        sm._action_log.append("exit_connecting")

    sm.states["CONNECTED"].on_enter = on_enter_connected
    sm.states["CONNECTING"].on_exit = on_exit_connecting
    return sm


# ── Plugin Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_plugin_registry():
    """Clear the plugin registry before and after each test."""
    PluginRegistry.clear()
    yield
    PluginRegistry.clear()


@pytest.fixture
def plugin_context(event_bus: EventBus) -> PluginContext:
    """Create a PluginContext for testing."""
    return PluginContext(
        event_bus=event_bus,
        config=None,
        logger=MagicMock(),
    )


@pytest.fixture
def sample_plugin_meta() -> PluginMeta:
    """Create a sample PluginMeta for testing."""
    return PluginMeta(
        name="test_plugin",
        version="1.0.0",
        author="Test Author",
        description="A test plugin",
        plugin_type=PluginType.PROTOCOL,
    )


# ── API Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def api_client() -> Generator:
    """Create a test client for the FastAPI application."""
    from fastapi.testclient import TestClient

    from vpn_simulator.api.app import app

    with TestClient(app) as client:
        yield client


# ── CLI Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def cli_runner() -> Generator:
    """Create a Click CLI test runner."""
    from click.testing import CliRunner

    return CliRunner()
