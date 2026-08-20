"""OpenVPN 控制信道 TLS 助手：ssl.MemoryBIO 非阻塞握手 + 数据密钥交换。

OpenVPN 控制信道在 Hard Reset 后承载真实 TLS 记录（P_CONTROL_V1 载荷）。本模块用
Python `ssl` 的 ``MemoryBIO`` + ``SSLObject``（``wrap_bio``）在无 socket 的字节流上
驱动真实 TLS 1.3 握手，服务端证书复用 ``sstp/tls.py`` 的自签名 ECDSA P-256 证书。

数据密钥：真实 OpenVPN 用 TLS keying-material exporter（RFC 5705，标签
``EXPORTER-network-tunnel``）派生数据信道密钥；本环境 Python ssl 未暴露
``export_keying_material``（OpenSSL 4.x 移除），故改为在真实 TLS 加密信道内交换随机
32 字节数据密钥——数据密钥由 TLS 会话保护，不再是可由 ``--tls-auth`` 预共享密钥
直接推导，已在计划文档明示该差异。
"""

from __future__ import annotations

import ssl

DATA_KEY_LEN = 32
# OpenVPN 真实 keying-material exporter 标签（RFC 5705）。
EXPORTER_LABEL = b"EXPORTER-network-tunnel"


def create_tls_contexts() -> tuple[ssl.SSLContext, ssl.SSLContext]:
    """返回 ``(server_ctx, client_ctx)``，复用 ``sstp/tls.py`` 的自签名证书。"""
    from vpn_simulator.plugins.protocols.sstp.tls import create_tls_contexts as _sstp_create

    ctxs = _sstp_create()
    return ctxs.server, ctxs.client


class TLSBIO:
    """一组 ``MemoryBIO`` + ``SSLObject``，在无 socket 字节流上驱动 TLS。

    用法：``do_handshake()`` 抛 ``SSLWantReadError`` / ``SSLWantWriteError`` 时，
    调用方负责 ``take_outgoing()`` 发送、``feed_incoming()`` 喂入对端字节，再继续
    ``do_handshake()``。握手完成后用 ``write()`` 加密明文、``read()`` 解密密文。
    """

    def __init__(self, context: ssl.SSLContext, server_side: bool) -> None:
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._sslobj = context.wrap_bio(self._incoming, self._outgoing, server_side=server_side)

    def do_handshake(self) -> None:
        """推进握手；完成时返回，需要更多 IO 时抛 ``SSLWantRead/WriteError``。"""
        self._sslobj.do_handshake()

    def feed_incoming(self, data: bytes) -> None:
        """喂入对端发来的加密字节。"""
        self._incoming.write(data)

    def take_outgoing(self) -> bytes:
        """取走待发送的加密字节（TLS 记录）。"""
        return self._outgoing.read()

    def has_outgoing(self) -> bool:
        """是否有待发送字节。"""
        return self._outgoing.pending > 0

    def write(self, data: bytes) -> None:
        """加密一段明文，密文进入待发送队列。"""
        self._sslobj.write(data)

    def read(self, n: int) -> bytes:
        """从已喂入的密文中解出最多 ``n`` 字节明文（无数据时抛 ``SSLWantReadError``）。"""
        return self._sslobj.read(n)

    @property
    def version(self) -> str | None:
        """协商出的 TLS 版本。"""
        return self._sslobj.version()
