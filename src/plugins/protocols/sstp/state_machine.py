"""SSTP 协议状态机。

实现 SSTP (Secure Socket Tunneling Protocol) 的完整握手流程状态机。

SSTP 是 Microsoft 开发的 VPN 协议，通过 HTTPS (TCP 443) 传输 PPP 帧。
握手流程:
  1. TLS 握手 (模拟)
  2. SSTP 协商 (CALL_CONNECT_REQUEST/ACK/CONNECTED)
  3. PPP LCP 协商
  4. PPP 认证 (MS-CHAPv2)
  5. PPP IPCP 协商
  6. 数据传输

Reference:
    [MS-SSTP]: Secure Socket Tunneling Protocol (SSTP)
    https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-sstp
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class SSTPStateMachine(ProtocolStateMachine):
    """SSTP 协议状态机。

    完整的 SSTP 握手流程:
    1. INITIAL -> TLS_HANDSHAKE: 建立 TLS 连接 (模拟)
    2. TLS_HANDSHAKE -> SSTP_NEGOTIATION: TLS 握手完成，开始 SSTP 协商
    3. SSTP_NEGOTIATION -> PPP_LCP: SSTP CALL_CONNECTED，开始 PPP LCP
    4. PPP_LCP -> PPP_AUTH: LCP 协商完成，开始认证
    5. PPP_AUTH -> PPP_IPCP: 认证通过，开始 IPCP
    6. PPP_IPCP -> CONNECTED: IPCP 完成，隧道建立

    错误路径: 任意状态 -> ERROR / DISCONNECTED

    Attributes:
        protocol_name: 固定为 "SSTP"。
        default_port: 默认端口 443 (HTTPS)。
        tls_version: 模拟的 TLS 版本。
        ppp_mru: PPP MRU (Maximum Receive Unit)。
    """

    default_port: int = 443
    tls_version: str = "TLSv1.2"
    ppp_mru: int = 1500

    # SSTP 消息类型常量
    SSTP_MSG_CALL_CONNECT_REQUEST: int = 0x0001
    SSTP_MSG_CALL_CONNECT_ACK: int = 0x0002
    SSTP_MSG_CALL_CONNECT_NAK: int = 0x0003
    SSTP_MSG_CALL_CONNECTED: int = 0x0004
    SSTP_MSG_CALL_ABORT: int = 0x0005
    SSTP_MSG_CALL_DISCONNECT: int = 0x0006
    SSTP_MSG_CALL_DISCONNECT_ACK: int = 0x0007
    SSTP_MSG_ECHO_REQUEST: int = 0x0008
    SSTP_MSG_ECHO_RESPONSE: int = 0x0009

    # PPP 协议常量
    PPP_LCP: int = 0xC021
    PPP_CHAP: int = 0xC223
    PPP_IPCP: int = 0x8021
    PPP_IPV4: int = 0x0021

    def __init__(self) -> None:
        """初始化 SSTP 状态机，注册所有状态和转换。"""
        super().__init__("SSTP")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 SSTP 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态，等待客户端 TCP 连接
        - TLS_HANDSHAKE: TLS 握手阶段 (模拟 SSL/TLS 协商)
        - SSTP_NEGOTIATION: SSTP 协商阶段 (CALL_CONNECT_REQUEST -> ACK -> CONNECTED)
        - PPP_LCP: PPP LCP 链路控制协议协商
        - PPP_AUTH: PPP 认证阶段 (MS-CHAPv2)
        - PPP_IPCP: PPP IPCP 网络控制协议协商
        - CONNECTED: 已连接，数据通道就绪 (终态)
        - DISCONNECTED: 已断开 (终态)
        - ERROR: 错误 (终态)
        """
        states = [
            State("INITIAL", "初始状态，等待客户端 TCP 连接", is_initial=True),
            State("TLS_HANDSHAKE", "TLS 握手阶段 (模拟 SSL/TLS 协商)"),
            State(
                "SSTP_NEGOTIATION",
                "SSTP 协商阶段 (CALL_CONNECT_REQUEST -> ACK -> CONNECTED)",
            ),
            State("PPP_LCP", "PPP LCP 链路控制协议协商"),
            State("PPP_AUTH", "PPP 认证阶段 (MS-CHAPv2)"),
            State("PPP_IPCP", "PPP IPCP 网络控制协议协商"),
            State("CONNECTED", "SSTP 隧道已连接，数据通道就绪", is_final=True),
            State("DISCONNECTED", "已断开连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 SSTP 握手流程的所有状态转换。

        正常流程:
        INITIAL -> TLS_HANDSHAKE -> SSTP_NEGOTIATION ->
        PPP_LCP -> PPP_AUTH -> PPP_IPCP -> CONNECTED

        错误/断开流程:
        任意状态 -> ERROR / DISCONNECTED
        """
        transitions = [
            # TLS 握手
            StateTransition(
                "INITIAL",
                "TLS_HANDSHAKE",
                "TCP_CONNECTED",
                description="客户端 TCP 连接建立，开始 TLS 握手 (模拟)",
            ),
            StateTransition(
                "TLS_HANDSHAKE",
                "SSTP_NEGOTIATION",
                "TLS_HANDSHAKE_COMPLETE",
                description="TLS 握手完成 (TLSv1.2)，进入 SSTP 协商阶段",
            ),
            # SSTP 协商
            StateTransition(
                "SSTP_NEGOTIATION",
                "PPP_LCP",
                "SSTP_CALL_CONNECTED",
                description="SSTP 协商完成: CALL_CONNECT_REQUEST -> "
                "CALL_CONNECT_ACK -> CALL_CONNECTED",
            ),
            # PPP LCP
            StateTransition(
                "PPP_LCP",
                "PPP_AUTH",
                "LCP_NEGOTIATION_COMPLETE",
                description="PPP LCP 协商完成: MRU/魔术字/认证协议 "
                "配置交换",
            ),
            # PPP 认证
            StateTransition(
                "PPP_AUTH",
                "PPP_IPCP",
                "AUTHENTICATION_SUCCESS",
                description="MS-CHAPv2 认证通过",
            ),
            # PPP IPCP
            StateTransition(
                "PPP_IPCP",
                "CONNECTED",
                "IPCP_NEGOTIATION_COMPLETE",
                description="IPCP 协商完成: 分配客户端 IP、DNS、路由",
            ),
            # 错误路径
            StateTransition(
                "TLS_HANDSHAKE",
                "ERROR",
                "TLS_HANDSHAKE_FAILED",
                description="TLS 握手失败",
            ),
            StateTransition(
                "SSTP_NEGOTIATION",
                "ERROR",
                "SSTP_NEGOTIATION_FAILED",
                description="SSTP 协商失败 (收到 CALL_CONNECT_NAK 或 CALL_ABORT)",
            ),
            StateTransition(
                "PPP_LCP",
                "ERROR",
                "LCP_NEGOTIATION_FAILED",
                description="PPP LCP 协商失败",
            ),
            StateTransition(
                "PPP_AUTH",
                "ERROR",
                "AUTHENTICATION_FAILED",
                description="MS-CHAPv2 认证失败",
            ),
            StateTransition(
                "PPP_IPCP",
                "ERROR",
                "IPCP_NEGOTIATION_FAILED",
                description="IPCP 协商失败",
            ),
            # 断开路径
            StateTransition(
                "CONNECTED",
                "DISCONNECTED",
                "CALL_DISCONNECT",
                description="收到 SSTP CALL_DISCONNECT 消息",
            ),
            StateTransition(
                "CONNECTED",
                "DISCONNECTED",
                "CLIENT_DISCONNECTED",
                description="客户端 TCP 连接断开",
            ),
            StateTransition(
                "CONNECTED",
                "ERROR",
                "CALL_ABORT",
                description="收到 SSTP CALL_ABORT 消息",
            ),
            # 心跳
            StateTransition(
                "CONNECTED",
                "CONNECTED",
                "ECHO_REQUEST",
                description="收到 SSTP ECHO_REQUEST，回复 ECHO_RESPONSE",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
