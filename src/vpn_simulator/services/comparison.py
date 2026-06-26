"""协议对比服务。

提供两个协议的状态机数据对比功能，支持阶段分类和差异高亮。

Example:
    >>> from vpn_simulator.services import ComparisonService
    >>> service = ComparisonService()
    >>> result = await service.compare("pptp", "l2tp")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from vpn_simulator.domain.protocol import ProtocolStateMachine

logger = structlog.get_logger(__name__)


class PhaseCategory(str, Enum):
    """协议握手阶段分类。

    用于对比时标记每个状态所属的功能阶段，以便识别相似和差异步骤。
    """

    CONNECTION_INIT = "connection_init"
    CONTROL_CHANNEL = "control_channel"
    KEY_EXCHANGE = "key_exchange"
    AUTHENTICATION = "authentication"
    TUNNEL_SETUP = "tunnel_setup"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class StateInfo:
    """带阶段分类的状态信息。"""

    name: str
    description: str
    phase: PhaseCategory
    is_initial: bool = False
    is_final: bool = False


@dataclass
class TransitionInfo:
    """带阶段分类的转换信息。"""

    from_state: str
    to_state: str
    event: str
    description: str
    phase: PhaseCategory


@dataclass
class ProtocolStateData:
    """单个协议的完整状态机数据。"""

    name: str
    description: str
    states: list[StateInfo]
    transitions: list[TransitionInfo]


@dataclass
class ComparisonResult:
    """对比结果。"""

    protocol1: ProtocolStateData
    protocol2: ProtocolStateData
    common_phases: list[PhaseCategory]
    different_phases: list[PhaseCategory]


# 各协议状态到阶段的映射
_STATE_PHASE_MAP: dict[str, dict[str, PhaseCategory]] = {
    "PPTP": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "WAIT_SCCRQ": PhaseCategory.CONTROL_CHANNEL,
        "SCCRP_SENT": PhaseCategory.CONTROL_CHANNEL,
        "WAIT_OCRQ": PhaseCategory.CONTROL_CHANNEL,
        "OCRP_SENT": PhaseCategory.CONTROL_CHANNEL,
        "GRE_ESTABLISHED": PhaseCategory.TUNNEL_SETUP,
        "LCP_NEGOTIATION": PhaseCategory.TUNNEL_SETUP,
        "AUTHENTICATION": PhaseCategory.AUTHENTICATION,
        "IPCP_NEGOTIATION": PhaseCategory.TUNNEL_SETUP,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
    "L2TP": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "WAIT_SCCRQ": PhaseCategory.CONTROL_CHANNEL,
        "SCCRP_SENT": PhaseCategory.CONTROL_CHANNEL,
        "SCCCN_RECEIVED": PhaseCategory.CONTROL_CHANNEL,
        "ICRP_SENT": PhaseCategory.TUNNEL_SETUP,
        "ICCN_RECEIVED": PhaseCategory.TUNNEL_SETUP,
        "PPP_NEGOTIATION": PhaseCategory.AUTHENTICATION,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
    "OPENVPN": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "HARD_RESET_SENT": PhaseCategory.CONTROL_CHANNEL,
        "HARD_RESET_RECEIVED": PhaseCategory.CONTROL_CHANNEL,
        "TLS_HANDSHAKE": PhaseCategory.KEY_EXCHANGE,
        "TLS_ESTABLISHED": PhaseCategory.KEY_EXCHANGE,
        "PUSH_REQUEST_SENT": PhaseCategory.TUNNEL_SETUP,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
    "IPSEC": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "PHASE1_SA_SENT": PhaseCategory.KEY_EXCHANGE,
        "PHASE1_SA_RECEIVED": PhaseCategory.KEY_EXCHANGE,
        "PHASE1_KE_SENT": PhaseCategory.KEY_EXCHANGE,
        "PHASE1_KE_RECEIVED": PhaseCategory.KEY_EXCHANGE,
        "PHASE1_AUTH_SENT": PhaseCategory.AUTHENTICATION,
        "PHASE1_COMPLETE": PhaseCategory.AUTHENTICATION,
        "PHASE2_HASH_SENT": PhaseCategory.TUNNEL_SETUP,
        "PHASE2_HASH_RECEIVED": PhaseCategory.TUNNEL_SETUP,
        "PHASE2_COMPLETE": PhaseCategory.TUNNEL_SETUP,
        "ESP_TUNNEL": PhaseCategory.TUNNEL_SETUP,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
    "IKEV2": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "IKE_SA_INIT_SENT": PhaseCategory.KEY_EXCHANGE,
        "IKE_SA_INIT_COMPLETE": PhaseCategory.KEY_EXCHANGE,
        "IKE_AUTH_SENT": PhaseCategory.AUTHENTICATION,
        "IKE_AUTH_COMPLETE": PhaseCategory.AUTHENTICATION,
        "CHILD_SA_ESTABLISHED": PhaseCategory.TUNNEL_SETUP,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
    "WIREGUARD": {
        "INITIAL": PhaseCategory.CONNECTION_INIT,
        "INITIATION_SENT": PhaseCategory.KEY_EXCHANGE,
        "RESPONSE_RECEIVED": PhaseCategory.KEY_EXCHANGE,
        "TRANSPORT_READY": PhaseCategory.TUNNEL_SETUP,
        "CONNECTED": PhaseCategory.CONNECTED,
        "ERROR": PhaseCategory.ERROR,
    },
}

# 各协议描述
_PROTOCOL_DESCRIPTIONS: dict[str, str] = {
    "PPTP": "Point-to-Point Tunneling Protocol (RFC 2637) - TCP 1723 + GRE",
    "L2TP": "Layer 2 Tunneling Protocol (RFC 2661) - UDP 1701 + PPP",
    "OPENVPN": "Open Source VPN - TLS over UDP/TCP",
    "IPSEC": "IPSec IKEv1 (RFC 2409) - Main Mode + Quick Mode + ESP",
    "IKEV2": "IKEv2/IPSec (RFC 7296) - IKE_SA_INIT + IKE_AUTH + ESP",
    "WIREGUARD": "WireGuard - Noise_IKpsk2 + ChaCha20-Poly1305",
}

# 协议名大小写映射
_NAME_MAP: dict[str, str] = {
    "pptp": "PPTP",
    "l2tp": "L2TP",
    "openvpn": "OPENVPN",
    "ipsec": "IPSEC",
    "ikev2": "IKEV2",
    "wireguard": "WIREGUARD",
}


def _create_state_machine(name: str) -> ProtocolStateMachine:
    """根据协议名称创建状态机实例。

    Args:
        name: 协议名称（大写）。

    Returns:
        状态机实例。

    Raises:
        ValueError: 不支持的协议名称。
    """
    if name == "PPTP":
        from plugins.protocols.pptp.state_machine import PPTPStateMachine
        return PPTPStateMachine()
    elif name == "L2TP":
        from plugins.protocols.l2tp.state_machine import L2TPStateMachine
        return L2TPStateMachine()
    elif name == "OPENVPN":
        from plugins.protocols.openvpn.state_machine import OpenVPNStateMachine
        return OpenVPNStateMachine()
    elif name == "IPSEC":
        from plugins.protocols.ipsec.state_machine import IPSecStateMachine
        return IPSecStateMachine()
    elif name == "IKEV2":
        from plugins.protocols.ikev2.state_machine import IKEv2StateMachine
        return IKEv2StateMachine()
    elif name == "WIREGUARD":
        from plugins.protocols.wireguard.state_machine import WireGuardStateMachine
        return WireGuardStateMachine()
    else:
        raise ValueError(f"Unsupported protocol: {name}")


class ComparisonService:
    """协议对比服务。

    提供两个协议状态机的对比分析，识别共同阶段和差异阶段。
    """

    def get_available_protocols(self) -> list[dict[str, Any]]:
        """获取所有可用协议的列表。

        Returns:
            协议信息列表，包含 name 和 description。
        """
        protocols = []
        for name, desc in _PROTOCOL_DESCRIPTIONS.items():
            protocols.append({"name": name.lower(), "description": desc})
        return protocols

    async def compare(
        self,
        protocol1_name: str,
        protocol2_name: str,
    ) -> ComparisonResult:
        """对比两个协议的状态机。

        Args:
            protocol1_name: 第一个协议名称。
            protocol2_name: 第二个协议名称。

        Returns:
            对比结果。

        Raises:
            ValueError: 协议名称不存在。
        """
        p1_key = _NAME_MAP.get(protocol1_name.lower())
        p2_key = _NAME_MAP.get(protocol2_name.lower())

        if p1_key is None:
            raise ValueError(f"Protocol '{protocol1_name}' not found")
        if p2_key is None:
            raise ValueError(f"Protocol '{protocol2_name}' not found")

        data1 = self._build_protocol_data(p1_key)
        data2 = self._build_protocol_data(p2_key)

        phases1 = {s.phase for s in data1.states if s.phase not in (PhaseCategory.CONNECTED, PhaseCategory.ERROR)}
        phases2 = {s.phase for s in data2.states if s.phase not in (PhaseCategory.CONNECTED, PhaseCategory.ERROR)}

        common = sorted(phases1 & phases2, key=lambda p: p.value)
        different = sorted(phases1 ^ phases2, key=lambda p: p.value)

        logger.info(
            "comparison_completed",
            protocol1=p1_key,
            protocol2=p2_key,
            common_phases=[p.value for p in common],
        )

        return ComparisonResult(
            protocol1=data1,
            protocol2=data2,
            common_phases=common,
            different_phases=different,
        )

    def _build_protocol_data(self, name: str) -> ProtocolStateData:
        """构建协议状态机数据。

        创建协议状态机实例，提取状态和转换数据，
        并附加阶段分类信息。

        Args:
            name: 协议名称（大写）。

        Returns:
            协议状态机数据。
        """
        sm = _create_state_machine(name)
        phase_map = _STATE_PHASE_MAP.get(name, {})

        states = []
        for state in sm.states.values():
            phase = phase_map.get(state.name, PhaseCategory.TUNNEL_SETUP)
            states.append(StateInfo(
                name=state.name,
                description=state.description,
                phase=phase,
                is_initial=state.is_initial,
                is_final=state.is_final,
            ))

        transitions = []
        for t in sm.transitions:
            phase = phase_map.get(t.to_state, PhaseCategory.TUNNEL_SETUP)
            transitions.append(TransitionInfo(
                from_state=t.from_state,
                to_state=t.to_state,
                event=t.event,
                description=t.description,
                phase=phase,
            ))

        return ProtocolStateData(
            name=name,
            description=_PROTOCOL_DESCRIPTIONS.get(name, ""),
            states=states,
            transitions=transitions,
        )
