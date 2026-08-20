# VPN Simulator v2 — PPP LCP/IPCP 控制协商计划 v18

> 承接 `PLAN_ENHANCEMENT_V17.md`（MS-CHAPv2 已覆盖 l2tp/pptp/sstp/openconnect）。
> 本计划把 PPP 的 LCP（RFC 1661）与 IPCP（RFC 1332）链路/网络控制协商真实化，
> 接入 SSTP 握手：CALL_CONNECTED 后走真实 LCP Configure-Request/Ack 与
> IPCP Configure-Request/Ack（在 TLS 流上），替换 `SSTPHandshake` 里合成的
> `LCP_NEGOTIATION_COMPLETE` / `IPCP_NEGOTIATION_COMPLETE` 触发。

## 一、背景与现状

- `SSTPHandshake.respond()` 当前在 CALL_CONNECTED 后合成触发 LCP/AUTH/IPCP 完成。
- PPP 的 LCP（RFC 1661）与 IPCP（RFC 1332）共用同一控制帧格式：
  `Code(1) | Identifier(1) | Length(2) | Data(Length-4)`。
- LCP 选项：MRU（type 1，4 字节）；IPCP 选项：IP-Address（type 3，6 字节）。

## 二、报文格式（RFC 1661 / RFC 1332 教学简化）

```
Configure-Request: Code=1 | Identifier | Length | Options
Configure-Ack    : Code=2 | Identifier | Length | Options(回显)
LCP  MRU 选项    : type=1 | len=4 | MRU(2)
IPCP IP-Address  : type=3 | len=6 | IP(4)
```

## 三、分阶段任务

### P1 — LCP/IPCP 帧

新增 `plugins/protocols/ppp/control.py`：`build_configure_request` / `build_configure_ack` /
`parse_frame` + LCP MRU / IPCP IP-Address 选项构造。

### P2 — 接入 SSTP 握手

`sstp_handshake.py`：客户端 `initiate()` 在 CALL_CONNECT_ACK 后发 LCP/IPCP
Configure-Request 并校验 Ack；服务端 `respond()` 收 Request、回 Ack，并触发
`LCP_NEGOTIATION_COMPLETE` / `IPCP_NEGOTIATION_COMPLETE`（AUTH 仍合成，MS-CHAPv2
在 validation 层）。

### P3 — 测试 + 文档

- `tests/unit/test_ppp_control.py`：LCP/IPCP 帧往返、坏长度拒绝。
- `tests/integration/test_sstp_handshake.py`：端到端状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- SSTP 握手在 CALL_CONNECTED 后走真实 LCP/IPCP 协商。
- 每功能独立提交并推送到 `origin/main`。

## 五、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。SSTP 握手路径现为：
真实 TLS → CALL_CONNECT → 真实 LCP Configure-Request/Ack → MS-CHAPv2（validation 层）
→ 真实 IPCP Configure-Request/Ack。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `8435abf` | `ppp/control.py`：LCP/IPCP Configure-Request/Ack framing + MRU/IP 选项 + 单元测试 |
| P2 | `cbc2e69` | `sstp_handshake.py`：CALL_CONNECTED 后真实 LCP/IPCP 协商（替换合成触发） |
| P3 | 本提交 | README 同步 |

最终指标：后端 1328 tests 通过、82.2% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

