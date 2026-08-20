# VPN Simulator v2 — OpenVPN 数据面真实报文仿真计划 v5

> 承接 `PLAN_ENHANCEMENT_V4.md`（WireGuard 数据面已闭环）。V3 已实现 OpenVPN
> 控制信道 framing + `--tls-auth` HMAC（Hard Reset 交换、驱动状态机到
> TLS_HANDSHAKE），但数据面仍是「TLS 数据面密钥协商待接入」占位。本计划补上
> OpenVPN **数据面**：用 AES-256-GCM 真实加解密数据报文，并做真实加密往返。

## 一、背景与现状

- OpenVPN 控制信道（V3）：`control_channel.py` 完成 Hard Reset 交换，`respond()`
  返回客户端 session_id、`initiate()` 返回 `(客户端 sid, 服务端 sid)`。
- 数据面缺失：`P_DATA_V2(9)` 报文格式、AES-256-GCM 加解密、数据密钥派生、
  packet_id 重放防护。
- `validation.py` 的 OpenVPN「tunnel」步骤为占位文案「TLS 数据面密钥协商待接入」。

## 二、数据信道密钥派生（教学简化，明示）

真实 OpenVPN 用 TLS 握手 + keying-material exporter（`EXPORTER-openvpn-1`）派生
数据密钥；本计划**不实现完整 TLS 握手**（超出「控制面/握手层」边界），改用
HKDF-SHA256 从 `--tls-auth` 预共享密钥 + 双方 session_id 派生 32 字节数据密钥，
作为「模拟的 TLS keying-material export」，并在代码与文档中明示该简化。

## 三、数据信道报文格式（P_DATA_V2 教学版）

```
opcode(1, =9) | peer_id(8, BE) | packet_id(4, BE) | ciphertext+tag(AES-256-GCM)
```

- AEAD：AES-256-GCM，nonce = `packet_id(4, BE) || 0x0000000000000000`（12 字节）。
- 关联数据（AD）为空；密文尾部附 16 字节认证标签。
- `peer_id` 为接收方 session_id；`packet_id` 每方向单调递增，用于重放防护。

## 四、分阶段任务

### P1 — 数据信道报文格式 + 加解密

新增 `plugins/protocols/openvpn/data_channel.py`：

- `derive_data_key(tls_auth_key, client_sid, server_sid)`（HKDF-SHA256）。
- `build_data_packet(data_key, peer_id, packet_id, plaintext)` /
  `parse_data_packet(data_key, raw) -> (peer_id, packet_id, plaintext)`。
- `OpenVPNDataSession`：`seal()` 递增 `send_packet_id`，`open()` 做重放防护。

### P2 — 数据面真实往返编排 + 接入 validation

新增 `services/openvpn_transport.py`：`OpenVPNTransport(socket, session, local_id,
peer_id)`，`send_data`/`recv_data`（校验 `peer_id` 匹配本端）。

`validation.py`：OpenVPN「tunnel」步骤改为真实数据往返（控制信道 Hard Reset 后，
同 socket 派生数据密钥 → 客户端 seal→发送→服务端 open→seal 应答→客户端 open）。

### P3 — 测试 + 文档

- `tests/unit/test_openvpn_data_channel.py`：seal/open 往返、篡改解密失败、重放
  拒绝、坏长度/坏类型。
- `tests/integration/test_openvpn_transport_flow.py`：控制握手 + 数据面加密往返。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- OpenVPN `validate()` 的 tunnel 步骤为真实 AES-256-GCM 数据面往返。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `bf23818` | `data_channel.py`：HKDF 数据密钥派生 + AES-256-GCM seal/open + packet_id 重放防护 |
| P2 | `179e3cf` | `services/openvpn_transport.py` + `validation.py` tunnel 步骤真实数据往返 |
| P3 | 本提交 | 单元/集成测试（10+2 条）+ README 同步 |

最终指标：后端 1221 tests 通过、80.7% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

