"""Integration tests: IKEv2 handshake end-to-end + state machine."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.ikev2.state_machine import IKEv2StateMachine
from vpn_simulator.services.ikev2_handshake import IKEv2Handshake

INITIATOR_ID = b"initiator@vpn-simulator.local"
RESPONDER_ID = b"responder@vpn-simulator.local"


@pytest.mark.asyncio
async def test_ikev2_handshake_end_to_end() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_sm = IKEv2StateMachine()
        initiator_hs = IKEv2Handshake(INITIATOR_ID, initiator_sock, state_machine=initiator_sm)
        responder_hs = IKEv2Handshake(RESPONDER_ID, responder_sock)

        initiator_spis, responder_spis = await asyncio.gather(
            initiator_hs.initiate(responder_addr, RESPONDER_ID),
            responder_hs.respond(INITIATOR_ID),
        )

        # 双方须对 SPI 达成一致：initiator 返回 (spi_i, spi_r)，responder 返回 (spi_i, spi_r)。
        assert initiator_spis == responder_spis
        assert initiator_sm.current_state == "CONNECTED"


@pytest.mark.asyncio
async def test_ikev2_auth_rejects_wrong_identity() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = IKEv2Handshake(INITIATOR_ID, initiator_sock)
        responder_hs = IKEv2Handshake(RESPONDER_ID, responder_sock)

        results = await asyncio.gather(
            initiator_hs.initiate(responder_addr, RESPONDER_ID, timeout=1.0),
            responder_hs.respond(b"wrong-identity"),
            return_exceptions=True,
        )
        assert any(isinstance(r, ValueError) for r in results)
