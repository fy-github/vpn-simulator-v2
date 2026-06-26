"""VPN Simulator 领域模型。

导出所有核心领域模型：
- ProtocolStateMachine: 协议状态机基类
- ConnectionInfo / ConnectionManager: 连接模型
- PacketInfo / PacketField: 报文模型
- FaultInfo / FaultManager: 故障模型
- AttackInfo / AttackManager: 攻击模型
- Tutorial / TutorialStep / TutorialSession: 教程模型
- BenchmarkInfo / BenchmarkManager: 基准测试模型
"""

from vpn_simulator.domain.attack import (
    AttackInfo,
    AttackManager,
    AttackResult,
    AttackStatus,
    AttackType,
)
from vpn_simulator.domain.benchmark import (
    BenchmarkInfo,
    BenchmarkManager,
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkType,
)
from vpn_simulator.domain.connection import (
    ConnectionInfo,
    ConnectionManager,
    ConnectionState,
    ConnectionType,
)
from vpn_simulator.domain.fault import (
    FaultInfo,
    FaultManager,
    FaultParams,
    FaultType,
)
from vpn_simulator.domain.packet import (
    PacketDirection,
    PacketField,
    PacketInfo,
    PacketType,
    export_packets_to_pcap,
)
from vpn_simulator.domain.protocol import (
    ProtocolStateMachine,
    State,
    StateTransition,
    TransitionRecord,
)
from vpn_simulator.domain.tutorial import (
    Tutorial,
    TutorialSession,
    TutorialStep,
)

__all__ = [
    # Attack
    "AttackInfo",
    "AttackManager",
    "AttackResult",
    "AttackStatus",
    "AttackType",
    # Benchmark
    "BenchmarkInfo",
    "BenchmarkManager",
    "BenchmarkMetrics",
    "BenchmarkResult",
    "BenchmarkStatus",
    "BenchmarkType",
    # Connection
    "ConnectionInfo",
    "ConnectionManager",
    "ConnectionState",
    "ConnectionType",
    # Fault
    "FaultInfo",
    "FaultManager",
    "FaultParams",
    "FaultType",
    # Packet
    "PacketDirection",
    "PacketField",
    "PacketInfo",
    "PacketType",
    "export_packets_to_pcap",
    # Protocol
    "ProtocolStateMachine",
    "State",
    "StateTransition",
    "TransitionRecord",
    # Tutorial
    "Tutorial",
    "TutorialSession",
    "TutorialStep",
]
