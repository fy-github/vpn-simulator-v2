"""Tests for ComparisonService - protocol comparison service."""

from __future__ import annotations

import pytest

from vpn_simulator.services.comparison import (
    ComparisonResult,
    ComparisonService,
    PhaseCategory,
    ProtocolStateData,
    StateInfo,
    TransitionInfo,
)


@pytest.fixture
def service() -> ComparisonService:
    return ComparisonService()


class TestComparisonServiceInit:
    def test_service_creation(self, service: ComparisonService):
        assert service is not None


class TestGetAvailableProtocols:
    def test_returns_list(self, service: ComparisonService):
        protocols = service.get_available_protocols()
        assert isinstance(protocols, list)
        assert len(protocols) > 0

    def test_protocol_structure(self, service: ComparisonService):
        protocols = service.get_available_protocols()
        proto = protocols[0]
        assert "name" in proto
        assert "description" in proto

    def test_contains_pptp(self, service: ComparisonService):
        protocols = service.get_available_protocols()
        names = [p["name"] for p in protocols]
        assert "pptp" in names


class TestCompare:
    @pytest.mark.asyncio
    async def test_compare_pptp_l2tp(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        assert isinstance(result, ComparisonResult)
        assert result.protocol1 is not None
        assert result.protocol2 is not None
        assert isinstance(result.common_phases, list)
        assert isinstance(result.different_phases, list)

    @pytest.mark.asyncio
    async def test_compare_same_protocol(self, service: ComparisonService):
        result = await service.compare("pptp", "pptp")
        assert len(result.common_phases) > 0
        assert len(result.different_phases) == 0

    @pytest.mark.asyncio
    async def test_compare_invalid_protocol1(self, service: ComparisonService):
        with pytest.raises(ValueError, match="not found"):
            await service.compare("invalid", "pptp")

    @pytest.mark.asyncio
    async def test_compare_invalid_protocol2(self, service: ComparisonService):
        with pytest.raises(ValueError, match="not found"):
            await service.compare("pptp", "invalid")

    @pytest.mark.asyncio
    async def test_compare_result_structure(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        assert hasattr(result, "protocol1")
        assert hasattr(result, "protocol2")
        assert hasattr(result, "common_phases")
        assert hasattr(result, "different_phases")


class TestProtocolStateData:
    @pytest.mark.asyncio
    async def test_protocol_data_structure(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        data = result.protocol1
        assert isinstance(data, ProtocolStateData)
        assert data.name is not None
        assert isinstance(data.states, list)
        assert isinstance(data.transitions, list)

    @pytest.mark.asyncio
    async def test_state_info_structure(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        state = result.protocol1.states[0]
        assert isinstance(state, StateInfo)
        assert state.name is not None
        assert isinstance(state.phase, PhaseCategory)

    @pytest.mark.asyncio
    async def test_transition_info_structure(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        if result.protocol1.transitions:
            t = result.protocol1.transitions[0]
            assert isinstance(t, TransitionInfo)
            assert t.from_state is not None
            assert t.to_state is not None


class TestPhaseCategory:
    def test_phase_values(self):
        assert PhaseCategory.CONNECTION_INIT.value == "connection_init"
        assert PhaseCategory.CONTROL_CHANNEL.value == "control_channel"
        assert PhaseCategory.KEY_EXCHANGE.value == "key_exchange"
        assert PhaseCategory.AUTHENTICATION.value == "authentication"
        assert PhaseCategory.TUNNEL_SETUP.value == "tunnel_setup"
        assert PhaseCategory.CONNECTED.value == "connected"
        assert PhaseCategory.ERROR.value == "error"


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_comparisons(self, service: ComparisonService):
        for p1, p2 in [("pptp", "l2tp"), ("openvpn", "ipsec"), ("ikev2", "wireguard")]:
            result = await service.compare(p1, p2)
            assert result.protocol1 is not None
            assert result.protocol2 is not None

    @pytest.mark.asyncio
    async def test_common_phases_not_empty(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        assert len(result.common_phases) > 0

    @pytest.mark.asyncio
    async def test_phase_categories_in_result(self, service: ComparisonService):
        result = await service.compare("pptp", "l2tp")
        all_phases = result.common_phases + result.different_phases
        assert all(isinstance(p, PhaseCategory) for p in all_phases)
