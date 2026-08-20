# VPN Simulator v2 — L2TP 数据面仿真计划 v12

> 承接 `PLAN_ENHANCEMENT_V11.md`（PPTP GRE 数据面已闭环）。本计划把 L2TP 的
> **数据面**真实化：在控制握手（SCCRQ/SCCRP/SCCCN + ICRQ/ICRP/ICCN + HMAC 隧道认证）
> 建立后，用真实 L2TP 数据报文（RFC 2661，T=0 数据消息 + tunnel_id + session_id）
> 做数据面往返，替换「PPP 数据面待接入」占位，使 l2tp 的 tunnel 步骤升级为真实
> L2TP 数据往返。至此 6 个 validation 协议全部具备真实数据面。

## 一、背景与现状

- `validation.py` 的 l2tp tunnel 步骤现为「L2TP 隧道与会话已建立（PPP 数据面待接入）」。
- L2TP 控制与数据共用 UDP 1701，故数据往返复用控制握手同一对 UDP 套接字。
- L2TP 数据消息（RFC 2661）为明文（加密/认证由内层 PPP/IPSec 承担，如实体现）。

## 二、报文格式（RFC 2661 数据消息）

```
L2TP 数据报文: version_flags(2,BE)=0x0002(T=0,数据) | tunnel_id(2,BE) | session_id(2,BE) | payload
```

- 首字节 T 位（0x8000）=0 表示数据消息（=1 为控制）；版本号 2。
- tunnel_id/session_id 为**接收方**的标识（发送方填对端 id），取握手协商值
  （client tunnel/session=1，server tunnel/session=2）。
- payload 为 PPP 帧（教学简化，不实现 LCP/IPCP）。

## 三、分阶段任务

### P1 — L2TP 数据报文

新增 `plugins/protocols/l2tp/data_channel.py`：`build_l2tp_data` / `parse_l2tp_data`
（校验 T 位、版本号）。

### P2 — 数据收发编排 + 接入 validation

新增 `services/l2tp_data_transport.py`：`L2TPDataTransport(socket, local_tunnel, local_session, peer_tunnel, peer_session)`。
`validation.py`：l2tp 的 tunnel 步骤做真实 L2TP 数据往返（复用控制握手同一套接字，
`_run_l2tp_handshake_and_data`）。

### P3 — 测试 + 文档

- `tests/unit/test_l2tp_data_channel.py`：往返、坏 T 位/坏长度拒绝。
- `tests/integration/test_l2tp_data_flow.py`：握手后 L2TP 数据面往返。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- l2tp 的 tunnel 步骤为真实 L2TP 数据面往返。
- 每功能独立提交并推送到 `origin/main`。

## 五、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。至此 **6 个 validation 协议
全部具备真实控制面握手 + 真实数据面往返**。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `67f0e8d` | `l2tp/data_channel.py`：L2TP 数据报文 framing（T=0 + tunnel/session id） |
| P2 | `bdc1228` | `services/l2tp_data_transport.py` + validation l2tp tunnel 改真实数据往返（复用控制握手套接字） |
| P3 | 本提交 | 单元/集成测试（4+2 条）+ README 同步 |

最终指标：后端 1291 tests 通过、81.8% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

