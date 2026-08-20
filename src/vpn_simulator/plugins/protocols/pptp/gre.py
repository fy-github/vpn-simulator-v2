"""PPTP GRE 数据面报文（RFC 2784，Key 扩展，教学简化）。

PPTP 数据面为 GRE-over-IP（协议号 47），本模块实现 GRE 报文封装：

```
GRE 报文: flags(2,BE)=0x2000(K) | protocol_type(2,BE)=0x880B(PPP) | key(4,BE) | payload
```

- ``K`` 位（0x2000）表示存在 4 字节 Key；不设 C/R/S 位（无 checksum/seq，教学简化）。
- Protocol Type 0x880B = PPP；payload 为 PPP 帧（教学简化，不实现 LCP/IPCP）。
- GRE 为明文封装（如实体现 PPTP 数据面无加密）。

socket 往返编排见 `services/gre_transport.py`。
"""

from __future__ import annotations

FLAG_KEY = 0x2000  # K 位：存在 4 字节 Key
PROTOCOL_PPP = 0x880B
GRE_HEADER_LEN = 4  # flags(2) + protocol(2)
KEY_LEN = 4


def build_gre_packet(key: int, payload: bytes) -> bytes:
    """组帧一条 GRE 报文（K 位 + PPP + key + payload）。"""
    return (
        FLAG_KEY.to_bytes(2, "big")
        + PROTOCOL_PPP.to_bytes(2, "big")
        + key.to_bytes(KEY_LEN, "big")
        + payload
    )


def parse_gre_packet(raw: bytes) -> tuple[int, bytes]:
    """解帧一条 GRE 报文，返回 ``(key, payload)``。

    Raises:
        ValueError: 长度不足，或 K 位未设置，或 protocol 非 PPP。
    """
    if len(raw) < GRE_HEADER_LEN + KEY_LEN:
        raise ValueError(f"invalid GRE packet length: {len(raw)}")
    flags = int.from_bytes(raw[0:2], "big")
    if flags & FLAG_KEY == 0:
        raise ValueError("GRE key flag not set")
    protocol = int.from_bytes(raw[2:4], "big")
    if protocol != PROTOCOL_PPP:
        raise ValueError(f"unexpected GRE protocol type: 0x{protocol:04x}")
    key = int.from_bytes(raw[4:8], "big")
    return key, raw[8:]
