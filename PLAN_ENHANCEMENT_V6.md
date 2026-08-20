# VPN Simulator v2 — IKEv2/IPSec 真实握手仿真计划 v6

> 承接 `PLAN_ENHANCEMENT_V5.md`（OpenVPN 数据面已闭环）。本计划把 IKEv2/IPSec
> 的**控制面握手**真实化：用真实密码学（X25519 DH + HKDF-SHA256 + ChaCha20-Poly1305
> + HMAC-SHA256）完成 IKE_SA_INIT → IKE_AUTH 两阶段交换，驱动 IKEv2 状态机到
> CONNECTED，闭合 validation 中 ikev2 的「真实握手待接入」缺口。

## 一、背景与现状

- IKEv2 插件已有完整状态机（`IKEv2StateMachine`）：INITIAL → IKE_SA_INIT_SENT →
  IKE_SA_INIT_COMPLETE → IKE_AUTH_SENT → IKE_AUTH_COMPLETE → CHILD_SA_ESTABLISHED →
  CONNECTED，但无真实报文握手（`validation.py` 中 ikev2 仍为 skip）。
- 与 WireGuard/OpenVPN 同属「控制面/握手层」边界：本计划做真实握手与密钥协商，
  不做 ESP 数据面转发。

## 二、密码学（全部真实）

- DH：X25519（Curve25519）。
- 密钥派生：HKDF-SHA256——`SKEYSEED = HKDF(salt=Ni||Nr, ikm=DH_shared)`，再派生
  `SK_ei/SK_er`（加密）、`SK_ai/SK_ar`（完整性）、`SK_pi`（PSK AUTH）。
- IKE_AUTH 加密：ChaCha20-Poly1305（AEAD），nonce = `msgid(4,LE)||0x00*8`。
- AUTH：HMAC-SHA256(SK_pi, identity)——教学简化的 PSK 认证（明示）。

## 三、报文格式（教学简化版）

```
头部: spi_i(8) | spi_r(8) | version(1)=0x20 | exchange(1) | flags(1) | msgid(4)
IKE_SA_INIT(34) 请求: 头部 + KE_i(32) + Nonce_i(32)         # spi_r 为 0
IKE_SA_INIT(34) 响应: 头部 + KE_r(32) + Nonce_r(32)
IKE_AUTH(35)   请求: 头部 + ciphertext+tag(AEAD)            # 明文=identity+AUTH
IKE_AUTH(35)   响应: 头部 + ciphertext+tag(AEAD)
```

## 四、分阶段任务

### P1 — IKEv2 密码学与报文格式

新增 `plugins/protocols/ikev2/crypto.py`：

- `generate_spi()` / `generate_ephemeral()` / `generate_nonce()`。
- `derive_key_set(shared, nonce_i, nonce_r) -> IKEv2KeySet`（HKDF-SHA256）。
- `build_ike_sa_init(...)` / `parse_ike_sa_init(...)`、
  `build_ike_auth(...)` / `parse_ike_auth(...)`（AEAD + HMAC AUTH 校验）。

### P2 — 握手编排 + 接入 validation

新增 `services/ikev2_handshake.py`：`IKEv2Handshake` 的 `initiate()` / `respond()`
在 UDP 套接字上执行 IKE_SA_INIT → IKE_AUTH 交换，驱动 `IKEv2StateMachine` 到
CONNECTED。`validation.py`：ikev2 分支走真实握手（handshake/tunnel/latency）。

### P3 — 测试 + 文档

- `tests/unit/test_ikev2_crypto.py`：密钥派生、报文往返、篡改/坏长度/坏 AUTH 拒绝。
- `tests/integration/test_ikev2_handshake.py`：真实握手端到端 + 状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("ikev2")` 的 handshake/tunnel/latency 为真实握手结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `4bbb88e` | `crypto.py`：X25519 DH + HKDF-SHA256 密钥派生 + IKE_SA_INIT/IKE_AUTH 报文 + ChaCha20-Poly1305 + HMAC AUTH |
| P2 | `fa7309c` | `services/ikev2_handshake.py` + `validation.py` ikev2 真实握手（驱动状态机到 CONNECTED） |
| P3 | 本提交 | 单元/集成测试（14+2 条）+ README 同步 |

最终指标：后端 1237 tests 通过、81.0% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

