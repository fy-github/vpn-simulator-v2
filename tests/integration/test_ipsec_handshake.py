"""Integration tests: IKEv1/IPSec Main Mode + Quick Mode handshake end-to-end."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.ipsec.crypto import generate_psk
from vpn_simulator.plugins.protocols.ipsec.state_machine import IPSecStateMachine
from vpn_simulator.services.ipsec_handshake import IPsecHandshake

INITIATOR_ID = b"initiator@vpn-simulator.local"
RESPONDER_ID = b"responder@vpn-simulator.local"


@pytest.mark.asyncio
async def test_ipsec_handshake_end_to_end() -> None:
    psk = generate_psk()

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_sm = IPSecStateMachine()
        initiator_hs = IPsecHandshake(INITIATOR_ID, psk, initiator_sock, state_machine=initiator_sm)
        responder_hs = IPsecHandshake(RESPONDER_ID, psk, responder_sock)

        initiator_cookies, responder_cookies = await asyncio.gather(
            initiator_hs.initiate(responder_addr, RESPONDER_ID),
            responder_hs.respond(INITIATOR_ID),
        )

        assert initiator_cookies == responder_cookies
        assert initiator_sm.current_state == "CONNECTED"


@pytest.mark.asyncio
async def test_ipsec_handshake_rejects_wrong_psk() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = IPsecHandshake(INITIATOR_ID, generate_psk(), initiator_sock)
        responder_hs = IPsecHandshake(RESPONDER_ID, generate_psk(), responder_sock)

        results = await asyncio.gather(
            initiator_hs.initiate(responder_addr, RESPONDER_ID, timeout=1.0),
            responder_hs.respond(INITIATOR_ID),
            return_exceptions=True,
        )
        assert any(isinstance(r, ValueError) for r in results)
