# VPN Simulator v2 — PPTP GRE 数据面仿真计划 v11

> 承接 `PLAN_ENHANCEMENT_V10.md`（ESP 数据面已闭环）。本计划把 PPTP 的 **GRE 数据面**
> 真实化：在 TCP 控制握手（SCCRQ/SCCRP + OCRQ/OCRP）建立后，用真实 GRE 报文
> （RFC 2784，Protocol Type 0x880B=PPP，Key 扩展）做数据面往返，替换
> 「GRE 隧道就绪（PPP 认证待接入）」占位，使 pptp 的 tunnel 步骤升级为真实 GRE 往返。

## 一、背景与现状

- `validation.py` 的 pptp tunnel 步骤现为「GRE 隧道就绪（PPP 认证待接入）」占位。
- PPTP 数据面为 GRE-over-IP（协议号 47），本计划用环回 UDP 套接字模拟（明示教学简化）。
- GRE 为明文封装（如实体现 PPTP 数据面无加密），密钥为握手协商的 call id。

## 二、报文格式（RFC 2784，Key 扩展）

```
GRE 报文: flags(2,BE)=0x2000(K) | protocol_type(2,BE)=0x880B(PPP) | key(4,BE) | payload
```

- `K` 位（0x2000）表示存在 4 字节 Key；不设 C/R/S 位（教学简化，无 checksum/seq）。
- Protocol Type 0x880B = PPP；payload 为 PPP 帧（教学简化，不实现 LCP/IPCP）。
- Key 取 PPTP 握手协商的 call id（client=1, server=2）。

## 三、分阶段任务

### P1 — GRE 报文

新增 `plugins/protocols/pptp/gre.py`：`build_gre_packet` / `parse_gre_packet`
（校验 K 位、protocol、key）。

### P2 — GRE 收发编排 + 接入 validation

新增 `services/gre_transport.py`：`GRETransport(socket, local_key, peer_key)`。
`validation.py`：pptp 的 tunnel 步骤做真实 GRE 数据面往返
（`_run_pptp_handshake_and_gre`，TCP 控制握手 + UDP GRE 数据往返）。

### P3 — 测试 + 文档

- `tests/unit/test_gre.py`：往返、坏标志位/坏长度拒绝。
- `tests/integration/test_gre_transport.py`：PPTP 握手后 GRE 数据面往返。
- `README.md`：测试数/特性说明同步。

## 四、验收

- 后端 pytest 全绿；mypy/ruff/black 全绿。
- pptp 的 tunnel 步骤为真实 GRE 数据面往返。
- 每功能独立提交并推送到 `origin/main`。

## 五、完成状态

全部阶段（P1–P3）已实现、测试并推送到 `origin/main`。

| 阶段 | 提交 | 说明 |
|------|------|------|
| P1 | `bc70538` | `pptp/gre.py`：GRE 报文 framing（K 位 + PPP 0x880B + key） |
| P2 | `2cb61ee` | `services/gre_transport.py` + validation pptp tunnel 改真实 GRE 往返 |
| P3 | 本提交 | 单元/集成测试（4+2 条）+ README 同步 |

最终指标：后端 1285 tests 通过、81.7% 覆盖率（`--cov-fail-under=78`）；
mypy / ruff / black 全绿。

