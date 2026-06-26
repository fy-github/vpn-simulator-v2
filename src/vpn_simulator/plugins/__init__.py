"""VPN Simulator Plugin System.

This package provides the core plugin infrastructure for VPN Simulator:

- **PluginType**: Enumeration of plugin categories
- **PluginMeta**: Plugin metadata container
- **Plugin**: Abstract base class for all plugins
- **PluginRegistry**: Centralized plugin registration and discovery
- **PluginLoader**: Dynamic plugin loading from directories
- **PluginContext**: Dependency injection container for plugins
- **@plugin**: Decorator for easy plugin registration

Example:
    from vpn_simulator.plugins import Plugin, PluginType, PluginMeta, plugin, PluginContext

    @plugin("my_protocol")
    class MyProtocol(Plugin):
        def meta(self) -> PluginMeta:
            return PluginMeta(
                name="my_protocol",
                version="1.0.0",
                author="Me",
                description="My custom protocol",
                plugin_type=PluginType.PROTOCOL,
            )

        async def initialize(self, context: PluginContext) -> None:
            self._context = context

        async def shutdown(self) -> None:
            pass
"""

from vpn_simulator.plugins.context import PluginContext
from vpn_simulator.plugins.loader import (
    PluginInitError,
    PluginLoadError,
    PluginLoader,
    PluginLoaderError,
)
from vpn_simulator.plugins.registry import (
    Plugin,
    PluginMeta,
    PluginRegistry,
    PluginType,
    plugin,
)

__all__ = [
    # Core types
    "PluginType",
    "PluginMeta",
    "Plugin",
    # Registry
    "PluginRegistry",
    # Loader
    "PluginLoader",
    "PluginLoaderError",
    "PluginLoadError",
    "PluginInitError",
    # Context
    "PluginContext",
    # Decorator
    "plugin",
]
