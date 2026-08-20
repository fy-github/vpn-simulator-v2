# VPN Simulator v2 — IKEv1/IPSec 真实握手仿真计划 v7

> 承接 `PLAN_ENHANCEMENT_V6.md`（IKEv2 握手已闭环）。本计划把 IKEv1/IPSec 的
> **控制面握手**真实化：用真实密码学（X25519 DH + HKDF-SHA256 + ChaCha20-Poly1305
> + HMAC-SHA256）完成 Phase 1 Main Mode（6 消息）与 Phase 2 Quick Mode（3 消息），
> 驱动 `IPsecStateMachine` 到 CONNECTED，闭合 validation 中 ipsec 的「真实握手待接入」。

## 一、背景与现状

- IPSec 插件已有 Main Mode + Quick Mode 状态机（`IPsecStateMachine`），事件：
  SEND/RECEIVE_PHASE1_SA、SEND/RECEIVE_PHASE1_KE、SEND/RECEIVE_PHASE1_AUTH、
  SEND/RECEIVE_PHASE2_HASH、SEND_PHASE2_ACK、ESP_SA_READY、TUNNEL_ESTABLISHED。
- 无真实报文握手（`validation.py` 中 ipsec 仍为 skip）。

## 二、密码学（全部真实，DH 组教学简化）

- DH：X25519（教学简化，替代 IKEv1 传统 MODP 组，明示）。
- PRF：HKDF-SHA256——`SKEYID = HKDF(psk, salt=Ni‖Nr)`，再派生 `SKEYID_a`（认证）、
  `SKEYID_e`（加密）。
- 认证：`HASH = HMAC-SHA256(SKEYID, KE_i‖KE_r‖Ni‖Nr‖ID)`（教学简化 PSK 认证，明示）。
- Phase 1 消息 5/6 加密：ChaCha20-Poly1305，nonce = `msgid(4,LE)‖方向(4,LE)‖0x00*4`
  （方向位避免对称密钥 nonce 复用）。

## 三、报文格式（教学简化版）

```
头部: cookie_i(8) | cookie_r(8) | exchange(1) | flags(1) | msgid(4)   # 22B
Main Mode(2) msg1(I): 头部 + SA_placeholder(4)
            msg2(R): 头部 + SA_placeholder(4)
            msg3(I): 头部 + KE_i(32) + Nonce_i(32)
            msg4(R): 头部 + KE_r(32) + Nonce_r(32)
            msg5(I): 头部 + AEAD(ID_i + HASH_I)
            msg6(R): 头部 + AEAD(ID_r + HASH_R)
Quick Mode(32) qm1(I): 头部(msgid=1) + HASH1(32) + Nonce2_i(32)
            qm2(R): 头部(msgid=1) + HASH2(32) + Nonce2_r(32)
            qm3(I): 头部(msgid=1) + HASH3(32)
```

## 四、分阶段任务

### P1 — IKEv1 密码学与报文格式

新增 `plugins/protocols/ipsec/crypto.py`：cookie/PSK/nonce/临时密钥生成、
X25519 DH、`derive_key_set`（SKEYID/SKEYID_a/SKEYID_e）、Main Mode/Quick Mode
报文 build/parse、HASH 认证、msg5/6 的 AEAD 加解密。

### P2 — 握手编排 + 接入 validation

新增 `services/ipsec_handshake.py`：`IPsecHandshake.initiate()/respond()` 执行
Main Mode + Quick Mode，驱动 `IPsecStateMachine` 到 CONNECTED。`validation.py`：
ipsec 分支走真实握手（handshake/tunnel/latency）。

### P3 — 测试 + 文档

- `tests/unit/test_ipsec_crypto.py`：密钥派生、报文往返、篡改/坏 AUTH/坏长度拒绝。
- `tests/integration/test_ipsec_handshake.py`：端到端握手 + 状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("ipsec")` 的 handshake/tunnel/latency 为真实握手结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `bfcb0ca` | `crypto.py`：X25519 DH + HKDF 密钥派生 + Main Mode/Quick Mode 报文 + AEAD + HMAC HASH |
| P2 | `4eb6707` | `services/ipsec_handshake.py` + `validation.py` ipsec 真实握手（驱动状态机到 CONNECTED） |
| P3 | 本提交 | 单元/集成测试（14+2 条）+ README 同步 |

最终指标：后端 1253 tests 通过、81.3% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

