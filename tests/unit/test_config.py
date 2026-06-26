"""Unit tests for the configuration management module.

Tests cover:
- Config data class defaults and custom values
- ConfigManager load/save operations
- Configuration merging logic
- Environment variable loading
- Config change watchers
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from vpn_simulator.core.config import Config, ConfigManager


class TestConfig:
    """Tests for the Config data class."""

    def test_default_values(self):
        """Verify Config has expected default values."""
        config = Config()
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8080
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.locale == "zh-CN"
        assert config.platform == "auto"
        assert config.protocols == {}
        assert config.faults == {}
        assert config.attacks == {}

    def test_custom_values(self):
        """Verify Config accepts custom values."""
        config = Config(
            server_host="127.0.0.1",
            server_port=9090,
            log_level="DEBUG",
            locale="en-US",
        )
        assert config.server_host == "127.0.0.1"
        assert config.server_port == 9090
        assert config.log_level == "DEBUG"
        assert config.locale == "en-US"

    def test_dict_fields_are_independent(self):
        """Verify dict fields are independent between instances."""
        config1 = Config()
        config2 = Config()
        config1.protocols["pptp"] = {"port": 1723}
        assert "pptp" not in config2.protocols


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_init_with_default_dir(self):
        """Verify ConfigManager uses home directory by default."""
        manager = ConfigManager()
        assert manager.config_dir == Path.home() / ".vpn-simulator"

    def test_init_with_custom_dir(self, tmp_path: Path):
        """Verify ConfigManager accepts custom config directory."""
        manager = ConfigManager(config_dir=tmp_path)
        assert manager.config_dir == tmp_path
        assert manager.config_file == tmp_path / "config.yaml"

    def test_load_returns_default_config(self, config_manager: ConfigManager):
        """Verify load returns default config when no file exists."""
        config = config_manager.load()
        assert isinstance(config, Config)
        assert config.server_port == 8080

    def test_load_from_yaml_file(self, tmp_path: Path):
        """Verify config is loaded from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server_host": "192.168.1.1",
            "server_port": 9999,
            "log_level": "DEBUG",
        }
        config_file.write_text(yaml.dump(config_data))

        manager = ConfigManager(config_dir=tmp_path)
        config = manager.load()

        assert config.server_host == "192.168.1.1"
        assert config.server_port == 9999
        assert config.log_level == "DEBUG"

    def test_save_creates_file(self, config_manager: ConfigManager):
        """Verify save creates config file and directory."""
        config = Config(server_port=9090)
        config_manager.save(config)

        assert config_manager.config_file.exists()

    def test_save_and_reload(self, config_manager: ConfigManager):
        """Verify saved config file is created and can be loaded."""
        config = Config(server_port=9090, log_level="DEBUG")
        config_manager.save(config)

        assert config_manager.config_file.exists()
        reloaded = config_manager.load()
        assert isinstance(reloaded, Config)

    def test_save_without_config_raises(self, config_manager: ConfigManager):
        """Verify save raises ValueError when no config is available."""
        with pytest.raises(ValueError, match="No config to save"):
            config_manager.save()

    def test_config_property_auto_loads(self, config_manager: ConfigManager):
        """Verify config property auto-loads if not already loaded."""
        assert config_manager._config is None
        config = config_manager.config
        assert isinstance(config, Config)
        assert config_manager._config is not None

    def test_reload(self, tmp_path: Path):
        """Verify reload re-reads the config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"server_port": 1111}))

        manager = ConfigManager(config_dir=tmp_path)
        config1 = manager.load()
        assert config1.server_port == 1111

        config_file.write_text(yaml.dump({"server_port": 2222}))
        config2 = manager.reload()
        assert config2.server_port == 2222

    def test_merge_config_override_scalar(self, config_manager: ConfigManager):
        """Verify scalar values are overridden during merge."""
        base = Config(server_port=8080)
        override = {"server_port": 9090}
        merged = config_manager._merge_config(base, override)
        assert merged.server_port == 9090

    def test_merge_config_deep_merge_dict(self, config_manager: ConfigManager):
        """Verify dict values are deep merged."""
        base = Config(protocols={"pptp": {"port": 1723}})
        override = {"protocols": {"l2tp": {"port": 1701}}}
        merged = config_manager._merge_config(base, override)
        assert merged.protocols["pptp"]["port"] == 1723
        assert merged.protocols["l2tp"]["port"] == 1701

    def test_merge_config_unknown_key_ignored(self, config_manager: ConfigManager):
        """Verify unknown keys are ignored during merge."""
        base = Config()
        override = {"unknown_key": "value"}
        merged = config_manager._merge_config(base, override)
        assert not hasattr(merged, "unknown_key")

    def test_on_change_watcher(self, config_manager: ConfigManager):
        """Verify config change watcher is called on save."""
        notified: list[Config] = []
        config_manager.on_change(lambda c: notified.append(c))

        config = Config()
        config_manager.save(config)

        assert len(notified) == 1
        assert notified[0] is config

    def test_multiple_watchers(self, config_manager: ConfigManager):
        """Verify multiple watchers are all notified."""
        notified_a: list[Config] = []
        notified_b: list[Config] = []
        config_manager.on_change(lambda c: notified_a.append(c))
        config_manager.on_change(lambda c: notified_b.append(c))

        config = Config()
        config_manager.save(config)

        assert len(notified_a) == 1
        assert len(notified_b) == 1

    def test_watcher_error_does_not_break(self, config_manager: ConfigManager):
        """Verify watcher errors are caught and do not prevent other watchers."""
        notified: list[str] = []

        def bad_watcher(c):
            raise RuntimeError("Watcher error")

        def good_watcher(c):
            notified.append("good")

        config_manager.on_change(bad_watcher)
        config_manager.on_change(good_watcher)

        config_manager.save(Config())
        assert "good" in notified

    def test_load_env_vars(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch):
        """Verify environment variables override config values."""
        monkeypatch.setenv("VPN_SIM_SERVER_PORT", "5555")
        monkeypatch.setenv("VPN_SIM_LOG_LEVEL", "WARNING")
        monkeypatch.setenv("VPN_SIM_SERVER_HOST", "10.0.0.1")

        config = config_manager.load()
        assert config.server_port == 5555
        assert config.log_level == "WARNING"
        assert config.server_host == "10.0.0.1"

    def test_load_env_vars_invalid_int(self, config_manager: ConfigManager, monkeypatch: pytest.MonkeyPatch):
        """Verify invalid int env var is handled gracefully."""
        monkeypatch.setenv("VPN_SIM_SERVER_PORT", "not_a_number")
        config = config_manager.load()
        assert config.server_port == 8080  # falls back to default

    def test_config_to_dict(self, config_manager: ConfigManager):
        """Verify config is serialized to dict correctly."""
        config = Config(server_port=9090, log_level="DEBUG")
        result = config_manager._config_to_dict(config)

        assert result["server"]["port"] == 9090
        assert result["logging"]["level"] == "DEBUG"
        assert "database" in result
        assert "i18n" in result
