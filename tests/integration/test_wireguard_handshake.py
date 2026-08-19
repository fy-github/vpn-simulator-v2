"""Integration tests: real WireGuard handshake over loopback UDP."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.wireguard.crypto import WireGuardIdentity
from vpn_simulator.plugins.protocols.wireguard.state_machine import (
    WireGuardStateMachine,
)
from vpn_simulator.services.wireguard_handshake import WireGuardHandshake


@pytest.mark.asyncio
async def test_loopback_handshake_drives_state_machine():
    initiator = WireGuardIdentity.generate()
    responder = WireGuardIdentity.generate()
    state_machine = WireGuardStateMachine()

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_hs = WireGuardHandshake(initiator, initiator_sock, state_machine)
        responder_hs = WireGuardHandshake(responder, responder_sock)

        (send_i, recv_i), (recv_r, send_r) = await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder.public_bytes, 0x11111111),
            responder_hs.respond(sender_index=0x22222222),
        )

    # 双方派生出一致的传输密钥
    assert send_i == recv_r
    assert recv_i == send_r
    assert send_i != recv_i

    # 真实报文驱动状态机完成完整握手
    assert state_machine.current_state == "CONNECTED"
    events = [record.event for record in state_machine.history]
    assert events == [
        "SEND_INITIATION",
        "RECEIVE_RESPONSE",
        "DERIVE_KEYS",
        "DATA_CHANNEL_READY",
    ]


@pytest.mark.asyncio
async def test_responder_timeout():
    responder = WireGuardIdentity.generate()

    async with UdpSocket("127.0.0.1", 0) as responder_sock:
        responder_hs = WireGuardHandshake(responder, responder_sock)
        with pytest.raises(TimeoutError):
            await responder_hs.respond(sender_index=1, timeout=0.1)
