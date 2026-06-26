"""VPN Simulator 服务层。

提供应用层业务逻辑服务，协调 Domain 模型和 Plugin 系统。

Example:
    >>> from vpn_simulator.services import ProtocolService, ConnectionService
    >>> from vpn_simulator.services import FaultService, AttackService
    >>> from vpn_simulator.services import ComparisonService, TutorialService
    >>> from vpn_simulator.services import BenchmarkService
    >>> from vpn_simulator.services import DPIService, IoTService, VoiceService
"""

from vpn_simulator.services.attack import AttackService
from vpn_simulator.services.benchmark import BenchmarkService
from vpn_simulator.services.comparison import ComparisonService
from vpn_simulator.services.connection import ConnectionService
from vpn_simulator.services.dpi import DPIService
from vpn_simulator.services.fault import FaultService
from vpn_simulator.services.iot import IoTService
from vpn_simulator.services.learning import LearningService
from vpn_simulator.services.metrics import MetricsService
from vpn_simulator.services.obfuscation import ObfuscationService
from vpn_simulator.services.packet_parser import PacketParser
from vpn_simulator.services.protocol import ProtocolService
from vpn_simulator.services.scenario import ScenarioService
from vpn_simulator.services.scenario_engine import ScenarioEngine
from vpn_simulator.services.traffic import TrafficService
from vpn_simulator.services.tutorial import TutorialService
from vpn_simulator.services.vendor_cli import VendorCLIService
from vpn_simulator.services.voice import VoiceService

__all__ = [
    "AttackService",
    "BenchmarkService",
    "ComparisonService",
    "ConnectionService",
    "DPIService",
    "FaultService",
    "IoTService",
    "LearningService",
    "MetricsService",
    "ObfuscationService",
    "PacketParser",
    "ProtocolService",
    "ScenarioEngine",
    "ScenarioService",
    "TrafficService",
    "TutorialService",
    "VendorCLIService",
    "VoiceService",
]
