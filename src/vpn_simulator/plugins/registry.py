"""Plugin Registry - Manages plugin registration and discovery.

This module provides the core plugin registry system including:
- PluginType enum for categorizing plugins
- PluginMeta dataclass for plugin metadata
- Plugin abstract base class for all plugins
- PluginRegistry for centralized plugin management
- @plugin decorator for easy plugin registration

Example:
    @plugin("pptp")
    class PPTPProtocol(Plugin):
        def meta(self) -> PluginMeta:
            return PluginMeta(...)

        async def initialize(self, context: PluginContext) -> None:
            pass

        async def shutdown(self) -> None:
            pass
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from vpn_simulator.plugins.context import PluginContext

T = TypeVar("T", bound="Plugin")


class PluginType(Enum):
    """Plugin type enumeration.

    Categorizes plugins into different functional areas:
    - PROTOCOL: VPN protocol implementations (PPTP, L2TP, etc.)
    - FAULT: Fault injection plugins (latency, packet loss, etc.)
    - ATTACK: Attack simulation plugins (MITM, replay, etc.)
    - EXPORTER: Data export plugins (PCAP, JSON, etc.)
    - AUTH: Authentication plugins (local, LDAP, OAuth2, etc.)
    """

    PROTOCOL = "protocol"
    FAULT = "fault"
    ATTACK = "attack"
    EXPORTER = "exporter"
    AUTH = "auth"


@dataclass
class PluginMeta:
    """Plugin metadata container.

    Stores essential information about a plugin including its identity,
    version, authorship, and configuration requirements.

    Attributes:
        name: Unique plugin identifier (e.g., "pptp", "latency")
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author or organization
        description: Brief description of plugin functionality
        plugin_type: Category of the plugin
        dependencies: List of required plugin names
        config_schema: JSON Schema for plugin configuration
    """

    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """Abstract base class for all plugins.

    All VPN Simulator plugins must inherit from this class and implement
    the required abstract methods. The plugin lifecycle is:

    1. Registration: Plugin class is decorated with @plugin("name")
    2. Instantiation: PluginRegistry creates an instance
    3. Initialization: initialize() is called with PluginContext
    4. Operation: Plugin performs its designated function
    5. Shutdown: shutdown() is called for cleanup

    Example:
        @plugin("pptp")
        class PPTPProtocol(Plugin):
            def meta(self) -> PluginMeta:
                return PluginMeta(
                    name="pptp",
                    version="1.0.0",
                    author="VPN Simulator",
                    description="PPTP Protocol Implementation",
                    plugin_type=PluginType.PROTOCOL,
                )

            async def initialize(self, context: PluginContext) -> None:
                self._context = context

            async def shutdown(self) -> None:
                pass
    """

    @abstractmethod
    def meta(self) -> PluginMeta:
        """Return plugin metadata.

        Returns:
            PluginMeta containing plugin identity and configuration.
        """
        ...

    @abstractmethod
    async def initialize(self, context: "PluginContext") -> None:
        """Initialize the plugin with provided context.

        Called once after plugin instantiation. Use this to set up
        resources, register event handlers, and validate configuration.

        Args:
            context: PluginContext providing access to shared services.

        Raises:
            PluginInitializationError: If initialization fails.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the plugin and release resources.

        Called during application shutdown or plugin unloading.
        Ensure all resources are properly released.
        """
        ...


class PluginRegistry:
    """Centralized plugin registry.

    Manages plugin registration, discovery, and lifecycle. Plugins are
    registered either via the @plugin decorator or manually through
    the register() class method.

    Thread Safety:
        This registry uses class-level storage and is safe for use
        in single-threaded async contexts. For multi-threaded access,
        external synchronization is required.

    Example:
        # Via decorator (preferred)
        @plugin("my_plugin")
        class MyPlugin(Plugin):
            ...

        # Manual registration
        PluginRegistry.register(MyPlugin())

        # Query plugins
        plugin = PluginRegistry.get("my_plugin")
        protocols = PluginRegistry.get_by_type(PluginType.PROTOCOL)
    """

    _plugins: dict[str, Plugin] = {}
    _plugins_by_type: dict[PluginType, list[Plugin]] = {}

    @classmethod
    def register(cls, plugin: Plugin) -> None:
        """Register a plugin instance.

        Adds the plugin to both the name-based and type-based indices.
        If a plugin with the same name already exists, it will be replaced.

        Args:
            plugin: Plugin instance to register.

        Example:
            plugin = PPTPProtocol()
            PluginRegistry.register(plugin)
        """
        meta = plugin.meta()
        cls._plugins[meta.name] = plugin

        if meta.plugin_type not in cls._plugins_by_type:
            cls._plugins_by_type[meta.plugin_type] = []
        cls._plugins_by_type[meta.plugin_type].append(plugin)

    @classmethod
    def get(cls, name: str) -> Plugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name to look up.

        Returns:
            Plugin instance if found, None otherwise.

        Example:
            plugin = PluginRegistry.get("pptp")
            if plugin:
                await plugin.initialize(context)
        """
        return cls._plugins.get(name)

    @classmethod
    def get_by_type(cls, plugin_type: PluginType) -> list[Plugin]:
        """Get all plugins of a specific type.

        Args:
            plugin_type: PluginType to filter by.

        Returns:
            List of Plugin instances matching the type.

        Example:
            protocols = PluginRegistry.get_by_type(PluginType.PROTOCOL)
            for plugin in protocols:
                print(plugin.meta().name)
        """
        return cls._plugins_by_type.get(plugin_type, [])

    @classmethod
    def list_all(cls) -> list[PluginMeta]:
        """List metadata for all registered plugins.

        Returns:
            List of PluginMeta for all registered plugins.

        Example:
            for meta in PluginRegistry.list_all():
                print(f"{meta.name} v{meta.version}")
        """
        return [p.meta() for p in cls._plugins.values()]

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a plugin by name.

        Args:
            name: Plugin name to unregister.

        Returns:
            True if plugin was found and removed, False otherwise.
        """
        plugin = cls._plugins.pop(name, None)
        if plugin is None:
            return False

        meta = plugin.meta()
        if meta.plugin_type in cls._plugins_by_type:
            try:
                cls._plugins_by_type[meta.plugin_type].remove(plugin)
            except ValueError:
                pass
        return True

    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins.

        Useful for testing or resetting the registry.
        """
        cls._plugins.clear()
        cls._plugins_by_type.clear()


def plugin(name: str) -> Callable[[type[T]], type[T]]:
    """Plugin registration decorator.

    Registers a Plugin subclass with the PluginRegistry. The decorated
    class is instantiated and registered immediately at decoration time.

    Args:
        name: Unique name for the plugin.

    Returns:
        Decorator function that registers and returns the class.

    Example:
        @plugin("pptp")
        class PPTPProtocol(Plugin):
            def meta(self) -> PluginMeta:
                return PluginMeta(
                    name="pptp",
                    version="1.0.0",
                    author="VPN Simulator",
                    description="PPTP Protocol",
                    plugin_type=PluginType.PROTOCOL,
                )

            async def initialize(self, context: PluginContext) -> None:
                pass

            async def shutdown(self) -> None:
                pass
    """

    def decorator(cls: type[T]) -> type[T]:
        instance = cls()
        PluginRegistry.register(instance)
        return cls

    return decorator
