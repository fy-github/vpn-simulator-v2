"""WireGuard 协议状态机。

实现 WireGuard 的握手流程状态机。
握手流程: Initiation (52B) -> Response (92B) -> 数据通道 -> 完成

WireGuard 使用 Noise_IKpsk2 协议进行密钥交换。
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class WireGuardStateMachine(ProtocolStateMachine):
    """WireGuard 协议状态机。

    完整的 WireGuard 握手流程 (Noise_IKpsk2):
    1. INITIAL -> INITIATION_SENT: 发送 Handshake Initiation (52 字节)
       - 包含: Sender Index + ephemeral_private + encrypted_static + encrypted_timestamp
    2. INITIATION_SENT -> RESPONSE_RECEIVED: 收到 Handshake Response (92 字节)
       - 包含: Sender Index + Receiver Index + ephemeral_private + encrypted_nothing
    3. RESPONSE_RECEIVED -> TRANSPORT_READY: 计算对称密钥
       - 使用 Noise_IKpsk2 派生会话密钥 (ChaCha20-Poly1305)
    4. TRANSPORT_READY -> CONNECTED: 数据通道就绪

    错误路径: 任意状态 -> ERROR

    Attributes:
        protocol_name: 固定为 "WireGuard"。
        default_port: 默认端口 51820。
        initiation_size: Initiation 消息大小，52 字节。
        response_size: Response 消息大小，92 字节。
        transport_header_size: Transport 消息头大小，32 字节。
    """

    default_port: int = 51820
    initiation_size: int = 52
    response_size: int = 92
    transport_header_size: int = 32

    def __init__(self) -> None:
        """初始化 WireGuard 状态机，注册所有状态和转换。"""
        super().__init__("WireGuard")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 WireGuard 握手流程的所有状态。

        状态列表:
        - INITIAL: 初始状态
        - INITIATION_SENT: 已发送 Handshake Initiation (52B)
        - RESPONSE_RECEIVED: 已收到 Handshake Response (92B)
        - TRANSPORT_READY: 会话密钥已派生，数据通道就绪
        - CONNECTED: 已连接（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            State("INITIATION_SENT", "已发送 Handshake Initiation (52B)"),
            State("RESPONSE_RECEIVED", "已收到 Handshake Response (92B)"),
            State("TRANSPORT_READY", "会话密钥已派生，数据通道就绪"),
            State("CONNECTED", "WireGuard 隧道已连接", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 WireGuard 握手流程的所有状态转换。

        正常流程:
        INITIAL -> INITIATION_SENT -> RESPONSE_RECEIVED ->
        TRANSPORT_READY -> CONNECTED

        错误流程:
        任意状态 -> ERROR
        """
        transitions = [
            # Noise_IKpsk2 握手
            StateTransition(
                "INITIAL", "INITIATION_SENT", "SEND_INITIATION",
                description="发送 Handshake Initiation (52B): "
                            "msg_type=1 + sender_index + unencrypted_ephemeral + "
                            "encrypted_static + encrypted_timestamp",
            ),
            StateTransition(
                "INITIATION_SENT", "RESPONSE_RECEIVED", "RECEIVE_RESPONSE",
                description="收到 Handshake Response (92B): "
                            "msg_type=2 + sender_index + receiver_index + "
                            "unencrypted_ephemeral + encrypted_nothing",
            ),
            # 会话密钥派生
            StateTransition(
                "RESPONSE_RECEIVED", "TRANSPORT_READY", "DERIVE_KEYS",
                description="使用 Noise_IKpsk2 派生 ChaCha20-Poly1305 会话密钥",
            ),
            # 数据通道
            StateTransition(
                "TRANSPORT_READY", "CONNECTED", "DATA_CHANNEL_READY",
                description="数据通道就绪，可传输加密数据",
            ),
            # 错误路径
            StateTransition(
                "INITIATION_SENT", "ERROR", "RESPONSE_TIMEOUT",
                description="Handshake Response 接收超时",
            ),
            StateTransition(
                "RESPONSE_RECEIVED", "ERROR", "KEY_DERIVATION_FAILED",
                description="会话密钥派生失败",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
