"""Plugin Loader - Dynamic plugin discovery and loading.

This module provides functionality to dynamically discover and load plugins
from directories. It supports:

- Scanning directories for plugin modules
- Loading Python modules dynamically
- Validating loaded plugins
- Managing plugin lifecycle (initialize/shutdown)

Example:
    loader = PluginLoader(context)
    await loader.load_directory(Path("plugins/protocols"))
    await loader.initialize_all()
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType

from vpn_simulator.plugins.context import PluginContext
from vpn_simulator.plugins.registry import Plugin, PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoaderError(Exception):
    """Base exception for plugin loader errors."""


class PluginLoadError(PluginLoaderError):
    """Raised when a plugin fails to load."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load plugin from {path}: {reason}")


class PluginInitError(PluginLoaderError):
    """Raised when a plugin fails to initialize."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason
        super().__init__(f"Failed to initialize plugin '{name}': {reason}")


class PluginLoader:
    """Dynamic plugin loader.

    Discovers and loads plugins from filesystem directories. Plugins are
    Python modules that use the @plugin decorator to register themselves
    with the PluginRegistry.

    The loader supports two directory structures:

    1. Flat structure (single plugin per file):
       plugins/
           pptp.py
           l2tp.py

    2. Package structure (plugin as package):
       plugins/
           pptp/
               __init__.py
               plugin.py
           l2tp/
               __init__.py
               plugin.py

    Attributes:
        context: PluginContext for plugin initialization.
        _loaded_modules: Set of already loaded module paths.

    Example:
        context = PluginContext(event_bus=event_bus, config=config)
        loader = PluginLoader(context)

        # Load from directory
        await loader.load_directory(Path("plugins/protocols"))

        # Initialize all loaded plugins
        await loader.initialize_all()

        # Or initialize specific plugin
        await loader.initialize_plugin("pptp")
    """

    def __init__(self, context: PluginContext) -> None:
        """Initialize the plugin loader.

        Args:
            context: PluginContext providing shared services.
        """
        self.context = context
        self._loaded_modules: set[Path] = set()
        self._initialized_plugins: set[str] = set()

    async def load_directory(self, directory: Path, recursive: bool = True) -> list[str]:
        """Load all plugins from a directory.

        Scans the directory for Python modules and packages containing
        plugin definitions. Each discovered plugin is registered with
        the PluginRegistry.

        Args:
            directory: Path to scan for plugins.
            recursive: Whether to scan subdirectories.

        Returns:
            List of loaded plugin names.

        Raises:
            PluginLoadError: If a plugin fails to load.

        Example:
            names = await loader.load_directory(Path("plugins/protocols"))
            print(f"Loaded: {names}")
        """
        if not directory.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return []

        if not directory.is_dir():
            raise PluginLoadError(directory, "Path is not a directory")

        loaded: list[str] = []

        # Load Python files directly
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            names = await self._load_module_file(py_file)
            loaded.extend(names)

        # Load packages (directories with __init__.py)
        if recursive:
            for subdir in directory.iterdir():
                if not subdir.is_dir() or subdir.name.startswith("_"):
                    continue

                init_file = subdir / "__init__.py"
                if init_file.exists():
                    names = await self._load_package(subdir)
                    loaded.extend(names)

        logger.info(f"Loaded {len(loaded)} plugin(s) from {directory}: {loaded}")
        return loaded

    async def _load_module_file(self, path: Path) -> list[str]:
        if path in self._loaded_modules:
            return []

        before_names = {m.name for m in PluginRegistry.list_all()}
        module = self._load_module(path)
        self._loaded_modules.add(path)

        after_names = {m.name for m in PluginRegistry.list_all()}
        new_plugins = list(after_names - before_names)
        return new_plugins

    async def _load_package(self, directory: Path) -> list[str]:
        """Load a plugin package.

        Args:
            directory: Path to the package directory.

        Returns:
            List of plugin names registered from this package.
        """
        init_file = directory / "__init__.py"
        plugin_file = directory / "plugin.py"

        loaded: list[str] = []

        # Load __init__.py first
        if init_file.exists():
            names = await self._load_module_file(init_file)
            loaded.extend(names)

        # Load plugin.py if it exists
        if plugin_file.exists():
            names = await self._load_module_file(plugin_file)
            loaded.extend(names)

        return loaded

    def _load_module(self, path: Path) -> ModuleType:
        """Dynamically load a Python module.

        Args:
            path: Path to the Python file.

        Returns:
            Loaded module.

        Raises:
            PluginLoadError: If the module fails to load.
        """
        module_name = f"vpn_simulator_plugin_{path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(path, "Could not create module spec")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        except Exception as e:
            raise PluginLoadError(path, str(e)) from e

    async def initialize_plugin(self, name: str) -> None:
        """Initialize a specific plugin.

        Calls the plugin's initialize() method with the context.
        If the plugin is already initialized, this is a no-op.

        Args:
            name: Plugin name to initialize.

        Raises:
            PluginInitError: If initialization fails.
        """
        if name in self._initialized_plugins:
            return

        plugin = PluginRegistry.get(name)
        if plugin is None:
            raise PluginInitError(name, "Plugin not found in registry")

        try:
            logger.info(f"Initializing plugin: {name}")
            await plugin.initialize(self.context)
            self._initialized_plugins.add(name)
            logger.info(f"Plugin initialized: {name}")

        except Exception as e:
            raise PluginInitError(name, str(e)) from e

    async def initialize_all(self) -> list[str]:
        """Initialize all registered plugins.

        Initializes plugins in dependency order. Plugins with no
        dependencies are initialized first.

        Returns:
            List of successfully initialized plugin names.

        Raises:
            PluginInitError: If any plugin fails to initialize.
        """
        all_plugins = PluginRegistry.list_all()
        initialized: list[str] = []
        pending = {m.name for m in all_plugins}

        max_iterations = len(all_plugins) + 1
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1
            progress = False

            for meta in all_plugins:
                if meta.name not in pending:
                    continue

                # Check if all dependencies are satisfied
                deps_satisfied = all(
                    dep in initialized or dep in self._initialized_plugins
                    for dep in meta.dependencies
                )

                if deps_satisfied:
                    await self.initialize_plugin(meta.name)
                    initialized.append(meta.name)
                    pending.discard(meta.name)
                    progress = True

            if not progress and pending:
                unsatisfied = {
                    name: next(
                        m.dependencies
                        for m in all_plugins
                        if m.name == name
                    )
                    for name in pending
                }
                raise PluginInitError(
                    list(pending)[0],
                    f"Circular or missing dependencies: {unsatisfied}"
                )

        return initialized

    async def shutdown_plugin(self, name: str) -> None:
        """Shutdown a specific plugin.

        Args:
            name: Plugin name to shutdown.
        """
        plugin = PluginRegistry.get(name)
        if plugin and name in self._initialized_plugins:
            try:
                logger.info(f"Shutting down plugin: {name}")
                await plugin.shutdown()
                self._initialized_plugins.discard(name)
            except Exception as e:
                logger.error(f"Error shutting down plugin '{name}': {e}")

    async def shutdown_all(self) -> None:
        """Shutdown all initialized plugins.

        Shuts down plugins in reverse initialization order.
        """
        for name in reversed(list(self._initialized_plugins)):
            await self.shutdown_plugin(name)
