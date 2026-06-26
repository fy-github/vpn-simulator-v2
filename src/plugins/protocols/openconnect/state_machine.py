"""OpenConnect 协议状态机。

实现 OpenConnect SSL VPN 协议的完整握手流程状态机。

OpenConnect 是一个开源的 SSL VPN 协议，兼容 Cisco AnyConnect。
握手流程:
  1. TLS 握手 (模拟)
  2. CSTP 协商 (Connect Secure Tunnel Protocol - HTTP-like CONNECT)
  3. DTLS 握手 (可选，用于 UDP 数据通道)
  4. PPP LCP 协商
  5. PPP 认证 (MS-CHAPv2 / EAP)
  6. PPP IPCP 协商
  7. 数据传输

Reference:
    OpenConnect Protocol Documentation
    https://www.infradead.org/openconnect/protocol.html
    https://gitlab.com/openconnect/openconnect
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class OpenConnectStateMachine(ProtocolStateMachine):
    """OpenConnect 协议状态机。

    完整的 OpenConnect 握手流程:
    1. INITIAL -> TLS_HANDSHAKE: 建立 TLS 连接 (模拟)
    2. TLS_HANDSHAKE -> CSTP_NEGOTIATION: TLS 完成，发送 CSTP CONNECT
    3. CSTP_NEGOTIATION -> DTLS_HANDSHAKE: CSTP 隧道参数协商完成，尝试 DTLS
    4. DTLS_HANDSHAKE -> PPP_LCP: DTLS 完成或跳过，开始 PPP LCP
    5. PPP_LCP -> PPP_AUTH: LCP 协商完成，开始认证
    6. PPP_AUTH -> PPP_IPCP: 认证通过，开始 IPCP
    7. PPP_IPCP -> CONNECTED: IPCP 完成，隧道建立

    错误路径: 任意状态 -> ERROR / DISCONNECTED

    Attributes:
        protocol_name: 固定为 "OpenConnect"。
        default_port: 默认端口 443 (HTTPS)。
        tls_version: 模拟的 TLS 版本。
        cstp_version: CSTP 协议版本。
        ppp_mru: PPP MRU (Maximum Receive Unit)。
    """

    default_port: int = 443
    tls_version: str = "TLSv1.3"
    cstp_version: str = "1"
    ppp_mru: int = 1406

    # CSTP 消息类型常量
    CSTP_DATA: int = 0x00
    CSTP_DPD_REQ: int = 0x03
    CSTP_DPD_RESP: int = 0x04
    CSTP_DISCONNECT: int = 0x05
    CSTP_COMPRESSED: int = 0x40

    # CSTP 头部大小 (8 bytes: type(2) + length(2) + header(4))
    CSTP_HEADER_SIZE: int = 8

    # PPP 协议常量
    PPP_LCP: int = 0xC021
    PPP_CHAP: int = 0xC223
    PPP_EAP: int = 0xC227
    PPP_IPCP: int = 0x8021
    PPP_IPV4: int = 0x0021
    PPP_IPV6: int = 0x0057

    # DTLS 常量
    DTLS_VERSION: str = "1.2"
    DTLS_HEADER_SIZE: int = 13

    def __init__(self) -> None:
        """初始化 OpenConnect 状态机，注册所有状态和转换。"""
        super().__init__("OpenConnect")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 OpenConnect 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态，等待客户端 TCP 连接
        - TLS_HANDSHAKE: TLS 握手阶段 (模拟 SSL/TLS 协商)
        - CSTP_NEGOTIATION: CSTP 协商阶段 (HTTP CONNECT + 隧道参数)
        - DTLS_HANDSHAKE: DTLS 握手阶段 (可选，UDP 数据通道)
        - PPP_LCP: PPP LCP 链路控制协议协商
        - PPP_AUTH: PPP 认证阶段 (MS-CHAPv2 / EAP)
        - PPP_IPCP: PPP IPCP 网络控制协议协商
        - CONNECTED: 已连接，数据通道就绪 (终态)
        - DISCONNECTED: 已断开 (终态)
        - ERROR: 错误 (终态)
        """
        states = [
            State("INITIAL", "初始状态，等待客户端 TCP 连接", is_initial=True),
            State("TLS_HANDSHAKE", "TLS 握手阶段 (模拟 SSL/TLS 协商)"),
            State(
                "CSTP_NEGOTIATION",
                "CSTP 协商阶段 (HTTP CONNECT 隧道参数交换)",
            ),
            State(
                "DTLS_HANDSHAKE",
                "DTLS 握手阶段 (可选，建立 UDP 数据通道)",
            ),
            State("PPP_LCP", "PPP LCP 链路控制协议协商"),
            State("PPP_AUTH", "PPP 认证阶段 (MS-CHAPv2 / EAP)"),
            State("PPP_IPCP", "PPP IPCP 网络控制协议协商"),
            State("CONNECTED", "OpenConnect 隧道已连接，数据通道就绪", is_final=True),
            State("DISCONNECTED", "已断开连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 OpenConnect 握手流程的所有状态转换。

        正常流程:
        INITIAL -> TLS_HANDSHAKE -> CSTP_NEGOTIATION -> DTLS_HANDSHAKE ->
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
                "CSTP_NEGOTIATION",
                "TLS_HANDSHAKE_COMPLETE",
                description="TLS 握手完成 (TLSv1.3)，进入 CSTP 协商阶段",
            ),
            # CSTP 协商
            StateTransition(
                "CSTP_NEGOTIATION",
                "DTLS_HANDSHAKE",
                "CSTP_NEGOTIATION_COMPLETE",
                description="CSTP 协商完成: HTTP CONNECT 200 OK + "
                "X-CSTP-Base-MTU / X-CSTP-Address 等隧道参数",
            ),
            # DTLS 握手 (可选)
            StateTransition(
                "DTLS_HANDSHAKE",
                "PPP_LCP",
                "DTLS_HANDSHAKE_COMPLETE",
                description="DTLS 握手完成 (DTLSv1.2)，UDP 数据通道就绪",
            ),
            StateTransition(
                "DTLS_HANDSHAKE",
                "PPP_LCP",
                "DTLS_SKIPPED",
                description="DTLS 握手跳过 (客户端不支持或配置禁用)",
            ),
            # PPP LCP
            StateTransition(
                "PPP_LCP",
                "PPP_AUTH",
                "LCP_NEGOTIATION_COMPLETE",
                description="PPP LCP 协商完成: MRU/魔术字/认证协议配置交换",
            ),
            # PPP 认证
            StateTransition(
                "PPP_AUTH",
                "PPP_IPCP",
                "AUTHENTICATION_SUCCESS",
                description="MS-CHAPv2 / EAP 认证通过",
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
                description="TLS 握手失败 (证书验证错误 / 协议不兼容)",
            ),
            StateTransition(
                "CSTP_NEGOTIATION",
                "ERROR",
                "CSTP_NEGOTIATION_FAILED",
                description="CSTP 协商失败 (HTTP 非 200 响应或参数不兼容)",
            ),
            StateTransition(
                "DTLS_HANDSHAKE",
                "ERROR",
                "DTLS_HANDSHAKE_FAILED",
                description="DTLS 握手失败 (Cookie 验证错误 / 密码套件不匹配)",
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
                description="MS-CHAPv2 / EAP 认证失败",
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
                "CSTP_DISCONNECT",
                description="收到 CSTP DISCONNECT 消息",
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
                "TUNNEL_ERROR",
                description="隧道内部错误 (MTU 不匹配 / 数据通道异常)",
            ),
            # 心跳 (DPD - Dead Peer Detection)
            StateTransition(
                "CONNECTED",
                "CONNECTED",
                "DPD_REQUEST",
                description="收到 CSTP DPD_REQ，回复 DPD_RESP",
            ),
            StateTransition(
                "CONNECTED",
                "CONNECTED",
                "DPD_RESPONSE",
                description="收到 CSTP DPD_RESP，更新活跃时间戳",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
