# VPN Simulator v2 — OpenConnect 接入 PPP LCP/IPCP 协商计划 v19

> 承接 `PLAN_ENHANCEMENT_V18.md`（SSTP 已接入真实 LCP/IPCP）。本计划把同一套真实
> LCP/IPCP 协商（`ppp/control.py`）接入 OpenConnect 握手，替换其合成的
> `LCP_NEGOTIATION_COMPLETE` / `IPCP_NEGOTIATION_COMPLETE` 触发。

## 一、背景与现状

- OpenConnect 状态机：CSTP_NEGOTIATION_COMPLETE → DTLS_HANDSHAKE → DTLS_SKIPPED →
  PPP_LCP → PPP_AUTH → PPP_IPCP → CONNECTED。
- `OpenConnectHandshake.respond()` 当前合成触发 LCP/AUTH/IPCP；复用 V18 的
  `ppp/control.py` 帧 + 客户端/服务端 LCP/IPCP 交换。

## 二、分阶段任务

### P1 — 接入 OpenConnect 握手

`openconnect_handshake.py`：客户端 `initiate()` 在 CSTP CONNECT 后做 LCP/IPCP
Configure-Request/Ack；服务端 `respond()` 在 DTLS_SKIPPED 后收 LCP Request、回 Ack、
触发 LCP/AUTH/IPCP（真实 LCP/IPCP，AUTH 合成）。

### P2 — 测试 + 文档

- `tests/integration/test_openconnect_handshake.py`：状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 三、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- OpenConnect 握手在 CSTP CONNECT 后走真实 LCP/IPCP。
- 每功能独立提交并推送到 `origin/main`。

## 四、完成状态

全部阶段（P1–P2）已实现、测试并推送到 `origin/main`。OpenConnect 握手路径现为：
真实 TLS → CSTP CONNECT → DTLS_SKIPPED → 真实 LCP Configure-Request/Ack → MS-CHAPv2
（validation 层）→ 真实 IPCP Configure-Request/Ack。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `2a82644` | `openconnect_handshake.py`：CSTP CONNECT 后真实 LCP/IPCP 协商（替换合成触发） |
| P2 | 本提交 | README 同步 |

至此 PPP 协议栈（LCP → MS-CHAPv2 → IPCP）在两个 TLS 承载协议（SSTP / OpenConnect）
上均真实化。最终指标：后端 1328 tests 通过、82.2% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

