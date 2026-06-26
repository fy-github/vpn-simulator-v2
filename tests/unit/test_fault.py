"""Unit tests for the fault model module.

Tests cover:
- FaultType enum values
- FaultParams data class
- FaultInfo creation and serialization
- Fault activation/deactivation
- FaultManager CRUD operations
"""

from __future__ import annotations

import pytest

from vpn_simulator.domain.fault import (
    FaultInfo,
    FaultManager,
    FaultParams,
    FaultType,
)


class TestFaultType:
    """Tests for the FaultType enum."""

    def test_fault_type_values(self):
        """Verify all fault type values."""
        assert FaultType.LATENCY.value == "latency"
        assert FaultType.PACKET_LOSS.value == "packet_loss"
        assert FaultType.BANDWIDTH.value == "bandwidth"
        assert FaultType.REORDER.value == "reorder"
        assert FaultType.DUPLICATE.value == "duplicate"
        assert FaultType.CORRUPT.value == "corrupt"

    def test_fault_type_count(self):
        """Verify the number of fault types."""
        assert len(FaultType) == 6


class TestFaultParams:
    """Tests for the FaultParams data class."""

    def test_default_values(self):
        """Verify FaultParams has expected defaults."""
        params = FaultParams()
        assert params.delay_ms == 0
        assert params.jitter_ms == 0
        assert params.loss_rate == 0.0
        assert params.bandwidth_kbps == 0
        assert params.reorder_probability == 0.0
        assert params.duplicate_count == 0
        assert params.corrupt_probability == 0.0

    def test_custom_values(self):
        """Verify FaultParams accepts custom values."""
        params = FaultParams(
            delay_ms=100,
            jitter_ms=20,
            loss_rate=0.1,
            bandwidth_kbps=1000,
        )
        assert params.delay_ms == 100
        assert params.jitter_ms == 20
        assert params.loss_rate == 0.1
        assert params.bandwidth_kbps == 1000

    def test_to_dict(self, fault_params: FaultParams):
        """Verify to_dict returns correct dictionary."""
        data = fault_params.to_dict()
        assert data["delay_ms"] == 100
        assert data["jitter_ms"] == 20
        assert data["loss_rate"] == 0.1
        assert data["bandwidth_kbps"] == 1000
        assert data["reorder_probability"] == 0.0
        assert data["duplicate_count"] == 0
        assert data["corrupt_probability"] == 0.0


class TestFaultInfo:
    """Tests for the FaultInfo data class."""

    def test_creation_with_defaults(self):
        """Verify FaultInfo is created with expected defaults."""
        fault = FaultInfo()
        assert fault.id is not None
        assert len(fault.id) == 36  # UUID
        assert fault.fault_type == FaultType.LATENCY
        assert fault.params == {}
        assert fault.target == ""
        assert fault.active is True
        assert fault.created_at is not None
        assert fault.updated_at is None

    def test_creation_with_custom_values(self, sample_fault: FaultInfo):
        """Verify FaultInfo accepts custom values."""
        assert sample_fault.id == "test-fault-001"
        assert sample_fault.fault_type == FaultType.LATENCY
        assert sample_fault.params == {"delay_ms": 100, "jitter_ms": 20}
        assert sample_fault.target == "pptp"
        assert sample_fault.active is True

    def test_to_dict(self, sample_fault: FaultInfo):
        """Verify to_dict returns correct dictionary."""
        data = sample_fault.to_dict()
        assert data["id"] == "test-fault-001"
        assert data["type"] == "latency"
        assert data["params"] == {"delay_ms": 100, "jitter_ms": 20}
        assert data["target"] == "pptp"
        assert data["active"] is True
        assert "created_at" in data

    def test_activate(self, sample_fault: FaultInfo):
        """Verify fault activation."""
        sample_fault.active = False
        sample_fault.activate()
        assert sample_fault.active is True
        assert sample_fault.updated_at is not None

    def test_deactivate(self, sample_fault: FaultInfo):
        """Verify fault deactivation."""
        sample_fault.deactivate()
        assert sample_fault.active is False
        assert sample_fault.updated_at is not None


class TestFaultManager:
    """Tests for the FaultManager class."""

    @pytest.mark.asyncio
    async def test_create_fault(self, fault_manager: FaultManager):
        """Verify fault creation."""
        fault = await fault_manager.create_fault(
            FaultType.LATENCY,
            params={"delay_ms": 100},
            target="pptp",
        )
        assert fault.fault_type == FaultType.LATENCY
        assert fault.params == {"delay_ms": 100}
        assert fault.target == "pptp"
        assert fault.active is True

    @pytest.mark.asyncio
    async def test_create_fault_defaults(self, fault_manager: FaultManager):
        """Verify fault creation with default parameters."""
        fault = await fault_manager.create_fault(FaultType.PACKET_LOSS)
        assert fault.params == {}
        assert fault.target == ""

    @pytest.mark.asyncio
    async def test_get_fault(self, fault_manager: FaultManager):
        """Verify fault retrieval by ID."""
        fault = await fault_manager.create_fault(FaultType.LATENCY)
        retrieved = await fault_manager.get_fault(fault.id)
        assert retrieved is fault

    @pytest.mark.asyncio
    async def test_get_nonexistent_fault(self, fault_manager: FaultManager):
        """Verify None is returned for nonexistent fault."""
        retrieved = await fault_manager.get_fault("nonexistent-id")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_faults_empty(self, fault_manager: FaultManager):
        """Verify empty fault list."""
        faults = await fault_manager.list_faults()
        assert faults == []

    @pytest.mark.asyncio
    async def test_list_faults(self, fault_manager: FaultManager):
        """Verify listing all faults."""
        await fault_manager.create_fault(FaultType.LATENCY)
        await fault_manager.create_fault(FaultType.PACKET_LOSS)
        await fault_manager.create_fault(FaultType.BANDWIDTH)

        faults = await fault_manager.list_faults()
        assert len(faults) == 3

    @pytest.mark.asyncio
    async def test_list_faults_by_type(self, fault_manager: FaultManager):
        """Verify filtering faults by type."""
        await fault_manager.create_fault(FaultType.LATENCY)
        await fault_manager.create_fault(FaultType.LATENCY)
        await fault_manager.create_fault(FaultType.PACKET_LOSS)

        latency_faults = await fault_manager.list_faults(fault_type=FaultType.LATENCY)
        assert len(latency_faults) == 2
        assert all(f.fault_type == FaultType.LATENCY for f in latency_faults)

    @pytest.mark.asyncio
    async def test_list_faults_active_only(self, fault_manager: FaultManager):
        """Verify filtering active faults only."""
        fault1 = await fault_manager.create_fault(FaultType.LATENCY)
        fault2 = await fault_manager.create_fault(FaultType.PACKET_LOSS)
        await fault_manager.deactivate_fault(fault2.id)

        active_faults = await fault_manager.list_faults(active_only=True)
        assert len(active_faults) == 1
        assert active_faults[0].id == fault1.id

    @pytest.mark.asyncio
    async def test_remove_fault(self, fault_manager: FaultManager):
        """Verify fault removal."""
        fault = await fault_manager.create_fault(FaultType.LATENCY)
        result = await fault_manager.remove_fault(fault.id)
        assert result is True

        retrieved = await fault_manager.get_fault(fault.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_fault(self, fault_manager: FaultManager):
        """Verify removing nonexistent fault returns False."""
        result = await fault_manager.remove_fault("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_activate_fault(self, fault_manager: FaultManager):
        """Verify fault activation."""
        fault = await fault_manager.create_fault(FaultType.LATENCY)
        await fault_manager.deactivate_fault(fault.id)
        assert fault.active is False

        activated = await fault_manager.activate_fault(fault.id)
        assert activated is not None
        assert activated.active is True

    @pytest.mark.asyncio
    async def test_activate_nonexistent_fault(self, fault_manager: FaultManager):
        """Verify activating nonexistent fault returns None."""
        result = await fault_manager.activate_fault("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_fault(self, fault_manager: FaultManager):
        """Verify fault deactivation."""
        fault = await fault_manager.create_fault(FaultType.LATENCY)
        deactivated = await fault_manager.deactivate_fault(fault.id)
        assert deactivated is not None
        assert deactivated.active is False

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_fault(self, fault_manager: FaultManager):
        """Verify deactivating nonexistent fault returns None."""
        result = await fault_manager.deactivate_fault("nonexistent-id")
        assert result is None
