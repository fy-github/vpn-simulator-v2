# VPN Simulator v2 - 功能增强计划 v2（细化版）

## 文档目的

本文档是 `PLAN_ENHANCEMENT_V2.md` 的细化版本，基于竞品分析与本仓库现状，定义
VPN Simulator v2 的下一阶段路线图。相较 v2 初稿，本版新增两处战略调整：

1. **真实报文仿真方向**：从"纯状态机 + 模拟流量"升级为"状态机骨架 + 真实报文
   收发（控制面/握手层）"，由新增的 `packetio` 核心模块承载。
2. **持久化与工程卫生前置**：在新增功能（F1–F8）之前，先把状态持久化与工程
   卫生欠账补清，作为一切上层功能的可靠地基。

---

## 一、战略定位

### 1.1 对标结论（简）

| 类别 | 代表项目 | 与本项目的关系 |
|------|----------|----------------|
| 真实镜像仿真器 | GNS3 / EVE-NG / Cisco CML | 重、需授权镜像、吃资源；本项目的差异是"零镜像开箱即用" |
| 网络/SDN 仿真 | Mininet / Containerlab / Kathará | 真实转发但不覆盖 VPN 协议 |
| 离散事件仿真 | ns-3 / OMNeT++(INET) | 学术建模，可借鉴状态机建模方式 |
| 网络损伤/混沌 | WANem / toxiproxy / Chaos Mesh | 与故障注入最接近，F1 可借鉴其损伤模型 |
| 报文库 | Scapy / Impacket | 真实报文方向的地基 |
| 路由协议 | FRRouting / BIRD / ExaBGP | F5 参考实现 |
| SNMP 模拟 | SnmpSim | F4 直接对标 |
| 可观测 | Prometheus + Grafana | F6 |
| C2 框架 | Sliver / Cobalt Strike | F8 参考（需伦理边界） |

### 1.2 差异化定位

**无需真实镜像、开箱即用的多协议 VPN 教学 + 安全测试沙盒**，卡在 GNS3（太重）
与纯理论教程之间。护城河 = 插件架构 + 协议状态机 + 现代 Web UI + 真实报文层
（本次新增）。

### 1.3 真实报文方向的边界

"升级到真实报文"≠"实现一个可用的 VPN 服务"。本方向的明确边界：

- **做**：真实收发协议**控制面/握手**报文（如 WireGuard Handshake、OpenVPN
  `--tls-auth`/静态密钥握手、IKEv2 SA_INIT 等），并驱动状态机随真实报文推进。
- **不做**：加密隧道**数据面**转发、真实密钥协商密码学（可先 stubbed）、可作为
  生产网关对外服务。

状态机仍是骨架，`packetio` 是新的"感官/输入层"：让握手、故障注入、配置验证、
PCAP 回放从"模拟"变成"真测"。

---

## 二、路线图总览

| 阶段 | 主题 | 核心交付 | 预估工期 |
|------|------|----------|----------|
| Phase 0 | 持久化 + 工程卫生 | 状态重启不丢、CI 补 mypy、文档修正、exporters 定案、安全默认值 | 2–3 周 |
| Phase 1 | 真实报文地基 | `packetio` 模块 + 首个协议真实握手（WireGuard/OpenVPN） | 3–4 周 |
| Phase 2 | P1 功能（F1–F3） | 时间变化损伤、VPN 配置验证、PCAP 回放（基于真实报文） | 4–6 周 |
| Phase 3 | P2 功能（F4–F6） | SNMP 模拟、路由协议、Grafana/Prometheus | 6–8 周 |
| Phase 4 | P3 功能（F7–F8） | 大规模设备、C2 攻击场景 | 8 周以上 |

> 执行顺序：**Phase 0 → Phase 1 → F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8**。
> 其中 Phase 1 的 `packetio` 是 F1/F2/F3 的地基，故置于 P1 功能之前。

### 执行进度（已全部完成 ✅）

| 阶段/功能 | 状态 | 提交 |
|-----------|------|------|
| Phase 0（持久化 + 工程卫生） | ✅ 完成 | `f44907d`…`5a1edcf`（含 mypy 全绿、README 修正、exporters 首个 Prometheus 导出、默认绑 127.0.0.1、启动状态恢复） |
| Phase 1（真实报文地基） | ✅ 完成 | `00d3125`、`ee09333`、`aa96fcf`、`cbd34a0`（真实 X25519/ChaCha20-Poly1305/BLAKE2s Noise_IKpsk2 握手 + scapy 报文层 + UDP 收发 + 报文入流量流） |
| F1 时间变化损伤 | ✅ 完成 | `22cb357`、`09fc1aa` |
| F2 VPN 配置验证 | ✅ 完成 | `30a8b1f` |
| F3 PCAP 回放 | ✅ 完成 | `c2a98c6` |
| F4 SNMP 设备模拟 | ✅ 完成 | `4225824` |
| F5 路由协议模拟 | ✅ 完成 | `12587f5` |
| F6 Grafana 集成 | ✅ 完成 | `e083fd2` |
| F7 大规模设备模拟 | ✅ 完成 | `9fac173` |
| F8 C2 攻击场景 | ✅ 完成 | `7d792a7` |

---

## 三、Phase 0：持久化 + 工程卫生

### 3.1 P0-1 状态持久化（核心）

**现状问题**：DB 已建表（connections/packets/state_transitions/faults/attacks/
config_history/topologies）且连接/故障/攻击已做写通（write-through），但
**启动时从不读回**，协议运行状态也无表——重启即全丢。

**方案**：

1. 新增 `ProtocolRecord` 表（protocol name / state / config / started_at），
   记录协议"运行/停止"状态。
2. 各服务新增 `restore_from_db()`，应用启动（lifespan）时依次水合：
   - `ConnectionService`：从 `connections` 读回 `state in (connected, ...)` 的连接
   - `FaultService`：从 `faults` 读回 `active=True` 的故障
   - `AttackService`：从 `attacks` 读回 `status=running` 的攻击
   - `ProtocolService`：从 `protocols` 读回上次运行的协议
3. 保持写通，补齐遗漏的写回点（如协议 start/stop 落库）。
4. 验收：`server stop` 后重启，协议/连接/故障/攻击状态自动恢复，`server status`
   显示一致。

**文件**：`core/database.py`（加表）、`services/{protocol,connection,fault,attack}.py`
（加 restore）、`api/app.py`（lifespan 调 restore）。

### 3.2 P0-2 工程卫生

| # | 项 | 动作 |
|---|----|------|
| H1 | CI 补 mypy | `.github/workflows/ci.yml` 加 `uv run mypy src/vpn_simulator`（现已全绿） |
| H2 | 文档漂移 | README：8→9 协议、补 VXLAN 行、1037→1040 测试、更新特性表 |
| H3 | exporters 定案 | 实现首个 exporter：Prometheus 文本指标导出（为 F6 铺路），空壳 `plugins/exporters/` 做实 |
| H4 | 安全默认值 | CLI `server start` 默认 host 改 `127.0.0.1`；`VPN_SIM_API_KEY` 文档化（本地免认证、生产必开） |

---

## 四、Phase 1：真实报文地基（packetio）

### 4.1 目标

建立真实报文收发能力，让状态机由真实网络报文驱动。

### 4.2 技术方案

- 新增 `src/vpn_simulator/core/packetio.py`（或 `services/packetio.py`）：
  - 基于 `scapy` 构造/解析报文
  - UDP/TCP 套接字收发（asyncio `create_datagram_endpoint` / `open_connection`）
  - 报文 ↔ 领域事件（`EventBus`）桥接：收到真实握手报文 → 发布
    `protocol.packet_received` → 状态机推进
- 首个试点协议：**WireGuard**（UDP，握手结构简单）——已定案；OpenVPN 后续
  （TCP + 静态密钥 `--tls-auth` 路径）暂缓。
- 密码学边界：**接入真实曲线**（已定案）——握手密钥协商走真实
  X25519 ECDH + ChaCha20-Poly1305 AEAD + BLAKE2s 哈希/KDF，实现 Noise_IKpsk2
  握手；不做数据面转发，也不作为生产 VPN 网关对外提供隧道。

### 4.3 验收标准

- [x] `packetio` 能真实收/发 UDP 报文并解析出 WireGuard Handshake Init 结构
- [x] 真实报文驱动 WireGuard 状态机至少完成一次握手状态跳转
- [x] 与 Web UI 的 traffic 流打通：真实报文进入 `packets` 表与 WS 流

---

## 五、Phase 2–4：F1–F8 功能（精化）

> **状态：F1–F8 已全部实现并合入 main（见上"执行进度"）。**
> 以下在 v2 初稿基础上精化，标注与真实报文/持久化的关系。

### 5.1 F1: 时间变化网络损伤

- 目标：网络条件随时间变化（拥塞渐增、带宽波动）。
- 与现状关系：在 6 个 fault 插件上叠加**调度层**（时间线 + 变化曲线），不复写
  插件；损伤参数作用于真实报文流（Phase 1 后）与模拟流量（Phase 1 前）。
- 变化类型：linear / exponential / step / sine / random（5 种，同初稿）。
- 配置：`config/impairments/time_varying.yaml`。
- API：`/api/v1/impairments/{presets,start,stop,status,timeline}`。
- 验收：5 种变化类型、时间线图表实时更新、预设一键应用、损伤状态持久化（Phase 0 后）。

### 5.2 F2: VPN 配置验证

- 目标：验证 VPN 配置有效性，测量握手延迟与吞吐。
- 与真实报文关系：验证的"握手/隧道/延迟/吞吐"项，在 Phase 1 后走真实报文，
  从"模拟校验"升级为"真测"。
- 验证项：语法 / 端口可达性 / 握手 / 认证 / 隧道 / 延迟 / 吞吐（7 项）。
- API：`/api/v1/validation/{validate,results,history,batch}`。
- 验收：6 种协议配置验证、详细步骤展示、延迟+吞吐测量、历史持久化。

### 5.3 F3: PCAP 回放

- 目标：从 PCAP/PCAPNG 回放流量，按原始时序重放。
- 依赖：`scapy`（`rdpcap`/`PcapReader`）；回放进 `traffic` 流；真实报文层到位后
  可"回放真实握手包"驱动状态机。
- 功能：解析 / 时序回放 / 速度控制(0.5x–10x) / 协议过滤 / 统计分析。
- API：`/api/v1/pcap/{upload,files,replay,status,stats}`。
- 验收：PCAP/PCAPNG、原始时序、速度控制、协议过滤。

### 5.4 F4: SNMP 设备模拟

- 目标：模拟 SNMP v2c/v3 设备（路由器/交换机/服务器/防火墙）。
- 参考：SnmpSim；依赖 `pysnmp`。
- API：`/api/v1/snmp/{devices,oids}`。
- 验收：v2c/v3、10+ 设备类型、OID 查询与遍历。

### 5.5 F5: 路由协议模拟

- 目标：模拟 OSPF/BGP 邻居建立与路由表。
- 参考：FRR / BIRD / ExaBGP；可纯 Python 状态机实现，真实报文层到位后可发真实
  BGP OPEN/KEEPALIVE。
- 验收：OSPF 邻居建立、BGP 会话建立、路由表查询。

### 5.6 F6: Grafana 集成

- 目标：Prometheus 指标导出 + 内置 Grafana 仪表板 + 告警规则。
- 依赖：`prometheus-client`；与 P0-2 的 exporters 打通。
- 验收：`/metrics` 端点、内置仪表板、告警规则配置。

### 5.7 F7: 大规模设备模拟

- 目标：模拟 30,000+ 网络设备。
- 方案：asyncio + 连接池 + 懒加载；设备状态不逐台落库（仅聚合）。
- 验收：30,000+ 设备并发、内存可控、UI 不卡顿。

### 5.8 F8: C2 攻击场景

- 目标：DNS C2、Sliver 等高级 C2 攻击场景（**带伦理声明与隔离提示**）。
- 验收：5+ C2 场景、检测特征输出、隔离/教育用途声明。

---

## 六、项目结构（新增/变更）

```
src/vpn_simulator/
├── core/
│   ├── packetio.py            # 新增：真实报文收发（Phase 1）
│   └── database.py            # 变更：加 ProtocolRecord 表（P0-1）
├── domain/
│   ├── impairment.py          # 新增（F1）
│   ├── validation.py          # 新增（F2）
│   ├── pcap.py                # 新增（F3）
│   ├── snmp.py                # 新增（F4）
│   ├── routing.py             # 新增（F5）
│   ├── scale.py               # 新增（F7）
│   └── c2.py                  # 新增（F8）
├── services/
│   ├── protocol.py            # 变更：restore_from_db（P0-1）
│   ├── connection.py          # 变更：restore_from_db（P0-1）
│   ├── fault.py               # 变更：restore_from_db（P0-1）
│   ├── attack.py              # 变更：restore_from_db（P0-1）
│   ├── impairment.py          # 新增（F1）
│   ├── validation.py          # 新增（F2）
│   ├── pcap.py                # 新增（F3）
│   ├── snmp.py                # 新增（F4）
│   ├── routing.py             # 新增（F5）
│   ├── grafana.py             # 新增（F6）
│   ├── scale.py               # 新增（F7）
│   ├── c2.py                  # 新增（F8）
│   └── retention.py           # 新增（packets/state_transitions 保留策略）
├── api/routers/
│   ├── impairment.py          # 新增（F1）
│   ├── validation.py          # 新增（F2）
│   ├── pcap.py                # 新增（F3）
│   ├── snmp.py                # 新增（F4）
│   ├── routing.py             # 新增（F5）
│   ├── grafana.py             # 新增（F6）
│   ├── scale.py               # 新增（F7）
│   ├── c2.py                  # 新增（F8）
│   └── retention.py           # 新增（保留策略）
└── plugins/exporters/
    └── prometheus.py          # 新增：首个 exporter（P0-2 H3，为 F6 铺路）
```

> 注：F6 的 `/metrics` 端点由 Phase 0 的 `plugins/exporters/prometheus.py` 提供，
> 渲染底层已迁移到官方 `prometheus-client`（输出与手写格式字节兼容）；F6 增量
> 交付为内置 Grafana 仪表板 + 告警规则（`config/grafana/`）。
>
> 注：F7 的大规模设备聚合统计通过 `ScaleAggregateRecord` 单行落库（`/api/v1/scale/{persist,snapshots}`），
> 不逐设备写 30,000 行。

---

## 七、里程碑与验收

| 里程碑 | 内容 | 验收 | 状态 |
|--------|------|------|------|
| M0 | Phase 0 | 重启状态不丢；CI 含 mypy 且全绿；README 正确；exporters 有首个实现；默认绑 127.0.0.1 | ✅ |
| M1 | Phase 1 | 真实 UDP 报文驱动 WireGuard 握手状态跳转 | ✅ |
| M2 | F1+F2+F3 | 损伤时间线、6 协议配置真测、PCAP 时序回放 | ✅ |
| M3 | F4+F5+F6 | SNMP OID 查询、BGP/OSPF 会话、`/metrics` 端点 | ✅ |
| M4 | F7+F8 | 30,000+ 设备、5+ C2 场景 | ✅ |

---

## 八、技术依赖

| 依赖 | 用途 | 版本 | 引入阶段 |
|------|------|------|----------|
| scapy | 报文构造/解析、PCAP 回放 | 2.7.0（已引入） | Phase 1 / F3 |
| cryptography | X25519 / ChaCha20-Poly1305（WireGuard 握手真实曲线） | 50.0.0（已引入） | Phase 1 |
| pysnmp | SNMP OID 校验（`ObjectIdentifier`） | 7.1.28（已引入） | F4 |
| prometheus-client | Prometheus 指标渲染（`/metrics` 端点） | 0.26.0（已引入，F6 收尾） | P0-2 H3 / F6 |
| pyshark | PCAP 深度解析（可选，未引入） | 0.6+ | F3 |
| grafana-api | Grafana 集成（可选，未引入） | 1.0+ | F6 |
| exabgp | BGP 模拟（可选，未引入） | 4.0+ | F5 |

---

## 九、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| scapy 报文解析性能 | 中 | 仅控制面报文；异步 I/O；必要时缓存解析 |
| 真实握手密码学复杂度 | 高 | 用 `cryptography` 库真实实现 Noise_IKpsk2；以单测锁住握手往返与密钥一致性 |
| 大规模模拟资源 | 高 | asyncio + 连接池 + 懒加载 + 聚合落库 |
| 安全/伦理（C2、攻击模拟） | 高 | 默认绑 127.0.0.1、API Key、隔离声明 |
| 持久化迁移兼容 | 中 | `create_all` 幂等；新增表不影响既有表 |

---

## 十、待确认问题

1. ~~**真实报文首协议**~~ ✅ **已定案：WireGuard**（UDP，握手结构简单）；OpenVPN 暂缓。
2. ~~**密码学边界**~~ ✅ **已定案：接入真实曲线**（X25519 ECDH + ChaCha20-Poly1305 + BLAKE2s，实现 Noise_IKpsk2 握手）。
3. ~~**持久化范围**~~ ✅ **已定案：对 `packets` / `state_transitions` 增加保留策略**——`RetentionService` 按「最大行数（保留最新 N 行）+ 最大保留时长（TTL）」清理，应用启动时挂起周期任务自动清理，另暴露 `/api/v1/retention/{status,cleanup}` 供手动触发（防止无限增长）。
4. ~~**exporters 首实现**~~ ✅ **已定案：Prometheus 文本格式导出**（`plugins/exporters/prometheus.py`，为 F6 `/metrics` 铺路）。
5. ~~**SNMP 版本**~~ ✅ **已定案：v2c + v3 同时支持**（F4 模拟 12 种设备类型，设备按 v2c/v3 轮换）。
