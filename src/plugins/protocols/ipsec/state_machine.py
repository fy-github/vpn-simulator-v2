"""IPSec 协议状态机。

实现 IPSec (IKEv1) 的握手流程状态机。
握手流程: Phase1_Main (6步) -> Phase2_Quick (3步) -> ESP 隧道 -> 完成

RFC 2409: The Internet Key Exchange (IKE)
RFC 2401: Security Architecture for the Internet Protocol
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class IPSecStateMachine(ProtocolStateMachine):
    """IPSec (IKEv1) 协议状态机。

    完整的 IPSec 握手流程:

    Phase 1 - Main Mode (6 消息):
    1. INITIAL -> PHASE1_SA_SENT: 发送 SA 提议
    2. PHASE1_SA_SENT -> PHASE1_SA_RECEIVED: 收到 SA 选定
    3. PHASE1_SA_RECEIVED -> PHASE1_KE_SENT: 发送 Key Exchange + Nonce
    4. PHASE1_KE_SENT -> PHASE1_KE_RECEIVED: 收到 Key Exchange + Nonce
    5. PHASE1_KE_RECEIVED -> PHASE1_AUTH_SENT: 发送加密的 ID + Auth
    6. PHASE1_AUTH_SENT -> PHASE1_COMPLETE: 收到加密的 ID + Auth

    Phase 2 - Quick Mode (3 消息):
    7. PHASE1_COMPLETE -> PHASE2_HASH_SENT: 发送 Hash + SA + Nonce
    8. PHASE2_HASH_SENT -> PHASE2_HASH_RECEIVED: 收到 Hash + SA + Nonce
    9. PHASE2_HASH_RECEIVED -> PHASE2_COMPLETE: 最终确认

    ESP 隧道:
    10. PHASE2_COMPLETE -> CONNECTED: ESP SA 就绪

    错误路径: 任意状态 -> ERROR

    Attributes:
        protocol_name: 固定为 "IPSec"。
        ike_port: IKE 端口，默认 500。
        esp_protocol: ESP 协议号，默认 50。
        nat_t_port: NAT-T 端口，默认 4500。
    """

    def __init__(self) -> None:
        """初始化 IPSec 状态机，注册所有状态和转换。"""
        super().__init__("IPSec")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 IPSec 握手流程的所有状态。

        Phase 1 (Main Mode) 状态:
        - INITIAL: 初始状态
        - PHASE1_SA_SENT: 已发送 Phase1 SA 提议
        - PHASE1_SA_RECEIVED: 已收到 Phase1 SA 选定
        - PHASE1_KE_SENT: 已发送 Key Exchange + Nonce
        - PHASE1_KE_RECEIVED: 已收到 Key Exchange + Nonce
        - PHASE1_AUTH_SENT: 已发送加密的 ID + 认证数据
        - PHASE1_COMPLETE: Phase 1 完成，ISAKMP SA 建立

        Phase 2 (Quick Mode) 状态:
        - PHASE2_HASH_SENT: 已发送 Phase2 Hash + SA + Nonce
        - PHASE2_HASH_RECEIVED: 已收到 Phase2 Hash + SA + Nonce
        - PHASE2_COMPLETE: Phase 2 完成，IPSec SA 建立

        ESP 隧道状态:
        - ESP_TUNNEL: ESP 隧道就绪
        - CONNECTED: 已连接（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            # Phase 1 - Main Mode
            State("PHASE1_SA_SENT", "已发送 Phase1 SA 提议"),
            State("PHASE1_SA_RECEIVED", "已收到 Phase1 SA 选定"),
            State("PHASE1_KE_SENT", "已发送 Key Exchange + Nonce"),
            State("PHASE1_KE_RECEIVED", "已收到 Key Exchange + Nonce"),
            State("PHASE1_AUTH_SENT", "已发送加密的 ID + 认证数据"),
            State("PHASE1_COMPLETE", "Phase 1 完成，ISAKMP SA 建立"),
            # Phase 2 - Quick Mode
            State("PHASE2_HASH_SENT", "已发送 Phase2 Hash + SA + Nonce"),
            State("PHASE2_HASH_RECEIVED", "已收到 Phase2 Hash + SA + Nonce"),
            State("PHASE2_COMPLETE", "Phase 2 完成，IPSec SA 建立"),
            # ESP 隧道
            State("ESP_TUNNEL", "ESP 隧道就绪"),
            State("CONNECTED", "IPSec 隧道已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 IPSec 握手流程的所有状态转换。

        正常流程:
        INITIAL -> PHASE1_SA_SENT -> PHASE1_SA_RECEIVED -> PHASE1_KE_SENT ->
        PHASE1_KE_RECEIVED -> PHASE1_AUTH_SENT -> PHASE1_COMPLETE ->
        PHASE2_HASH_SENT -> PHASE2_HASH_RECEIVED -> PHASE2_COMPLETE ->
        ESP_TUNNEL -> CONNECTED

        错误流程:
        任意状态 -> ERROR
        """
        transitions = [
            # Phase 1 - Main Mode (消息 1-2: SA 协商)
            StateTransition(
                "INITIAL", "PHASE1_SA_SENT", "SEND_PHASE1_SA",
                description="发送 Phase1 SA 提议 (加密算法/DH组/认证方式)",
            ),
            StateTransition(
                "PHASE1_SA_SENT", "PHASE1_SA_RECEIVED", "RECEIVE_PHASE1_SA",
                description="收到 Phase1 SA 选定",
            ),
            # Phase 1 - Main Mode (消息 3-4: Key Exchange)
            StateTransition(
                "PHASE1_SA_RECEIVED", "PHASE1_KE_SENT", "SEND_PHASE1_KE",
                description="发送 DH 公钥 + Nonce",
            ),
            StateTransition(
                "PHASE1_KE_SENT", "PHASE1_KE_RECEIVED", "RECEIVE_PHASE1_KE",
                description="收到 DH 公钥 + Nonce，计算共享密钥",
            ),
            # Phase 1 - Main Mode (消息 5-6: 认证)
            StateTransition(
                "PHASE1_KE_RECEIVED", "PHASE1_AUTH_SENT", "SEND_PHASE1_AUTH",
                description="发送加密的 ID + 认证数据 (PSK/证书)",
            ),
            StateTransition(
                "PHASE1_AUTH_SENT", "PHASE1_COMPLETE", "RECEIVE_PHASE1_AUTH",
                description="收到加密的 ID + 认证数据，Phase 1 完成",
            ),
            # Phase 2 - Quick Mode (消息 1-3)
            StateTransition(
                "PHASE1_COMPLETE", "PHASE2_HASH_SENT", "SEND_PHASE2_HASH",
                description="发送 Phase2 Hash + SA 提议 + Nonce",
            ),
            StateTransition(
                "PHASE2_HASH_SENT", "PHASE2_HASH_RECEIVED", "RECEIVE_PHASE2_HASH",
                description="收到 Phase2 Hash + SA 选定 + Nonce",
            ),
            StateTransition(
                "PHASE2_HASH_RECEIVED", "PHASE2_COMPLETE", "SEND_PHASE2_ACK",
                description="发送 Phase2 最终确认",
            ),
            # ESP 隧道
            StateTransition(
                "PHASE2_COMPLETE", "ESP_TUNNEL", "ESP_SA_READY",
                description="ESP SA 就绪，建立 ESP 隧道",
            ),
            StateTransition(
                "ESP_TUNNEL", "CONNECTED", "TUNNEL_ESTABLISHED",
                description="IPSec ESP 隧道建立完成",
            ),
            # 错误路径
            StateTransition(
                "PHASE1_SA_SENT", "ERROR", "PHASE1_SA_FAILED",
                description="Phase 1 SA 协商失败",
            ),
            StateTransition(
                "PHASE1_AUTH_SENT", "ERROR", "PHASE1_AUTH_FAILED",
                description="Phase 1 认证失败",
            ),
            StateTransition(
                "PHASE2_HASH_SENT", "ERROR", "PHASE2_FAILED",
                description="Phase 2 协商失败",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
