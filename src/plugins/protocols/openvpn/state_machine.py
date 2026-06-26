"""OpenVPN 协议状态机。

实现 OpenVPN 的握手流程状态机。
握手流程: P_HARD_RESET -> TLS 握手 -> PUSH_REQUEST -> PUSH_REPLY -> 完成

OpenVPN 使用 TLS over UDP (或 TCP) 进行控制通道协商。
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class OpenVPNStateMachine(ProtocolStateMachine):
    """OpenVPN 协议状态机。

    完整的 OpenVPN 握手流程:
    1. INITIAL -> HARD_RESET_SENT: 发送 P_HARD_RESET_CLIENT_V2
    2. HARD_RESET_SENT -> HARD_RESET_RECEIVED: 收到 P_HARD_RESET_SERVER_V2
    3. HARD_RESET_RECEIVED -> TLS_HANDSHAKE: 开始 TLS 握手
    4. TLS_HANDSHAKE -> TLS_ESTABLISHED: TLS 握手完成
    5. TLS_ESTABLISHED -> PUSH_REQUEST_SENT: 发送 PUSH_REQUEST
    6. PUSH_REQUEST_SENT -> CONNECTED: 收到 PUSH_REPLY (含 IP/路由)

    错误路径: 任意状态 -> ERROR

    Attributes:
        protocol_name: 固定为 "OpenVPN"。
        default_port: 默认端口 1194。
        tls_version: TLS 版本，默认 "1.3"。
    """

    def __init__(self) -> None:
        """初始化 OpenVPN 状态机，注册所有状态和转换。"""
        super().__init__("OpenVPN")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 OpenVPN 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态
        - HARD_RESET_SENT: 已发送 P_HARD_RESET_CLIENT_V2
        - HARD_RESET_RECEIVED: 已收到 P_HARD_RESET_SERVER_V2
        - TLS_HANDSHAKE: TLS 握手中
        - TLS_ESTABLISHED: TLS 已建立
        - PUSH_REQUEST_SENT: 已发送 PUSH_REQUEST
        - CONNECTED: 已连接（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            State("HARD_RESET_SENT", "已发送 P_HARD_RESET_CLIENT_V2"),
            State("HARD_RESET_RECEIVED", "已收到 P_HARD_RESET_SERVER_V2"),
            State("TLS_HANDSHAKE", "TLS 握手中"),
            State("TLS_ESTABLISHED", "TLS 通道已建立"),
            State("PUSH_REQUEST_SENT", "已发送 PUSH_REQUEST"),
            State("CONNECTED", "OpenVPN 隧道已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 OpenVPN 握手流程的所有状态转换。

        正常流程:
        INITIAL -> HARD_RESET_SENT -> HARD_RESET_RECEIVED -> TLS_HANDSHAKE ->
        TLS_ESTABLISHED -> PUSH_REQUEST_SENT -> CONNECTED

        错误流程:
        任意状态 -> ERROR
        """
        transitions = [
            # Hard Reset 阶段
            StateTransition(
                "INITIAL", "HARD_RESET_SENT", "SEND_HARD_RESET",
                description="发送 P_HARD_RESET_CLIENT_V2",
            ),
            StateTransition(
                "HARD_RESET_SENT", "HARD_RESET_RECEIVED", "RECEIVE_HARD_RESET",
                description="收到 P_HARD_RESET_SERVER_V2",
            ),
            # TLS 握手阶段
            StateTransition(
                "HARD_RESET_RECEIVED", "TLS_HANDSHAKE", "START_TLS",
                description="开始 TLS 握手",
            ),
            StateTransition(
                "TLS_HANDSHAKE", "TLS_ESTABLISHED", "TLS_COMPLETE",
                description="TLS 握手完成",
            ),
            # Push 阶段
            StateTransition(
                "TLS_ESTABLISHED", "PUSH_REQUEST_SENT", "SEND_PUSH_REQUEST",
                description="发送 PUSH_REQUEST",
            ),
            StateTransition(
                "PUSH_REQUEST_SENT", "CONNECTED", "RECEIVE_PUSH_REPLY",
                description="收到 PUSH_REPLY，分配 IP 和路由",
            ),
            # 错误路径
            StateTransition(
                "TLS_HANDSHAKE", "ERROR", "TLS_FAILED",
                description="TLS 握手失败",
            ),
            StateTransition(
                "HARD_RESET_SENT", "ERROR", "RESET_TIMEOUT",
                description="Hard Reset 响应超时",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
