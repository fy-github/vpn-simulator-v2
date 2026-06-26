"""Tests for PluginLoader - dynamic plugin discovery and loading."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from vpn_simulator.plugins.context import PluginContext
from vpn_simulator.plugins.loader import (
    PluginInitError,
    PluginLoadError,
    PluginLoader,
    PluginLoaderError,
)
from vpn_simulator.plugins.registry import PluginRegistry


@pytest.fixture
def mock_context():
    return MagicMock(spec=PluginContext)


@pytest.fixture
def loader(mock_context) -> PluginLoader:
    PluginRegistry.clear()
    return PluginLoader(mock_context)


class TestPluginLoaderInit:
    def test_loader_creation(self, loader: PluginLoader):
        assert loader is not None
        assert loader.context is not None
        assert len(loader._loaded_modules) == 0
        assert len(loader._initialized_plugins) == 0


class TestLoadDirectory:
    @pytest.mark.asyncio
    async def test_load_nonexistent_directory(self, loader: PluginLoader, tmp_path: Path):
        result = await loader.load_directory(tmp_path / "nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_load_file_not_directory(self, loader: PluginLoader, tmp_path: Path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(PluginLoadError):
            await loader.load_directory(file_path)

    @pytest.mark.asyncio
    async def test_load_directory_skips_underscore(self, loader: PluginLoader, tmp_path: Path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "_private.py").write_text("# private")
        result = await loader.load_directory(plugin_dir)
        assert result == []

    @pytest.mark.asyncio
    async def test_load_directory_no_recursive(self, loader: PluginLoader, tmp_path: Path):
        pkg_dir = tmp_path / "plugins" / "my_plugin"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("# init")
        result = await loader.load_directory(pkg_dir.parent, recursive=False)
        assert result == []

    @pytest.mark.asyncio
    async def test_load_directory_with_non_python_files(self, loader: PluginLoader, tmp_path: Path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        (plugin_dir / "readme.txt").write_text("not a plugin")
        (plugin_dir / "config.yaml").write_text("key: value")
        result = await loader.load_directory(plugin_dir)
        assert result == []

    @pytest.mark.asyncio
    async def test_load_empty_directory(self, loader: PluginLoader, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = await loader.load_directory(empty_dir)
        assert result == []


class TestLoadModule:
    def test_load_module_success(self, loader: PluginLoader, tmp_path: Path):
        py_file = tmp_path / "simple.py"
        py_file.write_text("x = 42\n")
        module = loader._load_module(py_file)
        assert module.x == 42

    def test_load_module_invalid_syntax(self, loader: PluginLoader, tmp_path: Path):
        py_file = tmp_path / "bad.py"
        py_file.write_text("def foo(:\n")
        with pytest.raises(PluginLoadError):
            loader._load_module(py_file)


class TestInitializePlugin:
    @pytest.mark.asyncio
    async def test_initialize_plugin_not_found(self, loader: PluginLoader):
        with pytest.raises(PluginInitError, match="not found"):
            await loader.initialize_plugin("nonexistent")

    @pytest.mark.asyncio
    async def test_initialize_plugin_already_initialized(self, loader: PluginLoader):
        loader._initialized_plugins.add("test")
        await loader.initialize_plugin("test")


class TestShutdownPlugin:
    @pytest.mark.asyncio
    async def test_shutdown_plugin_not_initialized(self, loader: PluginLoader):
        await loader.shutdown_plugin("nonexistent")


class TestShutdownAll:
    @pytest.mark.asyncio
    async def test_shutdown_all_empty(self, loader: PluginLoader):
        await loader.shutdown_all()


class TestErrorHierarchy:
    def test_error_hierarchy(self):
        assert issubclass(PluginLoadError, PluginLoaderError)
        assert issubclass(PluginInitError, PluginLoaderError)
        assert issubclass(PluginLoaderError, Exception)

    def test_load_error_attributes(self):
        path = Path("/test/plugin.py")
        error = PluginLoadError(path, "test reason")
        assert error.path == path
        assert error.reason == "test reason"

    def test_init_error_attributes(self):
        error = PluginInitError("my_plugin", "test reason")
        assert error.name == "my_plugin"
        assert error.reason == "test reason"
