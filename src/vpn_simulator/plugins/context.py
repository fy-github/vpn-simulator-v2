"""Plugin Context - Dependency injection container for plugins.

This module provides the PluginContext class which serves as a dependency
injection container, providing plugins with access to shared services:

- Event bus for inter-plugin communication
- Configuration manager for settings
- Logger for structured logging
- Database session for persistence
- Platform adapter for OS-specific operations

Example:
    context = PluginContext(
        event_bus=event_bus,
        config=config_manager,
        logger=logger,
    )
    await plugin.initialize(context)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from vpn_simulator.core.events import EventBus


@dataclass
class PluginContext:
    """Dependency injection container for plugins.

    Provides plugins with access to shared services and resources.
    Each plugin receives a PluginContext during initialization, which
    it uses to interact with the broader system.

    Attributes:
        event_bus: Event bus for publishing and subscribing to events.
        config: Configuration manager for reading settings.
        logger: Logger instance for structured logging.
        database: Database session or connection (optional).
        platform: Platform adapter for OS-specific operations (optional).
        extra: Additional context-specific data.

    Example:
        # Creating a context
        context = PluginContext(
            event_bus=event_bus,
            config=config_manager,
            logger=logging.getLogger("plugin"),
        )

        # Using in a plugin
        class MyPlugin(Plugin):
            async def initialize(self, context: PluginContext) -> None:
                self._logger = context.logger
                self._event_bus = context.event_bus

                # Subscribe to events
                context.event_bus.on_async(
                    "connection.created",
                    self._on_connection_created,
                )

                # Read configuration
                port = context.config.get("my_plugin.port", default=8080)
    """

    event_bus: EventBus
    """Event bus for inter-plugin communication."""

    config: Any = None
    """Configuration manager instance."""

    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("vpn_simulator.plugin"))
    """Logger instance for structured logging."""

    database: Any = None
    """Database session or connection (optional)."""

    platform: Any = None
    """Platform adapter for OS-specific operations (optional)."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Additional context-specific data."""

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Convenience method that delegates to the config manager.

        Args:
            key: Configuration key (dot-notation supported).
            default: Default value if key not found.

        Returns:
            Configuration value or default.

        Example:
            port = context.get_config("protocols.pptp.port", default=1723)
        """
        if self.config is None:
            return default

        if hasattr(self.config, "get"):
            return self.config.get(key, default)

        # Support dict-like config
        if isinstance(self.config, dict):
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

        return default

    def emit_event(self, event_name: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event on the event bus.

        Convenience method for emitting events without directly
        referencing the event bus.

        Args:
            event_name: Name of the event to emit.
            data: Event data payload.

        Example:
            context.emit_event("plugin.loaded", {"name": "pptp"})
        """
        if self.event_bus:
            import asyncio

            if asyncio.iscoroutinefunction(self.event_bus.emit):
                asyncio.create_task(self.event_bus.emit(event_name, data or {}))
            else:
                self.event_bus.emit(event_name, data or {})

    def create_child_logger(self, name: str) -> logging.Logger:
        """Create a child logger for a plugin.

        Creates a logger that inherits from the context's logger,
        useful for plugin-specific logging.

        Args:
            name: Logger name suffix.

        Returns:
            Logger instance with plugin-specific naming.

        Example:
            logger = context.create_child_logger("pptp")
            logger.info("PPTP plugin initialized")
        """
        return logging.getLogger(f"{self.logger.name}.{name}")
