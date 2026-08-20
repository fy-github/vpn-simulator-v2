# VPN Simulator v2 — PPTP 真实握手仿真计划 v9

> 承接 `PLAN_ENHANCEMENT_V8.md`（L2TP 握手已闭环）。本计划把 PPTP 的**控制面握手**
> 真实化：在 TCP 1723 上完成 Start-Control-Connection-Request/Reply 与
> Outgoing-Call-Request/Reply 两阶段交换（真实 magic cookie + 真实消息类型），驱动
> `PPTPStateMachine` 到 CONNECTED，闭合 validation 中 pptp 的「真实握手待接入」缺口
> （也是最后一个未接入的 validation 协议）。

## 一、背景与现状

- PPTP 插件已有状态机（`PPTPStateMachine`，服务器视角）：INITIAL → WAIT_SCCRQ →
  SCCRP_SENT → WAIT_OCRQ → OCRP_SENT → GRE_ESTABLISHED → LCP_NEGOTIATION →
  AUTHENTICATION → IPCP_NEGOTIATION → CONNECTED，事件 START/RECEIVE_SCCRQ/
  SCCRP_SENT_OK/RECEIVE_OCRQ/GRE_READY/START_LCP/LCP_COMPLETE/AUTH_SUCCESS/IPCP_COMPLETE。
- 无真实报文握手（`validation.py` 中 pptp 仍为 skip）。PPTP 控制信道走 **TCP**（1723），
  本计划用 asyncio 流（stream）直接实现，不扩展现有 `UdpSocket`。

## 二、协议特性（PPTP 控制信道为明文，如实体现）

- PPTP 控制信道无加密（RFC 2637，明文控制 + GRE 数据），认证在 PPP 层的 MS-CHAPv2。
  本计划只做控制面握手（SCCRQ/SCCRP + OCRQ/OCRP），如实体现明文字段；MS-CHAPv2
  认证与 PPP LCP/IPCP 协商不实现（明示，状态机相应阶段以真实控制握手结果驱动到 CONNECTED）。

## 三、报文格式（教学简化版）

```
控制报文: length(2,BE) | message_type(2,BE)=1 | magic_cookie(4,BE)=0x1A2B3C4D
          | control_type(2,BE) | reserved(2)=0 | body
SCCRQ(1) body: protocol_version(2)=0x0100
SCCRP(2) body: protocol_version(2) | result_code(1)=1 | error_code(1)=0
OCRQ(7)  body: call_id(2,BE) | call_serial(2,BE)
OCRP(8)  body: call_id(2,BE) | peer_call_id(2,BE) | result_code(1)=1
```

消息类型取 RFC 2637 值：SCCRQ=1、SCCRP=2、OCRQ=7、OCRP=8。

## 四、分阶段任务

### P1 — PPTP 控制报文

新增 `plugins/protocols/pptp/control.py`：控制报文 framing（长度/magic cookie/
消息类型）+ SCCRQ/SCCRP/OCRQ/OCRP build/parse + TCP 流读取辅助。

### P2 — 握手编排 + 接入 validation

新增 `services/pptp_handshake.py`：`PPTPHandshake.initiate()/respond()` 基于 asyncio
流执行 SCCRQ/SCCRP + OCRQ/OCRP，驱动 `PPTPStateMachine` 到 CONNECTED。
`validation.py`：pptp 分支走真实握手（TCP 控制连接，handshake/tunnel/latency）。

### P3 — 测试 + 文档

- `tests/unit/test_pptp_control.py`：报文往返、坏长度/坏 cookie/坏类型拒绝。
- `tests/integration/test_pptp_handshake.py`：端到端 TCP 握手 + 状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("pptp")` 的 handshake/tunnel/latency 为真实握手结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。至此 **6 个 validation 协议
（wireguard/openvpn/ikev2/ipsec/l2tp/pptp）全部接入真实控制面握手**。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `20c3afa` | `control.py`：控制报文 framing（length/magic cookie/消息类型）+ SCCRQ/SCCRP/OCRQ/OCRP |
| P2 | `5d9baa8` | `services/pptp_handshake.py`（TCP 流）+ `validation.py` pptp 真实握手 + 更新旧 skip 测试 |
| P3 | 本提交 | 单元/集成测试（8+1 条）+ README 同步 |

最终指标：后端 1271 tests 通过、81.6% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

