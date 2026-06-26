"""PPTP 协议状态机。

实现 PPTP (Point-to-Point Tunneling Protocol) 的握手流程状态机。
握手流程: SCCRQ -> SCCRP -> OCRQ -> OCRP -> GRE 建立 -> LCP -> 认证 -> IPCP -> 完成

RFC 2637: Point-to-Point Tunneling Protocol (PPTP)
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class PPTPStateMachine(ProtocolStateMachine):
    """PPTP 协议状态机。

    完整的 PPTP 握手流程:
    1. INITIAL -> WAIT_SCCRQ: 开始监听 TCP 1723
    2. WAIT_SCCRQ -> SCCRP_SENT: 收到 SCCRQ，发送 SCCRP
    3. SCCRP_SENT -> WAIT_OCRQ: SCCRP 发送成功
    4. WAIT_OCRQ -> OCRP_SENT: 收到 OCRQ，发送 OCRP
    5. OCRP_SENT -> GRE_ESTABLISHED: GRE 隧道就绪
    6. GRE_ESTABLISHED -> LCP_NEGOTIATION: 开始 LCP 协商
    7. LCP_NEGOTIATION -> AUTHENTICATION: LCP 完成，开始认证
    8. AUTHENTICATION -> IPCP_NEGOTIATION: 认证成功，开始 IPCP
    9. IPCP_NEGOTIATION -> CONNECTED: IPCP 完成，连接建立

    错误路径: 任意状态 -> ERROR (认证失败/协商超时/协议错误)

    Attributes:
        protocol_name: 固定为 "PPTP"。
        control_port: PPTP 控制端口，默认 1723。
        gre_protocol: GRE 协议号，默认 47。
    """

    def __init__(self) -> None:
        """初始化 PPTP 状态机，注册所有状态和转换。"""
        super().__init__("PPTP")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 PPTP 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态
        - WAIT_SCCRQ: 等待 Start-Control-Connection-Request
        - SCCRP_SENT: 已发送 Start-Control-Connection-Reply
        - WAIT_OCRQ: 等待 Outgoing-Call-Request
        - OCRP_SENT: 已发送 Outgoing-Call-Reply
        - GRE_ESTABLISHED: GRE 隧道已建立
        - LCP_NEGOTIATION: PPP LCP 协商中
        - AUTHENTICATION: PPP 认证中 (MS-CHAPv2)
        - IPCP_NEGOTIATION: PPP IPCP 协商中
        - CONNECTED: 已连接（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            State("WAIT_SCCRQ", "等待 Start-Control-Connection-Request"),
            State("SCCRP_SENT", "已发送 Start-Control-Connection-Reply"),
            State("WAIT_OCRQ", "等待 Outgoing-Call-Request"),
            State("OCRP_SENT", "已发送 Outgoing-Call-Reply"),
            State("GRE_ESTABLISHED", "GRE 隧道已建立"),
            State("LCP_NEGOTIATION", "PPP LCP 协商中"),
            State("AUTHENTICATION", "PPP 认证中 (MS-CHAPv2)"),
            State("IPCP_NEGOTIATION", "PPP IPCP 协商中"),
            State("CONNECTED", "PPTP 隧道已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 PPTP 握手流程的所有状态转换。

        正常流程:
        INITIAL -> WAIT_SCCRQ -> SCCRP_SENT -> WAIT_OCRQ -> OCRP_SENT ->
        GRE_ESTABLISHED -> LCP_NEGOTIATION -> AUTHENTICATION ->
        IPCP_NEGOTIATION -> CONNECTED

        错误流程:
        任意状态 -> ERROR (认证失败、协商超时、协议错误)
        """
        transitions = [
            # 正常握手流程
            StateTransition(
                "INITIAL", "WAIT_SCCRQ", "START",
                description="开始监听 TCP 1723",
            ),
            StateTransition(
                "WAIT_SCCRQ", "SCCRP_SENT", "RECEIVE_SCCRQ",
                description="收到 SCCRQ，发送 SCCRP",
            ),
            StateTransition(
                "SCCRP_SENT", "WAIT_OCRQ", "SCCRP_SENT_OK",
                description="SCCRP 发送成功，等待 OCRQ",
            ),
            StateTransition(
                "WAIT_OCRQ", "OCRP_SENT", "RECEIVE_OCRQ",
                description="收到 OCRQ，发送 OCRP",
            ),
            StateTransition(
                "OCRP_SENT", "GRE_ESTABLISHED", "GRE_READY",
                description="GRE 隧道就绪",
            ),
            StateTransition(
                "GRE_ESTABLISHED", "LCP_NEGOTIATION", "START_LCP",
                description="开始 PPP LCP 协商",
            ),
            StateTransition(
                "LCP_NEGOTIATION", "AUTHENTICATION", "LCP_COMPLETE",
                description="LCP 协商完成，开始 MS-CHAPv2 认证",
            ),
            StateTransition(
                "AUTHENTICATION", "IPCP_NEGOTIATION", "AUTH_SUCCESS",
                description="认证成功，开始 IPCP 协商",
            ),
            StateTransition(
                "IPCP_NEGOTIATION", "CONNECTED", "IPCP_COMPLETE",
                description="IPCP 协商完成，PPTP 隧道建立",
            ),
            # 错误路径
            StateTransition(
                "AUTHENTICATION", "ERROR", "AUTH_FAILED",
                description="MS-CHAPv2 认证失败",
            ),
            StateTransition(
                "LCP_NEGOTIATION", "ERROR", "LCP_FAILED",
                description="LCP 协商失败",
            ),
            StateTransition(
                "IPCP_NEGOTIATION", "ERROR", "IPCP_FAILED",
                description="IPCP 协商失败",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
