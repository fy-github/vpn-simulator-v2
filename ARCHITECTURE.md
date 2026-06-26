# VPN Simulator v2 - 技术架构设计文档

## 文档信息

| 项目 | 说明 |
|------|------|
| 版本 | 2.0.0 |
| 日期 | 2026-06-24 |
| 作者 | VPN Simulator Team |
| 状态 | 设计阶段 |

---

## 一、设计原则

### 1.1 核心原则

| 原则 | 说明 | 实践 |
|------|------|------|
| **插件化** | 所有功能模块可插拔 | 协议、故障、攻击都是插件 |
| **依赖倒置** | 高层不依赖低层抽象 | 使用依赖注入容器 |
| **事件驱动** | 组件间通过事件解耦 | 统一事件总线 |
| **配置优先** | 行为由配置决定，非硬编码 | YAML + 环境变量 + CLI |
| **可观测性** | 日志、指标、追踪三位一体 | 结构化日志 + OpenTelemetry |
| **跨平台** | 核心逻辑平台无关 | 平台抽象层 |

### 1.2 设计模式

```
┌─────────────────────────────────────────────────────────────────┐
│                      设计模式应用                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  创建型模式:                                                     │
│  ├── 工厂模式: 协议实例创建                                     │
│  ├── 单例模式: 配置管理器、事件总线                             │
│  └── 建造者模式: 复杂配置对象构建                               │
│                                                                  │
│  结构型模式:                                                     │
│  ├── 适配器模式: 跨平台套接字适配                               │
│  ├── 装饰器模式: 故障注入叠加                                   │
│  ├── 外观模式: 简化的公共 API                                   │
│  └── 代理模式: 远程节点通信                                     │
│                                                                  │
│  行为型模式:                                                     │
│  ├── 状态模式: 协议状态机                                       │
│  ├── 策略模式: 不同故障注入策略                                 │
│  ├── 观察者模式: 事件订阅发布                                   │
│  ├── 命令模式: CLI 命令封装                                     │
│  └── 模板方法模式: 协议基类定义流程                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、整体架构

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      表示层 (Presentation)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Web GUI    │  │    CLI      │  │  SDK/Client │            │
│  │  (React)    │  │  (Click)    │  │  (Python)   │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         └────────────────┴────────────────┘                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      接口层 (Interface)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│  │  │ REST    │  │WebSocket│  │  gRPC   │  │ GraphQL │  │   │
│  │  │ Router  │  │ Handler │  │ Service │  │ Schema  │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      应用层 (Application)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Application Services                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Protocol    │  │  Fault      │  │  Attack     │    │   │
│  │  │ Service     │  │  Service    │  │  Service    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Connection  │  │  Tutorial   │  │  Recording  │    │   │
│  │  │ Service     │  │  Service    │  │  Service    │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      领域层 (Domain)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Core Domain Models                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Protocol    │  │ Connection  │  │ Packet      │    │   │
│  │  │ (状态机)    │  │ (连接)      │  │ (报文)      │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Fault       │  │ Attack      │  │ Topology    │    │   │
│  │  │ (故障)      │  │ (攻击)      │  │ (拓扑)      │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Plugin System                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │  Protocol   │  │   Fault     │  │   Attack    │    │   │
│  │  │  Registry   │  │   Registry  │  │   Registry  │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      基础设施层 (Infrastructure)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Event Bus  │  │  Config     │  │  Database   │            │
│  │  (事件总线) │  │  Manager    │  │  (SQLite)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Platform   │  │  Logger     │  │  Metrics    │            │
│  │  Adapter    │  │  (结构化)   │  │  (Prometheus)│           │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖图

```
┌─────────────────────────────────────────────────────────────────┐
│                      模块依赖关系                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    vpn-simulator-core                     │   │
│  │  (核心领域模型、接口定义、事件系统)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  protocols  │    │   faults    │    │   attacks   │         │
│  │  (协议插件) │    │ (故障插件)  │    │ (攻击插件)  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                    │                    │             │
│         └────────────────────┼────────────────────┘             │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    vpn-simulator-app                      │   │
│  │  (应用服务、API、CLI)                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   web-ui    │    │    cli      │    │   sdk       │         │
│  │  (Web界面)  │    │ (命令行)    │    │ (开发包)    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、插件系统设计

### 3.1 插件架构

```python
# 插件系统核心设计

from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PluginType(Enum):
    """插件类型枚举"""
    PROTOCOL = "protocol"      # 协议插件
    FAULT = "fault"            # 故障注入插件
    ATTACK = "attack"          # 攻击插件
    EXPORTER = "exporter"      # 导出器插件
    AUTH = "auth"              # 认证插件

@dataclass
class PluginMeta:
    """插件元数据"""
    name: str                   # 插件名称
    version: str                # 版本号
    author: str                 # 作者
    description: str            # 描述
    plugin_type: PluginType     # 插件类型
    dependencies: list[str]     # 依赖的其他插件
    config_schema: dict         # 配置 schema

class Plugin(ABC):
    """插件基类"""
    
    @abstractmethod
    def meta(self) -> PluginMeta:
        """返回插件元数据"""
        pass
    
    @abstractmethod
    async def initialize(self, context: 'PluginContext') -> None:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭插件"""
        pass

class PluginRegistry:
    """插件注册表"""
    
    _plugins: Dict[str, Plugin] = {}
    _plugins_by_type: Dict[PluginType, list[Plugin]] = {}
    
    @classmethod
    def register(cls, plugin: Plugin) -> None:
        """注册插件"""
        meta = plugin.meta()
        cls._plugins[meta.name] = plugin
        
        if meta.plugin_type not in cls._plugins_by_type:
            cls._plugins_by_type[meta.plugin_type] = []
        cls._plugins_by_type[meta.plugin_type].append(plugin)
    
    @classmethod
    def get(cls, name: str) -> Optional[Plugin]:
        """获取插件"""
        return cls._plugins.get(name)
    
    @classmethod
    def get_by_type(cls, plugin_type: PluginType) -> list[Plugin]:
        """按类型获取插件"""
        return cls._plugins_by_type.get(plugin_type, [])
    
    @classmethod
    def list_all(cls) -> list[PluginMeta]:
        """列出所有插件"""
        return [p.meta() for p in cls._plugins.values()]

# 插件装饰器
def plugin(name: str):
    """插件注册装饰器"""
    def decorator(cls):
        plugin_instance = cls()
        PluginRegistry.register(plugin_instance)
        return cls
    return decorator

# 使用示例
@plugin("pptp")
class PPTPProtocol(Plugin):
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="pptp",
            version="1.0.0",
            author="VPN Simulator",
            description="PPTP Protocol Implementation",
            plugin_type=PluginType.PROTOCOL,
            dependencies=[],
            config_schema={...}
        )
    
    async def initialize(self, context: PluginContext) -> None:
        # 初始化逻辑
        pass
    
    async def shutdown(self) -> None:
        # 清理逻辑
        pass
```

### 3.2 插件目录结构

```
plugins/
├── protocols/                    # 协议插件
│   ├── pptp/
│   │   ├── __init__.py
│   │   ├── plugin.py            # 插件入口
│   │   ├── server.py            # 服务端实现
│   │   ├── state_machine.py     # 状态机
│   │   ├── handlers.py          # 报文处理
│   │   └── config.yaml          # 默认配置
│   ├── l2tp/
│   ├── openvpn/
│   ├── ipsec/
│   ├── ikev2/
│   ├── wireguard/
│   ├── sstp/                    # 新增
│   └── openconnect/             # 新增
│
├── faults/                       # 故障注入插件
│   ├── latency/
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   └── injector.py
│   ├── packet_loss/
│   ├── bandwidth/
│   ├── reorder/
│   ├── duplicate/
│   └── corrupt/
│
├── attacks/                      # 攻击插件
│   ├── mitm/
│   │   ├── __init__.py
│   │   ├── plugin.py
│   │   └── attack.py
│   ├── replay/
│   ├── brute_force/
│   ├── downgrade/
│   └── traffic_analysis/
│
├── exporters/                    # 导出器插件
│   ├── pcap/
│   │   ├── __init__.py
│   │   └── exporter.py
│   ├── json/
│   ├── csv/
│   └── html/
│
└── auth/                         # 认证插件
    ├── local/
    ├── ldap/
    └── oauth2/
```

---

## 四、核心领域模型

### 4.1 协议状态机

```python
# 协议状态机核心设计

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

@dataclass
class StateTransition:
    """状态转换"""
    from_state: str
    to_state: str
    event: str
    guard: Optional[Callable] = None      # 守卫条件
    action: Optional[Callable] = None     # 转换动作
    description: str = ""

@dataclass
class State:
    """状态定义"""
    name: str
    description: str
    is_initial: bool = False
    is_final: bool = False
    on_enter: Optional[Callable] = None   # 进入状态动作
    on_exit: Optional[Callable] = None    # 退出状态动作

class ProtocolStateMachine(ABC):
    """协议状态机基类"""
    
    def __init__(self, protocol_name: str):
        self.protocol_name = protocol_name
        self.states: Dict[str, State] = {}
        self.transitions: List[StateTransition] = []
        self.current_state: Optional[str] = None
        self.history: List[Dict[str, Any]] = []
        self._listeners: List[Callable] = []
    
    def add_state(self, state: State) -> None:
        """添加状态"""
        self.states[state.name] = state
        if state.is_initial:
            self.current_state = state.name
    
    def add_transition(self, transition: StateTransition) -> None:
        """添加转换"""
        self.transitions.append(transition)
    
    async def trigger(self, event: str, context: Dict[str, Any] = None) -> bool:
        """触发事件"""
        # 查找匹配的转换
        transition = self._find_transition(self.current_state, event)
        if not transition:
            return False
        
        # 检查守卫条件
        if transition.guard and not transition.guard(context):
            return False
        
        # 记录历史
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "from": self.current_state,
            "to": transition.to_state,
            "event": event,
            "context": context
        })
        
        # 执行退出动作
        current = self.states[self.current_state]
        if current.on_exit:
            await current.on_exit(context)
        
        # 执行转换动作
        if transition.action:
            await transition.action(context)
        
        # 更新状态
        old_state = self.current_state
        self.current_state = transition.to_state
        
        # 执行进入动作
        new = self.states[self.current_state]
        if new.on_enter:
            await new.on_enter(context)
        
        # 通知监听器
        await self._notify_listeners(old_state, self.current_state, event)
        
        return True
    
    def _find_transition(self, from_state: str, event: str) -> Optional[StateTransition]:
        """查找转换"""
        for t in self.transitions:
            if t.from_state == from_state and t.event == event:
                return t
        return None
    
    def on_transition(self, listener: Callable) -> None:
        """注册转换监听器"""
        self._listeners.append(listener)
    
    async def _notify_listeners(self, from_state: str, to_state: str, event: str) -> None:
        """通知监听器"""
        for listener in self._listeners:
            await listener(from_state, to_state, event)
    
    def get_visualization_data(self) -> Dict[str, Any]:
        """获取可视化数据"""
        return {
            "protocol": self.protocol_name,
            "current_state": self.current_state,
            "states": [
                {
                    "name": s.name,
                    "description": s.description,
                    "is_initial": s.is_initial,
                    "is_final": s.is_final,
                    "is_current": s.name == self.current_state
                }
                for s in self.states.values()
            ],
            "transitions": [
                {
                    "from": t.from_state,
                    "to": t.to_state,
                    "event": t.event,
                    "description": t.description
                }
                for t in self.transitions
            ],
            "history": self.history
        }

# PPTP 状态机实现示例
class PPTPStateMachine(ProtocolStateMachine):
    """PPTP 协议状态机"""
    
    def __init__(self):
        super().__init__("PPTP")
        self._setup_states()
        self._setup_transitions()
    
    def _setup_states(self):
        """定义状态"""
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            State("WAIT_SCCRQ", "等待 SCCRQ"),
            State("SCCRP_SENT", "已发送 SCCRP"),
            State("WAIT_OCRQ", "等待 OCRQ"),
            State("OCRP_SENT", "已发送 OCRP"),
            State("GRE_ESTABLISHED", "GRE 隧道已建立"),
            State("LCP_NEGOTIATION", "LCP 协商中"),
            State("AUTHENTICATION", "认证中"),
            State("IPCP_NEGOTIATION", "IPCP 协商中"),
            State("CONNECTED", "已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)
    
    def _setup_transitions(self):
        """定义转换"""
        transitions = [
            StateTransition("INITIAL", "WAIT_SCCRQ", "START", 
                          description="开始监听"),
            StateTransition("WAIT_SCCRQ", "SCCRP_SENT", "RECEIVE_SCCRQ",
                          description="收到 SCCRQ，发送 SCCRP"),
            StateTransition("SCCRP_SENT", "WAIT_OCRQ", "SCCRP_SENT_OK",
                          description="SCCRP 发送成功"),
            StateTransition("WAIT_OCRQ", "OCRP_SENT", "RECEIVE_OCRQ",
                          description="收到 OCRQ，发送 OCRP"),
            StateTransition("OCRP_SENT", "GRE_ESTABLISHED", "GRE_READY",
                          description="GRE 隧道就绪"),
            StateTransition("GRE_ESTABLISHED", "LCP_NEGOTIATION", "START_LCP",
                          description="开始 LCP 协商"),
            StateTransition("LCP_NEGOTIATION", "AUTHENTICATION", "LCP_COMPLETE",
                          description="LCP 完成，开始认证"),
            StateTransition("AUTHENTICATION", "IPCP_NEGOTIATION", "AUTH_SUCCESS",
                          description="认证成功，开始 IPCP"),
            StateTransition("IPCP_NEGOTIATION", "CONNECTED", "IPCP_COMPLETE",
                          description="IPCP 完成，连接建立"),
        ]
        for t in transitions:
            self.add_transition(t)
```

### 4.2 连接模型

```python
# 连接模型设计

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid

class ConnectionState(Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class ConnectionType(Enum):
    """连接类型"""
    CLIENT = "client"
    SERVER = "server"

@dataclass
class ConnectionInfo:
    """连接信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol: str = ""
    state: ConnectionState = ConnectionState.CONNECTING
    connection_type: ConnectionType = ConnectionType.CLIENT
    
    # 网络信息
    local_address: str = ""
    local_port: int = 0
    remote_address: str = ""
    remote_port: int = 0
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    
    # 统计信息
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    
    # 协议特定信息
    protocol_data: Dict[str, Any] = field(default_factory=dict)
    
    # 错误信息
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "protocol": self.protocol,
            "state": self.state.value,
            "connection_type": self.connection_type.value,
            "local_address": self.local_address,
            "local_port": self.local_port,
            "remote_address": self.remote_address,
            "remote_port": self.remote_port,
            "created_at": self.created_at.isoformat(),
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "protocol_data": self.protocol_data,
            "error_message": self.error_message,
            "error_code": self.error_code,
        }

class ConnectionManager:
    """连接管理器"""
    
    def __init__(self):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._event_bus: Optional['EventBus'] = None
    
    async def create_connection(self, protocol: str, **kwargs) -> ConnectionInfo:
        """创建连接"""
        conn = ConnectionInfo(protocol=protocol, **kwargs)
        self._connections[conn.id] = conn
        
        if self._event_bus:
            await self._event_bus.emit("connection.created", conn.to_dict())
        
        return conn
    
    async def update_state(self, conn_id: str, state: ConnectionState) -> None:
        """更新连接状态"""
        conn = self._connections.get(conn_id)
        if not conn:
            raise ValueError(f"Connection {conn_id} not found")
        
        old_state = conn.state
        conn.state = state
        
        if state == ConnectionState.CONNECTED:
            conn.connected_at = datetime.now()
        elif state == ConnectionState.DISCONNECTED:
            conn.disconnected_at = datetime.now()
        
        if self._event_bus:
            await self._event_bus.emit("connection.state_changed", {
                "connection_id": conn_id,
                "old_state": old_state.value,
                "new_state": state.value,
                "timestamp": datetime.now().isoformat()
            })
    
    async def get_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """获取连接"""
        return self._connections.get(conn_id)
    
    async def list_connections(self, protocol: str = None) -> List[ConnectionInfo]:
        """列出连接"""
        connections = list(self._connections.values())
        if protocol:
            connections = [c for c in connections if c.protocol == protocol]
        return connections
    
    async def remove_connection(self, conn_id: str) -> None:
        """移除连接"""
        if conn_id in self._connections:
            del self._connections[conn_id]
            
            if self._event_bus:
                await self._event_bus.emit("connection.removed", {
                    "connection_id": conn_id
                })
```

### 4.3 报文模型

```python
# 报文模型设计

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
import struct

class PacketDirection(Enum):
    """报文方向"""
    INCOMING = "incoming"   # 入站
    OUTGOING = "outgoing"   # 出站

class PacketType(Enum):
    """报文类型"""
    CONTROL = "control"     # 控制报文
    DATA = "data"           # 数据报文
    ERROR = "error"         # 错误报文

@dataclass
class PacketField:
    """报文字段"""
    name: str
    offset: int
    length: int
    value: Any
    description: str
    field_type: str = "bytes"  # bytes, int, string, ip, mac
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "offset": self.offset,
            "length": self.length,
            "value": str(self.value),
            "description": self.description,
            "field_type": self.field_type
        }

@dataclass
class PacketInfo:
    """报文信息"""
    id: str
    timestamp: datetime
    direction: PacketDirection
    packet_type: PacketType
    protocol: str
    
    # 网络层
    src_ip: str = ""
    dst_ip: str = ""
    src_port: int = 0
    dst_port: int = 0
    
    # 报文内容
    raw_data: bytes = b""
    fields: List[PacketField] = field(default_factory=list)
    
    # 解析信息
    parsed: bool = False
    parse_error: Optional[str] = None
    
    # 关联信息
    connection_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "packet_type": self.packet_type.value,
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "raw_data_hex": self.raw_data.hex(),
            "fields": [f.to_dict() for f in self.fields],
            "parsed": self.parsed,
            "parse_error": self.parse_error,
            "connection_id": self.connection_id,
            "session_id": self.session_id,
        }
    
    def to_pcap_record(self) -> bytes:
        """转换为 PCAP 记录"""
        # PCAP record header
        ts_sec = int(self.timestamp.timestamp())
        ts_usec = int((self.timestamp.timestamp() % 1) * 1000000)
        incl_len = len(self.raw_data)
        orig_len = incl_len
        
        header = struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len)
        return header + self.raw_data
```

---

## 五、事件系统设计

### 5.1 事件总线

```python
# 事件总线设计

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """事件"""
    name: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    event_id: str = ""

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = 1000
    
    def on(self, event_name: str, handler: Callable) -> None:
        """注册同步事件处理器"""
        self._handlers[event_name].append(handler)
    
    def on_async(self, event_name: str, handler: Callable) -> None:
        """注册异步事件处理器"""
        self._async_handlers[event_name].append(handler)
    
    def off(self, event_name: str, handler: Callable) -> None:
        """取消注册事件处理器"""
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)
        if handler in self._async_handlers[event_name]:
            self._async_handlers[event_name].remove(handler)
    
    async def emit(self, event_name: str, data: Dict[str, Any] = None, source: str = "") -> None:
        """触发事件"""
        event = Event(
            name=event_name,
            data=data or {},
            source=source
        )
        
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # 执行同步处理器
        for handler in self._handlers.get(event_name, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in sync handler for {event_name}: {e}")
        
        # 执行异步处理器
        for handler in self._async_handlers.get(event_name, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in async handler for {event_name}: {e}")
    
    def get_history(self, event_name: str = None, limit: int = 100) -> List[Event]:
        """获取事件历史"""
        if event_name:
            events = [e for e in self._history if e.name == event_name]
        else:
            events = self._history
        return events[-limit:]

# 事件类型定义
class EventTypes:
    """事件类型常量"""
    
    # 协议事件
    PROTOCOL_STARTED = "protocol.started"
    PROTOCOL_STOPPED = "protocol.stopped"
    PROTOCOL_ERROR = "protocol.error"
    
    # 连接事件
    CONNECTION_CREATED = "connection.created"
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_CLOSED = "connection.closed"
    CONNECTION_ERROR = "connection.error"
    
    # 状态机事件
    STATE_TRANSITION = "state.transition"
    
    # 报文事件
    PACKET_RECEIVED = "packet.received"
    PACKET_SENT = "packet.sent"
    PACKET_DROPPED = "packet.dropped"
    
    # 故障注入事件
    FAULT_INJECTED = "fault.injected"
    FAULT_REMOVED = "fault.removed"
    
    # 攻击事件
    ATTACK_STARTED = "attack.started"
    ATTACK_COMPLETED = "attack.completed"
    ATTACK_DETECTED = "attack.detected"
    
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "config.changed"
```

---

## 六、配置管理设计

### 6.1 配置管理器

```python
# 配置管理设计

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """配置"""
    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 8080
    
    # 数据库配置
    database_url: str = "sqlite:///vpn_simulator.db"
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"
    
    # 协议配置
    protocols: Dict[str, Any] = field(default_factory=dict)
    
    # 故障注入配置
    faults: Dict[str, Any] = field(default_factory=dict)
    
    # 攻击配置
    attacks: Dict[str, Any] = field(default_factory=dict)
    
    # 国际化配置
    locale: str = "zh-CN"
    
    # 跨平台配置
    platform: str = "auto"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".vpn-simulator"
        self.config_file = self.config_dir / "config.yaml"
        self._config: Optional[Config] = None
        self._watchers: List[Callable] = []
    
    def load(self) -> Config:
        """加载配置"""
        # 1. 加载默认配置
        config = Config()
        
        # 2. 加载配置文件
        if self.config_file.exists():
            with open(self.config_file) as f:
                file_config = yaml.safe_load(f) or {}
                config = self._merge_config(config, file_config)
        
        # 3. 加载环境变量
        config = self._load_env_vars(config)
        
        self._config = config
        return config
    
    def save(self, config: Config = None) -> None:
        """保存配置"""
        config = config or self._config
        if not config:
            raise ValueError("No config to save")
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            yaml.dump(self._config_to_dict(config), f, default_flow_style=False)
        
        self._notify_watchers()
    
    def _merge_config(self, base: Config, override: Dict[str, Any]) -> Config:
        """合并配置"""
        # 深度合并逻辑
        for key, value in override.items():
            if hasattr(base, key):
                setattr(base, key, value)
        return base
    
    def _load_env_vars(self, config: Config) -> Config:
        """加载环境变量"""
        env_mapping = {
            "VPN_SIM_SERVER_HOST": "server_host",
            "VPN_SIM_SERVER_PORT": "server_port",
            "VPN_SIM_DATABASE_URL": "database_url",
            "VPN_SIM_LOG_LEVEL": "log_level",
            "VPN_SIM_LOCALE": "locale",
        }
        
        for env_var, config_attr in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                # 类型转换
                if config_attr == "server_port":
                    value = int(value)
                setattr(config, config_attr, value)
        
        return config
    
    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """配置转字典"""
        return {
            "server": {
                "host": config.server_host,
                "port": config.server_port,
            },
            "database": {
                "url": config.database_url,
            },
            "logging": {
                "level": config.log_level,
                "format": config.log_format,
            },
            "protocols": config.protocols,
            "faults": config.faults,
            "attacks": config.attacks,
            "i18n": {
                "locale": config.locale,
            },
        }
    
    def on_change(self, callback: Callable) -> None:
        """注册配置变更监听器"""
        self._watchers.append(callback)
    
    def _notify_watchers(self) -> None:
        """通知监听器"""
        for watcher in self._watchers:
            try:
                watcher(self._config)
            except Exception as e:
                logger.error(f"Error notifying config watcher: {e}")
    
    @property
    def config(self) -> Config:
        """获取当前配置"""
        if not self._config:
            self.load()
        return self._config
```

---

## 七、跨平台适配层

### 7.1 平台抽象

```python
# 跨平台适配层设计

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import platform
import logging

logger = logging.getLogger(__name__)

@dataclass
class PlatformInfo:
    """平台信息"""
    os: str                  # windows, darwin, linux
    arch: str                # x86_64, arm64
    version: str             # 系统版本
    is_admin: bool           # 是否管理员/root
    python_version: str      # Python 版本

class PlatformAdapter(ABC):
    """平台适配器基类"""
    
    @abstractmethod
    def get_platform_info(self) -> PlatformInfo:
        """获取平台信息"""
        pass
    
    @abstractmethod
    async def check_privileges(self) -> bool:
        """检查权限"""
        pass
    
    @abstractmethod
    async def create_raw_socket(self, protocol: int) -> Any:
        """创建原始套接字"""
        pass
    
    @abstractmethod
    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        """配置防火墙"""
        pass
    
    @abstractmethod
    async def get_network_interfaces(self) -> list[Dict[str, Any]]:
        """获取网络接口"""
        pass
    
    @abstractmethod
    async def manage_service(self, action: str, service_name: str) -> bool:
        """管理系统服务"""
        pass

class WindowsAdapter(PlatformAdapter):
    """Windows 平台适配器"""
    
    def get_platform_info(self) -> PlatformInfo:
        return PlatformInfo(
            os="windows",
            arch=platform.machine(),
            version=platform.version(),
            is_admin=self._check_admin(),
            python_version=platform.python_version()
        )
    
    async def check_privileges(self) -> bool:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    
    async def create_raw_socket(self, protocol: int) -> Any:
        import socket
        # Windows 原始套接字需要管理员权限
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock
    
    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        # 使用 netsh 命令配置 Windows 防火墙
        import subprocess
        cmd = f'netsh advfirewall firewall add rule name="{rule["name"]}" ...'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    async def get_network_interfaces(self) -> list[Dict[str, Any]]:
        import psutil
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            interfaces.append({
                "name": name,
                "addresses": [addr.address for addr in addrs]
            })
        return interfaces
    
    async def manage_service(self, action: str, service_name: str) -> bool:
        import subprocess
        cmd = f'net {action} {service_name}'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    def _check_admin(self) -> bool:
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

class MacOSAdapter(PlatformAdapter):
    """macOS 平台适配器"""
    
    def get_platform_info(self) -> PlatformInfo:
        return PlatformInfo(
            os="darwin",
            arch=platform.machine(),
            version=platform.mac_ver()[0],
            is_admin=self._check_root(),
            python_version=platform.python_version()
        )
    
    async def check_privileges(self) -> bool:
        import os
        return os.geteuid() == 0
    
    async def create_raw_socket(self, protocol: int) -> Any:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock
    
    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        # macOS 使用 pfctl
        import subprocess
        cmd = f'echo "{rule["pf_rule"]}" | sudo pfctl -f -'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    async def get_network_interfaces(self) -> list[Dict[str, Any]]:
        import psutil
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            interfaces.append({
                "name": name,
                "addresses": [addr.address for addr in addrs]
            })
        return interfaces
    
    async def manage_service(self, action: str, service_name: str) -> bool:
        import subprocess
        if action == "start":
            cmd = f'launchctl load {service_name}'
        elif action == "stop":
            cmd = f'launchctl unload {service_name}'
        else:
            return False
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    def _check_root(self) -> bool:
        import os
        return os.geteuid() == 0

class LinuxAdapter(PlatformAdapter):
    """Linux 平台适配器"""
    
    def get_platform_info(self) -> PlatformInfo:
        return PlatformInfo(
            os="linux",
            arch=platform.machine(),
            version=platform.release(),
            is_admin=self._check_root(),
            python_version=platform.python_version()
        )
    
    async def check_privileges(self) -> bool:
        import os
        return os.geteuid() == 0
    
    async def create_raw_socket(self, protocol: int) -> Any:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return sock
    
    async def configure_firewall(self, rule: Dict[str, Any]) -> bool:
        # Linux 使用 iptables
        import subprocess
        cmd = f'iptables {rule["action"]} {rule["chain"]} ...'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    async def get_network_interfaces(self) -> list[Dict[str, Any]]:
        import psutil
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            interfaces.append({
                "name": name,
                "addresses": [addr.address for addr in addrs]
            })
        return interfaces
    
    async def manage_service(self, action: str, service_name: str) -> bool:
        import subprocess
        cmd = f'systemctl {action} {service_name}'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0
    
    def _check_root(self) -> bool:
        import os
        return os.geteuid() == 0

def get_platform_adapter() -> PlatformAdapter:
    """获取平台适配器"""
    system = platform.system().lower()
    
    if system == "windows":
        return WindowsAdapter()
    elif system == "darwin":
        return MacOSAdapter()
    elif system == "linux":
        return LinuxAdapter()
    else:
        raise ValueError(f"Unsupported platform: {system}")
```

---

## 八、API 设计

### 8.1 REST API 端点

```yaml
# REST API 设计

openapi: 3.0.0
info:
  title: VPN Simulator API
  version: 2.0.0
  description: VPN Simulator REST API

paths:
  # 协议管理
  /api/v1/protocols:
    get:
      summary: 列出所有协议
      responses:
        200:
          description: 协议列表
          
  /api/v1/protocols/{name}/start:
    post:
      summary: 启动协议
      parameters:
        - name: name
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                port:
                  type: integer
                config:
                  type: object
      responses:
        200:
          description: 协议已启动
          
  /api/v1/protocols/{name}/stop:
    post:
      summary: 停止协议
      responses:
        200:
          description: 协议已停止
          
  /api/v1/protocols/{name}/status:
    get:
      summary: 获取协议状态
      responses:
        200:
          description: 协议状态
          
  # 连接管理
  /api/v1/connections:
    get:
      summary: 列出所有连接
      parameters:
        - name: protocol
          in: query
          schema:
            type: string
        - name: state
          in: query
          schema:
            type: string
      responses:
        200:
          description: 连接列表
          
  /api/v1/connections/{id}:
    get:
      summary: 获取连接详情
      responses:
        200:
          description: 连接详情
          
    delete:
      summary: 断开连接
      responses:
        200:
          description: 连接已断开
          
  # 故障注入
  /api/v1/faults:
    get:
      summary: 列出所有故障
    post:
      summary: 添加故障
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                type:
                  type: string
                  enum: [latency, packet_loss, bandwidth, reorder, duplicate, corrupt]
                params:
                  type: object
                target:
                  type: string
      responses:
        201:
          description: 故障已添加
          
  /api/v1/faults/{id}:
    delete:
      summary: 移除故障
      responses:
        200:
          description: 故障已移除
          
  # 攻击
  /api/v1/attacks:
    get:
      summary: 列出所有攻击
    post:
      summary: 发起攻击
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                type:
                  type: string
                  enum: [mitm, replay, brute_force, downgrade, traffic_analysis]
                params:
                  type: object
                target:
                  type: string
      responses:
        200:
          description: 攻击已发起
          
  # 拓扑
  /api/v1/topology:
    get:
      summary: 获取拓扑
    put:
      summary: 更新拓扑
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Topology'
              
  # 日志
  /api/v1/logs:
    get:
      summary: 获取日志
      parameters:
        - name: protocol
          in: query
          schema:
            type: string
        - name: level
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
      responses:
        200:
          description: 日志列表
          
  # 统计
  /api/v1/stats:
    get:
      summary: 获取统计信息
      responses:
        200:
          description: 统计信息

  # 配置
  /api/v1/config:
    get:
      summary: 获取配置
    put:
      summary: 更新配置
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Config'

components:
  schemas:
    Protocol:
      type: object
      properties:
        name:
          type: string
        state:
          type: string
        port:
          type: integer
        connections:
          type: integer
          
    Connection:
      type: object
      properties:
        id:
          type: string
        protocol:
          type: string
        state:
          type: string
        local_address:
          type: string
        remote_address:
          type: string
          
    Fault:
      type: object
      properties:
        id:
          type: string
        type:
          type: string
        params:
          type: object
        active:
          type: boolean
          
    Attack:
      type: object
      properties:
        id:
          type: string
        type:
          type: string
        status:
          type: string
        target:
          type: string
          
    Topology:
      type: object
      properties:
        nodes:
          type: array
          items:
            $ref: '#/components/schemas/Node'
        edges:
          type: array
          items:
            $ref: '#/components/schemas/Edge'
            
    Config:
      type: object
      properties:
        server:
          type: object
        protocols:
          type: object
        faults:
          type: object
```

### 8.2 WebSocket 事件

```python
# WebSocket 事件设计

from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import json

class WebSocketManager:
    """WebSocket 管理器"""
    
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._event_bus: Optional[EventBus] = None
    
    async def connect(self, websocket: WebSocket, channel: str = "default") -> None:
        """连接"""
        await websocket.accept()
        
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        """断开"""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
    
    async def broadcast(self, event: str, data: Dict[str, Any], channel: str = "default") -> None:
        """广播消息"""
        if channel not in self._connections:
            return
        
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        disconnected = set()
        for websocket in self._connections[channel]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.add(websocket)
        
        # 清理断开的连接
        self._connections[channel] -= disconnected
    
    async def send_to(self, websocket: WebSocket, event: str, data: Dict[str, Any]) -> None:
        """发送到特定连接"""
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        await websocket.send_text(message)
    
    def subscribe_to_events(self, event_bus: EventBus) -> None:
        """订阅事件总线"""
        self._event_bus = event_bus
        
        # 订阅所有事件并广播
        async def on_event(event: Event):
            await self.broadcast(event.name, event.data)
        
        event_bus.on_async("*", on_event)

# WebSocket 端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 处理客户端消息
            message = json.loads(data)
            
            if message.get("action") == "subscribe":
                # 订阅特定事件
                pass
            elif message.get("action") == "unsubscribe":
                # 取消订阅
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
```

---

## 九、数据库设计

### 9.1 数据库 Schema

```sql
-- 数据库 Schema 设计

-- 连接记录表
CREATE TABLE connections (
    id TEXT PRIMARY KEY,
    protocol TEXT NOT NULL,
    state TEXT NOT NULL,
    connection_type TEXT NOT NULL,
    local_address TEXT,
    local_port INTEGER,
    remote_address TEXT,
    remote_port INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    connected_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    bytes_sent INTEGER DEFAULT 0,
    bytes_received INTEGER DEFAULT 0,
    packets_sent INTEGER DEFAULT 0,
    packets_received INTEGER DEFAULT 0,
    protocol_data JSON,
    error_message TEXT,
    error_code TEXT
);

-- 报文记录表
CREATE TABLE packets (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    direction TEXT NOT NULL,
    packet_type TEXT NOT NULL,
    protocol TEXT NOT NULL,
    src_ip TEXT,
    dst_ip TEXT,
    src_port INTEGER,
    dst_port INTEGER,
    raw_data BLOB,
    fields JSON,
    connection_id TEXT REFERENCES connections(id),
    session_id TEXT
);

-- 状态机历史表
CREATE TABLE state_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    connection_id TEXT REFERENCES connections(id),
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    event TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSON
);

-- 故障配置表
CREATE TABLE faults (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    params JSON NOT NULL,
    target TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 攻击记录表
CREATE TABLE attacks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL,
    params JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result JSON
);

-- 配置历史表
CREATE TABLE config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config JSON NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT
);

-- 拓扑配置表
CREATE TABLE topologies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    topology JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_connections_protocol ON connections(protocol);
CREATE INDEX idx_connections_state ON connections(state);
CREATE INDEX idx_packets_timestamp ON packets(timestamp);
CREATE INDEX idx_packets_connection ON packets(connection_id);
CREATE INDEX idx_state_transitions_protocol ON state_transitions(protocol);
CREATE INDEX idx_state_transitions_connection ON state_transitions(connection_id);
```

---

## 十、部署架构

### 10.1 Docker 部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  # VPN Simulator 主服务
  vpn-simulator:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"     # REST API
      - "8081:8081"     # WebSocket
      - "1723:1723"     # PPTP
      - "1701:1701"     # L2TP
      - "1194:1194"     # OpenVPN
      - "500:500"       # IPSec
      - "4500:4500"     # IPSec NAT-T
      - "51820:51820"   # WireGuard
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - VPN_SIM_SERVER_HOST=0.0.0.0
      - VPN_SIM_SERVER_PORT=8080
      - VPN_SIM_DATABASE_URL=sqlite:///data/vpn_simulator.db
      - VPN_SIM_LOG_LEVEL=INFO
    networks:
      - vpn-network
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped
    
  # Web UI
  web-ui:
    build:
      context: ./web-ui
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://vpn-simulator:8080
    depends_on:
      - vpn-simulator
    networks:
      - vpn-network
    restart: unless-stopped
    
  # 数据库 (可选，生产环境)
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=vpn_simulator
      - POSTGRES_USER=vpn
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - vpn-network
    restart: unless-stopped
    
  # Redis (可选，缓存和消息队列)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - vpn-network
    restart: unless-stopped

networks:
  vpn-network:
    driver: bridge

volumes:
  postgres-data:
```

### 10.2 Kubernetes 部署

```yaml
# helm/values.yaml

replicaCount: 1

image:
  repository: vpn-simulator
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  ports:
    - name: api
      port: 8080
      targetPort: 8080
    - name: websocket
      port: 8081
      targetPort: 8081
    - name: pptp
      port: 1723
      targetPort: 1723
    - name: l2tp
      port: 1701
      targetPort: 1701
    - name: openvpn
      port: 1194
      targetPort: 1194
    - name: ipsec
      port: 500
      targetPort: 500
    - name: ipsec-nat-t
      port: 4500
      targetPort: 4500
    - name: wireguard
      port: 51820
      targetPort: 51820

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
  hosts:
    - host: vpn-simulator.example.com
      paths:
        - path: /
          pathType: Prefix

config:
  server:
    host: 0.0.0.0
    port: 8080
  database:
    url: sqlite:///data/vpn_simulator.db
  logging:
    level: INFO
    format: json

resources:
  limits:
    cpu: 1000m
    memory: 512Mi
  requests:
    cpu: 500m
    memory: 256Mi

persistence:
  enabled: true
  storageClass: standard
  accessModes:
    - ReadWriteOnce
  size: 10Gi

securityContext:
  capabilities:
    add:
      - NET_ADMIN
      - NET_RAW
```

---

## 十一、开发环境设置

### 11.1 项目结构

```
vpn-simulator-v2/
├── src/                          # 源代码
│   ├── vpn_simulator/            # 主包
│   │   ├── __init__.py
│   │   ├── main.py               # 入口点
│   │   ├── core/                 # 核心模块
│   │   │   ├── __init__.py
│   │   │   ├── events.py         # 事件系统
│   │   │   ├── config.py         # 配置管理
│   │   │   ├── database.py       # 数据库
│   │   │   └── platform.py       # 平台适配
│   │   ├── domain/               # 领域模型
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py       # 协议基类
│   │   │   ├── connection.py     # 连接模型
│   │   │   ├── packet.py         # 报文模型
│   │   │   ├── fault.py          # 故障模型
│   │   │   └── attack.py         # 攻击模型
│   │   ├── plugins/              # 插件系统
│   │   │   ├── __init__.py
│   │   │   ├── registry.py       # 插件注册表
│   │   │   ├── loader.py         # 插件加载器
│   │   │   └── context.py        # 插件上下文
│   │   ├── services/             # 应用服务
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py       # 协议服务
│   │   │   ├── connection.py     # 连接服务
│   │   │   ├── fault.py          # 故障服务
│   │   │   └── attack.py         # 攻击服务
│   │   ├── api/                  # API 层
│   │   │   ├── __init__.py
│   │   │   ├── app.py            # FastAPI 应用
│   │   │   ├── routers/          # 路由
│   │   │   ├── middleware/       # 中间件
│   │   │   └── websocket.py      # WebSocket
│   │   └── cli/                  # CLI 层
│   │       ├── __init__.py
│   │       └── commands.py       # CLI 命令
│   │
│   └── plugins/                  # 内置插件
│       ├── protocols/            # 协议插件
│       │   ├── pptp/
│       │   ├── l2tp/
│       │   ├── openvpn/
│       │   ├── ipsec/
│       │   ├── ikev2/
│       │   ├── wireguard/
│       │   ├── sstp/
│       │   └── openconnect/
│       ├── faults/               # 故障插件
│       │   ├── latency/
│       │   ├── packet_loss/
│       │   └── ...
│       ├── attacks/              # 攻击插件
│       │   ├── mitm/
│       │   ├── replay/
│       │   └── ...
│       └── exporters/            # 导出器插件
│           ├── pcap/
│           └── ...
│
├── web-ui/                       # Web 前端
│   ├── src/
│   │   ├── components/           # React 组件
│   │   ├── pages/                # 页面
│   │   ├── services/             # API 服务
│   │   ├── hooks/                # 自定义 Hook
│   │   ├── store/                # 状态管理
│   │   └── locales/              # 国际化
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── tests/                        # 测试
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── e2e/                      # 端到端测试
│
├── docs/                         # 文档
│   ├── api/                      # API 文档
│   ├── architecture/             # 架构文档
│   └── guides/                   # 使用指南
│
├── scripts/                      # 脚本
│   ├── build.py                  # 构建脚本
│   ├── deploy.py                 # 部署脚本
│   └── migrate.py                # 迁移脚本
│
├── docker/                       # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
│
├── helm/                         # Helm Chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│
├── config/                       # 配置文件
│   ├── default.yaml
│   ├── development.yaml
│   └── production.yaml
│
├── pyproject.toml                # Python 项目配置
├── poetry.lock                   # 依赖锁定
├── Makefile                      # 常用命令
└── README.md                     # 项目说明
```

### 11.2 pyproject.toml

```toml
[tool.poetry]
name = "vpn-simulator"
version = "2.0.0"
description = "VPN Protocol Simulator - Teaching, Testing, and Research Platform"
authors = ["VPN Simulator Team"]
license = "Apache-2.0"
readme = "README.md"
homepage = "https://github.com/vpn-simulator/vpn-simulator"
repository = "https://github.com/vpn-simulator/vpn-simulator"
keywords = ["vpn", "network", "simulator", "testing", "protocol"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Networking",
    "Topic :: Software Development :: Testing",
]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
websockets = "^12.0"
pydantic = "^2.5.0"
pyyaml = "^6.0.1"
python-dotenv = "^1.0.0"
click = "^8.1.7"
rich = "^13.7.0"
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
aiosqlite = "^0.19.0"
psutil = "^5.9.7"
structlog = "^24.1.0"
opentelemetry-api = "^1.22.0"
opentelemetry-sdk = "^1.22.0"
opentelemetry-instrumentation-fastapi = "^0.43b0"
httpx = "^0.26.0"
python-multipart = "^0.0.6"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
mypy = "^1.8.0"
ruff = "^0.1.9"
black = "^24.1.0"
isort = "^5.13.2"
pre-commit = "^3.6.0"

[tool.poetry.group.web.dependencies]
# Web UI dependencies are in web-ui/package.json

[tool.poetry.scripts]
vpn-simulator = "vpn_simulator.cli:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.isort]
profile = "black"
known_first_party = ["vpn_simulator"]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### 11.3 Makefile

```makefile
# Makefile

.PHONY: help install dev test lint format build run clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	poetry install

dev: ## 安装开发依赖
	poetry install --with dev

test: ## 运行测试
	poetry run pytest

test-cov: ## 运行测试并生成覆盖率报告
	poetry run pytest --cov=vpn_simulator --cov-report=html

lint: ## 运行 linting
	poetry run ruff check .
	poetry run mypy .

format: ## 格式化代码
	poetry run black .
	poetry run isort .

run: ## 运行应用
	poetry run uvicorn vpn_simulator.api.app:app --reload

run-cli: ## 运行 CLI
	poetry run vpn-simulator --help

build: ## 构建 Docker 镜像
	docker build -t vpn-simulator .

run-docker: ## 运行 Docker 容器
	docker-compose up -d

stop-docker: ## 停止 Docker 容器
	docker-compose down

clean: ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov

db-migrate: ## 运行数据库迁移
	poetry run alembic upgrade head

db-revision: ## 创建数据库迁移
	poetry run alembic revision --autogenerate -m "$(msg)"

docs: ## 生成文档
	poetry run mkdocs build

docs-serve: ## 本地预览文档
	poetry run mkdocs serve

web-install: ## 安装 Web UI 依赖
	cd web-ui && npm install

web-dev: ## 运行 Web UI 开发服务器
	cd web-ui && npm run dev

web-build: ## 构建 Web UI
	cd web-ui && npm run build
```

---

## 十二、安全考虑

### 12.1 安全清单

| 类别 | 措施 | 优先级 |
|------|------|--------|
| **认证** | API Key / JWT 认证 | P0 |
| **授权** | 基于角色的访问控制 (RBAC) | P0 |
| **输入验证** | 所有输入参数验证 | P0 |
| **SQL 注入** | 使用 ORM，参数化查询 | P0 |
| **XSS 防护** | 输出编码，CSP 头 | P0 |
| **CSRF 防护** | CSRF Token | P1 |
| **HTTPS** | 强制 HTTPS | P0 |
| **密钥管理** | 环境变量，密钥轮换 | P0 |
| **审计日志** | 记录所有敏感操作 | P1 |
| **速率限制** | API 速率限制 | P1 |
| **容器安全** | 非 root 运行，最小权限 | P1 |
| **依赖扫描** | 定期扫描依赖漏洞 | P1 |

---

## 十三、性能考虑

### 13.1 性能指标

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| API 响应时间 | < 100ms (P95) | Prometheus |
| WebSocket 延迟 | < 50ms | 自定义指标 |
| 并发连接数 | > 1000 | 压力测试 |
| 内存使用 | < 512MB | 监控 |
| CPU 使用 | < 50% | 监控 |
| 启动时间 | < 5s | 计时 |

### 13.2 优化策略

| 策略 | 应用场景 |
|------|----------|
| 异步 I/O | 所有网络操作 |
| 连接池 | 数据库连接 |
| 缓存 | 配置、静态数据 |
| 批量操作 | 日志写入、统计更新 |
| 懒加载 | 插件、大型对象 |
| 压缩 | WebSocket 消息、API 响应 |

---

## 十四、监控和可观测性

### 14.1 监控架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      监控架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    应用层                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Metrics   │  │    Logs     │  │   Traces    │    │   │
│  │  │  (Prometheus)│  │  (ELK/Loki) │  │  (Jaeger)   │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐   │
│  │                    采集层                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ OpenTelemetry│ │  Fluentd    │  │  Zipkin     │    │   │
│  │  │   SDK       │  │             │  │             │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐   │
│  │                    存储层                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Prometheus  │  │ Elasticsearch│ │  Jaeger     │    │   │
│  │  │             │  │  / Loki     │  │             │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐   │
│  │                    可视化层                                │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                    Grafana                          │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十五、附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| 插件 | 可独立加载的功能模块 |
| 状态机 | 描述协议状态转换的数学模型 |
| 故障注入 | 人为引入故障以测试系统韧性 |
| 拓扑 | 网络节点和连接的布局 |
| PCAP | 网络抓包文件格式 |

### B. 参考文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [OpenTelemetry 文档](https://opentelemetry.io/)
- [Docker 文档](https://docs.docker.com/)
- [Kubernetes 文档](https://kubernetes.io/)

### C. 变更历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| 2.0.0 | 2026-06-24 | VPN Simulator Team | 初始版本 |
