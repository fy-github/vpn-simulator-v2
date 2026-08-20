"""L2TP 数据面报文（RFC 2661 数据消息，教学简化）。

L2TP 控制与数据共用 UDP 1701，数据消息与控制消息用首字节 T 位区分：T=0 为数据
消息，T=1 为控制消息。数据报文格式：

```
L2TP 数据报文: version_flags(2,BE)=0x0002 | tunnel_id(2,BE) | session_id(2,BE) | payload
```

- ``version_flags``：首字节 T 位（0x8000）=0（数据），版本号 2（低 4 位）。
- tunnel_id / session_id 为**接收方**的标识（发送方填对端 id）。
- L2TP 数据消息为明文（加密/认证由内层 PPP/IPSec 承担，如实体现）。
- payload 为 PPP 帧（教学简化，不实现 LCP/IPCP）。

socket 往返编排见 `services/l2tp_data_transport.py`。
"""

from __future__ import annotations

FLAG_TYPE_MASK = 0x8000  # T 位：1=控制，0=数据
VERSION_MASK = 0x000F
VERSION_2 = 0x02
HEADER_LEN = 6  # version_flags(2) + tunnel_id(2) + session_id(2)


def build_l2tp_data(tunnel_id: int, session_id: int, payload: bytes) -> bytes:
    """组帧一条 L2TP 数据报文（T=0, version=2）。"""
    return (
        VERSION_2.to_bytes(2, "big")
        + tunnel_id.to_bytes(2, "big")
        + session_id.to_bytes(2, "big")
        + payload
    )


def parse_l2tp_data(raw: bytes) -> tuple[int, int, bytes]:
    """解帧一条 L2TP 数据报文，返回 ``(tunnel_id, session_id, payload)``。

    Raises:
        ValueError: 长度不足，或 T 位表示控制消息，或版本号非 2。
    """
    if len(raw) < HEADER_LEN:
        raise ValueError(f"invalid L2TP data length: {len(raw)}")
    flags = int.from_bytes(raw[0:2], "big")
    if flags & FLAG_TYPE_MASK:
        raise ValueError("not an L2TP data message (T=1)")
    if flags & VERSION_MASK != VERSION_2:
        raise ValueError(f"unsupported L2TP version: {flags & VERSION_MASK}")
    tunnel_id = int.from_bytes(raw[2:4], "big")
    session_id = int.from_bytes(raw[4:6], "big")
    return tunnel_id, session_id, raw[HEADER_LEN:]
