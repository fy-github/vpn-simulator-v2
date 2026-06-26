"""Unit tests for the plugin registry module.

Tests cover:
- PluginType enum values
- PluginMeta data class
- Plugin abstract base class
- PluginRegistry registration and retrieval
- PluginRegistry type-based filtering
- PluginRegistry unregister and clear
- @plugin decorator
"""

from __future__ import annotations

from typing import Any

import pytest

from vpn_simulator.plugins.context import PluginContext
from vpn_simulator.plugins.registry import (
    Plugin,
    PluginMeta,
    PluginRegistry,
    PluginType,
    plugin,
)


# ── Test Helpers ───────────────────────────────────────────────────────────────


class MockPlugin(Plugin):
    """A mock plugin for testing."""

    def __init__(self, name: str = "mock", plugin_type: PluginType = PluginType.PROTOCOL):
        self._name = name
        self._plugin_type = plugin_type
        self._initialized = False
        self._shutdown = False

    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self._name,
            version="1.0.0",
            author="Test",
            description=f"Mock {self._name} plugin",
            plugin_type=self._plugin_type,
        )

    async def initialize(self, context: PluginContext) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._shutdown = True


class FaultPlugin(Plugin):
    """A mock fault plugin for testing."""

    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="mock_fault",
            version="1.0.0",
            author="Test",
            description="Mock fault plugin",
            plugin_type=PluginType.FAULT,
        )

    async def initialize(self, context: PluginContext) -> None:
        pass

    async def shutdown(self) -> None:
        pass


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestPluginType:
    """Tests for the PluginType enum."""

    def test_plugin_type_values(self):
        """Verify all plugin type values."""
        assert PluginType.PROTOCOL.value == "protocol"
        assert PluginType.FAULT.value == "fault"
        assert PluginType.ATTACK.value == "attack"
        assert PluginType.EXPORTER.value == "exporter"
        assert PluginType.AUTH.value == "auth"

    def test_plugin_type_count(self):
        """Verify the number of plugin types."""
        assert len(PluginType) == 5


class TestPluginMeta:
    """Tests for the PluginMeta data class."""

    def test_creation_with_required_fields(self):
        """Verify PluginMeta can be created with required fields."""
        meta = PluginMeta(
            name="test",
            version="1.0.0",
            author="Author",
            description="Description",
            plugin_type=PluginType.PROTOCOL,
        )
        assert meta.name == "test"
        assert meta.version == "1.0.0"
        assert meta.author == "Author"
        assert meta.description == "Description"
        assert meta.plugin_type == PluginType.PROTOCOL
        assert meta.dependencies == []
        assert meta.config_schema == {}

    def test_creation_with_all_fields(self):
        """Verify PluginMeta accepts all fields."""
        meta = PluginMeta(
            name="test",
            version="2.0.0",
            author="Author",
            description="Description",
            plugin_type=PluginType.FAULT,
            dependencies=["dep1", "dep2"],
            config_schema={"type": "object"},
        )
        assert meta.dependencies == ["dep1", "dep2"]
        assert meta.config_schema == {"type": "object"}


class TestPlugin:
    """Tests for the Plugin abstract base class."""

    def test_cannot_instantiate_abstract(self):
        """Verify Plugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Plugin()

    @pytest.mark.asyncio
    async def test_mock_plugin_lifecycle(self, plugin_context: PluginContext):
        """Verify mock plugin lifecycle (initialize/shutdown)."""
        plugin_instance = MockPlugin()
        assert plugin_instance._initialized is False
        assert plugin_instance._shutdown is False

        await plugin_instance.initialize(plugin_context)
        assert plugin_instance._initialized is True

        await plugin_instance.shutdown()
        assert plugin_instance._shutdown is True


class TestPluginRegistry:
    """Tests for the PluginRegistry class."""

    def test_register_plugin(self):
        """Verify plugin registration."""
        plugin_instance = MockPlugin()
        PluginRegistry.register(plugin_instance)

        retrieved = PluginRegistry.get("mock")
        assert retrieved is plugin_instance

    def test_register_replaces_existing(self):
        """Verify registering plugin with same name replaces existing."""
        plugin1 = MockPlugin("duplicate")
        plugin2 = MockPlugin("duplicate")
        PluginRegistry.register(plugin1)
        PluginRegistry.register(plugin2)

        retrieved = PluginRegistry.get("duplicate")
        assert retrieved is plugin2

    def test_get_nonexistent_returns_none(self):
        """Verify getting nonexistent plugin returns None."""
        retrieved = PluginRegistry.get("nonexistent")
        assert retrieved is None

    def test_get_by_type(self):
        """Verify filtering plugins by type."""
        protocol_plugin = MockPlugin("pptp", PluginType.PROTOCOL)
        fault_plugin = MockPlugin("latency", PluginType.FAULT)
        PluginRegistry.register(protocol_plugin)
        PluginRegistry.register(fault_plugin)

        protocols = PluginRegistry.get_by_type(PluginType.PROTOCOL)
        assert len(protocols) == 1
        assert protocols[0] is protocol_plugin

        faults = PluginRegistry.get_by_type(PluginType.FAULT)
        assert len(faults) == 1
        assert faults[0] is fault_plugin

    def test_get_by_type_empty(self):
        """Verify empty list for type with no plugins."""
        result = PluginRegistry.get_by_type(PluginType.EXPORTER)
        assert result == []

    def test_list_all(self):
        """Verify listing all plugins."""
        PluginRegistry.register(MockPlugin("pptp"))
        PluginRegistry.register(MockPlugin("l2tp"))
        PluginRegistry.register(MockPlugin("latency", PluginType.FAULT))

        all_metas = PluginRegistry.list_all()
        assert len(all_metas) == 3
        names = {m.name for m in all_metas}
        assert names == {"pptp", "l2tp", "latency"}

    def test_list_all_empty(self):
        """Verify empty list when no plugins registered."""
        assert PluginRegistry.list_all() == []

    def test_unregister_plugin(self):
        """Verify plugin unregistration."""
        plugin_instance = MockPlugin()
        PluginRegistry.register(plugin_instance)

        result = PluginRegistry.unregister("mock")
        assert result is True
        assert PluginRegistry.get("mock") is None

    def test_unregister_nonexistent(self):
        """Verify unregistering nonexistent plugin returns False."""
        result = PluginRegistry.unregister("nonexistent")
        assert result is False

    def test_unregister_removes_from_type_index(self):
        """Verify unregistering removes plugin from type-based index."""
        plugin_instance = MockPlugin("pptp", PluginType.PROTOCOL)
        PluginRegistry.register(plugin_instance)

        PluginRegistry.unregister("pptp")
        protocols = PluginRegistry.get_by_type(PluginType.PROTOCOL)
        assert len(protocols) == 0

    def test_clear(self):
        """Verify clearing all plugins."""
        PluginRegistry.register(MockPlugin("pptp"))
        PluginRegistry.register(MockPlugin("l2tp"))

        PluginRegistry.clear()
        assert PluginRegistry.list_all() == []
        assert PluginRegistry.get("pptp") is None


class TestPluginDecorator:
    """Tests for the @plugin decorator."""

    def test_decorator_registers_plugin(self):
        """Verify @plugin decorator registers the plugin."""
        @plugin("decorated")
        class DecoratedPlugin(Plugin):
            def meta(self) -> PluginMeta:
                return PluginMeta(
                    name="decorated",
                    version="1.0.0",
                    author="Test",
                    description="Decorated plugin",
                    plugin_type=PluginType.PROTOCOL,
                )

            async def initialize(self, context: PluginContext) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        assert PluginRegistry.get("decorated") is not None
        meta = PluginRegistry.get("decorated").meta()
        assert meta.name == "decorated"

    def test_decorator_returns_class(self):
        """Verify @plugin decorator returns the original class."""
        @plugin("test_class")
        class TestPlugin(Plugin):
            def meta(self) -> PluginMeta:
                return PluginMeta(
                    name="test_class",
                    version="1.0.0",
                    author="Test",
                    description="Test",
                    plugin_type=PluginType.PROTOCOL,
                )

            async def initialize(self, context: PluginContext) -> None:
                pass

            async def shutdown(self) -> None:
                pass

        # The class itself should be returned, not an instance
        assert isinstance(TestPlugin, type)
