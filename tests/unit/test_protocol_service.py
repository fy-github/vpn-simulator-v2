"""Tests for ProtocolService - protocol management service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager
from vpn_simulator.core.events import EventBus
from vpn_simulator.plugins.registry import PluginType
from vpn_simulator.services.protocol import ProtocolService


@pytest.fixture
def mock_event_bus():
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_config_manager():
    cm = MagicMock(spec=ConfigManager)
    cm.config = MagicMock()
    cm.config.protocols = {
        "pptp": {"port": 1723},
        "l2tp": {"port": 1701},
    }
    return cm


@pytest.fixture
def mock_db_manager():
    dm = MagicMock(spec=DatabaseManager)
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    mock_session.add = MagicMock()
    dm.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    dm.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return dm


@pytest.fixture
def service(mock_event_bus, mock_config_manager, mock_db_manager) -> ProtocolService:
    return ProtocolService(
        event_bus=mock_event_bus,
        config_manager=mock_config_manager,
        db_manager=mock_db_manager,
    )


class TestProtocolServiceInit:
    def test_service_creation(self, service: ProtocolService):
        assert service is not None
        assert service._active_state_machines == {}


class TestListProtocols:
    @pytest.mark.asyncio
    async def test_list_protocols_empty(self, service: ProtocolService):
        protocols = await service.list_protocols()
        assert isinstance(protocols, list)


class TestGetProtocol:
    @pytest.mark.asyncio
    async def test_get_protocol_not_found(self, service: ProtocolService):
        result = await service.get_protocol("nonexistent")
        assert result is None


class TestStartProtocol:
    @pytest.mark.asyncio
    async def test_start_protocol_not_found(self, service: ProtocolService):
        with pytest.raises(ValueError, match="not found"):
            await service.start_protocol("nonexistent")

    @pytest.mark.asyncio
    async def test_start_protocol_emits_event(self, service: ProtocolService, mock_event_bus):
        with patch('vpn_simulator.services.protocol.PluginRegistry') as mock_registry:
            mock_plugin = MagicMock()
            mock_meta = MagicMock()
            mock_meta.plugin_type = PluginType.PROTOCOL
            mock_plugin.meta.return_value = mock_meta
            mock_registry.get.return_value = mock_plugin
            mock_registry.get_by_type.return_value = []
            
            result = await service.start_protocol("pptp", port=1723)
            assert result["protocol"] == "pptp"
            assert result["status"] == "started"
            assert mock_event_bus.emit.called


class TestStopProtocol:
    @pytest.mark.asyncio
    async def test_stop_protocol_not_active(self, service: ProtocolService):
        result = await service.stop_protocol("pptp")
        assert result["status"] == "not_active"


class TestGetProtocolState:
    @pytest.mark.asyncio
    async def test_get_protocol_state_not_active(self, service: ProtocolService):
        result = await service.get_protocol_state("pptp")
        assert result is None


class TestTriggerProtocolEvent:
    @pytest.mark.asyncio
    async def test_trigger_event_not_active(self, service: ProtocolService):
        with pytest.raises(ValueError, match="not active"):
            await service.trigger_protocol_event("pptp", "START")


class TestGetStateHistory:
    @pytest.mark.asyncio
    async def test_get_state_history_empty(self, service: ProtocolService):
        history = await service.get_state_history("pptp")
        assert isinstance(history, list)
        assert len(history) == 0


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_start_already_active(self, service: ProtocolService, mock_event_bus):
        with patch('vpn_simulator.services.protocol.PluginRegistry') as mock_registry:
            mock_plugin = MagicMock()
            mock_meta = MagicMock()
            mock_meta.plugin_type = PluginType.PROTOCOL
            mock_plugin.meta.return_value = mock_meta
            mock_registry.get.return_value = mock_plugin
            mock_registry.get_by_type.return_value = []
            
            await service.start_protocol("pptp", port=1723)
            service._active_state_machines["pptp"] = MagicMock()
            result = await service.start_protocol("pptp", port=1723)
            assert result["status"] == "already_active"

    @pytest.mark.asyncio
    async def test_list_protocols_returns_list(self, service: ProtocolService):
        result = await service.list_protocols()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_state_history_returns_list(self, service: ProtocolService):
        result = await service.get_state_history("pptp")
        assert isinstance(result, list)
