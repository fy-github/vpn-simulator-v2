"""Integration tests: OpenVPN control-channel handshake over real loopback UDP."""

from __future__ import annotations

import asyncio

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.plugins.protocols.openvpn.control_channel import generate_tls_auth_key
from vpn_simulator.plugins.protocols.openvpn.state_machine import OpenVPNStateMachine
from vpn_simulator.services.openvpn_handshake import OpenVPNHandshake


@pytest.mark.asyncio
async def test_hard_reset_handshake_succeeds() -> None:
    key = generate_tls_auth_key()
    state_machine = OpenVPNStateMachine()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        client_hs = OpenVPNHandshake(key, client_sock, state_machine=state_machine)
        server_hs = OpenVPNHandshake(key, server_sock)

        initiate_result, respond_result = await asyncio.gather(
            client_hs.initiate(server_addr),
            server_hs.respond(),
        )

    client_session_id, server_session_id, data_key = initiate_result
    # respond() 返回 (发起方 session_id, 本端 session_id, 数据密钥)。
    assert respond_result[0] == client_session_id
    assert respond_result[1] == server_session_id
    assert respond_result[2] == data_key
    assert len(data_key) == 32
    assert server_session_id != client_session_id
    # 发起方状态机: INITIAL -> ... -> CONNECTED（完整 TLS + PUSH 流程）。
    assert state_machine.current_state == "CONNECTED"


@pytest.mark.asyncio
async def test_hard_reset_handshake_tamper_fails() -> None:
    key = generate_tls_auth_key()

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        client_hs = OpenVPNHandshake(key, client_sock)
        # 服务端使用错误的密钥：HMAC 校验失败，respond() 抛 ValueError。
        server_hs = OpenVPNHandshake(generate_tls_auth_key(), server_sock)

        with pytest.raises(ValueError):
            await asyncio.gather(
                client_hs.initiate(server_addr, timeout=1.0),
                server_hs.respond(timeout=1.0),
            )
