"""WireGuard 真实握手编排：packetio + crypto + 状态机。

在一次 UDP 套接字上执行真实的 WireGuard Noise_IKpsk2 握手：
- 发起方 `initiate()`：真实发送 Initiation(148B)、接收 Response(92B)，
  派生传输密钥，并驱动状态机 INITIAL → CONNECTED。
- 响应方 `respond()`：真实接收 Initiation、解密发起方静态公钥、发送
  Response、派生传输密钥。

本模块只做控制面握手，不转发数据面报文。
"""

from __future__ import annotations

from collections.abc import Callable

import structlog

from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.packet import PacketDirection
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
        on_packet: Callable[..., None] | None = None,
    ) -> None:
        self._identity = identity
        self._socket = socket
        self._state_machine = state_machine
        self._on_packet = on_packet

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
        local_addr = self._socket.local_address
        await self._socket.sendto(message, responder_addr)
        self._record(
            PacketDirection.OUTGOING, "HANDSHAKE_INITIATION", message, local_addr, responder_addr
        )
        logger.info("wireguard_initiation_sent", bytes=len(message), to=responder_addr)
        await self._trigger("SEND_INITIATION")

        response, peer_addr = await self._socket.recvfrom(timeout=timeout)
        self._record(
            PacketDirection.INCOMING, "HANDSHAKE_RESPONSE", response, peer_addr, local_addr
        )
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
        local_addr = self._socket.local_address
        self._record(
            PacketDirection.INCOMING, "HANDSHAKE_INITIATION", initiation, initiator_addr, local_addr
        )
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
        self._record(
            PacketDirection.OUTGOING, "HANDSHAKE_RESPONSE", response, local_addr, initiator_addr
        )
        logger.info("wireguard_response_sent", bytes=len(response), to=initiator_addr)

        recv_key, send_key = finish_responder(state)
        return recv_key, send_key

    async def _trigger(self, event: str) -> None:
        if self._state_machine is not None:
            await self._state_machine.trigger(event)

    def _record(
        self,
        direction: PacketDirection,
        message_type: str,
        data: bytes,
        src: tuple[str, int] | None,
        dst: tuple[str, int] | None,
    ) -> None:
        if self._on_packet is None:
            return
        src_ip, src_port = src if src else ("", 0)
        dst_ip, dst_port = dst if dst else ("", 0)
        self._on_packet(
            protocol="wireguard",
            message_type=message_type,
            direction=direction,
            raw_data=data,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
        )
