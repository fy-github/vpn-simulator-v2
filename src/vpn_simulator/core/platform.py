"""跨平台适配层模块

提供操作系统相关的平台抽象和适配器实现。
支持 Windows、macOS 和 Linux 平台。

Example:
    >>> from vpn_simulator.core.platform import get_platform_adapter
    >>> adapter = get_platform_adapter()
    >>> info = adapter.get_platform_info()
    >>> print(f"Running on {info.os} {info.arch}")
    >>> is_admin = await adapter.check_privileges()
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PlatformInfo:
    """平台信息

    Attributes:
        os: 操作系统类型 (windows/darwin/linux)
        arch: 系统架构 (x86_64/arm64)
        version: 系统版本
        is_admin: 是否有管理员/root 权限
        python_version: Python 版本
    """

    os: str
    arch: str
    version: str
    is_admin: bool
    python_version: str


class PlatformAdapter(ABC):
    """平台适配器基类

    定义跨平台操作的抽象接口。
    各平台实现必须提供这些方法的具体实现。
    """

    @abstractmethod
    def get_platform_info(self) -> PlatformInfo:
        """获取平台信息

        Returns:
            当前平台的详细信息
        """
        pass

    @abstractmethod
    async def check_privileges(self) -> bool:
        """检查是否有管理员/root 权限

        Returns:
            是否有管理员权限
        """
        pass

    @abstractmethod
    async def create_raw_socket(self, protocol: int) -> socket.socket:
        """创建原始套接字

        Args:
            protocol: 协议号 (如 socket.IPPROTO_GRE)

        Returns:
            原始套接字对象

        Raises:
            PermissionError: 没有管理员权限
            OSError: 创建套接字失败
        """
        pass

    @abstractmethod
    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        """配置防火墙规则

        Args:
            rule: 防火墙规则配置

        Returns:
            配置是否成功
        """
        pass

    @abstractmethod
    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """获取网络接口列表

        Returns:
            网络接口信息列表，每个接口包含 name 和 addresses
        """
        pass

    @abstractmethod
    async def manage_service(self, action: str, service_name: str) -> bool:
        """管理系统服务

        Args:
            action: 操作类型 (start/stop/restart/status)
            service_name: 服务名称

        Returns:
            操作是否成功
        """
        pass


class WindowsAdapter(PlatformAdapter):
    """Windows 平台适配器

    提供 Windows 特定的平台操作实现。
    """

    def get_platform_info(self) -> PlatformInfo:
        """获取 Windows 平台信息"""
        return PlatformInfo(
            os="windows",
            arch=platform.machine(),
            version=platform.version(),
            is_admin=self._check_admin(),
            python_version=platform.python_version(),
        )

    async def check_privileges(self) -> bool:
        """检查 Windows 管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
        except Exception:
            return False

    async def create_raw_socket(self, protocol: int) -> socket.socket:
        """创建 Windows 原始套接字

        Windows 原始套接字需要管理员权限。
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock

    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        """配置 Windows 防火墙

        使用 netsh 命令配置 Windows Defender 防火墙。
        """
        name = rule.get("name", "VPN Simulator")
        port = rule.get("port")
        protocol = rule.get("protocol", "TCP")
        action = rule.get("action", "allow")

        if not port:
            logger.error("firewall_rule_missing_port", rule=rule)
            return False

        cmd = (
            f'netsh advfirewall firewall add rule name="{name}" '
            f"dir=in action={action} protocol={protocol} localport={port}"
        )

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("firewall_rule_added", name=name, port=port)
                return True
            else:
                logger.error("firewall_rule_failed", name=name, error=result.stderr)
                return False
        except Exception as e:
            logger.error("firewall_command_error", error=str(e))
            return False

    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """获取 Windows 网络接口"""
        try:
            import psutil

            interfaces = []
            for name, addrs in psutil.net_if_addrs().items():
                interfaces.append({
                    "name": name,
                    "addresses": [addr.address for addr in addrs],
                })
            return interfaces
        except ImportError:
            logger.warning("psutil_not_installed")
            return []

    async def manage_service(self, action: str, service_name: str) -> bool:
        """管理 Windows 服务

        使用 net 命令管理服务。
        """
        cmd = f"net {action} {service_name}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error("service_manage_error", action=action, service=service_name, error=str(e))
            return False

    def _check_admin(self) -> bool:
        """内部检查管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]
        except Exception:
            return False


class MacOSAdapter(PlatformAdapter):
    """macOS 平台适配器

    提供 macOS 特定的平台操作实现。
    """

    def get_platform_info(self) -> PlatformInfo:
        """获取 macOS 平台信息"""
        return PlatformInfo(
            os="darwin",
            arch=platform.machine(),
            version=platform.mac_ver()[0],
            is_admin=self._check_root(),
            python_version=platform.python_version(),
        )

    async def check_privileges(self) -> bool:
        """检查 macOS root 权限"""
        return os.geteuid() == 0

    async def create_raw_socket(self, protocol: int) -> socket.socket:
        """创建 macOS 原始套接字"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock

    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        """配置 macOS 防火墙

        使用 pfctl 配置 macOS 包过滤防火墙。
        """
        pf_rule = rule.get("pf_rule")
        if not pf_rule:
            logger.error("firewall_rule_missing_pf_rule", rule=rule)
            return False

        cmd = f'echo "{pf_rule}" | sudo pfctl -f -'
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("firewall_rule_added")
                return True
            else:
                logger.error("firewall_rule_failed", error=result.stderr)
                return False
        except Exception as e:
            logger.error("firewall_command_error", error=str(e))
            return False

    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """获取 macOS 网络接口"""
        try:
            import psutil

            interfaces = []
            for name, addrs in psutil.net_if_addrs().items():
                interfaces.append({
                    "name": name,
                    "addresses": [addr.address for addr in addrs],
                })
            return interfaces
        except ImportError:
            logger.warning("psutil_not_installed")
            return []

    async def manage_service(self, action: str, service_name: str) -> bool:
        """管理 macOS 服务

        使用 launchctl 管理 launchd 服务。
        """
        if action == "start":
            cmd = f"launchctl load {service_name}"
        elif action == "stop":
            cmd = f"launchctl unload {service_name}"
        elif action == "status":
            cmd = f"launchctl list {service_name}"
        else:
            logger.error("unsupported_service_action", action=action)
            return False

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error("service_manage_error", action=action, service=service_name, error=str(e))
            return False

    def _check_root(self) -> bool:
        """内部检查 root 权限"""
        return os.geteuid() == 0


class LinuxAdapter(PlatformAdapter):
    """Linux 平台适配器

    提供 Linux 特定的平台操作实现。
    """

    def get_platform_info(self) -> PlatformInfo:
        """获取 Linux 平台信息"""
        return PlatformInfo(
            os="linux",
            arch=platform.machine(),
            version=platform.release(),
            is_admin=self._check_root(),
            python_version=platform.python_version(),
        )

    async def check_privileges(self) -> bool:
        """检查 Linux root 权限"""
        return os.geteuid() == 0

    async def create_raw_socket(self, protocol: int) -> socket.socket:
        """创建 Linux 原始套接字"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock

    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        """配置 Linux 防火墙

        使用 iptables 配置 Linux 防火墙规则。
        """
        action = rule.get("action", "-A")
        chain = rule.get("chain", "INPUT")
        port = rule.get("port")
        protocol = rule.get("protocol", "tcp")

        if not port:
            logger.error("firewall_rule_missing_port", rule=rule)
            return False

        cmd = f"iptables {action} {chain} -p {protocol} --dport {port} -j ACCEPT"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("firewall_rule_added", chain=chain, port=port)
                return True
            else:
                logger.error("firewall_rule_failed", error=result.stderr)
                return False
        except Exception as e:
            logger.error("firewall_command_error", error=str(e))
            return False

    async def get_network_interfaces(self) -> List[Dict[str, Any]]:
        """获取 Linux 网络接口"""
        try:
            import psutil

            interfaces = []
            for name, addrs in psutil.net_if_addrs().items():
                interfaces.append({
                    "name": name,
                    "addresses": [addr.address for addr in addrs],
                })
            return interfaces
        except ImportError:
            logger.warning("psutil_not_installed")
            return []

    async def manage_service(self, action: str, service_name: str) -> bool:
        """管理 Linux 服务

        使用 systemctl 管理 systemd 服务。
        """
        cmd = f"systemctl {action} {service_name}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error("service_manage_error", action=action, service=service_name, error=str(e))
            return False

    def _check_root(self) -> bool:
        """内部检查 root 权限"""
        return os.geteuid() == 0


def get_platform_adapter() -> PlatformAdapter:
    """获取当前平台的适配器工厂函数

    根据操作系统类型返回对应的平台适配器实例。

    Returns:
        平台适配器实例

    Raises:
        ValueError: 不支持的操作系统

    Example:
        >>> adapter = get_platform_adapter()
        >>> info = adapter.get_platform_info()
    """
    system = platform.system().lower()

    if system == "windows":
        adapter = WindowsAdapter()
    elif system == "darwin":
        adapter = MacOSAdapter()
    elif system == "linux":
        adapter = LinuxAdapter()
    else:
        raise ValueError(f"Unsupported platform: {system}")

    logger.info(
        "platform_adapter_created",
        os=system,
        arch=platform.machine(),
    )
    return adapter
