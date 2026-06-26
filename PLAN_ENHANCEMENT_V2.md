# VPN Simulator v2 - 功能增强计划 v2

## 文档目的

本文档定义 VPN Simulator v2 基于最新竞品分析的功能增强计划，包括时间变化网络损伤、VPN 配置验证、PCAP 回放等功能。

---

## 一、功能清单

### 1.1 P1 - 高价值功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F1 | 时间变化网络损伤 | 网络条件随时间变化（拥塞逐渐加剧） | 2 周 |
| F2 | VPN 配置验证 | 验证 VPN 配置有效性，测量延迟 | 1-2 周 |
| F3 | PCAP 回放 | 从 PCAP 文件回放流量 | 2 周 |

### 1.2 P2 - 中等价值功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F4 | SNMP 设备模拟 | 模拟 SNMP v2c/v3 设备 | 2 周 |
| F5 | 路由协议模拟 | OSPF、BGP 路由协议模拟 | 3 周 |
| F6 | Grafana 集成 | 高级监控仪表板 | 1-2 周 |

### 1.3 P3 - 低优先级功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F7 | 大规模设备模拟 | 模拟 30,000+ 网络设备 | 3-4 周 |
| F8 | C2 攻击场景 | DNS C2、Sliver C2 等高级攻击 | 2-3 周 |

---

## 二、详细设计

### 2.1 F1: 时间变化网络损伤

#### 目标
支持网络条件随时间变化，模拟真实世界的网络拥塞、带宽波动等场景。

#### 技术方案

```yaml
# config/impairments/time_varying.yaml
impairments:
  - id: "congestion_ramp"
    name: "拥塞渐增"
    description: "模拟网络拥塞逐渐加剧"
    duration_sec: 300
    parameters:
      latency:
        type: "linear"
        start_ms: 10
        end_ms: 500
      packet_loss:
        type: "exponential"
        start_rate: 0.001
        end_rate: 0.1
      bandwidth:
        type: "step"
        steps:
          - time_sec: 0
            value_kbps: 100000
          - time_sec: 100
            value_kbps: 50000
          - time_sec: 200
            value_kbps: 10000
```

#### 变化类型

| 类型 | 说明 | 公式 |
|------|------|------|
| linear | 线性变化 | `start + (end - start) * t / duration` |
| exponential | 指数变化 | `start * (end / start) ^ (t / duration)` |
| step | 阶梯变化 | 按时间点跳变 |
| sine | 正弦波动 | `amplitude * sin(2π * freq * t) + offset` |
| random | 随机波动 | 在范围内随机 |

#### API 端点

```
GET  /api/v1/impairments/presets          # 预设列表
POST /api/v1/impairments/start            # 启动损伤
POST /api/v1/impairments/stop             # 停止损伤
GET  /api/v1/impairments/status           # 当前状态
GET  /api/v1/impairments/timeline         # 时间线数据
```

#### 前端组件

```typescript
// web-ui/src/components/ImpairmentTimeline.tsx
const ImpairmentTimeline: React.FC = () => {
  // 时间线图表（Chart.js）
  // 参数曲线预览
  // 实时状态显示
  // 预设选择器
};
```

#### 验收标准

- [ ] 支持 5 种变化类型
- [ ] 时间线图表实时更新
- [ ] 预设场景一键应用

---

### 2.2 F2: VPN 配置验证

#### 目标
验证 VPN 配置的有效性，测量连接延迟和性能。

#### 验证项目

| 验证项 | 说明 |
|--------|------|
| 语法检查 | 配置格式是否正确 |
| 端口可达性 | 服务端口是否开放 |
| 握手测试 | 能否完成握手 |
| 认证测试 | 认证是否通过 |
| 隧道测试 | 能否建立隧道 |
| 延迟测量 | 握手延迟 |
| 吞吐量测试 | 数据传输速率 |

#### API 端点

```
POST /api/v1/validation/validate         # 验证配置
GET  /api/v1/validation/results          # 验证结果
GET  /api/v1/validation/history          # 历史记录
POST /api/v1/validation/batch            # 批量验证
```

#### 前端组件

```typescript
// web-ui/src/components/ConfigValidator.tsx
const ConfigValidator: React.FC = () => {
  // 配置输入框
  // 验证进度条
  // 结果展示（绿/黄/红）
  // 性能指标
};
```

#### 验收标准

- [ ] 支持 6 种协议配置验证
- [ ] 显示详细验证步骤
- [ ] 测量延迟和吞吐量

---

### 2.3 F3: PCAP 回放

#### 目标
从 PCAP 文件回放流量，用于测试和分析。

#### 功能

| 功能 | 说明 |
|------|------|
| 文件解析 | 解析 PCAP/PCAPNG 文件 |
| 流量回放 | 按原始时序回放 |
| 速度控制 | 0.5x/1x/2x/10x |
| 协议过滤 | 只回放特定协议 |
| 统计分析 | 流量统计和协议分布 |

#### API 端点

```
POST /api/v1/pcap/upload               # 上传 PCAP 文件
GET  /api/v1/pcap/files                # 文件列表
GET  /api/v1/pcap/files/{id}           # 文件详情
POST /api/v1/pcap/files/{id}/replay    # 开始回放
POST /api/v1/pcap/replay/stop          # 停止回放
GET  /api/v1/pcap/replay/status        # 回放状态
GET  /api/v1/pcap/files/{id}/stats     # 流量统计
```

#### 前端组件

```typescript
// web-ui/src/components/PcapReplay.tsx
const PcapReplay: React.FC = () => {
  // 文件上传
  // 回放控制（播放/暂停/停止）
  // 速度控制
  // 协议过滤
  // 流量统计图表
};
```

#### 验收标准

- [ ] 支持 PCAP/PCAPNG 格式
- [ ] 按原始时序回放
- [ ] 支持速度控制和协议过滤

---

### 2.4 F4: SNMP 设备模拟

#### 目标
模拟 SNMP v2c/v3 设备，用于监控系统测试。

#### 设备类型

| 设备 | OID 树 | 说明 |
|------|--------|------|
| 路由器 | IF-MIB, IP-MIB | 接口、路由表 |
| 交换机 | BRIDGE-MIB | MAC 表、VLAN |
| 服务器 | HOST-RESOURCES-MIB | CPU、内存、磁盘 |
| 防火墙 | NETSCREEN-MIB | 会话、策略 |

#### API 端点

```
GET  /api/v1/snmp/devices              # 设备列表
POST /api/v1/snmp/devices              # 创建设备
GET  /api/v1/snmp/devices/{id}         # 设备详情
POST /api/v1/snmp/devices/{id}/start   # 启动设备
POST /api/v1/snmp/devices/{id}/stop    # 停止设备
GET  /api/v1/snmp/devices/{id}/oids    # OID 查询
```

#### 验收标准

- [ ] 支持 SNMP v2c/v3
- [ ] 模拟 10+ 设备类型
- [ ] 支持 OID 查询和遍历

---

### 2.5 F5: 路由协议模拟

#### 目标
模拟 OSPF、BGP 路由协议，用于网络拓扑测试。

#### 协议支持

| 协议 | 功能 |
|------|------|
| OSPF | Hello、LSA、SPF 计算 |
| BGP | OPEN、UPDATE、KEEPALIVE |
| VRF | 路由隔离 |

#### 验收标准

- [ ] 模拟 OSPF 邻居建立
- [ ] 模拟 BGP 会话建立
- [ ] 支持路由表查询

---

### 2.6 F6: Grafana 集成

#### 目标
集成 Grafana 监控仪表板，提供高级可视化。

#### 功能

| 功能 | 说明 |
|------|------|
| Prometheus 导出 | 标准化指标导出 |
| 预设仪表板 | 内置 Grafana 仪表板 |
| 告警规则 | 配置告警阈值 |

#### 验收标准

- [ ] Prometheus 指标端点
- [ ] 内置 Grafana 仪表板
- [ ] 告警规则配置

---

## 三、项目结构

```
vpn-simulator-v2/
├── src/
│   ├── vpn_simulator/
│   │   ├── core/
│   │   │   ├── events.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── platform.py
│   │   ├── domain/
│   │   │   ├── protocol.py
│   │   │   ├── connection.py
│   │   │   ├── packet.py
│   │   │   ├── fault.py
│   │   │   ├── attack.py
│   │   │   ├── scenario.py
│   │   │   ├── benchmark.py
│   │   │   ├── impairment.py      # 新增
│   │   │   ├── validation.py      # 新增
│   │   │   └── pcap.py            # 新增
│   │   ├── services/
│   │   │   ├── ...
│   │   │   ├── impairment.py      # 新增
│   │   │   ├── validation.py      # 新增
│   │   │   ├── pcap.py            # 新增
│   │   │   └── snmp.py            # 新增
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   │   ├── ...
│   │   │   │   ├── impairment.py  # 新增
│   │   │   │   ├── validation.py  # 新增
│   │   │   │   ├── pcap.py        # 新增
│   │   │   │   └── snmp.py        # 新增
│   │   │   └── ...
│   │   └── ...
│   └── plugins/
│       └── ...
├── web-ui/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ...
│   │   │   ├── ImpairmentTimeline.tsx   # 新增
│   │   │   ├── ConfigValidator.tsx      # 新增
│   │   │   ├── PcapReplay.tsx           # 新增
│   │   │   └── SNMPManager.tsx          # 新增
│   │   ├── pages/
│   │   │   ├── ...
│   │   │   ├── Impairments.tsx          # 新增
│   │   │   ├── Validation.tsx           # 新增
│   │   │   ├── PCAP.tsx                 # 新增
│   │   │   └── SNMP.tsx                 # 新增
│   │   └── ...
│   └── ...
├── config/
│   ├── impairments/
│   │   └── time_varying.yaml            # 新增
│   ├── pcap/                            # 新增
│   └── snmp/                            # 新增
└── ...
```

---

## 四、实施计划

### 4.1 Phase 1: 核心增强 (4-5 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 1-2 | F1: 时间变化网络损伤 | ImpairmentService + API + 前端 |
| 3-4 | F2: VPN 配置验证 | ValidationService + API + 前端 |
| 5 | F3: PCAP 回放 | PcapService + API + 前端 |

### 4.2 Phase 2: 协议增强 (5-7 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 6-7 | F4: SNMP 设备模拟 | SNMPService + API + 前端 |
| 8-10 | F5: 路由协议模拟 | RoutingService + API + 前端 |
| 11-12 | F6: Grafana 集成 | Prometheus 导出 + 仪表板 |

### 4.3 Phase 3: 高级功能 (7-10 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 13-16 | F7: 大规模设备模拟 | 设备池 + 资源管理 |
| 17-19 | F8: C2 攻击场景 | 攻击场景 + 检测 |

---

## 五、技术依赖

### 5.1 新增依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| scapy | PCAP 解析和回放 | 2.5+ |
| pysnmp | SNMP 协议 | 6.0+ |
| prometheus-client | Prometheus 指标 | 0.17+ |
| pyshark | PCAP 深度解析 | 0.6+ |

### 5.2 可选依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| grafana-api | Grafana 集成 | 1.0+ |
| exabgp | BGP 模拟 | 4.0+ |

---

## 六、验收标准汇总

### 6.1 P1 功能验收

- [ ] F1: 支持 5 种变化类型，时间线图表实时更新
- [ ] F2: 支持 6 种协议配置验证，显示详细步骤
- [ ] F3: 支持 PCAP/PCAPNG 格式，按原始时序回放

### 6.2 P2 功能验收

- [ ] F4: 支持 SNMP v2c/v3，模拟 10+ 设备类型
- [ ] F5: 模拟 OSPF/BGP 邻居建立
- [ ] F6: Prometheus 指标端点，内置仪表板

### 6.3 P3 功能验收

- [ ] F7: 支持 30,000+ 设备模拟
- [ ] F8: 支持 5+ C2 攻击场景

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PCAP 解析性能 | 中 | 使用 pyshark + 缓存 |
| SNMP 兼容性 | 中 | 使用 pysnmp 标准实现 |
| 大规模模拟资源 | 高 | 使用连接池 + 懒加载 |
| 安全风险 | 高 | 隔离测试环境，权限控制 |

---

## 八、待确认问题

1. **PCAP 存储**: 文件系统 vs 数据库？
2. **SNMP 版本**: 仅 v2c vs 同时支持 v3？
3. **Grafana 部署**: 内嵌 vs 外部部署？
4. **大规模模拟**: 单机 vs 分布式？
