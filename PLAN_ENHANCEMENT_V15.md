# VPN Simulator v2 — OpenConnect (AnyConnect) 真实 TLS + CSTP 握手仿真计划 v15

> 承接 `PLAN_ENHANCEMENT_V14.md`（VXLAN 数据面已闭环）。本计划把最后一个插件协议
> **OpenConnect（AnyConnect）** 纳入 validation，真实化其握手：在 TCP 443 上完成
> 真实 TLS 握手（复用自签名 ECDSA 证书）+ CSTP HTTP CONNECT 隧道协商（X-CSTP-*），
> 驱动 `OpenConnectStateMachine` 到 CONNECTED。至此 9 个协议插件全部接入 validation。

## 一、背景与现状

- OpenConnect 插件已有状态机（`OpenConnectStateMachine`，服务器视角）：INITIAL →
  TLS_HANDSHAKE → CSTP_NEGOTIATION → DTLS_HANDSHAKE → PPP_LCP → PPP_AUTH →
  PPP_IPCP → CONNECTED，事件 TCP_CONNECTED/TLS_HANDSHAKE_COMPLETE/
  CSTP_NEGOTIATION_COMPLETE/DTLS_HANDSHAKE_COMPLETE/DTLS_SKIPPED/
  LCP_NEGOTIATION_COMPLETE/AUTHENTICATION_SUCCESS/IPCP_NEGOTIATION_COMPLETE。
- 协议栈：TCP(443) → TLS → CSTP（HTTP CONNECT + X-CSTP-*）→ PPP；可选 DTLS 数据通道。
  本计划实现 TCP + 真实 TLS + CSTP 协商，DTLS 与 PPP LCP/IPCP/MSCHAPv2 不实现
  （明示，DTLS 走 DTLS_SKIPPED）。

## 二、密码学（真实）

- TLS 1.2/1.3 握手（Python `ssl`），复用 `sstp/tls.py` 的自签名 ECDSA 证书助手。

## 三、CSTP 协商（AnyConnect 教学简化）

```
客户端: CONNECT /CSCOSSLC/tunnel HTTP/1.1
        Host: vpn-simulator.test
        X-CSTP-Version: 1
        X-CSTP-MTU: 1400

服务端: HTTP/1.1 200 CONNECTED
        X-CSTP-Version: 1
        X-CSTP-MTU: 1400
        Content-Length: 0
```

HTTP 头以 ``\\r\\n\\r\\n`` 结束；基于真实 AnyConnect CSTP 的 CONNECT 协商。

## 四、分阶段任务

### P1 — CSTP 报文

新增 `plugins/protocols/openconnect/cstp.py`：`build_connect_request` /
`parse_connect_request` / `build_connect_response` / `parse_connect_response`。

### P2 — 握手编排 + 接入 validation

新增 `services/openconnect_handshake.py`：`OpenConnectHandshake.initiate()/respond()`
（TLS 流 + CSTP CONNECT + 状态机，DTLS_SKIPPED）。
`validation.py`：SUPPORTED_PROTOCOLS/_AUTH_FIELDS/_DEFAULT_PORTS(443) 加 openconnect，
分支走真实 TLS + CSTP（`_run_openconnect_handshake`）。

### P3 — 测试 + 文档

- `tests/unit/test_openconnect_cstp.py`：请求/响应往返、坏状态码/坏版本拒绝。
- `tests/integration/test_openconnect_handshake.py`：端到端 TLS + CSTP，状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("openconnect")` 的 handshake/tunnel/latency 为真实 TLS + CSTP 结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。OpenConnect 成为第 9 个（也是
最后一个）validation 协议，**9 个协议插件全部接入 validation**。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `8fcfae6` | `openconnect/cstp.py`：CSTP CONNECT 请求/响应 framing（X-CSTP-*） |
| P2 | `b8b7c9c` | `services/openconnect_handshake.py`（TLS + CSTP + 状态机）+ validation 接入 + batch 测试数更新 |
| P3 | 本提交 | 单元/集成测试（5+1 条）+ README 同步 |

最终指标：后端 1311 tests 通过、82.1% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

