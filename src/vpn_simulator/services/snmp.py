"""SNMP 设备模拟服务（F4）。

模拟一组 SNMP v2c/v3 设备（12 种设备类型），提供 MIB-II system/interfaces
子树的 OID 查询（GET）与遍历（WALK）。OID 语法校验复用 pysnmp 的
`ObjectIdentifier`（ASN.1 对象标识符）。

Example:
    >>> service = SnmpService()
    >>> devices = service.list_devices()
    >>> value = service.get_oid(devices[0]["id"], "1.3.6.1.2.1.1.5.0")
"""

from __future__ import annotations

from typing import Any

import structlog
from pysnmp.proto.rfc1902 import ObjectIdentifier  # type: ignore[import-untyped]

from vpn_simulator.domain.snmp import DEVICE_TYPES, SnmpDevice

logger = structlog.get_logger(__name__)

# 基础 OID 与描述（MIB-II 子集）
_BASE_OIDS: list[dict[str, str]] = [
    {"oid": "1.3.6.1.2.1.1.1.0", "name": "sysDescr", "description": "系统描述"},
    {"oid": "1.3.6.1.2.1.1.3.0", "name": "sysUpTime", "description": "系统运行时间"},
    {"oid": "1.3.6.1.2.1.1.4.0", "name": "sysContact", "description": "系统联系人"},
    {"oid": "1.3.6.1.2.1.1.5.0", "name": "sysName", "description": "系统名称"},
    {"oid": "1.3.6.1.2.1.1.6.0", "name": "sysLocation", "description": "系统位置"},
    {"oid": "1.3.6.1.2.1.2.2.1.2", "name": "ifDescr", "description": "接口描述"},
    {"oid": "1.3.6.1.2.1.2.2.1.10", "name": "ifInOctets", "description": "接口入站字节数"},
    {"oid": "1.3.6.1.2.1.2.2.1.16", "name": "ifOutOctets", "description": "接口出站字节数"},
]


class SnmpService:
    """SNMP 设备模拟服务。"""

    def __init__(self, device_count: int = 24) -> None:
        self._devices: dict[str, SnmpDevice] = {
            d.id: d for d in self._generate_devices(device_count)
        }

    # ------------------------------------------------------------------
    # 设备
    # ------------------------------------------------------------------
    def list_devices(self) -> list[dict[str, Any]]:
        """列出所有模拟设备。"""
        return [d.to_dict() for d in self._devices.values()]

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """获取指定设备。"""
        device = self._devices.get(device_id)
        return device.to_dict() if device else None

    def list_oids(self) -> list[dict[str, str]]:
        """列出支持的 MIB 基础 OID。"""
        return list(_BASE_OIDS)

    # ------------------------------------------------------------------
    # OID 查询 / 遍历
    # ------------------------------------------------------------------
    def get_oid(self, device_id: str, oid: str, version: str = "2c") -> dict[str, Any]:
        """模拟一次 SNMP GET。

        Raises:
            ValueError: 设备不存在、OID 非法、设备不支持该版本、OID 无实例。
        """
        device = self._require_device(device_id, version)
        oid_tuple = self._parse_oid(oid)
        mib = self._build_mib(device)

        if oid_tuple not in mib:
            raise ValueError(f"no such instance: {oid}")
        snmp_type, value = mib[oid_tuple]
        return {
            "oid": oid,
            "name": self._oid_name(oid_tuple),
            "type": snmp_type,
            "value": value,
            "version": version,
        }

    def walk_oid(
        self, device_id: str, oid_prefix: str, version: str = "2c"
    ) -> list[dict[str, Any]]:
        """模拟一次 SNMP WALK（遍历子树）。

        返回以 `oid_prefix` 为前缀的所有 OID，按字典序升序排列。

        Raises:
            ValueError: 设备不存在、OID 非法、设备不支持该版本。
        """
        device = self._require_device(device_id, version)
        prefix = self._parse_oid(oid_prefix)
        mib = self._build_mib(device)

        result = []
        for oid_tuple in sorted(mib):
            if oid_tuple[: len(prefix)] == prefix:
                snmp_type, value = mib[oid_tuple]
                oid_str = ".".join(str(x) for x in oid_tuple)
                result.append(
                    {
                        "oid": oid_str,
                        "name": self._oid_name(oid_tuple),
                        "type": snmp_type,
                        "value": value,
                        "version": version,
                    }
                )
        return result

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _require_device(self, device_id: str, version: str) -> SnmpDevice:
        device = self._devices.get(device_id)
        if device is None:
            raise ValueError(f"device '{device_id}' not found")
        if version not in ("2c", "3"):
            raise ValueError(f"invalid SNMP version '{version}' (valid: 2c, 3)")
        if not device.supports(version):
            raise ValueError(f"device '{device.name}' does not support SNMP v{version}")
        return device

    @staticmethod
    def _parse_oid(oid: str) -> tuple[int, ...]:
        """用 pysnmp 校验并解析 OID 字符串为整数元组。"""
        try:
            return tuple(int(x) for x in ObjectIdentifier(oid).asTuple())
        except Exception as e:
            raise ValueError(f"invalid OID '{oid}': {e}") from e

    @staticmethod
    def _oid_name(oid_tuple: tuple[int, ...]) -> str:
        """尝试把 OID 映射到已知的 MIB 名称。"""
        for entry in _BASE_OIDS:
            base = tuple(int(x) for x in entry["oid"].split("."))
            if oid_tuple[: len(base)] == base:
                return entry["name"]
        return "unknown"

    def _build_mib(self, device: SnmpDevice) -> dict[tuple[int, ...], tuple[str, Any]]:
        """构造设备的 MIB-II system + interfaces 子树。"""
        mib: dict[tuple[int, ...], tuple[str, Any]] = {
            (1, 3, 6, 1, 2, 1, 1, 1, 0): (
                "OctetString",
                f"VPN Simulator {device.device_type} ({device.name})",
            ),
            (1, 3, 6, 1, 2, 1, 1, 3, 0): ("TimeTicks", device.uptime_seconds),
            (1, 3, 6, 1, 2, 1, 1, 4, 0): ("OctetString", device.contact),
            (1, 3, 6, 1, 2, 1, 1, 5, 0): ("OctetString", device.name),
            (1, 3, 6, 1, 2, 1, 1, 6, 0): ("OctetString", device.location),
        }
        for idx, ifname in enumerate(device.interfaces, start=1):
            base = (1, 3, 6, 1, 2, 1, 2, 2, 1)
            mib[base + (2, idx)] = ("OctetString", ifname)
            mib[base + (10, idx)] = ("Counter32", device.uptime_seconds * 100 + idx)
            mib[base + (16, idx)] = ("Counter32", device.uptime_seconds * 200 + idx)
        return mib

    @staticmethod
    def _generate_devices(count: int) -> list[SnmpDevice]:
        """生成 `count` 台设备（类型循环，v2c/v3 版本按序号轮换）。"""
        devices: list[SnmpDevice] = []
        for i in range(count):
            device_type = DEVICE_TYPES[i % len(DEVICE_TYPES)]
            if i % 3 == 0:
                versions = ["2c"]
            elif i % 3 == 1:
                versions = ["3"]
            else:
                versions = ["2c", "3"]
            devices.append(
                SnmpDevice(
                    name=f"{device_type}-{i + 1}",
                    device_type=device_type,
                    ip=f"10.0.{(i // 254) + 1}.{(i % 254) + 1}",
                    community=f"public-{i % 5}",
                    usm_user=f"admin-{i % 5}",
                    versions=versions,
                    uptime_seconds=3600 * (i + 1),
                    interfaces=(
                        ["eth0", "eth1"]
                        if device_type in ("router", "switch", "firewall", "load_balancer")
                        else ["eth0"]
                    ),
                )
            )
        return devices
