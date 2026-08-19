"""SNMP 设备模拟模型（F4）。

表示一台被模拟的 SNMP 设备（支持 v2c 社区串与 v3 USM 用户），及其
MIB-II 子树（system + interfaces）的 OID 值。查询与遍历由 `SnmpService`
基于这些数据模拟。

Example:
    >>> device = SnmpDevice(name="core-router-1", device_type="router", ip="10.0.0.1")
    >>> device.to_dict()["device_type"]
    'router'
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 支持的设备类型（≥10）
DEVICE_TYPES: list[str] = [
    "router",
    "switch",
    "firewall",
    "server",
    "load_balancer",
    "access_point",
    "printer",
    "ups",
    "iot_gateway",
    "storage",
    "camera",
    "sensor",
]


class SnmpVersion(str, Enum):
    """SNMP 协议版本。"""

    V2C = "2c"
    V3 = "3"


@dataclass
class SnmpDevice:
    """一台被模拟的 SNMP 设备。

    Attributes:
        id: 设备唯一标识。
        name: 设备名（sysName）。
        device_type: 设备类型（12 种之一）。
        ip: 管理 IP。
        community: v2c 社区串。
        usm_user: v3 USM 用户名。
        auth_protocol: v3 认证协议（如 SHA/MD5）。
        priv_protocol: v3 加密协议（如 AES/DES）。
        versions: 支持的 SNMP 版本（["2c"] / ["3"] / ["2c", "3"]）。
        location: 设备位置（sysLocation）。
        contact: 设备联系人（sysContact）。
        uptime_seconds: 已运行秒数（sysUpTime）。
        interfaces: 接口名列表（ifDescr）。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    device_type: str = "router"
    ip: str = "127.0.0.1"
    community: str = "public"
    usm_user: str = "admin"
    auth_protocol: str = "SHA"
    priv_protocol: str = "AES"
    versions: list[str] = field(default_factory=lambda: ["2c", "3"])
    location: str = "Simulated"
    contact: str = "admin@vpn-simulator.local"
    uptime_seconds: int = 0
    interfaces: list[str] = field(default_factory=lambda: ["eth0"])

    def supports(self, version: str) -> bool:
        """是否支持指定 SNMP 版本。"""
        return version in self.versions

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "ip": self.ip,
            "community": self.community,
            "usm_user": self.usm_user,
            "auth_protocol": self.auth_protocol,
            "priv_protocol": self.priv_protocol,
            "versions": self.versions,
            "location": self.location,
            "contact": self.contact,
            "uptime_seconds": self.uptime_seconds,
            "interfaces": self.interfaces,
        }
