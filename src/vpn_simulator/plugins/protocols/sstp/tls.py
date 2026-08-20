"""SSTP TLS 握手辅助：自签名证书生成 + TLS 上下文。

SSTP 协议栈为 TCP(443) → TLS → SSTP 控制 → PPP。本模块用真实 TLS 握手
（Python `ssl`），运行时生成自签名 ECDSA P-256 证书。客户端以
``verify_mode=CERT_NONE`` 跳过验证（教学模拟器不自建 CA，明示）。
"""

from __future__ import annotations

import datetime
import ipaddress
import ssl
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CERT_COMMON_NAME = "vpn-simulator.test"


def generate_self_signed_cert() -> tuple[bytes, bytes]:
    """生成一张自签名 ECDSA P-256 证书，返回 ``(cert_pem, key_pem)``。"""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CERT_COMMON_NAME)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(CERT_COMMON_NAME),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


@dataclass(frozen=True)
class TLSContexts:
    """服务端/客户端 TLS 上下文对。"""

    server: ssl.SSLContext
    client: ssl.SSLContext


def create_tls_contexts() -> TLSContexts:
    """生成自签名证书并创建服务端/客户端 TLS 上下文。"""
    cert_pem, key_pem = generate_self_signed_cert()
    with tempfile.TemporaryDirectory() as tmpdir:
        certfile = Path(tmpdir) / "cert.pem"
        keyfile = Path(tmpdir) / "key.pem"
        certfile.write_bytes(cert_pem)
        keyfile.write_bytes(key_pem)

        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.load_cert_chain(str(certfile), str(keyfile))

    client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_ctx.check_hostname = False
    client_ctx.verify_mode = ssl.CERT_NONE
    return TLSContexts(server=server_ctx, client=client_ctx)
