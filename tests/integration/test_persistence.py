"""Tests for startup state persistence (restore from DB).

Verifies that protocol/connection/fault/attack state survives an
application restart by hydrating domain state from the SQLite database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager, ProtocolRecord
from vpn_simulator.core.events import EventBus
from vpn_simulator.plugins.registry import PluginMeta, PluginType
from vpn_simulator.services.attack import AttackService
from vpn_simulator.services.connection import ConnectionService
from vpn_simulator.services.fault import FaultService
from vpn_simulator.services.protocol import ProtocolService


@pytest_asyncio.fixture
async def db_manager(tmp_path):
    db_path = tmp_path / "persist.db"
    manager = DatabaseManager(database_url=f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    yield manager
    await manager.close()


class TestConnectionPersistence:
    @pytest.mark.asyncio
    async def test_restore_connections(self, db_manager: DatabaseManager):
        svc = ConnectionService(EventBus(), ConfigManager(), db_manager)
        created = await svc.create_connection("pptp", remote_address="10.0.0.9")
        conn_id = created["id"]

        # 模拟重启：新服务实例从同一数据库恢复
        svc2 = ConnectionService(EventBus(), ConfigManager(), db_manager)
        await svc2.restore_connections()

        restored = await svc2.get_connection(conn_id)
        assert restored is not None
        assert restored["protocol"] == "pptp"
        assert restored["remote_address"] == "10.0.0.9"
        assert restored["state"] == "connecting"


class TestFaultPersistence:
    @pytest.mark.asyncio
    async def test_restore_faults(self, db_manager: DatabaseManager):
        svc = FaultService(EventBus(), ConfigManager(), db_manager)
        created = await svc.create_fault("latency", {"delay_ms": 50}, target="pptp")
        await svc.deactivate_fault(created["id"])

        svc2 = FaultService(EventBus(), ConfigManager(), db_manager)
        await svc2.restore_faults()

        restored = await svc2.get_fault(created["id"])
        assert restored is not None
        assert restored["type"] == "latency"
        assert restored["params"] == {"delay_ms": 50}
        assert restored["active"] is False


class TestAttackPersistence:
    @pytest.mark.asyncio
    async def test_restore_attacks(self, db_manager: DatabaseManager):
        svc = AttackService(EventBus(), ConfigManager(), db_manager)
        created = await svc.create_attack("mitm", {"port": 8888}, target="pptp")

        svc2 = AttackService(EventBus(), ConfigManager(), db_manager)
        await svc2.restore_attacks()

        restored = await svc2.get_attack(created["id"])
        assert restored is not None
        assert restored["type"] == "mitm"
        assert restored["status"] == "pending"
        assert restored["target"] == "pptp"


class TestProtocolPersistence:
    @pytest.mark.asyncio
    async def test_restore_protocols(self, db_manager: DatabaseManager):
        fake_state_machine = MagicMock()
        fake_plugin = MagicMock()
        fake_plugin.meta.return_value = PluginMeta(
            name="pptp",
            version="1.0.0",
            author="test",
            description="PPTP test plugin",
            plugin_type=PluginType.PROTOCOL,
        )
        fake_plugin.state_machine = fake_state_machine

        svc = ProtocolService(EventBus(), ConfigManager(), db_manager)
        with patch("vpn_simulator.services.protocol.PluginRegistry") as reg:
            reg.get.return_value = fake_plugin
            await svc.start_protocol("pptp", port=1723)

        # 验证已持久化到数据库
        async with db_manager.session() as session:
            record = await session.get(ProtocolRecord, "pptp")
            assert record is not None
            assert record.state == "running"
            assert record.port == 1723

        # 模拟重启：新服务实例从同一数据库恢复
        svc2 = ProtocolService(EventBus(), ConfigManager(), db_manager)
        with patch("vpn_simulator.services.protocol.PluginRegistry") as reg:
            reg.get.return_value = fake_plugin
            await svc2.restore_protocols()

        assert "pptp" in svc2._active_state_machines

    @pytest.mark.asyncio
    async def test_stop_protocol_clears_record(self, db_manager: DatabaseManager):
        fake_state_machine = MagicMock()
        fake_plugin = MagicMock()
        fake_plugin.meta.return_value = PluginMeta(
            name="pptp",
            version="1.0.0",
            author="test",
            description="PPTP test plugin",
            plugin_type=PluginType.PROTOCOL,
        )
        fake_plugin.state_machine = fake_state_machine

        svc = ProtocolService(EventBus(), ConfigManager(), db_manager)
        with patch("vpn_simulator.services.protocol.PluginRegistry") as reg:
            reg.get.return_value = fake_plugin
            await svc.start_protocol("pptp", port=1723)
            await svc.stop_protocol("pptp")

        async with db_manager.session() as session:
            record = await session.get(ProtocolRecord, "pptp")
            assert record is None
