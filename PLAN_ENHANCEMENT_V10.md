# VPN Simulator v2 — IPsec ESP 数据面仿真计划 v10

> 承接 `PLAN_ENHANCEMENT_V9.md`（PPTP 握手已闭环，6 协议控制面全部真实）。本计划
> 把 IKEv2/IPSec 的 **ESP 数据面**真实化：在控制面握手后，用真实 AES-256-GCM ESP
> 报文（RFC 4303 教学简化）做数据面加密往返，替换「ESP 数据面转发待接入」占位，
> 使 ikev2 与 ipsec 的 tunnel 步骤升级为真实 ESP 往返。

## 一、背景与现状

- `validation.py` 的 ikev2/ipsec tunnel 步骤现为「ESP 隧道就绪（数据面转发待接入）」
  占位。IKE 握手已派生密钥集（`IKEv2KeySet` / `IPsecKeySet`），可派生 ESP 密钥。
- WireGuard/OpenVPN 已做真实数据面往返，本计划补齐 IPsec 的 ESP 数据面。

## 二、密码学（真实）

- ESP 载荷：AES-256-GCM，nonce = `seq(4,BE)‖0x00*8`，关联数据 AD = `SPI(4)‖seq(4)`。
- 重放防护：`seq <= highest_recv_seq` 拒绝。
- ESP 密钥：从 IKE 握手密钥集派生 `ESP_KEY = HKDF-SHA256(加密密钥, info="IPsec ESP KEYMAT")`
  （教学简化替代 IKEv2 CHILD_SA KEYMAT / IKEv1 Quick Mode KEYMAT，明示）。

## 三、报文格式（RFC 4303 教学简化）

```
ESP 报文: SPI(4,BE) | Sequence Number(4,BE) | ciphertext+tag(AES-256-GCM)
```

加密明文为原始 payload（教学简化，不含显式 padding/next-header）。

## 四、分阶段任务

### P1 — ESP 报文 + 密钥派生

- 新增 `plugins/protocols/ipsec/esp.py`：`build_esp_packet` / `parse_esp_packet` /
  `ESPSession`（seal/open + 重放防护）。
- `plugins/protocols/ikev2/crypto.py` 与 `plugins/protocols/ipsec/crypto.py` 各加
  `derive_esp_key(加密密钥)`。

### P2 — ESP 收发编排 + 接入 validation

- 新增 `services/esp_transport.py`：`ESPTransport(socket, session, local_spi, peer_spi)`。
- `IKEv2Handshake.esp_key()` / `IPsecHandshake.esp_key()` 暴露派生 ESP 密钥。
- `validation.py`：ikev2/ipsec 的 tunnel 步骤做真实 ESP 往返（`_run_X_handshake_and_esp`）。

### P3 — 测试 + 文档

- `tests/unit/test_esp.py`：seal/open 往返、篡改/坏密钥/重放拒绝。
- `tests/integration/test_esp_flow.py`：IKE 握手后 ESP 数据面往返。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- ikev2/ipsec 的 tunnel 步骤为真实 ESP 数据面往返。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `8a8505b` | `ipsec/esp.py`（AES-256-GCM ESP 报文 + 重放防护）+ ikev2/ipsec crypto 加 `derive_esp_key` |
| P2 | `d8b1849` | `services/esp_transport.py` + `esp_key()` 方法 + validation ikev2/ipsec tunnel 改真实 ESP 往返 |
| P3 | 本提交 | 单元/集成测试（6+2 条）+ README 同步 |

最终指标：后端 1279 tests 通过、81.7% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

