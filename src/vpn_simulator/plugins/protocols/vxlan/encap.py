"""VXLAN 数据面封装（RFC 7348 教学简化）。

VXLAN 为无状态隧道封装协议（无控制面握手），在 UDP 4789 上封装 L2 帧：

```
VXLAN 报文: flags(1B)=0x08(I) | reserved(3B)=0 | VNI(3B,24位) | reserved(1B)=0 | payload
```

- I 位（0x08）表示 VNI 有效。
- VNI 为 24 位 VXLAN Network Identifier。
- payload 为内层以太网帧（教学简化，不实现完整 Ethernet 头）。
- VXLAN 为明文封装（如实体现，加密由外层 IPSec 等承担）。

socket 往返编排见 `services/vxlan_transport.py`。
"""

from __future__ import annotations

FLAG_I = 0x08
HEADER_LEN = 8  # flags(1) + reserved(3) + vni(3) + reserved(1)
MAX_VNI = 0xFFFFFF


def build_vxlan_packet(vni: int, payload: bytes) -> bytes:
    """组帧一条 VXLAN 报文（I 位 + VNI + payload）。"""
    if not 0 <= vni <= MAX_VNI:
        raise ValueError(f"VNI out of range: {vni}")
    return bytes([FLAG_I]) + b"\x00\x00\x00" + vni.to_bytes(3, "big") + b"\x00" + payload


def parse_vxlan_packet(raw: bytes) -> tuple[int, bytes]:
    """解帧一条 VXLAN 报文，返回 ``(vni, payload)``。

    Raises:
        ValueError: 长度不足，或 I 位未设置。
    """
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid VXLAN packet length: {len(raw)}")
    if raw[0] & FLAG_I == 0:
        raise ValueError("VXLAN I flag not set")
    vni = int.from_bytes(raw[4:7], "big")
    return vni, raw[HEADER_LEN:]
