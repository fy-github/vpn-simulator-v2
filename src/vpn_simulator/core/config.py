"""配置管理模块

提供配置加载、保存、合并和热加载功能。
支持 YAML 文件、环境变量和配置变更监听。

Example:
    >>> from vpn_simulator.core.config import ConfigManager
    >>> manager = ConfigManager()
    >>> config = manager.load()
    >>> print(config.server_port)
    8080
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog
import yaml
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

# 配置变更回调类型
ConfigWatcher = Callable[["Config"], None]


@dataclass
class Config:
    """应用配置数据类

    Attributes:
        server_host: 服务器监听地址
        server_port: 服务器监听端口
        database_url: 数据库连接 URL
        log_level: 日志级别
        log_format: 日志格式 (json/text)
        protocols: 协议相关配置
        faults: 故障注入配置
        attacks: 攻击配置
        locale: 国际化语言设置
        platform: 平台设置 (auto/windows/darwin/linux)
    """

    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 8080

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///vpn_simulator.db"

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"

    # 协议配置
    protocols: Dict[str, Any] = field(default_factory=dict)

    # 故障注入配置
    faults: Dict[str, Any] = field(default_factory=dict)

    # 攻击配置
    attacks: Dict[str, Any] = field(default_factory=dict)

    # 国际化配置
    locale: str = "zh-CN"

    # 跨平台配置
    platform: str = "auto"


class ConfigManager:
    """配置管理器

    负责配置的加载、保存、合并和热加载。
    支持多层配置覆盖：默认值 -> YAML 文件 -> 环境变量。

    Attributes:
        config_dir: 配置文件目录
        config_file: 配置文件路径
        _config: 当前配置实例
        _watchers: 配置变更监听器列表

    Example:
        >>> manager = ConfigManager(Path("/etc/vpn-simulator"))
        >>> config = manager.load()
        >>> manager.on_change(lambda c: print(f"Config changed: {c}"))
        >>> manager.save(config)
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """初始化配置管理器

        Args:
            config_dir: 配置文件目录，默认为 ~/.vpn-simulator
        """
        self.config_dir = config_dir or Path.home() / ".vpn-simulator"
        self.config_file = self.config_dir / "config.yaml"
        self._config: Optional[Config] = None
        self._watchers: List[ConfigWatcher] = []

    def load(self, env_file: Optional[Path] = None) -> Config:
        """加载配置

        按照优先级加载配置：默认值 -> YAML 文件 -> 环境变量。

        Args:
            env_file: .env 文件路径，None 则自动查找

        Returns:
            加载完成的配置对象
        """
        # 1. 加载 .env 文件
        load_dotenv(env_file)

        # 2. 加载默认配置
        config = Config()

        # 3. 加载配置文件
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                    config = self._merge_config(config, file_config)
                logger.info("config_file_loaded", path=str(self.config_file))
            except Exception as e:
                logger.error("config_file_load_error", path=str(self.config_file), error=str(e))

        # 4. 加载环境变量
        config = self._load_env_vars(config)

        self._config = config
        logger.info(
            "config_loaded",
            server=f"{config.server_host}:{config.server_port}",
            database=config.database_url,
        )
        return config

    def save(self, config: Optional[Config] = None) -> None:
        """保存配置到文件

        Args:
            config: 要保存的配置对象，None 则使用当前配置

        Raises:
            ValueError: 没有可保存的配置
        """
        config = config or self._config
        if not config:
            raise ValueError("No config to save")

        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w", encoding="utf-8") as f:
            yaml.dump(self._config_to_dict(config), f, default_flow_style=False, allow_unicode=True)

        logger.info("config_saved", path=str(self.config_file))
        self._notify_watchers(config)

    def reload(self) -> Config:
        """重新加载配置

        Returns:
            重新加载的配置对象
        """
        logger.info("config_reloading")
        return self.load()

    @property
    def config(self) -> Config:
        """获取当前配置

        如果未加载则自动加载。

        Returns:
            当前配置对象
        """
        if not self._config:
            self.load()
        return self._config

    def on_change(self, callback: ConfigWatcher) -> None:
        """注册配置变更监听器

        Args:
            callback: 配置变更时的回调函数
        """
        self._watchers.append(callback)
        logger.debug("config_watcher_registered", callback=callback.__name__)

    def _merge_config(self, base: Config, override: Dict[str, Any]) -> Config:
        """合并配置

        将覆盖配置深度合并到基础配置中。

        Args:
            base: 基础配置
            override: 覆盖配置字典

        Returns:
            合并后的配置
        """
        for key, value in override.items():
            if hasattr(base, key):
                current = getattr(base, key)
                # 深度合并字典类型
                if isinstance(current, dict) and isinstance(value, dict):
                    current.update(value)
                    setattr(base, key, current)
                else:
                    setattr(base, key, value)
        return base

    def _load_env_vars(self, config: Config) -> Config:
        """从环境变量加载配置

        环境变量前缀为 VPN_SIM_，映射到配置属性。

        Args:
            config: 基础配置

        Returns:
            加载环境变量后的配置
        """
        env_mapping: Dict[str, tuple[str, type]] = {
            "VPN_SIM_SERVER_HOST": ("server_host", str),
            "VPN_SIM_SERVER_PORT": ("server_port", int),
            "VPN_SIM_DATABASE_URL": ("database_url", str),
            "VPN_SIM_LOG_LEVEL": ("log_level", str),
            "VPN_SIM_LOG_FORMAT": ("log_format", str),
            "VPN_SIM_LOCALE": ("locale", str),
            "VPN_SIM_PLATFORM": ("platform", str),
        }

        for env_var, (config_attr, attr_type) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # 类型转换
                    if attr_type is int:
                        value = int(value)
                    elif attr_type is float:
                        value = float(value)
                    elif attr_type is bool:
                        value = value.lower() in ("true", "1", "yes")

                    setattr(config, config_attr, value)
                    logger.debug("env_var_loaded", env_var=env_var, config_attr=config_attr)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "env_var_parse_error",
                        env_var=env_var,
                        value=value,
                        error=str(e),
                    )

        return config

    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """将配置转换为可序列化的字典

        Args:
            config: 配置对象

        Returns:
            配置字典
        """
        return {
            "server": {
                "host": config.server_host,
                "port": config.server_port,
            },
            "database": {
                "url": config.database_url,
            },
            "logging": {
                "level": config.log_level,
                "format": config.log_format,
            },
            "protocols": config.protocols,
            "faults": config.faults,
            "attacks": config.attacks,
            "i18n": {
                "locale": config.locale,
            },
            "platform": config.platform,
        }

    def _notify_watchers(self, config: Config) -> None:
        """通知所有配置变更监听器

        Args:
            config: 新的配置对象
        """
        for watcher in self._watchers:
            try:
                watcher(config)
            except Exception as e:
                logger.error(
                    "config_watcher_error",
                    watcher=watcher.__name__,
                    error=str(e),
                )
