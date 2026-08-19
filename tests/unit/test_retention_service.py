"""Tests for RetentionService - packets/state_transitions cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from vpn_simulator.core.database import DatabaseManager, PacketRecord, StateTransitionRecord
from vpn_simulator.services.retention import RetentionService


async def _make_service() -> RetentionService:
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.initialize()
    return RetentionService(db)


@pytest.mark.asyncio
async def test_counts_empty():
    service = await _make_service()
    assert await service.counts() == {"packets": 0, "state_transitions": 0}


@pytest.mark.asyncio
async def test_ttl_cleanup():
    service = await _make_service()
    manager = service._manager()
    now = datetime.now(UTC)
    async with manager.session() as session:
        session.add_all(
            [
                PacketRecord(
                    id="p1",
                    direction="out",
                    packet_type="handshake",
                    protocol="wireguard",
                    timestamp=now - timedelta(days=10),
                ),
                PacketRecord(
                    id="p2",
                    direction="out",
                    packet_type="handshake",
                    protocol="wireguard",
                    timestamp=now - timedelta(hours=1),
                ),
                StateTransitionRecord(
                    protocol="wireguard",
                    from_state="idle",
                    to_state="init",
                    event="recv",
                    timestamp=now - timedelta(days=40),
                ),
                StateTransitionRecord(
                    protocol="wireguard",
                    from_state="init",
                    to_state="full",
                    event="recv",
                    timestamp=now,
                ),
            ]
        )

    assert await service.counts() == {"packets": 2, "state_transitions": 2}

    result = await service.cleanup(
        packet_ttl_seconds=2 * 86400,
        transition_ttl_seconds=10 * 86400,
        max_packets=0,
        max_transitions=0,
    )
    assert result["deleted_packets"] == 1
    assert result["deleted_state_transitions"] == 1
    assert result["remaining_packets"] == 1
    assert result["remaining_state_transitions"] == 1


@pytest.mark.asyncio
async def test_max_rows_cleanup_keeps_newest():
    service = await _make_service()
    manager = service._manager()
    now = datetime.now(UTC)
    async with manager.session() as session:
        session.add_all(
            [
                PacketRecord(
                    id=f"p{i}",
                    direction="out",
                    packet_type="data",
                    protocol="udp",
                    timestamp=now - timedelta(seconds=i),
                )
                for i in range(5)
            ]
        )

    result = await service.cleanup(
        max_packets=2,
        packet_ttl_seconds=0,
        max_transitions=0,
        transition_ttl_seconds=0,
    )
    assert result["deleted_packets"] == 3
    assert result["remaining_packets"] == 2
