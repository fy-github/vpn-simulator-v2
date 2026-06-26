"""IKEv2 协议状态机。

实现 IKEv2 的握手流程状态机。
握手流程: IKE_SA_INIT (2步) -> IKE_AUTH (2步) -> Child_SA -> 完成

RFC 7296: Internet Key Exchange Protocol Version 2 (IKEv2)
"""

from __future__ import annotations

from vpn_simulator.domain.protocol import ProtocolStateMachine, State, StateTransition


class IKEv2StateMachine(ProtocolStateMachine):
    """IKEv2 协议状态机。

    完整的 IKEv2 握手流程:

    IKE_SA_INIT Exchange (2 消息):
    1. INITIAL -> IKE_SA_INIT_SENT: 发送 SA + KE + Ni
    2. IKE_SA_INIT_SENT -> IKE_SA_INIT_COMPLETE: 收到 SA + KE + Nr

    IKE_AUTH Exchange (2 消息):
    3. IKE_SA_INIT_COMPLETE -> IKE_AUTH_SENT: 发送 IDi + Auth + TSi + TSr
    4. IKE_AUTH_SENT -> IKE_AUTH_COMPLETE: 收到 IDr + Auth + TSi + TSr

    Child SA:
    5. IKE_AUTH_COMPLETE -> CHILD_SA_ESTABLISHED: Child SA 建立
    6. CHILD_SA_ESTABLISHED -> CONNECTED: ESP 隧道就绪

    错误路径: 任意状态 -> ERROR

    Attributes:
        protocol_name: 固定为 "IKEv2"。
        ike_port: IKE 端口，默认 500。
        nat_t_port: NAT-T 端口，默认 4500。
        esp_protocol: ESP 协议号，默认 50。
    """

    def __init__(self) -> None:
        """初始化 IKEv2 状态机，注册所有状态和转换。"""
        super().__init__("IKEv2")
        self._setup_states()
        self._setup_transitions()

    def _setup_states(self) -> None:
        """定义 IKEv2 握手流程的所有状态。

        IKE_SA_INIT 阶段:
        - INITIAL: 初始状态
        - IKE_SA_INIT_SENT: 已发送 IKE_SA_INIT 请求
        - IKE_SA_INIT_COMPLETE: IKE_SA_INIT 完成

        IKE_AUTH 阶段:
        - IKE_AUTH_SENT: 已发送 IKE_AUTH 请求
        - IKE_AUTH_COMPLETE: IKE_AUTH 完成，IKE SA 建立

        Child SA 阶段:
        - CHILD_SA_ESTABLISHED: Child SA 已建立
        - CONNECTED: 已连接，ESP 隧道就绪（终态）
        - ERROR: 错误（终态）
        """
        states = [
            State("INITIAL", "初始状态", is_initial=True),
            # IKE_SA_INIT
            State("IKE_SA_INIT_SENT", "已发送 IKE_SA_INIT (SA + KE + Ni)"),
            State("IKE_SA_INIT_COMPLETE", "IKE_SA_INIT 完成 (SA + KE + Nr)"),
            # IKE_AUTH
            State("IKE_AUTH_SENT", "已发送 IKE_AUTH (IDi + Auth + TSi + TSr)"),
            State("IKE_AUTH_COMPLETE", "IKE_AUTH 完成，IKE SA 建立"),
            # Child SA
            State("CHILD_SA_ESTABLISHED", "Child SA 已建立"),
            State("CONNECTED", "IKEv2 隧道已连接，ESP 就绪", is_final=True),
            State("ERROR", "错误", is_final=True),
        ]
        for state in states:
            self.add_state(state)

    def _setup_transitions(self) -> None:
        """定义 IKEv2 握手流程的所有状态转换。

        正常流程:
        INITIAL -> IKE_SA_INIT_SENT -> IKE_SA_INIT_COMPLETE ->
        IKE_AUTH_SENT -> IKE_AUTH_COMPLETE -> CHILD_SA_ESTABLISHED -> CONNECTED

        错误流程:
        任意状态 -> ERROR
        """
        transitions = [
            # IKE_SA_INIT Exchange
            StateTransition(
                "INITIAL", "IKE_SA_INIT_SENT", "SEND_IKE_SA_INIT",
                description="发送 IKE_SA_INIT: SA 提议 + DH 公钥 + Nonce Ni",
            ),
            StateTransition(
                "IKE_SA_INIT_SENT", "IKE_SA_INIT_COMPLETE", "RECEIVE_IKE_SA_INIT",
                description="收到 IKE_SA_INIT 响应: SA 选定 + DH 公钥 + Nonce Nr",
            ),
            # IKE_AUTH Exchange
            StateTransition(
                "IKE_SA_INIT_COMPLETE", "IKE_AUTH_SENT", "SEND_IKE_AUTH",
                description="发送 IKE_AUTH: IDi + 认证 + TSi + TSr (加密)",
            ),
            StateTransition(
                "IKE_AUTH_SENT", "IKE_AUTH_COMPLETE", "RECEIVE_IKE_AUTH",
                description="收到 IKE_AUTH 响应: IDr + 认证 + TSi + TSr (加密)",
            ),
            # Child SA
            StateTransition(
                "IKE_AUTH_COMPLETE", "CHILD_SA_ESTABLISHED", "CHILD_SA_READY",
                description="Child SA 建立，ESP SA 就绪",
            ),
            StateTransition(
                "CHILD_SA_ESTABLISHED", "CONNECTED", "ESP_TUNNEL_READY",
                description="ESP 隧道就绪，IKEv2 连接完成",
            ),
            # 错误路径
            StateTransition(
                "IKE_SA_INIT_SENT", "ERROR", "IKE_SA_INIT_FAILED",
                description="IKE_SA_INIT 失败 (不兼容的 SA 或 DH 组)",
            ),
            StateTransition(
                "IKE_AUTH_SENT", "ERROR", "IKE_AUTH_FAILED",
                description="IKE_AUTH 失败 (认证失败或不兼容的提议)",
            ),
            StateTransition(
                "CHILD_SA_ESTABLISHED", "ERROR", "CHILD_SA_FAILED",
                description="Child SA 建立失败",
            ),
        ]
        for t in transitions:
            self.add_transition(t)
