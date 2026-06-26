# VPN Simulator v2 - 并发压力测试功能实现计划

## 1. Context

### 用户需求
实现 VPN Simulator v2 的并发压力测试功能，用于测试 VPN 协议的性能和稳定性。

### 目标
- 支持配置并发数、连接速率、保持时间、目标协议
- 实时统计连接数、成功率、平均延迟、吞吐量
- 生成 HTML/JSON 格式的压测报告
- 提供 REST API 和 CLI 命令接口
- 使用 asyncio 实现并发，structlog 记录日志

### 约束条件
- 不实现真实 VPN 连接（使用模拟连接）
- 不修改已有的协议插件
- 遵循现有代码模式和架构

---

## 2. 实现方案

### 2.1 Domain 层：`src/vpn_simulator/domain/stress_test.py`

**核心模型：**

```python
class StressTestStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class StressTestConfig:
    protocol: str           # 目标协议
    concurrency: int        # 并发数（默认 100）
    connection_rate: float  # 每秒新建连接数（默认 10）
    duration: int           # 测试持续时间（秒，默认 60）
    timeout: int            # 单连接超时（秒，默认 30）

class ConnectionResult:
    connection_id: str
    success: bool
    connect_time: float     # 连接耗时（毫秒）
    error: Optional[str]

class StressTestStats:
    total_connections: int
    successful_connections: int
    failed_connections: int
    active_connections: int
    avg_latency: float      # 平均延迟（毫秒）
    p50_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float       # 每秒连接数
    elapsed_time: float     # 已用时间（秒）

class StressTestReport:
    test_id: str
    config: StressTestConfig
    stats: StressTestStats
    started_at: datetime
    completed_at: Optional[datetime]
    results: List[ConnectionResult]
```

**管理器：**
```python
class StressTestManager:
    _tests: Dict[str, StressTestInfo]
    
    async def create_test(config) -> StressTestInfo
    async def get_test(test_id) -> Optional[StressTestInfo]
    async def list_tests() -> List[StressTestInfo]
    async def remove_test(test_id) -> bool
```

---

### 2.2 Service 层：`src/vpn_simulator/services/stress_test.py`

**核心服务：**

```python
class StressTestService:
    def __init__(self, event_bus, config_manager, db_manager)
    
    async def start_test(config: StressTestConfig) -> dict
        # 1. 创建测试实例
        # 2. 启动异步压力测试任务
        # 3. 发布事件
        # 4. 返回测试信息
    
    async def stop_test(test_id: str) -> dict
        # 1. 停止测试任务
        # 2. 更新状态
        # 3. 发布事件
    
    async def get_status(test_id: str) -> dict
        # 返回实时统计信息
    
    async def get_report(test_id: str, format: str = "json") -> dict/str
        # 生成报告（JSON 或 HTML）
    
    async def _run_stress_test(test_id: str)
        # 核心测试逻辑：
        # 1. 创建 asyncio.Semaphore 限制并发
        # 2. 按 connection_rate 创建连接
        # 3. 模拟连接（使用 asyncio.sleep 模拟延迟）
        # 4. 收集统计信息
        # 5. 定时更新 stats
```

**模拟连接逻辑：**
```python
async def _simulate_connection(protocol: str, timeout: int) -> ConnectionResult:
    # 模拟连接建立延迟（50-200ms）
    connect_time = random.uniform(50, 200)
    await asyncio.sleep(connect_time / 1000)
    
    # 模拟 5% 失败率
    success = random.random() > 0.05
    
    return ConnectionResult(
        connection_id=str(uuid.uuid4()),
        success=success,
        connect_time=connect_time,
        error=None if success else "Simulated connection timeout"
    )
```

---

### 2.3 API 层：`src/vpn_simulator/api/routers/stress.py`

**端点设计：**

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/stress/start` | 启动压力测试 |
| POST | `/api/v1/stress/stop` | 停止压力测试 |
| GET | `/api/v1/stress/status` | 获取测试状态 |
| GET | `/api/v1/stress/report` | 获取测试报告 |
| GET | `/api/v1/stress/tests` | 列出所有测试 |

**请求/响应模型：**

```python
class StartStressTestRequest(BaseModel):
    protocol: str = Field(..., pattern="^(pptp|l2tp|openvpn|ipsec|ikev2|wireguard)$")
    concurrency: int = Field(100, ge=1, le=10000)
    connection_rate: float = Field(10.0, ge=0.1, le=1000.0)
    duration: int = Field(60, ge=1, le=3600)
    timeout: int = Field(30, ge=1, le=300)

class StressTestStatusResponse(BaseModel):
    test_id: str
    status: str
    stats: StressTestStatsResponse

class StressTestStatsResponse(BaseModel):
    total_connections: int
    successful_connections: int
    failed_connections: int
    active_connections: int
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float
    elapsed_time: float
```

---

### 2.4 CLI 层：`src/vpn_simulator/cli/commands/stress.py`

**命令设计：**

```bash
# 启动压力测试
vpn-simulator stress start --protocol pptp --concurrency 100 --duration 60

# 查看测试状态
vpn-simulator stress status [TEST_ID]

# 停止测试
vpn-simulator stress stop [TEST_ID]

# 生成报告
vpn-simulator stress report [TEST_ID] --format html --output report.html

# 列出所有测试
vpn-simulator stress list
```

**实现要点：**
- 使用 click 库实现命令行参数解析
- 使用 rich 库美化输出
- 支持 JSON 输出格式（`--json` 选项）

---

### 2.5 数据库支持

在 `src/vpn_simulator/core/database.py` 中添加新表：

```python
class StressTestRecord(Base):
    __tablename__ = "stress_tests"
    
    id = Column(String(36), primary_key=True)
    protocol = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    config = Column(JSON, nullable=False)
    stats = Column(JSON)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    report = Column(JSON)
```

---

## 3. 文件变更清单

| 文件 | 操作 | 描述 |
|------|------|------|
| `src/vpn_simulator/domain/stress_test.py` | 新建 | 压力测试领域模型 |
| `src/vpn_simulator/services/stress_test.py` | 新建 | 压力测试服务层 |
| `src/vpn_simulator/api/routers/stress.py` | 新建 | 压力测试 API 路由 |
| `src/vpn_simulator/cli/commands/stress.py` | 新建 | 压力测试 CLI 命令 |
| `src/vpn_simulator/domain/__init__.py` | 修改 | 导出压力测试模型 |
| `src/vpn_simulator/services/__init__.py` | 修改 | 导出压力测试服务 |
| `src/vpn_simulator/api/app.py` | 修改 | 注册压力测试路由 |
| `src/vpn_simulator/api/routers/__init__.py` | 修改 | 导出路由模块 |
| `src/vpn_simulator/cli/__init__.py` | 修改 | 注册压力测试命令 |
| `src/vpn_simulator/core/database.py` | 修改 | 添加数据库表 |
| `src/vpn_simulator/core/events.py` | 修改 | 添加事件类型 |

---

## 4. 测试策略

### 4.1 单元测试
- `tests/unit/test_stress_test_domain.py` - 测试领域模型
- `tests/unit/test_stress_test_service.py` - 测试服务层

### 4.2 集成测试
- `tests/integration/test_stress_api.py` - 测试 API 端点
- `tests/integration/test_stress_cli.py` - 测试 CLI 命令

### 4.3 验证步骤
1. 运行单元测试：`pytest tests/unit/test_stress_test_*.py`
2. 运行集成测试：`pytest tests/integration/test_stress_*.py`
3. 手动验证 API：
   ```bash
   # 启动服务器
   uvicorn vpn_simulator.api.app:app --reload
   
   # 测试 API
   curl -X POST http://localhost:8080/api/v1/stress/start \
     -H "Content-Type: application/json" \
     -d '{"protocol": "pptp", "concurrency": 10, "duration": 5}'
   ```
4. 手动验证 CLI：
   ```bash
   vpn-simulator stress start --protocol pptp --concurrency 10 --duration 5
   vpn-simulator stress status
   vpn-simulator stress report --format json
   ```

---

## 5. 备忘录

### 5.1 技术决策
- 使用 `asyncio.Semaphore` 控制并发数
- 使用 `asyncio.create_task` 并发执行连接模拟
- 使用 `random.uniform` 模拟连接延迟（50-200ms）
- 使用百分位数算法计算 p50/p95/p99 延迟

### 5.2 风险点
- 高并发场景下的内存占用（需限制历史记录数量）
- asyncio 任务取消的优雅处理
- 报告生成的性能优化

### 5.3 后续扩展
- 支持自定义连接延迟分布
- 支持多种协议同时压测
- 支持压测结果对比
- 支持 WebSocket 实时推送统计信息
