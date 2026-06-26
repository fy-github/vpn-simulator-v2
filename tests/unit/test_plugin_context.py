"""Tests for PluginContext - dependency injection container."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, AsyncMock

import pytest

from vpn_simulator.core.events import EventBus
from vpn_simulator.plugins.context import PluginContext


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


class TestPluginContextInit:
    def test_create_with_event_bus(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus)
        assert ctx.event_bus is mock_event_bus
        assert ctx.config is None
        assert ctx.database is None
        assert ctx.platform is None
        assert ctx.extra == {}

    def test_create_with_all_fields(self, mock_event_bus):
        logger = logging.getLogger("test")
        ctx = PluginContext(
            event_bus=mock_event_bus,
            config={"key": "value"},
            logger=logger,
            database="db",
            platform="linux",
            extra={"x": 1},
        )
        assert ctx.config == {"key": "value"}
        assert ctx.logger is logger
        assert ctx.database == "db"
        assert ctx.platform == "linux"
        assert ctx.extra == {"x": 1}

    def test_default_logger(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus)
        assert ctx.logger is not None
        assert isinstance(ctx.logger, logging.Logger)


class TestGetConfig:
    def test_get_config_no_config(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus)
        result = ctx.get_config("key", default="fallback")
        assert result == "fallback"

    def test_get_config_with_dict(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus, config={"key": "value"})
        result = ctx.get_config("key", default="fallback")
        assert result == "value"

    def test_get_config_nested_dict(self, mock_event_bus):
        class NestedConfig:
            def get(self, key, default=None):
                keys = key.split(".")
                value = {"a": {"b": "c"}}
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value
        ctx = PluginContext(event_bus=mock_event_bus, config=NestedConfig())
        result = ctx.get_config("a.b", default="fallback")
        assert result == "c"

    def test_get_config_missing_key(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus, config={"key": "value"})
        result = ctx.get_config("missing", default="fallback")
        assert result == "fallback"

    def test_get_config_with_object(self, mock_event_bus):
        config_obj = MagicMock()
        config_obj.get = MagicMock(return_value="found")
        ctx = PluginContext(event_bus=mock_event_bus, config=config_obj)
        result = ctx.get_config("key")
        assert result == "found"


class TestEmitEvent:
    def test_emit_event_async(self, mock_event_bus):
        mock_event_bus.emit = AsyncMock()
        ctx = PluginContext(event_bus=mock_event_bus)
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(ctx.event_bus.emit("test.event", {"data": 1}))
        finally:
            loop.close()

    def test_emit_event_sync(self, mock_event_bus):
        mock_event_bus.emit = MagicMock()
        ctx = PluginContext(event_bus=mock_event_bus)
        ctx.emit_event("test.event", {"data": 1})
        mock_event_bus.emit.assert_called_once()

    def test_emit_event_no_bus(self):
        ctx = PluginContext(event_bus=None)
        ctx.emit_event("test.event")


class TestCreateChildLogger:
    def test_create_child_logger(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus)
        child = ctx.create_child_logger("pptp")
        assert child.name.endswith(".pptp")

    def test_child_logger_hierarchy(self, mock_event_bus):
        ctx = PluginContext(event_bus=mock_event_bus)
        child = ctx.create_child_logger("test")
        assert child.parent is ctx.logger
