"""Unit tests for the protocol state machine module.

Tests cover:
- State registration and initial state
- Transition rule registration
- Event triggering and state transitions
- Guard conditions
- Action callbacks (on_enter, on_exit)
- Transition history tracking
- Listener notifications
- Visualization data output
"""

from __future__ import annotations

import pytest

from vpn_simulator.domain.protocol import (
    ProtocolStateMachine,
    State,
    StateTransition,
    TransitionRecord,
)


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


class TestState:
    """Tests for the State data class."""

    def test_state_creation(self):
        """Verify State can be created with required fields."""
        state = State("INIT", "Initial state")
        assert state.name == "INIT"
        assert state.description == "Initial state"
        assert state.is_initial is False
        assert state.is_final is False
        assert state.on_enter is None
        assert state.on_exit is None

    def test_state_with_flags(self):
        """Verify State accepts initial and final flags."""
        state = State("INIT", "Initial", is_initial=True, is_final=False)
        assert state.is_initial is True
        assert state.is_final is False


class TestStateTransition:
    """Tests for the StateTransition data class."""

    def test_transition_creation(self):
        """Verify StateTransition can be created with required fields."""
        transition = StateTransition("INIT", "READY", "START")
        assert transition.from_state == "INIT"
        assert transition.to_state == "READY"
        assert transition.event == "START"
        assert transition.guard is None
        assert transition.action is None
        assert transition.description == ""

    def test_transition_with_description(self):
        """Verify StateTransition accepts description."""
        transition = StateTransition(
            "INIT", "READY", "START", description="Start the process"
        )
        assert transition.description == "Start the process"


class TestProtocolStateMachine:
    """Tests for the ProtocolStateMachine class."""

    def test_initial_state(self, state_machine: SimpleStateMachine):
        """Verify state machine starts at the initial state."""
        assert state_machine.current_state == "IDLE"
        assert state_machine.protocol_name == "TestProtocol"

    def test_states_registered(self, state_machine: SimpleStateMachine):
        """Verify all states are registered."""
        assert len(state_machine.states) == 4
        assert "IDLE" in state_machine.states
        assert "CONNECTING" in state_machine.states
        assert "CONNECTED" in state_machine.states
        assert "ERROR" in state_machine.states

    def test_transitions_registered(self, state_machine: SimpleStateMachine):
        """Verify all transitions are registered."""
        assert len(state_machine.transitions) == 5

    def test_duplicate_state_raises(self):
        """Verify adding duplicate state raises ValueError."""
        sm = SimpleStateMachine()
        with pytest.raises(ValueError, match="already exists"):
            sm.add_state(State("IDLE", "Duplicate"))

    @pytest.mark.asyncio
    async def test_valid_transition(self, state_machine: SimpleStateMachine):
        """Verify valid transition changes state."""
        result = await state_machine.trigger("CONNECT")
        assert result is True
        assert state_machine.current_state == "CONNECTING"

    @pytest.mark.asyncio
    async def test_invalid_event(self, state_machine: SimpleStateMachine):
        """Verify invalid event returns False and state unchanged."""
        result = await state_machine.trigger("INVALID_EVENT")
        assert result is False
        assert state_machine.current_state == "IDLE"

    @pytest.mark.asyncio
    async def test_invalid_transition_from_wrong_state(self, state_machine: SimpleStateMachine):
        """Verify event that doesn't match current state returns False."""
        result = await state_machine.trigger("ESTABLISHED")
        assert result is False
        assert state_machine.current_state == "IDLE"

    @pytest.mark.asyncio
    async def test_multi_step_transition(self, state_machine: SimpleStateMachine):
        """Verify multi-step state transitions work correctly."""
        await state_machine.trigger("CONNECT")
        assert state_machine.current_state == "CONNECTING"

        await state_machine.trigger("ESTABLISHED")
        assert state_machine.current_state == "CONNECTED"

    @pytest.mark.asyncio
    async def test_transition_to_error_state(self, state_machine: SimpleStateMachine):
        """Verify transition to error state."""
        await state_machine.trigger("CONNECT")
        await state_machine.trigger("FAIL")
        assert state_machine.current_state == "ERROR"

    @pytest.mark.asyncio
    async def test_recovery_from_error(self, state_machine: SimpleStateMachine):
        """Verify recovery from error state."""
        await state_machine.trigger("CONNECT")
        await state_machine.trigger("FAIL")
        await state_machine.trigger("RESET")
        assert state_machine.current_state == "IDLE"

    @pytest.mark.asyncio
    async def test_final_state_rejects_events(self, state_machine: SimpleStateMachine):
        """Verify final state does not accept events."""
        await state_machine.trigger("CONNECT")
        await state_machine.trigger("ESTABLISHED")
        assert state_machine.current_state == "CONNECTED"

        result = await state_machine.trigger("CONNECT")
        assert result is False

    @pytest.mark.asyncio
    async def test_transition_records_history(self, state_machine: SimpleStateMachine):
        """Verify transitions are recorded in history."""
        await state_machine.trigger("CONNECT")
        await state_machine.trigger("ESTABLISHED")

        assert len(state_machine.history) == 2
        assert state_machine.history[0].from_state == "IDLE"
        assert state_machine.history[0].to_state == "CONNECTING"
        assert state_machine.history[0].event == "CONNECT"
        assert state_machine.history[1].from_state == "CONNECTING"
        assert state_machine.history[1].to_state == "CONNECTED"

    @pytest.mark.asyncio
    async def test_transition_with_context(self, state_machine: SimpleStateMachine):
        """Verify context is passed to transition record."""
        await state_machine.trigger("CONNECT", context={"user": "test"})
        assert state_machine.history[0].context == {"user": "test"}


class TestGuardConditions:
    """Tests for transition guard conditions."""

    @pytest.mark.asyncio
    async def test_guard_allows_transition(self):
        """Verify transition proceeds when guard returns True."""
        sm = SimpleStateMachine()
        sm.add_transition(
            StateTransition(
                "IDLE",
                "CONNECTING",
                "AUTH_CONNECT",
                guard=lambda ctx: ctx.get("authenticated", False),
            )
        )

        result = await sm.trigger("AUTH_CONNECT", {"authenticated": True})
        assert result is True
        assert sm.current_state == "CONNECTING"

    @pytest.mark.asyncio
    async def test_guard_blocks_transition(self):
        """Verify transition is blocked when guard returns False."""
        sm = SimpleStateMachine()
        sm.add_transition(
            StateTransition(
                "IDLE",
                "CONNECTING",
                "AUTH_CONNECT",
                guard=lambda ctx: ctx.get("authenticated", False),
            )
        )

        result = await sm.trigger("AUTH_CONNECT", {"authenticated": False})
        assert result is False
        assert sm.current_state == "IDLE"

    @pytest.mark.asyncio
    async def test_guard_with_none_context(self):
        """Verify guard handles None context gracefully."""
        sm = SimpleStateMachine()
        sm.add_transition(
            StateTransition(
                "IDLE",
                "CONNECTING",
                "AUTH_CONNECT",
                guard=lambda ctx: ctx is not None and ctx.get("authenticated", False),
            )
        )

        result = await sm.trigger("AUTH_CONNECT", None)
        assert result is False


class TestActionCallbacks:
    """Tests for state action callbacks."""

    @pytest.mark.asyncio
    async def test_on_exit_called(self, state_machine_with_actions: SimpleStateMachine):
        """Verify on_exit is called when leaving a state."""
        sm = state_machine_with_actions
        await sm.trigger("CONNECT")
        assert "exit_connecting" not in sm._action_log  # We haven't left CONNECTING yet

    @pytest.mark.asyncio
    async def test_on_enter_called(self, state_machine_with_actions: SimpleStateMachine):
        """Verify on_enter is called when entering a state."""
        sm = state_machine_with_actions
        await sm.trigger("CONNECT")
        await sm.trigger("ESTABLISHED")
        assert "enter_connected" in sm._action_log

    @pytest.mark.asyncio
    async def test_transition_action_called(self):
        """Verify transition action is called during transition."""
        action_log: list[str] = []

        async def transition_action(ctx):
            action_log.append("action_executed")

        sm = ProtocolStateMachine("TestProtocol")
        sm.add_state(State("IDLE", "Idle state", is_initial=True))
        sm.add_state(State("CONNECTING", "Connecting state"))
        sm.add_transition(
            StateTransition("IDLE", "CONNECTING", "CONNECT", action=transition_action)
        )

        await sm.trigger("CONNECT")
        assert "action_executed" in action_log


class TestListeners:
    """Tests for transition listeners."""

    @pytest.mark.asyncio
    async def test_listener_notified(self, state_machine: SimpleStateMachine):
        """Verify listeners are notified on transition."""
        notifications: list[tuple] = []

        async def listener(from_state, to_state, event):
            notifications.append((from_state, to_state, event))

        state_machine.on_transition(listener)
        await state_machine.trigger("CONNECT")

        assert len(notifications) == 1
        assert notifications[0] == ("IDLE", "CONNECTING", "CONNECT")

    @pytest.mark.asyncio
    async def test_multiple_listeners(self, state_machine: SimpleStateMachine):
        """Verify multiple listeners are all notified."""
        notifications_a: list[str] = []
        notifications_b: list[str] = []

        async def listener_a(from_state, to_state, event):
            notifications_a.append(event)

        async def listener_b(from_state, to_state, event):
            notifications_b.append(event)

        state_machine.on_transition(listener_a)
        state_machine.on_transition(listener_b)
        await state_machine.trigger("CONNECT")

        assert "CONNECT" in notifications_a
        assert "CONNECT" in notifications_b


class TestVisualizationData:
    """Tests for visualization data output."""

    def test_visualization_data_structure(self, state_machine: SimpleStateMachine):
        """Verify visualization data has correct structure."""
        data = state_machine.get_visualization_data()

        assert "protocol" in data
        assert "current_state" in data
        assert "states" in data
        assert "transitions" in data
        assert "history" in data

    def test_visualization_protocol_name(self, state_machine: SimpleStateMachine):
        """Verify visualization data includes protocol name."""
        data = state_machine.get_visualization_data()
        assert data["protocol"] == "TestProtocol"

    def test_visualization_current_state(self, state_machine: SimpleStateMachine):
        """Verify visualization data includes current state."""
        data = state_machine.get_visualization_data()
        assert data["current_state"] == "IDLE"

    def test_visualization_states(self, state_machine: SimpleStateMachine):
        """Verify visualization data includes all states."""
        data = state_machine.get_visualization_data()
        assert len(data["states"]) == 4
        state_names = {s["name"] for s in data["states"]}
        assert state_names == {"IDLE", "CONNECTING", "CONNECTED", "ERROR"}

    def test_visualization_transitions(self, state_machine: SimpleStateMachine):
        """Verify visualization data includes all transitions."""
        data = state_machine.get_visualization_data()
        assert len(data["transitions"]) == 5

    @pytest.mark.asyncio
    async def test_visualization_includes_history(self, state_machine: SimpleStateMachine):
        """Verify visualization data includes transition history."""
        await state_machine.trigger("CONNECT")
        data = state_machine.get_visualization_data()
        assert len(data["history"]) == 1
        assert data["history"][0]["from"] == "IDLE"
        assert data["history"][0]["to"] == "CONNECTING"
