"""Unit tests for ImpairmentEngine's real-packet impairment decisions (P2)."""

from __future__ import annotations

import pytest
from vpn_simulator.core.impairment_engine import ImpairmentEngine, OutboundDecision
from vpn_simulator.core.packetio import UdpSocket


class TestOutboundDecision:
    """F1/P2 — impairment decision model."""

    @pytest.mark.asyncio
    async def test_no_impairment(self) -> None:
        engine = ImpairmentEngine()
        decision = await engine.apply_outbound(b"ping")
        assert decision == OutboundDecision()
        assert decision.drop is False
        assert decision.data is None
        assert decision.delay_ms == 0.0
        assert decision.duplicate is False
        assert decision.reorder is False

    @pytest.mark.asyncio
    async def test_loss_drops(self) -> None:
        engine = ImpairmentEngine(lambda: {"loss_rate": 1.0})
        decision = await engine.apply_outbound(b"ping")
        assert decision.drop is True

    @pytest.mark.asyncio
    async def test_corrupt_flips_bytes(self) -> None:
        engine = ImpairmentEngine(lambda: {"corrupt_probability": 1.0, "corrupt_bytes": 2})
        original = b"hello world"
        decision = await engine.apply_outbound(original)
        assert decision.data is not None
        assert decision.data != original
        assert len(decision.data) == len(original)

    @pytest.mark.asyncio
    async def test_duplicate(self) -> None:
        engine = ImpairmentEngine(lambda: {"duplicate_probability": 1.0})
        decision = await engine.apply_outbound(b"ping")
        assert decision.duplicate is True

    @pytest.mark.asyncio
    async def test_reorder(self) -> None:
        engine = ImpairmentEngine(lambda: {"reorder_probability": 1.0})
        decision = await engine.apply_outbound(b"ping")
        assert decision.reorder is True

    @pytest.mark.asyncio
    async def test_delay(self) -> None:
        engine = ImpairmentEngine(lambda: {"delay_ms": 10.0})
        decision = await engine.apply_outbound(b"ping")
        assert decision.delay_ms >= 10.0

    @pytest.mark.asyncio
    async def test_bandwidth_rate_limits(self) -> None:
        # 8 kbps = 1000 bytes/s；1000 字节报文需等待约 1 秒。
        engine = ImpairmentEngine(lambda: {"bandwidth_kbps": 8.0})
        decision = await engine.apply_outbound(b"x" * 1000)
        assert decision.delay_ms > 0.0


class TestSocketImpairment:
    """P2 — impairment applied through UdpSocket.sendto."""

    @pytest.mark.asyncio
    async def test_duplicate_sends_twice(self) -> None:
        engine = ImpairmentEngine(lambda: {"duplicate_probability": 1.0})
        async with (
            UdpSocket("127.0.0.1", 0, impairment=engine) as sender,
            UdpSocket("127.0.0.1", 0) as receiver,
        ):
            target = receiver.local_address
            assert target is not None
            await sender.sendto(b"ping", target)

            first = await receiver.recvfrom(timeout=1.0)
            second = await receiver.recvfrom(timeout=1.0)
            assert first[0] == b"ping"
            assert second[0] == b"ping"
            assert sender.duplicated_packets == 1

    @pytest.mark.asyncio
    async def test_corrupt_changes_payload(self) -> None:
        engine = ImpairmentEngine(lambda: {"corrupt_probability": 1.0, "corrupt_bytes": 1})
        async with (
            UdpSocket("127.0.0.1", 0, impairment=engine) as sender,
            UdpSocket("127.0.0.1", 0) as receiver,
        ):
            target = receiver.local_address
            assert target is not None
            original = b"hello world"
            await sender.sendto(original, target)

            data, _ = await receiver.recvfrom(timeout=1.0)
            assert data != original
            assert len(data) == len(original)
            assert sender.corrupted_packets == 1
