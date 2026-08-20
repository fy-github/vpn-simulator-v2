# VPN Simulator v2 — VXLAN 数据面封装仿真计划 v14

> 承接 `PLAN_ENHANCEMENT_V13.md`（SSTP 真实 TLS 已闭环）。本计划把第 8 个协议
> **VXLAN** 纳入 validation，真实化其数据面封装：VXLAN 为**无状态**封装协议
> （RFC 7348，无握手），在 UDP 4789 上做真实 VXLAN 头（VNI）封装/解封装往返，
> 使 vxlan 的 tunnel 步骤为真实 VXLAN 往返（handshake 步骤如实标记 SKIP）。

## 一、背景与现状

- VXLAN 插件已有状态机（`VXLANStateMachine`，同步接口：IDLE → INTERFACE_CREATED →
  PEER_DISCOVERED → TUNNEL_ESTABLISHED → FORWARDING）。
- VXLAN 无控制面握手（无状态隧道，控制面为静态/外部配置），故 validation 的
  handshake 步骤为 SKIP，tunnel 步骤做真实 VXLAN 封装/解封装往返。

## 二、报文格式（RFC 7348 教学简化）

```
VXLAN 报文: flags(1B)=0x08(I) | reserved(3B)=0 | VNI(3B,24位) | reserved(1B)=0 | payload
```

- I 位（0x08）表示 VNI 有效。
- VNI 为 24 位 VXLAN Network Identifier。
- payload 为内层以太网帧（教学简化，不实现完整 Ethernet 头）。
- VXLAN 为明文封装（如实体现，加密由外层 IPSec 等承担）。

## 三、分阶段任务

### P1 — VXLAN 报文

新增 `plugins/protocols/vxlan/encap.py`：`build_vxlan_packet` / `parse_vxlan_packet`
（校验 I 位、VNI）。

### P2 — 收发编排 + 接入 validation

新增 `services/vxlan_transport.py`：`VXLANTransport(socket, local_vni, peer_vni)`。
`validation.py`：SUPPORTED_PROTOCOLS/_AUTH_FIELDS(vni)/_DEFAULT_PORTS(4789) 加 vxlan，
vxlan 分支 handshake=SKIP、tunnel=真实 VXLAN 往返（`_run_vxlan_roundtrip`）。

### P3 — 测试 + 文档

- `tests/unit/test_vxlan_encap.py`：往返、坏 I 位/坏长度拒绝。
- `tests/integration/test_vxlan_transport.py`：VXLAN 封装/解封装往返 + 错误 VNI 拒绝。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- `validate("vxlan")` 的 tunnel 步骤为真实 VXLAN 往返。
- 每功能独立提交并推送到 `origin/main`。

## 五、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。VXLAN 成为第 8 个 validation
协议（无握手，数据面真实封装）。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `e137e15` | `vxlan/encap.py`：VXLAN 报文 framing（I 位 + VNI） |
| P2 | `29bd91e` | `services/vxlan_transport.py` + validation vxlan 分支（handshake=SKIP）+ batch 测试数更新 |
| P3 | 本提交 | 单元/集成测试（4+2 条）+ README 同步 |

最终指标：后端 1305 tests 通过、82.0% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

