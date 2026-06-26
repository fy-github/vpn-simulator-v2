# VPN Simulator v2 - 功能增强计划

## 文档目的

本文档定义 VPN Simulator v2 基于竞品分析的功能增强计划，包括实时流量可视化、场景预设、自动化测试等功能。

---

## 一、功能清单

### 1.1 P1 - 高价值功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F1 | 实时流量可视化 | 在拓扑图上显示数据包流动动画 | 2-3 周 |
| F2 | 场景预设 | 3G/LTE/卫星/Starlink 等网络场景 | 1 周 |
| F3 | YAML 场景自动化 | 定义测试场景，自动执行 | 2 周 |
| F4 | 性能可视化图表 | 吞吐量、延迟、丢包图表 | 1-2 周 |

### 1.2 P2 - 中等价值功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F5 | 协议深度检测 (DPI) | 集成 nDPI 进行协议识别 | 2 周 |
| F6 | 流量混淆测试 | 测试 obfs4、Shadowsocks 等 | 2 周 |
| F7 | IoT 设备模拟 | 模拟摄像头、传感器 | 1-2 周 |
| F8 | 语音模拟 (RTP) | VoIP 测试，MOS 评分 | 2 周 |
| F9 | 多厂商 CLI | 支持 Cisco/Huawei 语法 | 2-3 周 |

### 1.3 P3 - 低优先级功能

| # | 功能 | 说明 | 预计工期 |
|---|------|------|----------|
| F10 | AI 实验室构建 | 自然语言构建拓扑 | 3-4 周 |
| F11 | WebAssembly 引擎 | 高性能模拟 | 4-6 周 |
| F12 | 协议模糊测试 | 安全测试 | 3 周 |

---

## 二、详细设计

### 2.1 F1: 实时流量可视化

#### 目标
在 Web UI 的拓扑图上实时显示数据包流动动画，让用户直观看到网络通信过程。

#### 技术方案

```
┌─────────────────────────────────────────────────────────────────┐
│                      前端 (React + Canvas)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ 拓扑编辑器  │  │ 流量动画    │  │ 协议过滤器  │            │
│  │ (ReactFlow) │  │ (Canvas)    │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                      后端 (FastAPI)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ 流量捕获    │  │ 事件广播    │  │ 协议解析    │            │
│  │ (tcpdump)   │  │ (WebSocket) │  │ (nDPI)      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

#### 数据流

1. **后端**: 使用 `tcpdump` 或原始套接字捕获流量
2. **后端**: 解析数据包，提取源/目标 IP、协议、端口
3. **后端**: 通过 WebSocket 推送流量事件
4. **前端**: 接收事件，在 Canvas 上绘制动画

#### 前端组件

```typescript
// web-ui/src/components/TrafficVisualizer.tsx
interface TrafficEvent {
  id: string;
  timestamp: number;
  srcNode: string;
  dstNode: string;
  protocol: string;
  size: number;
  direction: 'request' | 'response';
}

const TrafficVisualizer: React.FC = () => {
  // 使用 Canvas 绘制数据包动画
  // 支持协议过滤（TCP/UDP/ICMP/ARP）
  // 支持速度控制（1x/2x/0.5x）
  // 支持暂停/继续
};
```

#### API 端点

```
WS /api/v1/traffic/stream          # 实时流量流
GET /api/v1/traffic/statistics     # 流量统计
POST /api/v1/traffic/capture       # 开始捕获
POST /api/v1/traffic/stop          # 停止捕获
```

#### 验收标准

- [ ] 拓扑图上显示数据包流动动画
- [ ] 支持协议过滤（TCP/UDP/ICMP/ARP）
- [ ] 支持速度控制（1x/2x/0.5x）
- [ ] 支持暂停/继续
- [ ] 显示实时流量统计

---

### 2.2 F2: 场景预设

#### 目标
提供预设的网络场景（3G、LTE、卫星、Starlink），用户一键应用即可模拟真实网络环境。

#### 场景定义

```yaml
# config/scenarios/presets.yaml
scenarios:
  - id: "3g"
    name: "3G 网络"
    description: "模拟 3G 移动网络环境"
    params:
      latency_ms: 200
      jitter_ms: 50
      packet_loss_rate: 0.02
      bandwidth_kbps: 2000
      
  - id: "lte"
    name: "4G LTE"
    description: "模拟 4G LTE 网络环境"
    params:
      latency_ms: 50
      jitter_ms: 20
      packet_loss_rate: 0.01
      bandwidth_kbps: 50000
      
  - id: "satellite"
    name: "卫星网络"
    description: "模拟地球同步卫星网络"
    params:
      latency_ms: 600
      jitter_ms: 100
      packet_loss_rate: 0.05
      bandwidth_kbps: 10000
      
  - id: "starlink"
    name: "Starlink"
    description: "模拟 Starlink 低轨卫星网络"
    params:
      latency_ms: 40
      jitter_ms: 15
      packet_loss_rate: 0.005
      bandwidth_kbps: 100000
      
  - id: "wifi_congested"
    name: "拥塞 WiFi"
    description: "模拟拥塞的公共 WiFi"
    params:
      latency_ms: 100
      jitter_ms: 80
      packet_loss_rate: 0.1
      bandwidth_kbps: 5000
      
  - id: "fiber"
    name: "光纤网络"
    description: "模拟高速光纤网络"
    params:
      latency_ms: 5
      jitter_ms: 2
      packet_loss_rate: 0.001
      bandwidth_kbps: 1000000
```

#### API 端点

```
GET /api/v1/scenarios              # 列出所有场景
GET /api/v1/scenarios/{id}         # 获取场景详情
POST /api/v1/scenarios/{id}/apply  # 应用场景
DELETE /api/v1/scenarios/{id}/remove # 移除场景
```

#### 前端组件

```typescript
// web-ui/src/components/ScenarioSelector.tsx
const ScenarioSelector: React.FC = () => {
  // 场景列表（卡片形式）
  // 一键应用
  // 自定义参数调整
  // 实时预览效果
};
```

#### 验收标准

- [ ] 提供 6+ 预设场景
- [ ] 一键应用场景
- [ ] 支持自定义参数调整
- [ ] 实时显示场景效果

---

### 2.3 F3: YAML 场景自动化

#### 目标
支持 YAML 格式定义测试场景，自动执行测试并生成报告。

#### 场景定义格式

```yaml
# config/scenarios/automation/pptp_basic.yaml
name: "PPTP 基础连接测试"
description: "测试 PPTP 协议的基本连接功能"
version: "1.0"
author: "VPN Simulator"

# 前置条件
setup:
  - start_protocol: "pptp"
    config:
      port: 1723
      
# 测试步骤
steps:
  - name: "建立连接"
    action: "connect"
    params:
      protocol: "pptp"
      user: "test"
      password: "test123"
    expect:
      state: "connected"
      timeout: 10
      
  - name: "验证 IP 分配"
    action: "check"
    params:
      target: "connection.ip_address"
    expect:
      not_null: true
      
  - name: "测试延迟"
    action: "ping"
    params:
      target: "10.0.0.1"
      count: 10
    expect:
      avg_latency_ms: "< 50"
      packet_loss: "< 5%"
      
  - name: "断开连接"
    action: "disconnect"
    expect:
      state: "disconnected"

# 清理
teardown:
  - stop_protocol: "pptp"
```

#### 执行引擎

```python
# src/vpn_simulator/services/scenario_engine.py
class ScenarioEngine:
    """场景执行引擎"""
    
    async def load_scenario(self, path: str) -> Scenario:
        """加载 YAML 场景"""
        pass
        
    async def execute(self, scenario: Scenario) -> ScenarioResult:
        """执行场景"""
        pass
        
    async def validate_step(self, step: Step, result: Any) -> bool:
        """验证步骤结果"""
        pass
```

#### API 端点

```
GET /api/v1/scenarios/automation              # 列出自动化场景
POST /api/v1/scenarios/automation/{id}/run    # 运行场景
GET /api/v1/scenarios/automation/{id}/status  # 获取执行状态
GET /api/v1/scenarios/automation/{id}/report  # 获取报告
```

#### 验收标准

- [ ] 支持 YAML 格式定义场景
- [ ] 自动执行测试步骤
- [ ] 验证每步结果
- [ ] 生成 HTML/JSON 报告

---

### 2.4 F4: 性能可视化图表

#### 目标
提供实时性能图表，显示吞吐量、延迟、丢包等指标。

#### 图表类型

| 图表 | 说明 | 库 |
|------|------|-----|
| 吞吐量时序图 | 实时显示 Mbps | Chart.js |
| 延迟分布图 | 直方图 + 累积分布 | Chart.js |
| 丢包率时序图 | 实时显示丢包 % | Chart.js |
| 连接数时序图 | 并发连接数 | Chart.js |
| 协议分布饼图 | TCP/UDP/ICMP 占比 | Chart.js |

#### 前端组件

```typescript
// web-ui/src/components/PerformanceCharts.tsx
const PerformanceCharts: React.FC = () => {
  // 使用 Chart.js 绘制图表
  // 支持时间范围选择（1m/5m/15m/1h）
  // 支持导出 PNG/CSV
  // 支持全屏显示
};
```

#### 数据源

```python
# src/vpn_simulator/services/metrics.py
class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.throughput = []  # [(timestamp, bytes)]
        self.latency = []     # [(timestamp, ms)]
        self.packet_loss = [] # [(timestamp, rate)]
        self.connections = [] # [(timestamp, count)]
```

#### 验收标准

- [ ] 实时更新图表
- [ ] 支持时间范围选择
- [ ] 支持导出 PNG/CSV
- [ ] 支持全屏显示

---

### 2.5 F5: 协议深度检测 (DPI)

#### 目标
集成 nDPI 库，对流量进行深度协议检测和识别。

#### 技术方案

```python
# src/vpn_simulator/services/dpi.py
class DPIService:
    """深度包检测服务"""
    
    def __init__(self):
        self.ndpi = NDPIWrapper()  # nDPI Python 绑定
        
    def analyze_packet(self, packet: bytes) -> ProtocolInfo:
        """分析单个数据包"""
        pass
        
    def get_protocol_stats(self) -> Dict[str, int]:
        """获取协议统计"""
        pass
```

#### 支持的协议

- 应用层：HTTP, HTTPS, DNS, SSH, Telnet, FTP, SMTP, POP3, IMAP
- 流媒体：YouTube, Netflix, Spotify, Twitch
- 社交：Facebook, Twitter, Instagram, WhatsApp
- VPN：OpenVPN, WireGuard, IPSec, L2TP
- P2P：BitTorrent, eDonkey

#### API 端点

```
GET /api/v1/dpi/protocols        # 支持的协议列表
GET /api/v1/dpi/statistics       # 协议统计
POST /api/v1/dpi/analyze         # 分析数据包
```

#### 验收标准

- [ ] 识别 100+ 应用协议
- [ ] 实时协议统计
- [ ] 协议分布可视化

---

### 2.6 F6: 流量混淆测试

#### 目标
测试 VPN 流量混淆技术（obfs4、Shadowsocks、udp2raw）的效果。

#### 混淆技术

| 技术 | 说明 | 检测难度 |
|------|------|----------|
| obfs4 | 流量随机化 | 高 |
| Shadowsocks | 加密代理 | 中 |
| udp2raw | UDP 转 TCP | 中 |
| Meek | 域名前置 | 高 |
| Snowflake | WebRTC | 高 |

#### 测试指标

- 协议识别率（nDPI 能否识别）
- 流量特征（包大小分布、时间间隔）
- Shannon 熵（载荷随机性）

#### 验收标准

- [ ] 支持 5+ 混淆技术
- [ ] 测量协议识别率
- [ ] 生成混淆效果报告

---

### 2.7 F7: IoT 设备模拟

#### 目标
模拟常见 IoT 设备（摄像头、传感器、智能音箱）的网络行为。

#### 设备类型

```yaml
# config/iot/devices.yaml
devices:
  - id: "ip_camera"
    name: "IP 摄像头"
    protocols: ["RTSP", "HTTP", "ONVIF"]
    traffic_pattern: "continuous"
    bandwidth_kbps: 2000
    
  - id: "temperature_sensor"
    name: "温度传感器"
    protocols: ["MQTT", "CoAP"]
    traffic_pattern: "periodic"
    interval_sec: 60
    
  - id: "smart_speaker"
    name: "智能音箱"
    protocols: ["HTTPS", "WebSocket"]
    traffic_pattern: "burst"
```

#### 验收标准

- [ ] 支持 10+ IoT 设备类型
- [ ] 模拟真实流量模式
- [ ] 支持自定义设备配置

---

### 2.8 F8: 语音模拟 (RTP)

#### 目标
模拟 VoIP 通话，测量语音质量（MOS 评分）。

#### 技术指标

| 指标 | 说明 |
|------|------|
| MOS | Mean Opinion Score (1-5) |
| jitter | 抖动 (ms) |
| packet_loss | 丢包率 (%) |
| latency | 延迟 (ms) |

#### 编码支持

- G.711 (64 kbps)
- G.729 (8 kbps)
- Opus (6-510 kbps)

#### 验收标准

- [ ] 模拟 VoIP 通话
- [ ] 计算 MOS 评分
- [ ] 显示语音质量指标

---

### 2.9 F9: 多厂商 CLI

#### 目标
支持 Cisco IOS 和华为 VRP 命令语法。

#### 命令映射

| 功能 | Cisco IOS | 华为 VRP |
|------|-----------|----------|
| 显示接口 | `show ip interface brief` | `display ip interface brief` |
| 显示路由 | `show ip route` | `display ip routing-table` |
| 配置接口 | `interface GigabitEthernet0/0` | `interface GigabitEthernet0/0/0` |
| 保存配置 | `write memory` | `save` |

#### 验收标准

- [ ] 支持 Cisco IOS 语法
- [ ] 支持华为 VRP 语法
- [ ] 命令自动补全

---

## 三、实施计划

### 3.1 Phase 1: 核心增强 (4-6 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 1-2 | F1: 实时流量可视化 | TrafficVisualizer 组件 |
| 3 | F2: 场景预设 | ScenarioSelector 组件 |
| 4-5 | F3: YAML 场景自动化 | ScenarioEngine 服务 |
| 6 | F4: 性能可视化图表 | PerformanceCharts 组件 |

### 3.2 Phase 2: 协议增强 (4-6 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 7-8 | F5: 协议深度检测 | DPIService 服务 |
| 9-10 | F6: 流量混淆测试 | ObfuscationTester 服务 |
| 11-12 | F7: IoT 设备模拟 | IoTSimulator 服务 |

### 3.3 Phase 3: 高级功能 (6-8 周)

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 13-14 | F8: 语音模拟 | VoiceSimulator 服务 |
| 15-17 | F9: 多厂商 CLI | MultiVendorCLI 组件 |
| 18-20 | F10: AI 实验室构建 | AIBuilder 服务 |

---

## 四、技术依赖

### 4.1 新增依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| nDPI | 协议深度检测 | 4.0+ |
| Chart.js | 图表库 | 4.0+ |
| react-chartjs-2 | React 图表组件 | 5.0+ |
| PyYAML | YAML 解析 | 6.0+ |
| scapy | 数据包构造 | 2.5+ |

### 4.2 可选依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| obfs4proxy | obfs4 混淆 | - |
| shadowsocks | SS 混淆 | - |
| udp2raw | UDP 转 TCP | - |

---

## 五、验收标准汇总

### 5.1 P1 功能验收

- [ ] F1: 拓扑图上显示数据包流动动画
- [ ] F2: 提供 6+ 预设场景，一键应用
- [ ] F3: 支持 YAML 场景定义，自动执行
- [ ] F4: 实时性能图表，支持导出

### 5.2 P2 功能验收

- [ ] F5: 识别 100+ 应用协议
- [ ] F6: 支持 5+ 混淆技术
- [ ] F7: 支持 10+ IoT 设备类型
- [ ] F8: 模拟 VoIP 通话，计算 MOS
- [ ] F9: 支持 Cisco/Huawei 语法

### 5.3 P3 功能验收

- [ ] F10: 自然语言构建拓扑
- [ ] F11: WASM 引擎性能提升
- [ ] F12: 协议模糊测试

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| nDPI 集成复杂 | 高 | 使用 Python 绑定，渐进集成 |
| 实时性能问题 | 中 | 使用 WebSocket，优化渲染 |
| 跨平台兼容 | 中 | 使用 Docker，统一环境 |
| 安全风险 | 高 | 隔离测试环境，权限控制 |

---

## 七、待确认问题

1. **nDPI 集成方式**: 使用 Python 绑定 vs REST API？
2. **实时可视化**: 使用 Canvas vs WebGL？
3. **场景存储**: 文件系统 vs 数据库？
4. **AI 功能**: 使用 OpenAI vs 本地模型？
