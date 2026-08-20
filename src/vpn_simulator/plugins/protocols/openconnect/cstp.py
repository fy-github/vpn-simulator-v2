"""OpenConnect CSTP 隧道协商（AnyConnect 教学简化）。

AnyConnect/OpenConnect 的 CSTP（Cisco SSL Tunnel Protocol）在 TLS 之上用 HTTP
CONNECT 协商隧道参数（X-CSTP-* 头）。本模块实现该 CONNECT 请求/响应：

```
客户端: CONNECT /CSCOSSLC/tunnel HTTP/1.1
        Host: vpn-simulator.test
        X-CSTP-Version: 1
        X-CSTP-MTU: 1400

服务端: HTTP/1.1 200 CONNECTED
        X-CSTP-Version: 1
        X-CSTP-MTU: 1400
        Content-Length: 0
```

HTTP 头以 ``\\r\\n\\r\\n`` 结束（教学简化，不含 body）。
"""

from __future__ import annotations

CSTP_PATH = b"/CSCOSSLC/tunnel"
CSTP_VERSION = b"1"
DEFAULT_MTU = b"1400"
HEADER_END = b"\r\n\r\n"


def build_connect_request(host: str = "vpn-simulator.test") -> bytes:
    """构造 CSTP CONNECT 请求。"""
    return (
        b"CONNECT "
        + CSTP_PATH
        + b" HTTP/1.1\r\n"
        + b"Host: "
        + host.encode()
        + b"\r\n"
        + b"X-CSTP-Version: "
        + CSTP_VERSION
        + b"\r\n"
        + b"X-CSTP-MTU: "
        + DEFAULT_MTU
        + b"\r\n\r\n"
    )


def parse_connect_request(raw: bytes) -> None:
    """校验 CSTP CONNECT 请求。"""
    if not raw.startswith(b"CONNECT " + CSTP_PATH + b" HTTP/1.1"):
        raise ValueError("invalid CSTP CONNECT request line")
    if b"X-CSTP-Version: " + CSTP_VERSION not in raw:
        raise ValueError("unsupported X-CSTP-Version")


def build_connect_response() -> bytes:
    """构造 CSTP CONNECT 成功响应。"""
    return (
        b"HTTP/1.1 200 CONNECTED\r\n"
        + b"X-CSTP-Version: "
        + CSTP_VERSION
        + b"\r\n"
        + b"X-CSTP-MTU: "
        + DEFAULT_MTU
        + b"\r\n"
        + b"Content-Length: 0\r\n\r\n"
    )


def parse_connect_response(raw: bytes) -> None:
    """校验 CSTP CONNECT 响应。"""
    if not raw.startswith(b"HTTP/1.1 200"):
        raise ValueError("CSTP CONNECT status is not 200")
    if b"X-CSTP-Version: " + CSTP_VERSION not in raw:
        raise ValueError("unsupported X-CSTP-Version in response")
