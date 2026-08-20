# VPN Simulator v2 — L2TP 真实握手仿真计划 v8

> 承接 `PLAN_ENHANCEMENT_V7.md`（IKEv1/IPSec 握手已闭环）。本计划把 L2TP 的
> **控制面握手**真实化：在 UDP 1701 上完成 SCCRQ→SCCRP→SCCCN（控制连接）与
> ICRQ→ICRP→ICCN（会话）两阶段交换，含**真实隧道认证**（共享密钥 + HMAC-SHA256
> challenge-response），驱动 `L2TPStateMachine` 到 CONNECTED，闭合 validation 中
> l2tp 的「真实握手待接入」缺口。

## 一、背景与现状

- L2TP 插件已有状态机（`L2TPStateMachine`，服务器视角）：INITIAL → WAIT_SCCRQ →
  SCCRP_SENT → SCCCN_RECEIVED → ICRP_SENT → ICCN_RECEIVED → PPP_NEGOTIATION →
  CONNECTED，事件 START/RECEIVE_SCCRQ/RECEIVE_SCCCN/RECEIVE_ICRQ/RECEIVE_ICCN/
  START_PPP/PPP_COMPLETE。
- 无真实报文握手（`validation.py` 中 l2tp 仍为 skip）。L2TP 走 UDP，可复用
  `UdpSocket`。

## 二、密码学（隧道认证真实）

- 隧道认证：SCCRQ 携带 16 字节随机 challenge；SCCRP 携带
  `HMAC-SHA256(共享密钥, challenge || tunnel_id)` 的 challenge response；客户端
  校验（真实 HMAC，教学简化替代 RFC 2661 的 MD5 方案，明示）。
- 无 DH/加密（L2TP 本身无加密，PPP 层才有，本计划不实现 PPP 加密）。

## 三、报文格式（教学简化版）

```
头部: version_flags(2) | tunnel_id(2,BE) | session_id(2,BE) | ns(2,BE) | nr(2,BE)
      | message_type(2,BE)     # 12B
SCCRQ(1)  载荷: challenge(16) | assigned_tunnel_id(2)
SCCRP(2)  载荷: challenge_response(32) | assigned_tunnel_id(2)
SCCCN(4)  载荷: (空)
ICRQ(10)  载荷: assigned_session_id(2)
ICRP(11)  载荷: assigned_session_id(2)
ICCN(12)  载荷: (空)
```

消息类型取 RFC 2661 值：SCCRQ=1、SCCRP=2、SCCCN=4、ICRQ=10、ICRP=11、ICCN=12。

## 四、分阶段任务

### P1 — L2TP 控制报文 + 隧道认证

新增 `plugins/protocols/l2tp/control.py`：challenge/响应生成、HMAC 隧道认证、
控制报文 build/parse。

### P2 — 握手编排 + 接入 validation

新增 `services/l2tp_handshake.py`：`L2TPHandshake.initiate()/respond()` 执行
SCCRQ/SCCRP/SCCCN + ICRQ/ICRP/ICCN，驱动 `L2TPStateMachine` 到 CONNECTED。
`validation.py`：l2tp 分支走真实握手（handshake/tunnel/latency）。

### P3 — 测试 + 文档

- `tests/unit/test_l2tp_control.py`：认证、报文往返、篡改/坏响应拒绝。
- `tests/integration/test_l2tp_handshake.py`：端到端握手 + 状态机到 CONNECTED。
- `README.md`：测试数/特性说明同步。

## 五、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("l2tp")` 的 handshake/tunnel/latency 为真实握手结果。
- 每功能独立提交并推送到 `origin/main`。

## 六、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `4ad0eb6` | `control.py`：控制报文 framing + HMAC-SHA256 隧道认证（challenge-response） |
| P2 | `3788e11` | `services/l2tp_handshake.py` + `validation.py` l2tp 真实握手（驱动状态机到 CONNECTED） |
| P3 | 本提交 | 单元/集成测试（7+2 条）+ README 同步 |

最终指标：后端 1262 tests 通过、81.5% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

