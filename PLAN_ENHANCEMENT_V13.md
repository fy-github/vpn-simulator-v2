# VPN Simulator v2 — SSTP 真实 TLS 握手仿真计划 v13

> 承接 `PLAN_ENHANCEMENT_V12.md`（6 个 validation 协议控制面 + 数据面全部真实）。
> 本计划把第 7 个协议 **SSTP** 纳入 validation，并真实化其 TLS 握手：在 TCP 443 上
> 完成真实 TLS 握手（自签名 ECDSA 证书）+ SSTP 控制协商（CALL_CONNECT_REQUEST/ACK），
> 驱动 `SSTPStateMachine` 到 CONNECTED。这是首个真实 TLS 的 VPN 协议接入。

## 一、背景与现状

- SSTP 插件已有状态机（`SSTPStateMachine`，服务器视角）：INITIAL → TLS_HANDSHAKE →
  SSTP_NEGOTIATION → PPP_LCP → PPP_AUTH → PPP_IPCP → CONNECTED，事件 TCP_CONNECTED/
  TLS_HANDSHAKE_COMPLETE/SSTP_CALL_CONNECTED/LCP_NEGOTIATION_COMPLETE/AUTHENTICATION_SUCCESS/
  IPCP_NEGOTIATION_COMPLETE。
- SSTP 协议栈：TCP(443) → TLS → SSTP 控制 → PPP。本计划实现 TCP + 真实 TLS + SSTP
  控制（CALL_CONNECT），PPP LCP/IPCP/MSCHAPv2 不实现（明示，如实体现）。
- SSTP 为 Microsoft 专有协议（MS-SSTP），报文头为教学简化。

## 二、密码学（真实）

- TLS 1.2/1.3 握手（Python `ssl`），自签名 ECDSA P-256 证书（`cryptography` 运行时生成）。
- 客户端 `verify_mode=CERT_NONE`（教学模拟器不自建 CA，明示）。

## 三、报文格式（MS-SSTP 教学简化）

```
SSTP 控制报文: version_c(1B)=0x11 | message_type(2B,BE) | length(2B,BE) | payload
```

消息类型：CALL_CONNECT_REQUEST=0x0001、CALL_CONNECT_ACK=0x0002、CALL_CONNECT_NAK=0x0003、
CALL_CONNECTED=0x0004（教学简化，payload 为空）。

## 四、分阶段任务

### P1 — TLS 上下文 + SSTP 控制报文

- 新增 `plugins/protocols/sstp/tls.py`：`generate_self_signed_cert` / `create_tls_contexts`。
- 新增 `plugins/protocols/sstp/control.py`：`build_sstp_message` / `parse_sstp_message`。

### P2 — SSTP 握手编排 + 接入 validation

- 新增 `services/sstp_handshake.py`：`SSTPHandshake.initiate()/respond()`（TLS 流 +
  CALL_CONNECT 交换 + 状态机）。
- `validation.py`：SUPPORTED_PROTOCOLS/_AUTH_FIELDS/_DEFAULT_PORTS 加 sstp，
  sstp 分支走真实 TLS 握手（`_run_sstp_handshake`）。

### P3 — 测试 + 文档

- `tests/unit/test_sstp_control.py`：报文往返、坏长度/坏版本拒绝。
- `tests/integration/test_sstp_handshake.py`：端到端 TLS + CALL_CONNECT，状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("sstp")` 的 handshake/tunnel/latency 为真实 TLS 握手结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。SSTP 成为第 7 个（也是首个
真实 TLS 的）validation 协议。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `c767035` | `sstp/tls.py`（自签名 ECDSA 证书 + TLS 上下文）+ `sstp/control.py`（MS-SSTP 报文） |
| P2 | `92bb1a9` | `services/sstp_handshake.py`（TLS 流 + CALL_CONNECT + 状态机）+ validation 接入 |
| P3 | 本提交 | 单元/集成测试（7+1 条）+ README 同步 + batch 测试数更新 |

最终指标：后端 1299 tests 通过、81.9% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

