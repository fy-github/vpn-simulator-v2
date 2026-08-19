"""Tests for SnmpService - SNMP device simulation (F4)."""

from __future__ import annotations

import pytest
from vpn_simulator.domain.snmp import DEVICE_TYPES
from vpn_simulator.services.snmp import SnmpService

SYS_NAME = "1.3.6.1.2.1.1.5.0"


def test_list_devices_covers_10_plus_types():
    service = SnmpService()
    devices = service.list_devices()
    assert len(devices) == 24
    types = {d["device_type"] for d in devices}
    assert set(DEVICE_TYPES) <= types  # 12 种设备类型全覆盖


def test_get_device():
    service = SnmpService()
    device = service.list_devices()[0]
    fetched = service.get_device(device["id"])
    assert fetched == device
    assert service.get_device("missing") is None


def test_list_oids():
    service = SnmpService()
    oids = service.list_oids()
    assert len(oids) >= 8
    assert any(o["name"] == "sysName" for o in oids)


def test_get_oid_sysname():
    service = SnmpService()
    device = service.list_devices()[2]  # 支持 v2c 与 v3
    result = service.get_oid(device["id"], SYS_NAME)
    assert result["oid"] == SYS_NAME
    assert result["value"] == device["name"]
    assert result["type"] == "OctetString"
    assert result["version"] == "2c"


def test_get_oid_v3():
    service = SnmpService()
    device = service.list_devices()[2]
    result = service.get_oid(device["id"], SYS_NAME, version="3")
    assert result["version"] == "3"


def test_get_oid_invalid_oid_raises():
    service = SnmpService()
    device = service.list_devices()[0]
    with pytest.raises(ValueError, match="invalid OID"):
        service.get_oid(device["id"], "not-an-oid")


def test_get_oid_unsupported_version_raises():
    service = SnmpService()
    device = service.list_devices()[0]  # 仅 v2c
    with pytest.raises(ValueError, match="does not support"):
        service.get_oid(device["id"], SYS_NAME, version="3")


def test_get_oid_no_such_instance_raises():
    service = SnmpService()
    device = service.list_devices()[0]
    with pytest.raises(ValueError, match="no such instance"):
        service.get_oid(device["id"], "1.3.6.1.2.1.1.9.0")


def test_walk_system_subtree():
    service = SnmpService()
    device = service.list_devices()[2]
    entries = service.walk_oid(device["id"], "1.3.6.1.2.1.1")
    names = {e["name"] for e in entries}
    assert {"sysDescr", "sysUpTime", "sysName", "sysContact", "sysLocation"} <= names


def test_walk_interfaces_subtree():
    service = SnmpService()
    device = service.list_devices()[0]  # router，2 个接口
    entries = service.walk_oid(device["id"], "1.3.6.1.2.1.2.2.1")
    names = {e["name"] for e in entries}
    assert "ifDescr" in names
    assert "ifInOctets" in names
    assert "ifOutOctets" in names
    # 2 个接口 → 至少 6 条（descr/in/out × 2）
    assert len(entries) >= 6
