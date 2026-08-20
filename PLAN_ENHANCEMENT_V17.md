# VPN Simulator v2 — SSTP / OpenConnect 接入 MS-CHAPv2 认证计划 v17

> 承接 `PLAN_ENHANCEMENT_V16.md`（MS-CHAPv2 已接入 l2tp/pptp）。本计划把 MS-CHAPv2
> 认证扩展到另外两个承载 PPP 的协议：**SSTP** 与 **OpenConnect**，替换其隧道步骤里
> 的「PPP 认证待接入」占位，复用 `_run_mschapv2_auth` 助手。

## 一、背景与现状

- V16 已实现 `plugins/protocols/ppp/mschapv2.py`（MD4/SHA1/3×DES）与
  `_run_mschapv2_auth` 助手，并接入 l2tp/pptp。
- sstp 隧道步骤消息仍为「SSTP TLS 隧道与 CALL_CONNECTED 已建立（PPP 认证待接入）」；
  openconnect 为「OpenConnect TLS/CSTP 隧道已建立（DTLS 与 PPP 认证待接入）」。
- 二者握手后即承载 PPP，应在真实 TLS 握手成功后追加一次真实 MS-CHAPv2 挑战-响应。

## 二、分阶段任务

### P1 — 接入 sstp / openconnect 隧道步骤

`validation.py`：sstp 与 openconnect 分支在握手成功后调用 `_run_mschapv2_auth`，
隧道步骤成功条件改为「握手成功 AND MS-CHAPv2」，消息更新为
「SSTP TLS 隧道 + MS-CHAPv2 认证成功」/「OpenConnect TLS/CSTP 隧道 + MS-CHAPv2 认证成功」。

### P2 — 测试 + 文档

- `tests/unit/test_validation_service.py`：断言 sstp/openconnect 隧道消息含
  「MS-CHAPv2 认证成功」。
- `README.md`：测试数/特性说明同步。

## 三、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- sstp / openconnect 的 tunnel 步骤为「真实 TLS 握手 + 真实 MS-CHAPv2」。
- 每功能独立提交并推送到 `origin/main`。

## 四、完成状态

全部阶段（P1–P2）已实现、测试并推送到 `origin/main`。MS-CHAPv2 现已覆盖全部四个
承载 PPP 的协议（l2tp / pptp / sstp / openconnect）。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `1bd7b7c` | `validation.py` sstp/openconnect 隧道步骤接入 `_run_mschapv2_auth` + 测试断言 |
| P2 | 本提交 | README 同步 |

最终指标：后端 1322 tests 通过、82.2% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

