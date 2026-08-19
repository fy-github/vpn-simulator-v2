"""WireGuard 真实握手编排：packetio + crypto + 状态机。

在一次 UDP 套接字上执行真实的 WireGuard Noise_IKpsk2 握手：
- 发起方 `initiate()`：真实发送 Initiation(148B)、接收 Response(92B)，
  派生传输密钥，并驱动状态机 INITIAL → CONNECTED。
- 响应方 `respond()`：真实接收 Initiation、解密发起方静态公钥、发送
  Response、派生传输密钥。

本模块只做控制面握手，不转发数据面报文。
"""

from __future__ import annotations

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.protocol import ProtocolStateMachine
from vpn_simulator.plugins.protocols.wireguard.crypto import (
    WireGuardIdentity,
    build_initiation,
    build_response,
    finish_initiator,
    finish_responder,
    parse_initiation,
)
from vpn_simulator.plugins.protocols.wireguard.wire_format import (
    parse_wireguard_message,
)

logger = structlog.get_logger(__name__)

DEFAULT_HANDSHAKE_TIMEOUT = 5.0


class WireGuardHandshake:
    """在 UDP 套接字上执行一次真实 WireGuard 握手。"""

    def __init__(
        self,
        identity: WireGuardIdentity,
        socket: UdpSocket,
        state_machine: ProtocolStateMachine | None = None,
    ) -> None:
        self._identity = identity
        self._socket = socket
        self._state_machine = state_machine

    async def initiate(
        self,
        responder_addr: tuple[str, int],
        responder_static_public: bytes,
        sender_index: int,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[bytes, bytes]:
        """发起方执行握手，返回 (发送密钥, 接收密钥)。

        真实网络动作为每一步状态转换的前提：发送 Initiation 后才触发
        SEND_INITIATION，收到 Response 后才触发 RECEIVE_RESPONSE。
        """
        message, handshake = build_initiation(self._identity, responder_static_public, sender_index)
        await self._socket.sendto(message, responder_addr)
        logger.info("wireguard_initiation_sent", bytes=len(message), to=responder_addr)
        await self._trigger("SEND_INITIATION")

        response, _addr = await self._socket.recvfrom(timeout=timeout)
        packet = parse_wireguard_message(response)
        logger.info("wireguard_response_received", bytes=len(response), msg_type=packet.msg_type)
        await self._trigger("RECEIVE_RESPONSE")

        send_key, recv_key = finish_initiator(handshake, response)
        await self._trigger("DERIVE_KEYS")
        await self._trigger("DATA_CHANNEL_READY")
        return send_key, recv_key

    async def respond(
        self,
        sender_index: int,
        timeout: float = DEFAULT_HANDSHAKE_TIMEOUT,
    ) -> tuple[bytes, bytes]:
        """响应方执行握手，返回 (接收密钥, 发送密钥)。"""
        initiation, initiator_addr = await self._socket.recvfrom(timeout=timeout)
        packet = parse_wireguard_message(initiation)
        logger.info(
            "wireguard_initiation_received",
            bytes=len(initiation),
            msg_type=packet.msg_type,
            sender_index=packet.sender_index,
        )

        parsed = parse_initiation(self._identity, initiation)
        response, state = build_response(
            self._identity,
            parsed,
            sender_index=sender_index,
            receiver_index=parsed.sender_index,
        )
        await self._socket.sendto(response, initiator_addr)
        logger.info("wireguard_response_sent", bytes=len(response), to=initiator_addr)

        recv_key, send_key = finish_responder(state)
        return recv_key, send_key

    async def _trigger(self, event: str) -> None:
        if self._state_machine is not None:
            await self._state_machine.trigger(event)
