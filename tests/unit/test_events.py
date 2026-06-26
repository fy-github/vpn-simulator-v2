"""Unit tests for the event system module.

Tests cover:
- Event data class creation and defaults
- EventBus subscribe/unsubscribe mechanism
- Event emission with sync and async handlers
- Event history tracking and filtering
- Handler error handling
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from vpn_simulator.core.events import Event, EventBus, EventTypes


class TestEvent:
    """Tests for the Event data class."""

    def test_event_creation_with_defaults(self):
        """Verify Event is created with auto-generated id and timestamp."""
        event = Event(name="test.event", data={"key": "value"})
        assert event.name == "test.event"
        assert event.data == {"key": "value"}
        assert event.source == ""
        assert event.event_id is not None
        assert len(event.event_id) == 36  # UUID format
        assert isinstance(event.timestamp, datetime)

    def test_event_creation_with_all_fields(self):
        """Verify Event creation with explicitly provided fields."""
        event = Event(
            name="connection.created",
            data={"id": "123"},
            source="test_source",
            event_id="custom-id",
        )
        assert event.name == "connection.created"
        assert event.data == {"id": "123"}
        assert event.source == "test_source"
        assert event.event_id == "custom-id"

    def test_event_unique_ids(self):
        """Verify each Event gets a unique ID."""
        event1 = Event(name="test.event", data={})
        event2 = Event(name="test.event", data={})
        assert event1.event_id != event2.event_id


class TestEventBus:
    """Tests for the EventBus class."""

    def test_initial_state(self, event_bus: EventBus):
        """Verify EventBus starts with no handlers and empty history."""
        assert not event_bus.has_handlers("any.event")
        assert event_bus.get_history() == []

    @patch("vpn_simulator.core.events.logger")
    def test_register_sync_handler(self, mock_logger, event_bus: EventBus):
        """Verify sync handler registration."""
        handler = lambda e: None
        event_bus.on("test.event", handler)
        assert event_bus.has_handlers("test.event")

    @patch("vpn_simulator.core.events.logger")
    def test_register_async_handler(self, mock_logger, event_bus: EventBus):
        """Verify async handler registration."""
        async def handler(event):
            pass

        event_bus.on_async("test.event", handler)
        assert event_bus.has_handlers("test.event")

    @patch("vpn_simulator.core.events.logger")
    def test_unregister_handler(self, mock_logger, event_bus: EventBus):
        """Verify handler removal."""
        handler = lambda e: None
        event_bus.on("test.event", handler)
        assert event_bus.has_handlers("test.event")

        event_bus.off("test.event", handler)
        assert not event_bus.has_handlers("test.event")

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_triggers_sync_handler(self, mock_logger, event_bus: EventBus):
        """Verify sync handler is called when event is emitted."""
        received_events: list[Event] = []
        handler = lambda e: received_events.append(e)
        event_bus.on("test.event", handler)

        await event_bus.emit("test.event", {"key": "value"})

        assert len(received_events) == 1
        assert received_events[0].data == {"key": "value"}

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_triggers_async_handler(self, mock_logger, event_bus: EventBus):
        """Verify async handler is called when event is emitted."""
        received_events: list[Event] = []

        async def handler(event: Event):
            received_events.append(event)

        event_bus.on_async("test.event", handler)

        await event_bus.emit("test.event", {"key": "value"})

        assert len(received_events) == 1
        assert received_events[0].data == {"key": "value"}

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_multiple_handlers(self, mock_logger, event_bus: EventBus):
        """Verify multiple handlers are called in order."""
        call_order: list[str] = []

        def handler_a(e):
            call_order.append("A")

        def handler_b(e):
            call_order.append("B")

        event_bus.on("test.event", handler_a)
        event_bus.on("test.event", handler_b)

        await event_bus.emit("test.event")

        assert call_order == ["A", "B"]

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_returns_event(self, mock_logger, event_bus: EventBus):
        """Verify emit returns the created Event object."""
        result = await event_bus.emit("test.event", {"key": "value"}, source="test")
        assert isinstance(result, Event)
        assert result.name == "test.event"
        assert result.source == "test"

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_records_history(self, mock_logger, event_bus: EventBus):
        """Verify emitted events are recorded in history."""
        await event_bus.emit("event.a")
        await event_bus.emit("event.b")
        await event_bus.emit("event.a")

        history = event_bus.get_history()
        assert len(history) == 3

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_get_history_filtered(self, mock_logger, event_bus: EventBus):
        """Verify history can be filtered by event name."""
        await event_bus.emit("event.a")
        await event_bus.emit("event.b")
        await event_bus.emit("event.a")

        filtered = event_bus.get_history(event_name="event.a")
        assert len(filtered) == 2
        assert all(e.name == "event.a" for e in filtered)

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_get_history_limit(self, mock_logger, event_bus: EventBus):
        """Verify history respects limit parameter."""
        for i in range(10):
            await event_bus.emit("test.event", {"i": i})

        limited = event_bus.get_history(limit=3)
        assert len(limited) == 3

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_history_max_size(self, mock_logger):
        """Verify history is trimmed when max_history is exceeded."""
        bus = EventBus(max_history=5)
        for i in range(10):
            await bus.emit("test.event", {"i": i})

        assert len(bus.get_history()) == 5

    @patch("vpn_simulator.core.events.logger")
    def test_clear_history(self, mock_logger, event_bus: EventBus):
        """Verify history can be cleared."""
        event_bus._history.append(Event(name="test.event", data={}))
        event_bus.clear_history()
        assert event_bus.get_history() == []

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_sync_handler_error_does_not_break_emit(self, mock_logger, event_bus: EventBus):
        """Verify handler errors are caught and do not prevent other handlers."""
        call_log: list[str] = []

        def bad_handler(e):
            raise RuntimeError("Handler error")

        def good_handler(e):
            call_log.append("good")

        event_bus.on("test.event", bad_handler)
        event_bus.on("test.event", good_handler)

        await event_bus.emit("test.event")
        assert "good" in call_log

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_async_handler_error_does_not_break_emit(self, mock_logger, event_bus: EventBus):
        """Verify async handler errors are caught."""
        call_log: list[str] = []

        async def bad_handler(e):
            raise RuntimeError("Async handler error")

        async def good_handler(e):
            call_log.append("good")

        event_bus.on_async("test.event", bad_handler)
        event_bus.on_async("test.event", good_handler)

        await event_bus.emit("test.event")
        assert "good" in call_log

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_with_no_data(self, mock_logger, event_bus: EventBus):
        """Verify emit works with no data argument."""
        received_events: list[Event] = []
        event_bus.on("test.event", lambda e: received_events.append(e))

        await event_bus.emit("test.event")
        assert received_events[0].data == {}

    @patch("vpn_simulator.core.events.logger")
    @pytest.mark.asyncio
    async def test_emit_unsubscribed_event(self, mock_logger, event_bus: EventBus):
        """Verify emitting event with no handlers does not raise."""
        result = await event_bus.emit("no.handlers.event")
        assert isinstance(result, Event)


class TestEventTypes:
    """Tests for the EventTypes constants."""

    def test_protocol_events_exist(self):
        """Verify protocol event type constants are defined."""
        assert EventTypes.PROTOCOL_STARTED == "protocol.started"
        assert EventTypes.PROTOCOL_STOPPED == "protocol.stopped"
        assert EventTypes.PROTOCOL_ERROR == "protocol.error"

    def test_connection_events_exist(self):
        """Verify connection event type constants are defined."""
        assert EventTypes.CONNECTION_CREATED == "connection.created"
        assert EventTypes.CONNECTION_ESTABLISHED == "connection.established"
        assert EventTypes.CONNECTION_CLOSED == "connection.closed"
        assert EventTypes.CONNECTION_ERROR == "connection.error"

    def test_packet_events_exist(self):
        """Verify packet event type constants are defined."""
        assert EventTypes.PACKET_RECEIVED == "packet.received"
        assert EventTypes.PACKET_SENT == "packet.sent"
        assert EventTypes.PACKET_DROPPED == "packet.dropped"

    def test_fault_events_exist(self):
        """Verify fault event type constants are defined."""
        assert EventTypes.FAULT_INJECTED == "fault.injected"
        assert EventTypes.FAULT_REMOVED == "fault.removed"

    def test_attack_events_exist(self):
        """Verify attack event type constants are defined."""
        assert EventTypes.ATTACK_STARTED == "attack.started"
        assert EventTypes.ATTACK_COMPLETED == "attack.completed"
        assert EventTypes.ATTACK_DETECTED == "attack.detected"

    def test_system_events_exist(self):
        """Verify system event type constants are defined."""
        assert EventTypes.SYSTEM_STARTUP == "system.startup"
        assert EventTypes.SYSTEM_SHUTDOWN == "system.shutdown"
        assert EventTypes.CONFIG_CHANGED == "config.changed"
