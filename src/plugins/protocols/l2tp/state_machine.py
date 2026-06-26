"""L2TP 协议状态机。

实现 L2TP (Layer 2 Tunneling Protocol) 的握手流程状态机。
握手流程: SCCRQ -> SCCRP -> SCCCN -> ICRQ -> ICRP -> ICCN -> PPP -> 完成

RFC 2661: Layer Two Tunneling Protocol "L2TP"
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class L2TPStateMachine(ProtocolStateMachine):
    """L2TP 协议状态机。

    完整的 L2TP 握手流程:
    1. INITIAL -> WAIT_SCCRQ: 开始监听 UDP 1701
    2. WAIT_SCCRQ -> SCCRP_SENT: 收到 SCCRQ，发送 SCCRP
    3. SCCRP_SENT -> SCCCN_RECEIVED: 收到 SCCCN，控制连接建立
    4. SCCCN_RECEIVED -> ICRP_SENT: 收到 ICRQ，发送 ICRP
    5. ICRP_SENT -> ICCN_RECEIVED: 收到 ICCN，会话建立
    6. ICCN_RECEIVED -> PPP_NEGOTIATION: 开始 PPP over L2TP
    7. PPP_NEGOTIATION -> CONNECTED: PPP 协商完成

    错误路径: 任意状态 -> ERROR

    Attributes:
        protocol_name: 固定为 "L2TP"。
        control_port: L2TP 控制端口，默认 1701。
        avp_vendor_id: AVP 厂商标识，默认 0 (IETF)。
    """

    def __init__(self) -> None:
        """初始化 L2TP 状态机，注册所有状态和转换。"""
        super().__init__("L2TP")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 L2TP 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态
        - WAIT_SCCRQ: 等待 Start-Control-Connection-Request
        - SCCRP_SENT: 已发送 Start-Control-Connection-Reply
        - SCCCN_RECEIVED: 已收到 Start-Control-Connection-Connected
        - ICRP_SENT: 已发送 Incoming-Call-Reply
        - ICCN_RECEIVED: 已收到 Incoming-Call-Connected
        - PPP_NEGOTIATION: PPP over L2TP 协商中
        - CONNECTED: 已连接（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            State("WAIT_SCCRQ", "等待 Start-Control-Connection-Request"),
            State("SCCRP_SENT", "已发送 Start-Control-Connection-Reply"),
            State("SCCCN_RECEIVED", "已收到 Start-Control-Connection-Connected"),
            State("ICRP_SENT", "已发送 Incoming-Call-Reply"),
            State("ICCN_RECEIVED", "已收到 Incoming-Call-Connected"),
            State("PPP_NEGOTIATION", "PPP over L2TP 协商中"),
            State("CONNECTED", "L2TP 隧道已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 L2TP 握手流程的所有状态转换。

        正常流程:
        INITIAL -> WAIT_SCCRQ -> SCCRP_SENT -> SCCCN_RECEIVED ->
        ICRP_SENT -> ICCN_RECEIVED -> PPP_NEGOTIATION -> CONNECTED

        错误流程:
        任意状态 -> ERROR
        """
        transitions = [
            # 控制连接建立
            StateTransition(
                "INITIAL", "WAIT_SCCRQ", "START",
                description="开始监听 UDP 1701",
            ),
            StateTransition(
                "WAIT_SCCRQ", "SCCRP_SENT", "RECEIVE_SCCRQ",
                description="收到 SCCRQ，发送 SCCRP",
            ),
            StateTransition(
                "SCCRP_SENT", "SCCCN_RECEIVED", "RECEIVE_SCCCN",
                description="收到 SCCCN，控制连接建立",
            ),
            # 会话建立
            StateTransition(
                "SCCCN_RECEIVED", "ICRP_SENT", "RECEIVE_ICRQ",
                description="收到 ICRQ，发送 ICRP",
            ),
            StateTransition(
                "ICRP_SENT", "ICCN_RECEIVED", "RECEIVE_ICCN",
                description="收到 ICCN，会话建立",
            ),
            # PPP 协商
            StateTransition(
                "ICCN_RECEIVED", "PPP_NEGOTIATION", "START_PPP",
                description="开始 PPP over L2TP 协商",
            ),
            StateTransition(
                "PPP_NEGOTIATION", "CONNECTED", "PPP_COMPLETE",
                description="PPP 协商完成，L2TP 隧道建立",
            ),
            # 错误路径
            StateTransition(
                "PPP_NEGOTIATION", "ERROR", "PPP_FAILED",
                description="PPP 协商失败",
            ),
            StateTransition(
                "SCCRP_SENT", "ERROR", "SCCCN_TIMEOUT",
                description="SCCN 接收超时",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
