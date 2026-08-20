"""Unit tests: OpenVPN TLS-over-MemoryBIO handshake + app data (P1)."""

from __future__ import annotations

import ssl

from vpn_simulator.plugins.protocols.openvpn.tls import DATA_KEY_LEN, TLSBIO, create_tls_contexts


def _pump(server: TLSBIO, client: TLSBIO) -> None:
    """把一端待发送字节搬到对端 incoming，直到双方都无待发送字节。"""
    for _ in range(20):
        moved = False
        for src, dst in ((server, client), (client, server)):
            if src.has_outgoing():
                dst.feed_incoming(src.take_outgoing())
                moved = True
        if not moved:
            return


def _handshake(server: TLSBIO, client: TLSBIO) -> None:
    """交替推进两端握手（非阻塞 BIO 驱动）。"""
    for _ in range(100):
        for side in (server, client):
            try:
                side.do_handshake()
            except ssl.SSLWantReadError:
                pass
            except ssl.SSLWantWriteError:
                pass
            _pump(server, client)
        try:
            server.do_handshake()
            client.do_handshake()
            _pump(server, client)
            return
        except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
            _pump(server, client)
    raise RuntimeError("TLS handshake did not converge")


def test_tls_handshake_and_app_data() -> None:
    server_ctx, client_ctx = create_tls_contexts()
    server = TLSBIO(server_ctx, server_side=True)
    client = TLSBIO(client_ctx, server_side=False)

    _handshake(server, client)

    assert server.version == "TLSv1.3"
    assert client.version == "TLSv1.3"

    # 客户端加密一段明文，服务端解密。
    client.write(b"hello openvpn tls")
    _pump(server, client)
    assert server.read(32) == b"hello openvpn tls"

    # 服务端回一段，客户端解密。
    server.write(b"ack")
    _pump(server, client)
    assert client.read(32) == b"ack"


def test_data_key_len_constant() -> None:
    assert DATA_KEY_LEN == 32
