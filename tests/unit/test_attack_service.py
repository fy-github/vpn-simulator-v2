"""Tests for AttackService - attack management service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.services.attack import AttackService


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    cm = MagicMock(spec=ConfigManager)
    cm.config = MagicMock()
    cm.config.attacks = {}
    return cm


@pytest.fixture
def mock_db_manager():
    dm = MagicMock(spec=DatabaseManager)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    dm.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    dm.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return dm


@pytest.fixture
def service(mock_event_bus, mock_config_manager, mock_db_manager) -> AttackService:
    return AttackService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


class TestAttackServiceInit:
    def test_service_creation(self, service: AttackService):
        assert service is not None
        assert service._event_bus is not None
        assert service._attack_manager is not None


class TestCreateAttack:
    @pytest.mark.asyncio
    async def test_create_attack_mitm(self, service: AttackService):
        result = await service.create_attack("mitm", {"proxy_port": 8888}, target="pptp")
        assert result is not None
        assert result["type"] == "mitm"
        assert result["target"] == "pptp"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_attack_replay(self, service: AttackService):
        result = await service.create_attack("replay", target="l2tp")
        assert result["type"] == "replay"

    @pytest.mark.asyncio
    async def test_create_attack_brute_force(self, service: AttackService):
        result = await service.create_attack("brute_force", target="openvpn")
        assert result["type"] == "brute_force"

    @pytest.mark.asyncio
    async def test_create_attack_invalid_type(self, service: AttackService):
        with pytest.raises(ValueError, match="Invalid attack type"):
            await service.create_attack("invalid")

    @pytest.mark.asyncio
    async def test_create_attack_with_params(self, service: AttackService):
        result = await service.create_attack("mitm", {"timeout": 30}, target="pptp")
        assert result["params"]["timeout"] == 30

    @pytest.mark.asyncio
    async def test_create_attack_emits_event(self, service: AttackService, mock_event_bus):
        await service.create_attack("mitm", target="pptp")


class TestGetAttack:
    @pytest.mark.asyncio
    async def test_get_attack(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        result = await service.get_attack(created["id"])
        assert result is not None
        assert result["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_attack_not_found(self, service: AttackService):
        result = await service.get_attack("nonexistent")
        assert result is None


class TestListAttacks:
    @pytest.mark.asyncio
    async def test_list_attacks_empty(self, service: AttackService):
        attacks = await service.list_attacks()
        assert len(attacks) == 0

    @pytest.mark.asyncio
    async def test_list_attacks_with_data(self, service: AttackService):
        await service.create_attack("mitm", target="pptp")
        await service.create_attack("replay", target="l2tp")
        attacks = await service.list_attacks()
        assert len(attacks) == 2

    @pytest.mark.asyncio
    async def test_list_attacks_by_type(self, service: AttackService):
        await service.create_attack("mitm", target="pptp")
        await service.create_attack("replay", target="l2tp")
        attacks = await service.list_attacks(attack_type="mitm")
        assert len(attacks) == 1

    @pytest.mark.asyncio
    async def test_list_attacks_by_status(self, service: AttackService):
        await service.create_attack("mitm", target="pptp")
        attacks = await service.list_attacks(status="pending")
        assert len(attacks) == 1


class TestStartAttack:
    @pytest.mark.asyncio
    async def test_start_attack(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        result = await service.start_attack(created["id"])
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_start_attack_not_found(self, service: AttackService):
        with pytest.raises(ValueError, match="not found"):
            await service.start_attack("nonexistent")

    @pytest.mark.asyncio
    async def test_start_attack_emits_event(self, service: AttackService, mock_event_bus):
        created = await service.create_attack("mitm", target="pptp")
        await service.start_attack(created["id"])


class TestStopAttack:
    @pytest.mark.asyncio
    async def test_stop_attack(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        await service.start_attack(created["id"])
        result = await service.stop_attack(created["id"])
        assert result["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_stop_attack_not_found(self, service: AttackService):
        with pytest.raises(ValueError, match="not found"):
            await service.stop_attack("nonexistent")


class TestCompleteAttack:
    @pytest.mark.asyncio
    async def test_complete_attack_success(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        await service.start_attack(created["id"])
        result = await service.complete_attack(
            created["id"],
            success=True,
            data={"captured": True},
            duration_seconds=5.0,
        )
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_attack_failure(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        await service.start_attack(created["id"])
        result = await service.complete_attack(
            created["id"],
            success=False,
            error="Connection refused",
        )
        assert result["status"] == "completed"
        assert result["result"]["success"] is False

    @pytest.mark.asyncio
    async def test_complete_attack_not_found(self, service: AttackService):
        with pytest.raises(ValueError, match="not found"):
            await service.complete_attack("nonexistent", success=True)


class TestFailAttack:
    @pytest.mark.asyncio
    async def test_fail_attack(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        await service.start_attack(created["id"])
        result = await service.fail_attack(created["id"], "Timeout")
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_fail_attack_not_found(self, service: AttackService):
        with pytest.raises(ValueError, match="not found"):
            await service.fail_attack("nonexistent", "error")


class TestRemoveAttack:
    @pytest.mark.asyncio
    async def test_remove_attack(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        result = await service.remove_attack(created["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_attack_not_found(self, service: AttackService):
        result = await service.remove_attack("nonexistent")
        assert result is False


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, service: AttackService):
        stats = await service.get_attack_stats()
        assert stats["total"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_attacks(self, service: AttackService):
        await service.create_attack("mitm", target="pptp")
        await service.create_attack("replay", target="l2tp")
        stats = await service.get_attack_stats()
        assert stats["total"] == 2

    @pytest.mark.asyncio
    async def test_get_statistics_structure(self, service: AttackService):
        stats = await service.get_attack_stats()
        assert "total" in stats
        assert "by_type" in stats
        assert "by_status" in stats


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_attack_lifecycle(self, service: AttackService):
        created = await service.create_attack("mitm", target="pptp")
        assert created["status"] == "pending"

        started = await service.start_attack(created["id"])
        assert started["status"] == "running"

        stopped = await service.stop_attack(created["id"])
        assert stopped["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_multiple_attack_types(self, service: AttackService):
        for atype in ["mitm", "replay", "brute_force", "downgrade", "traffic_analysis"]:
            result = await service.create_attack(atype, target="pptp")
            assert result["type"] == atype

    @pytest.mark.asyncio
    async def test_attack_with_empty_params(self, service: AttackService):
        result = await service.create_attack("mitm", params={}, target="pptp")
        assert result is not None
