"""PPP 链路/网络控制协议（LCP/IPCP）帧（RFC 1661 / RFC 1332 教学简化）。

LCP 与 IPCP 共用同一控制帧格式：

```
Code(1) | Identifier(1) | Length(2) | Data(Length-4)
```

- Code=1 为 Configure-Request，Code=2 为 Configure-Ack。
- LCP 选项 MRU：`type=1 | len=4 | MRU(2)`。
- IPCP 选项 IP-Address：`type=3 | len=6 | IP(4)`。

真实协商编排见 `services/sstp_handshake.py`。
"""

from __future__ import annotations

CONFIGURE_REQUEST = 1
CONFIGURE_ACK = 2

HEADER_LEN = 4  # code(1) + identifier(1) + length(2)

LCP_OPT_MRU = 1
IPCP_OPT_IP_ADDRESS = 3

DEFAULT_MRU = 1500


def build_configure_request(identifier: int, options: bytes) -> bytes:
    """构造 Configure-Request（LCP/IPCP 通用）。"""
    return _build_frame(CONFIGURE_REQUEST, identifier, options)


def build_configure_ack(identifier: int, options: bytes) -> bytes:
    """构造 Configure-Ack，回显请求的选项（LCP/IPCP 通用）。"""
    return _build_frame(CONFIGURE_ACK, identifier, options)


def parse_frame(raw: bytes) -> tuple[int, int, bytes]:
    """解帧，返回 ``(code, identifier, data)``。

    Raises:
        ValueError: 长度不足或 Length 字段与报文不符。
    """
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid PPP control frame length: {len(raw)}")
    length = int.from_bytes(raw[2:4], "big")
    if length != len(raw):
        raise ValueError(f"PPP control length mismatch: {length} != {len(raw)}")
    return raw[0], raw[1], raw[4:]


def build_lcp_mru_option(mru: int = DEFAULT_MRU) -> bytes:
    """LCP MRU 选项。"""
    return bytes([LCP_OPT_MRU, 4]) + mru.to_bytes(2, "big")


def build_ipcp_ip_option(ip: str = "10.0.0.2") -> bytes:
    """IPCP IP-Address 选项（点分十进制）。"""
    octets = [int(part) for part in ip.split(".")]
    if len(octets) != 4 or any(not 0 <= o <= 255 for o in octets):
        raise ValueError(f"invalid IPv4 address: {ip}")
    return bytes([IPCP_OPT_IP_ADDRESS, 6]) + bytes(octets)


def _build_frame(code: int, identifier: int, options: bytes) -> bytes:
    length = HEADER_LEN + len(options)
    return bytes([code, identifier]) + length.to_bytes(2, "big") + options
