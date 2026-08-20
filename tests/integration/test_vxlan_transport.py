"""Integration tests: VXLAN 封装/解封装往返（真实 RFC 7348）。"""

from __future__ import annotations

import pytest
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.services.vxlan_transport import VXLANTransport


@pytest.mark.asyncio
async def test_vxlan_roundtrip() -> None:
    vni = 100

    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        client_addr = client_sock.local_address
        assert server_addr is not None and client_addr is not None

        client_t = VXLANTransport(client_sock, vni, vni)
        server_t = VXLANTransport(server_sock, vni, vni)

        payload = b"VXLAN data-plane payload"
        await client_t.send_data(server_addr, payload)
        assert await server_t.recv_data() == payload
        await server_t.send_data(client_addr, payload)
        assert await client_t.recv_data() == payload


@pytest.mark.asyncio
async def test_vxlan_wrong_vni_rejected() -> None:
    async with (
        UdpSocket("127.0.0.1", 0) as client_sock,
        UdpSocket("127.0.0.1", 0) as server_sock,
    ):
        server_addr = server_sock.local_address
        assert server_addr is not None

        # 服务端期望 VNI=100，但客户端错误地以 VNI=200 封装
        client_t = VXLANTransport(client_sock, local_vni=100, peer_vni=200)
        server_t = VXLANTransport(server_sock, local_vni=100, peer_vni=100)

        await client_t.send_data(server_addr, b"data")
        with pytest.raises(ValueError, match="VNI mismatch"):
            await server_t.recv_data()
