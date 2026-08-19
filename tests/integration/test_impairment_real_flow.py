"""Integration tests: impairment applies to real WireGuard handshake packets."""

from __future__ import annotations

import asyncio
import time

import pytest
from vpn_simulator.core.impairment_engine import ImpairmentEngine
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.wireguard.crypto import WireGuardIdentity
from vpn_simulator.plugins.protocols.wireguard.state_machine import (
    WireGuardStateMachine,
)
from vpn_simulator.services.wireguard_handshake import WireGuardHandshake


@pytest.mark.asyncio
async def test_latency_impairment_delays_real_handshake():
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    engine = ImpairmentEngine(lambda: {"delay_ms": 200.0})

    async with (
        UdpSocket("127.0.0.1", 0, impairment=engine) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(initiator, initiator_sock, WireGuardStateMachine())
        responder_hs = WireGuardHandshake(responder, responder_sock)

        start = time.perf_counter()
        await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder.public_bytes, 1),
            responder_hs.respond(sender_index=2),
        )
        elapsed = time.perf_counter() - start

    # 200ms 延迟应明显拉长握手（无损伤环回握手仅毫秒级）
    assert elapsed >= 0.18


@pytest.mark.asyncio
async def test_packet_loss_impairment_drops_real_packet():
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    engine = ImpairmentEngine(lambda: {"loss_rate": 1.0})

    async with (
        UdpSocket("127.0.0.1", 0, impairment=engine) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(initiator, initiator_sock, WireGuardStateMachine())
        responder_hs = WireGuardHandshake(responder, responder_sock)

        with pytest.raises(TimeoutError):
            await asyncio.gather(
                initiator_hs.initiate(responder_addr, responder.public_bytes, 1, timeout=0.5),
                responder_hs.respond(sender_index=2, timeout=0.5),
            )

    # 100% 丢包导致发起方 Initiation 被丢弃
    assert initiator_sock.dropped_packets == 1
