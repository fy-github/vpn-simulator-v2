# VPN Simulator v2 — WireGuard 数据面真实报文仿真计划 v4

> 承接 `PLAN_ENHANCEMENT_V3.md`（控制面/握手层已真实化：WireGuard Noise_IKpsk2
> 握手、OpenVPN 控制信道 `--tls-auth` HMAC），本计划把 WireGuard 推进到**数据面**：
> 用握手已派生的传输密钥真实加解密数据报文（ChaCha20-Poly1305），并做真实加密
> 往返，完成「真实报文仿真」在 WireGuard 上的闭环。

## 一、背景与现状

- WireGuard 握手（Noise_IKpsk2）已真实实现，`finish_initiator`/`finish_responder`
  已派生传输密钥（`initiator→responder` 与 `responder→initiator` 各一把），但
  `crypto.py` 明确「不提供数据面转发」。
- 数据面缺失三件套：`MSG_TYPE_DATA(4)` 报文格式、ChaCha20-Poly1305 加解密、
  counter 重放防护。
- `validation.py` 的 WireGuard「tunnel」步骤目前只断言「传输密钥已派生」，未做
  真实数据往返。

## 二、范围总览（P1–P3）

| 阶段 | 主题 | 交付 |
|------|------|------|
| P1 | 数据面报文格式 + 加解密 | `transport.py`：`MSG_TYPE_DATA`、ChaCha20-Poly1305 seal/open、counter 重放防护 |
| P2 | 数据面真实往返编排 | `services/wireguard_transport.py`：seal→send→recv→open 双向；接入 `validation.py` 的 tunnel 步骤 |
| P3 | 测试 + 文档 | 单元测试 + 握手→数据面端到端集成测试；README 同步 |

## 三、数据面报文格式（WireGuard 白皮书 §5.4.4）

```
type(4, LE, =4) | receiver_index(4, LE) | counter(8, LE) | ciphertext+tag(ChaCha20-Poly1305)
```

- AEAD：ChaCha20-Poly1305，nonce = `counter(8, LE) || 0x00000000`（12 字节）。
- 关联数据（AD）为空；密文尾部附 16 字节认证标签。
- 重放防护：接收方拒绝 `counter <= 已见最大 counter`（单调递增简化，滑动位图
  窗口留作后续增强）。

## 四、分阶段任务

### P1 — 数据面报文格式 + 加解密

新增 `plugins/protocols/wireguard/transport.py`：

- 常量 `MSG_TYPE_DATA = 4`；`_nonce(counter)` 生成 12 字节 nonce。
- 纯函数 `build_data_packet(send_key, receiver_index, counter, plaintext)` /
  `parse_data_packet(recv_key, raw) -> (receiver_index, counter, plaintext)`。
- `WireGuardTransportSession`：持有 `send_key`/`recv_key`，`seal()` 递增
  `send_counter`，`open()` 校验重放（`counter <= highest_recv_counter` 抛
  `ValueError`）。

### P2 — 数据面真实往返编排

新增 `services/wireguard_transport.py`：

- `WireGuardTransport`：绑定 `UdpSocket` + `WireGuardTransportSession`，提供
  `send_data(peer_addr, plaintext)`（seal→sendto）与 `recv_data(timeout)`
  （recvfrom→open，并校验 `receiver_index` 匹配本端 index）。
- `validation.py`：WireGuard「tunnel」步骤改为真实数据往返——握手拿到两把密钥后，
  发起方 seal 一段测试载荷→发送→响应方 open→校验→seal 应答→发起方 open→校验。

### P3 — 测试 + 文档

- `tests/unit/test_wireguard_transport.py`：seal/open 往返、篡改密文解密失败、
  counter 重放拒绝、坏长度/坏类型拒绝。
- `tests/integration/test_wireguard_transport_flow.py`：握手 + 数据面加密往返
  （环回 UDP），断言明文一致、双向可通、重放被拒。
- `README.md`：测试数/特性表同步；WireGuard 数据面真测说明。

## 五、验收

- 后端 pytest 全绿（含新增 transport 单元/集成测试）；mypy/ruff/black 全绿。
- WireGuard `validate()` 的 tunnel 步骤为真实数据面往返（非「密钥已派生」占位）。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `674d072` | `transport.py`：`MSG_TYPE_DATA` + ChaCha20-Poly1305 seal/open + counter 重放防护 |
| P2 | `3706a5a` | `services/wireguard_transport.py` + `validation.py` tunnel 步骤真实数据往返 |
| P3 | 本提交 | 单元/集成测试（9+2 条）+ README 同步 |

最终指标：后端 1209 tests 通过、80.6% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

