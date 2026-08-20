"""Integration tests: IKEv2 握手后 ESP 数据面往返（真实 AES-256-GCM）。"""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.ipsec.esp import ESPSession
from vpn_simulator.services.esp_transport import ESPTransport
from vpn_simulator.services.ikev2_handshake import IKEv2Handshake


@pytest.mark.asyncio
async def test_ikev2_handshake_then_esp_roundtrip() -> None:
    initiator_identity = b"initiator@test.local"
    responder_identity = b"responder@test.local"

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        initiator_addr = initiator_sock.local_address
        assert responder_addr is not None and initiator_addr is not None

        initiator_hs = IKEv2Handshake(initiator_identity, initiator_sock)
        responder_hs = IKEv2Handshake(responder_identity, responder_sock)

        await asyncio.gather(
            initiator_hs.initiate(responder_addr, responder_identity),
            responder_hs.respond(initiator_identity),
        )

        esp_key = initiator_hs.esp_key()
        assert esp_key is not None
        assert esp_key == responder_hs.esp_key()

        initiator_spi, responder_spi = 0x1001, 0x1002
        initiator_t = ESPTransport(
            initiator_sock, ESPSession(esp_key), initiator_spi, responder_spi
        )
        responder_t = ESPTransport(
            responder_sock, ESPSession(esp_key), responder_spi, initiator_spi
        )

        payload = b"ESP data-plane payload"
        await initiator_t.send_data(responder_addr, payload)
        assert await responder_t.recv_data() == payload
        await responder_t.send_data(initiator_addr, payload)
        assert await initiator_t.recv_data() == payload


@pytest.mark.asyncio
async def test_esp_wrong_key_rejected() -> None:
    import os

    async with (
        UdpSocket("127.0.0.1", 0) as initiator_sock,
        UdpSocket("127.0.0.1", 0) as responder_sock,
    ):
        responder_addr = responder_sock.local_address
        assert responder_addr is not None

        initiator_t = ESPTransport(initiator_sock, ESPSession(os.urandom(32)), 0x1001, 0x1002)
        responder_t = ESPTransport(responder_sock, ESPSession(os.urandom(32)), 0x1002, 0x1001)

        await initiator_t.send_data(responder_addr, b"data")
        with pytest.raises(ValueError, match="authentication failed"):
            await responder_t.recv_data()
