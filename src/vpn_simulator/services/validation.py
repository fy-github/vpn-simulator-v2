"""VPN 配置验证服务（F2）。

对 6 种协议执行 7 项配置验证：语法、端口可达性、握手、认证、隧道、延迟、
吞吐。其中 WireGuard 的握手/延迟走 Noise_IKpsk2 真实报文真测，OpenVPN 走
控制信道 Hard Reset（``--tls-auth`` HMAC）真测，吞吐做真实 UDP 回环测量；
其余协议的握手/隧道/延迟标注 skip（真实握手待相应协议接入）。

Example:
    >>> service = ValidationService(event_bus, config_manager, db_manager)
    >>> result = await service.validate("wireguard", {"port": 51820})
    >>> result.status  # "pass" | "fail"
"""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Any

import structlog
from sqlalchemy import select

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.core.database import DatabaseManager, ValidationRecord
from vpn_simulator.core.events import EventBus
from vpn_simulator.core.packetio import UdpSocket
from vpn_simulator.domain.validation import StepStatus, ValidationResult, ValidationStep
from vpn_simulator.plugins.protocols.ipsec.crypto import generate_psk
from vpn_simulator.plugins.protocols.ipsec.esp import ESPSession
from vpn_simulator.plugins.protocols.l2tp.control import generate_shared_secret
from vpn_simulator.plugins.protocols.openvpn.control_channel import generate_tls_auth_key
from vpn_simulator.plugins.protocols.openvpn.data_channel import (
    OpenVPNDataSession,
    derive_data_key,
)
from vpn_simulator.plugins.protocols.sstp.tls import create_tls_contexts
from vpn_simulator.plugins.protocols.wireguard.crypto import (
    WireGuardIdentity,
    b64_to_key,
)
from vpn_simulator.plugins.protocols.wireguard.transport import WireGuardTransportSession
from vpn_simulator.services.esp_transport import ESPTransport
from vpn_simulator.services.gre_transport import GRETransport
from vpn_simulator.services.ikev2_handshake import IKEv2Handshake
from vpn_simulator.services.ipsec_handshake import IPsecHandshake
from vpn_simulator.services.l2tp_data_transport import L2TPDataTransport
from vpn_simulator.services.l2tp_handshake import (
    CLIENT_SESSION_ID,
    CLIENT_TUNNEL_ID,
    SERVER_SESSION_ID,
    SERVER_TUNNEL_ID,
    L2TPHandshake,
)
from vpn_simulator.services.openconnect_handshake import OpenConnectHandshake
from vpn_simulator.services.openvpn_handshake import OpenVPNHandshake
from vpn_simulator.services.openvpn_transport import OpenVPNTransport
from vpn_simulator.services.pptp_handshake import PPTPHandshake
from vpn_simulator.services.sstp_handshake import SSTPHandshake
from vpn_simulator.services.vxlan_transport import VXLANTransport
from vpn_simulator.services.wireguard_handshake import WireGuardHandshake
from vpn_simulator.services.wireguard_transport import WireGuardTransport

logger = structlog.get_logger(__name__)

SUPPORTED_PROTOCOLS = [
    "pptp",
    "l2tp",
    "openvpn",
    "ipsec",
    "ikev2",
    "wireguard",
    "sstp",
    "vxlan",
    "openconnect",
]

_AUTH_FIELDS: dict[str, list[str]] = {
    "wireguard": ["private_key", "public_key"],
    "pptp": ["username", "password"],
    "l2tp": ["username", "password", "secret"],
    "openvpn": ["ca", "cert", "key", "username", "password"],
    "ipsec": ["psk", "cert"],
    "ikev2": ["psk", "cert", "username", "password"],
    "sstp": ["username", "password", "cert"],
    "vxlan": ["vni"],
    "openconnect": ["username", "password", "cert"],
}

_DEFAULT_PORTS: dict[str, int] = {
    "pptp": 1723,
    "l2tp": 1701,
    "openvpn": 1194,
    "ipsec": 500,
    "ikev2": 500,
    "wireguard": 51820,
    "sstp": 443,
    "vxlan": 4789,
    "openconnect": 443,
}


class ValidationService:
    """VPN 配置验证服务。"""

    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        db_manager: DatabaseManager,
    ) -> None:
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._db_manager = db_manager

    async def validate(
        self, protocol: str, config: dict[str, Any] | None = None
    ) -> ValidationResult:
        """对指定协议执行 7 项配置验证。

        Args:
            protocol: 协议名称（6 种之一）。
            config: 配置字典；None 视为空配置。

        Returns:
            验证结果。

        Raises:
            ValueError: 协议不支持。
        """
        if protocol not in SUPPORTED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol '{protocol}'. Valid: {SUPPORTED_PROTOCOLS}")

        config = dict(config or {})
        steps: list[ValidationStep] = []

        # 1. 语法
        steps.append(self._step_syntax(config))

        # 2. 端口可达性
        steps.append(self._step_port(protocol, config))

        # 3. 认证
        steps.append(self._step_auth(protocol, config))

        # 4/5/6. 握手 / 隧道 / 延迟（WireGuard 真测，其余 skip）
        handshake_ok = False
        latency_ms: float | None = None
        if protocol == "wireguard":
            handshake_ok, latency_ms, error, initiator_keys, responder_keys = (
                await self._run_wireguard_handshake()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    "真实 Noise_IKpsk2 握手成功" if handshake_ok else f"握手失败: {error}",
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            # 隧道：真实数据面加解密往返（握手已派生传输密钥）。
            if handshake_ok and initiator_keys is not None and responder_keys is not None:
                tunnel_ok, tunnel_error = await self._run_wireguard_data_roundtrip(
                    initiator_keys, responder_keys
                )
                steps.append(
                    ValidationStep(
                        "tunnel",
                        StepStatus.PASS if tunnel_ok else StepStatus.FAIL,
                        (
                            "真实数据面 ChaCha20-Poly1305 加解密往返成功"
                            if tunnel_ok
                            else f"数据面往返失败: {tunnel_error}"
                        ),
                    )
                )
            else:
                steps.append(ValidationStep("tunnel", StepStatus.FAIL, "握手失败，未建立隧道"))
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "openvpn":
            handshake_ok, latency_ms, error, tunnel_ok, tunnel_error = (
                await self._run_openvpn_handshake_and_data()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "控制信道 Hard Reset 成功（--tls-auth HMAC 校验通过）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if (handshake_ok and tunnel_ok) else StepStatus.FAIL,
                    (
                        "真实数据面 AES-256-GCM 加解密往返成功"
                        if tunnel_ok
                        else (
                            f"数据面往返失败: {tunnel_error}"
                            if handshake_ok
                            else "握手失败，未建立隧道"
                        )
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "ikev2":
            handshake_ok, latency_ms, error, esp_ok, esp_error = (
                await self._run_ikev2_handshake_and_esp()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 IKEv2 握手成功（IKE_SA_INIT + IKE_AUTH，X25519/HKDF/AEAD）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if esp_ok else StepStatus.FAIL,
                    (
                        "IKE SA / Child SA 已建立，真实 AES-256-GCM ESP 数据面往返成功"
                        if esp_ok
                        else f"ESP 数据面失败: {esp_error}"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "ipsec":
            handshake_ok, latency_ms, error, esp_ok, esp_error = (
                await self._run_ipsec_handshake_and_esp()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 IKEv1 握手成功（Main Mode + Quick Mode，X25519/HKDF/AEAD/HMAC）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if esp_ok else StepStatus.FAIL,
                    (
                        "ISAKMP/IPSec SA 已建立，真实 AES-256-GCM ESP 数据面往返成功"
                        if esp_ok
                        else f"ESP 数据面失败: {esp_error}"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "l2tp":
            handshake_ok, latency_ms, error, data_ok, data_error = (
                await self._run_l2tp_handshake_and_data()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 L2TP 握手成功（SCCRQ/SCCRP/SCCCN + ICRQ/ICRP/ICCN，隧道 HMAC 认证）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if data_ok else StepStatus.FAIL,
                    (
                        "L2TP 隧道与会话已建立，真实 L2TP 数据面往返成功（PPP 认证待接入）"
                        if data_ok
                        else f"L2TP 数据面失败: {data_error}"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "pptp":
            handshake_ok, latency_ms, error, gre_ok, gre_error = (
                await self._run_pptp_handshake_and_gre()
            )
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 PPTP 握手成功（SCCRQ/SCCRP + OCRQ/OCRP，TCP 控制连接）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if gre_ok else StepStatus.FAIL,
                    (
                        "PPTP 控制连接已建立，真实 GRE 数据面往返成功（PPP 认证待接入）"
                        if gre_ok
                        else f"GRE 数据面失败: {gre_error}"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "sstp":
            handshake_ok, latency_ms, error = await self._run_sstp_handshake()
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 SSTP 握手成功（TLS 1.2/1.3 + CALL_CONNECT_REQUEST/ACK）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "SSTP TLS 隧道与 CALL_CONNECTED 已建立（PPP 认证待接入）"
                        if handshake_ok
                        else "握手失败，未建立隧道"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        elif protocol == "vxlan":
            tunnel_ok, vxlan_latency, error = await self._run_vxlan_roundtrip()
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.SKIP,
                    "VXLAN 无握手（无状态数据面封装，控制面为外部静态配置）",
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if tunnel_ok else StepStatus.FAIL,
                    (
                        "真实 VXLAN 封装/解封装往返成功（VNI 校验）"
                        if tunnel_ok
                        else f"VXLAN 数据面失败: {error}"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if tunnel_ok else StepStatus.SKIP,
                    (
                        f"VXLAN 往返延迟 {vxlan_latency:.2f} ms"
                        if tunnel_ok and vxlan_latency is not None
                        else "VXLAN 往返失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(vxlan_latency, 2)}
                        if tunnel_ok and vxlan_latency is not None
                        else {}
                    ),
                )
            )
        elif protocol == "openconnect":
            handshake_ok, latency_ms, error = await self._run_openconnect_handshake()
            steps.append(
                ValidationStep(
                    "handshake",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "真实 OpenConnect 握手成功（TLS + CSTP CONNECT，X-CSTP-* 协商）"
                        if handshake_ok
                        else f"握手失败: {error}"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "tunnel",
                    StepStatus.PASS if handshake_ok else StepStatus.FAIL,
                    (
                        "OpenConnect TLS/CSTP 隧道已建立（DTLS 与 PPP 认证待接入）"
                        if handshake_ok
                        else "握手失败，未建立隧道"
                    ),
                )
            )
            steps.append(
                ValidationStep(
                    "latency",
                    StepStatus.PASS if handshake_ok else StepStatus.SKIP,
                    (
                        f"握手延迟 {latency_ms:.2f} ms"
                        if handshake_ok and latency_ms is not None
                        else "握手失败，无法测量"
                    ),
                    (
                        {"latency_ms": round(latency_ms, 2)}
                        if handshake_ok and latency_ms is not None
                        else {}
                    ),
                )
            )
        else:
            skip_msg = "该协议真实握手待接入"
            steps.append(ValidationStep("handshake", StepStatus.SKIP, skip_msg))
            steps.append(ValidationStep("tunnel", StepStatus.SKIP, skip_msg))
            steps.append(ValidationStep("latency", StepStatus.SKIP, skip_msg))

        # 7. 吞吐（真实 UDP 回环测量，通用传输层）
        try:
            throughput_mbps = await self._measure_throughput()
            steps.append(
                ValidationStep(
                    "throughput",
                    StepStatus.PASS,
                    f"UDP 回环吞吐 {throughput_mbps:.2f} Mbps",
                    {"throughput_mbps": round(throughput_mbps, 2)},
                )
            )
        except Exception as e:
            steps.append(ValidationStep("throughput", StepStatus.FAIL, f"吞吐测量失败: {e}"))

        result = ValidationResult(protocol=protocol, config=config, steps=steps)
        await self._insert_record(result)
        logger.info("validation_completed", protocol=protocol, status=result.status)
        return result

    # ------------------------------------------------------------------
    # 验证步骤
    # ------------------------------------------------------------------
    def _step_syntax(self, config: dict[str, Any]) -> ValidationStep:
        """语法：配置为 dict，port（若给出）为 0-65535 整数。"""
        if not isinstance(config, dict):
            return ValidationStep("syntax", StepStatus.FAIL, "配置必须是 JSON 对象")
        port = config.get("port")
        if port is not None and (
            not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535
        ):
            return ValidationStep(
                "syntax", StepStatus.FAIL, f"port 必须是 0-65535 的整数，得到 {port!r}"
            )
        return ValidationStep("syntax", StepStatus.PASS, "配置结构合法")

    def _step_port(self, protocol: str, config: dict[str, Any]) -> ValidationStep:
        """端口可达性：尝试在配置端口上绑定 UDP 套接字。"""
        port = config.get("port", _DEFAULT_PORTS.get(protocol, 0))
        if not port:
            return ValidationStep("port", StepStatus.PASS, "使用随机端口（port=0）")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("127.0.0.1", int(port)))
        except OSError as e:
            return ValidationStep("port", StepStatus.FAIL, f"端口 {port} 不可用: {e}")
        finally:
            sock.close()
        return ValidationStep("port", StepStatus.PASS, f"端口 {port} 可绑定")

    def _step_auth(self, protocol: str, config: dict[str, Any]) -> ValidationStep:
        """认证：检查协议所需的认证字段是否存在且合法。"""
        fields = _AUTH_FIELDS.get(protocol, [])
        present = [f for f in fields if config.get(f)]

        if protocol == "wireguard":
            private_key = config.get("private_key")
            if not private_key:
                return ValidationStep("auth", StepStatus.FAIL, "缺少认证字段: private_key")
            try:
                key = b64_to_key(str(private_key))
            except Exception:
                return ValidationStep("auth", StepStatus.FAIL, "private_key 不是合法的 Base64 密钥")
            if len(key) != 32:
                return ValidationStep("auth", StepStatus.FAIL, "private_key 长度不是 32 字节")
            return ValidationStep("auth", StepStatus.PASS, "私钥格式合法")

        if present:
            return ValidationStep("auth", StepStatus.PASS, f"认证字段已提供: {', '.join(present)}")
        return ValidationStep(
            "auth", StepStatus.FAIL, f"缺少认证字段（至少其一）: {', '.join(fields)}"
        )

    async def _run_wireguard_handshake(
        self,
    ) -> tuple[bool, float | None, str, tuple[bytes, bytes] | None, tuple[bytes, bytes] | None]:
        """在环回地址上执行一次真实 WireGuard 握手。

        Returns:
            (是否成功, 握手延迟毫秒, 错误信息, 发起方密钥对, 响应方密钥对)。
            密钥对为 ``(send_key, recv_key)``，失败时为 ``None``。
        """
        initiator = WireGuardIdentity.generate()
        responder = WireGuardIdentity.generate()
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as initiator_sock,
                UdpSocket("127.0.0.1", 0) as responder_sock,
            ):
                responder_addr = responder_sock.local_address
                if responder_addr is None:
                    return False, None, "响应方套接字未绑定", None, None
                initiator_hs = WireGuardHandshake(initiator, initiator_sock)
                responder_hs = WireGuardHandshake(responder, responder_sock)

                start = time.perf_counter()
                keys = await asyncio.gather(
                    initiator_hs.initiate(responder_addr, responder.public_bytes, 1),
                    responder_hs.respond(sender_index=2),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0

            if len(keys) != 2 or any(len(k) != 2 or any(len(b) != 32 for b in k) for k in keys):
                return False, latency_ms, "派生密钥长度异常", None, None
            initiator_keys, responder_keys = keys
            return True, latency_ms, "", initiator_keys, responder_keys
        except Exception as e:
            return False, None, str(e), None, None

    async def _run_wireguard_data_roundtrip(
        self,
        initiator_keys: tuple[bytes, bytes],
        responder_keys: tuple[bytes, bytes],
    ) -> tuple[bool, str]:
        """在环回地址上做一次真实 WireGuard 数据面加解密往返。

        Args:
            initiator_keys: 发起方 ``(send_key, recv_key)``。
            responder_keys: 响应方 ``(send_key, recv_key)``。

        Returns:
            (是否成功, 错误信息)。
        """
        initiator_send, initiator_recv = initiator_keys
        responder_recv, responder_send = responder_keys
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as initiator_sock,
                UdpSocket("127.0.0.1", 0) as responder_sock,
            ):
                responder_addr = responder_sock.local_address
                if responder_addr is None:
                    return False, "响应方套接字未绑定"

                initiator_transport = WireGuardTransport(
                    initiator_sock,
                    WireGuardTransportSession(send_key=initiator_send, recv_key=initiator_recv),
                    local_index=1,
                    peer_index=2,
                )
                responder_transport = WireGuardTransport(
                    responder_sock,
                    WireGuardTransportSession(send_key=responder_send, recv_key=responder_recv),
                    local_index=2,
                    peer_index=1,
                )

                plaintext = b"wireguard data-plane roundtrip"
                await initiator_transport.send_data(responder_addr, plaintext)
                received = await responder_transport.recv_data()
                if received != plaintext:
                    return False, "响应方解密明文不一致"

                await responder_transport.send_data(
                    initiator_sock.local_address or ("127.0.0.1", 0), b"ack"
                )
                ack = await initiator_transport.recv_data()
                if ack != b"ack":
                    return False, "发起方解密应答不一致"
            return True, ""
        except Exception as e:
            return False, str(e)

    async def _run_openvpn_handshake_and_data(
        self,
    ) -> tuple[bool, float | None, str, bool, str]:
        """在环回地址上执行 OpenVPN 控制信道握手 + 数据面加密往返。

        Returns:
            (握手是否成功, 握手延迟毫秒, 握手错误, 数据面是否成功, 数据面错误)。
        """
        tls_auth_key = generate_tls_auth_key()
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as client_sock,
                UdpSocket("127.0.0.1", 0) as server_sock,
            ):
                server_addr = server_sock.local_address
                if server_addr is None:
                    return False, None, "服务端套接字未绑定", False, ""
                client_hs = OpenVPNHandshake(tls_auth_key, client_sock)
                server_hs = OpenVPNHandshake(tls_auth_key, server_sock)

                start = time.perf_counter()
                client_result, _respond_result = await asyncio.gather(
                    client_hs.initiate(server_addr),
                    server_hs.respond(),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                client_session_id, server_session_id = client_result

                # 数据面：派生数据密钥，真实 AES-256-GCM 加解密往返。
                data_key = derive_data_key(tls_auth_key, client_session_id, server_session_id)
                client_transport = OpenVPNTransport(
                    client_sock,
                    OpenVPNDataSession(data_key=data_key),
                    local_id=client_session_id,
                    peer_id=server_session_id,
                )
                server_transport = OpenVPNTransport(
                    server_sock,
                    OpenVPNDataSession(data_key=data_key),
                    local_id=server_session_id,
                    peer_id=client_session_id,
                )

                plaintext = b"openvpn data-plane roundtrip"
                await client_transport.send_data(server_addr, plaintext)
                if await server_transport.recv_data() != plaintext:
                    return True, latency_ms, "", False, "服务端解密明文不一致"

                await server_transport.send_data(
                    client_sock.local_address or ("127.0.0.1", 0), b"ack"
                )
                if await client_transport.recv_data() != b"ack":
                    return True, latency_ms, "", False, "客户端解密应答不一致"

            return True, latency_ms, "", True, ""
        except Exception as e:
            return False, None, str(e), False, ""

    async def _run_ikev2_handshake_and_esp(self) -> tuple[bool, float | None, str, bool, str]:
        """在环回地址上执行真实 IKEv2 握手（IKE_SA_INIT + IKE_AUTH）+ ESP 数据面往返。

        Returns:
            (握手是否成功, 握手延迟毫秒, 握手错误, ESP 是否成功, ESP 错误)。
        """
        initiator_identity = b"initiator@vpn-simulator.local"
        responder_identity = b"responder@vpn-simulator.local"
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as initiator_sock,
                UdpSocket("127.0.0.1", 0) as responder_sock,
            ):
                responder_addr = responder_sock.local_address
                initiator_addr = initiator_sock.local_address
                if responder_addr is None or initiator_addr is None:
                    return False, None, "套接字未绑定", False, "套接字未绑定"
                initiator_hs = IKEv2Handshake(initiator_identity, initiator_sock)
                responder_hs = IKEv2Handshake(responder_identity, responder_sock)

                start = time.perf_counter()
                results = await asyncio.gather(
                    initiator_hs.initiate(responder_addr, responder_identity),
                    responder_hs.respond(initiator_identity),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0

                if len(results) != 2:
                    return False, latency_ms, "握手结果数量异常", False, "握手未完成"
                initiator_spis, responder_spis = results
                if initiator_spis[1] != responder_spis[1] or initiator_spis[0] != responder_spis[0]:
                    return False, latency_ms, "双方 SPI 不一致", False, "握手未完成"

                esp_key = initiator_hs.esp_key()
                if esp_key is None or esp_key != responder_hs.esp_key():
                    return True, latency_ms, "", False, "双方 ESP 密钥不一致"
                esp_ok, esp_error = await self._run_esp_roundtrip(
                    esp_key, initiator_sock, responder_sock, initiator_addr, responder_addr
                )
                return True, latency_ms, "", esp_ok, esp_error
        except Exception as e:
            return False, None, str(e), False, str(e)

    async def _run_ipsec_handshake_and_esp(self) -> tuple[bool, float | None, str, bool, str]:
        """在环回地址上执行真实 IKEv1 握手（Main Mode + Quick Mode）+ ESP 数据面往返。

        Returns:
            (握手是否成功, 握手延迟毫秒, 握手错误, ESP 是否成功, ESP 错误)。
        """
        initiator_identity = b"initiator@vpn-simulator.local"
        responder_identity = b"responder@vpn-simulator.local"
        psk = generate_psk()
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as initiator_sock,
                UdpSocket("127.0.0.1", 0) as responder_sock,
            ):
                responder_addr = responder_sock.local_address
                initiator_addr = initiator_sock.local_address
                if responder_addr is None or initiator_addr is None:
                    return False, None, "套接字未绑定", False, "套接字未绑定"
                initiator_hs = IPsecHandshake(initiator_identity, psk, initiator_sock)
                responder_hs = IPsecHandshake(responder_identity, psk, responder_sock)

                start = time.perf_counter()
                results = await asyncio.gather(
                    initiator_hs.initiate(responder_addr, responder_identity),
                    responder_hs.respond(initiator_identity),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0

                if len(results) != 2:
                    return False, latency_ms, "握手结果数量异常", False, "握手未完成"
                initiator_cookies, responder_cookies = results
                if initiator_cookies != responder_cookies:
                    return False, latency_ms, "双方 cookie 不一致", False, "握手未完成"

                esp_key = initiator_hs.esp_key()
                if esp_key is None or esp_key != responder_hs.esp_key():
                    return True, latency_ms, "", False, "双方 ESP 密钥不一致"
                esp_ok, esp_error = await self._run_esp_roundtrip(
                    esp_key, initiator_sock, responder_sock, initiator_addr, responder_addr
                )
                return True, latency_ms, "", esp_ok, esp_error
        except Exception as e:
            return False, None, str(e), False, str(e)

    async def _run_esp_roundtrip(
        self,
        esp_key: bytes,
        initiator_sock: UdpSocket,
        responder_sock: UdpSocket,
        initiator_addr: tuple[str, int],
        responder_addr: tuple[str, int],
    ) -> tuple[bool, str]:
        """在环回 UDP 上做一次真实 AES-256-GCM ESP 数据面往返。"""
        initiator_spi = 0x0000_1001
        responder_spi = 0x0000_1002
        initiator_t = ESPTransport(
            initiator_sock, ESPSession(esp_key), initiator_spi, responder_spi
        )
        responder_t = ESPTransport(
            responder_sock, ESPSession(esp_key), responder_spi, initiator_spi
        )
        payload = b"ESP data-plane roundtrip payload"
        try:
            await initiator_t.send_data(responder_addr, payload)
            if await responder_t.recv_data() != payload:
                return False, "ESP 明文不一致"
            await responder_t.send_data(initiator_addr, payload)
            if await initiator_t.recv_data() != payload:
                return False, "ESP 回环明文不一致"
            return True, ""
        except Exception as e:
            return False, str(e)

    async def _run_l2tp_handshake_and_data(self) -> tuple[bool, float | None, str, bool, str]:
        """在环回上执行真实 L2TP 握手 + L2TP 数据面往返（同一对 UDP 套接字）。

        Returns:
            (握手是否成功, 握手延迟毫秒, 握手错误, 数据面是否成功, 数据面错误)。
        """
        secret = generate_shared_secret()
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as client_sock,
                UdpSocket("127.0.0.1", 0) as server_sock,
            ):
                server_addr = server_sock.local_address
                client_addr = client_sock.local_address
                if server_addr is None or client_addr is None:
                    return False, None, "套接字未绑定", False, "套接字未绑定"
                client_hs = L2TPHandshake(secret, client_sock)
                server_hs = L2TPHandshake(secret, server_sock)

                start = time.perf_counter()
                results = await asyncio.gather(
                    client_hs.initiate(server_addr),
                    server_hs.respond(),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0

                if len(results) != 2:
                    return False, latency_ms, "握手结果数量异常", False, "握手未完成"
                client_ids, server_ids = results
                if client_ids != server_ids:
                    return False, latency_ms, "双方 tunnel_id 不一致", False, "握手未完成"
                if client_ids != (CLIENT_TUNNEL_ID, SERVER_TUNNEL_ID):
                    return True, latency_ms, "", False, "tunnel_id 不符合预期"

                data_ok, data_error = await self._run_l2tp_data_roundtrip(
                    client_sock, server_sock, client_addr, server_addr
                )
                return True, latency_ms, "", data_ok, data_error
        except Exception as e:
            return False, None, str(e), False, str(e)

    async def _run_l2tp_data_roundtrip(
        self,
        client_sock: UdpSocket,
        server_sock: UdpSocket,
        client_addr: tuple[str, int],
        server_addr: tuple[str, int],
    ) -> tuple[bool, str]:
        """在控制握手同一对 UDP 套接字上做一次真实 L2TP 数据面往返。"""
        client_t = L2TPDataTransport(
            client_sock, CLIENT_TUNNEL_ID, CLIENT_SESSION_ID, SERVER_TUNNEL_ID, SERVER_SESSION_ID
        )
        server_t = L2TPDataTransport(
            server_sock, SERVER_TUNNEL_ID, SERVER_SESSION_ID, CLIENT_TUNNEL_ID, CLIENT_SESSION_ID
        )
        payload = b"L2TP data-plane roundtrip payload"
        try:
            await client_t.send_data(server_addr, payload)
            if await server_t.recv_data() != payload:
                return False, "L2TP 数据明文不一致"
            await server_t.send_data(client_addr, payload)
            if await client_t.recv_data() != payload:
                return False, "L2TP 回环明文不一致"
            return True, ""
        except Exception as e:
            return False, str(e)

    async def _run_pptp_handshake_and_gre(self) -> tuple[bool, float | None, str, bool, str]:
        """在环回上执行真实 PPTP 控制握手（TCP）+ GRE 数据面往返（UDP）。

        Returns:
            (握手是否成功, 握手延迟毫秒, 握手错误, GRE 是否成功, GRE 错误)。
        """
        queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Queue()

        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await queue.put((reader, writer))

        server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        client_writer: asyncio.StreamWriter | None = None
        server_writer: asyncio.StreamWriter | None = None
        try:
            port = server.sockets[0].getsockname()[1]
            start = time.perf_counter()
            client_reader, client_writer = await asyncio.open_connection("127.0.0.1", port)
            server_reader, server_writer = await queue.get()

            client_hs = PPTPHandshake(client_reader, client_writer)
            server_hs = PPTPHandshake(server_reader, server_writer)
            results = await asyncio.gather(
                client_hs.initiate(),
                server_hs.respond(),
            )
            latency_ms = (time.perf_counter() - start) * 1000.0

            if len(results) != 2:
                return False, latency_ms, "握手结果数量异常", False, "握手未完成"
            client_ids, server_ids = results
            if client_ids != server_ids:
                return False, latency_ms, "双方 call_id 不一致", False, "握手未完成"

            client_key, server_key = client_ids
            gre_ok, gre_error = await self._run_gre_roundtrip(client_key, server_key)
            return True, latency_ms, "", gre_ok, gre_error
        except Exception as e:
            return False, None, str(e), False, str(e)
        finally:
            if client_writer is not None:
                client_writer.close()
            if server_writer is not None:
                server_writer.close()
            server.close()
            await server.wait_closed()

    async def _run_gre_roundtrip(self, client_key: int, server_key: int) -> tuple[bool, str]:
        """在环回 UDP 上做一次真实 GRE 数据面往返（模拟 GRE-over-IP）。"""
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as client_sock,
                UdpSocket("127.0.0.1", 0) as server_sock,
            ):
                server_addr = server_sock.local_address
                client_addr = client_sock.local_address
                if server_addr is None or client_addr is None:
                    return False, "套接字未绑定"
                client_t = GRETransport(client_sock, client_key, server_key)
                server_t = GRETransport(server_sock, server_key, client_key)
                payload = b"GRE data-plane roundtrip payload"
                await client_t.send_data(server_addr, payload)
                if await server_t.recv_data() != payload:
                    return False, "GRE 明文不一致"
                await server_t.send_data(client_addr, payload)
                if await client_t.recv_data() != payload:
                    return False, "GRE 回环明文不一致"
                return True, ""
        except Exception as e:
            return False, str(e)

    async def _run_sstp_handshake(self) -> tuple[bool, float | None, str]:
        """在环回 TCP 上执行一次真实 SSTP 握手（TLS + CALL_CONNECT）。

        Returns:
            (是否成功, 握手延迟毫秒, 错误信息)。
        """
        queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Queue()

        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await queue.put((reader, writer))

        try:
            contexts = create_tls_contexts()
            server = await asyncio.start_server(handle_client, "127.0.0.1", 0, ssl=contexts.server)
        except Exception as e:
            return False, None, f"TLS 服务端启动失败: {e}"

        client_writer: asyncio.StreamWriter | None = None
        server_writer: asyncio.StreamWriter | None = None
        try:
            port = server.sockets[0].getsockname()[1]
            start = time.perf_counter()
            client_reader, client_writer = await asyncio.open_connection(
                "127.0.0.1", port, ssl=contexts.client
            )
            server_reader, server_writer = await queue.get()

            client_hs = SSTPHandshake(client_reader, client_writer)
            server_hs = SSTPHandshake(server_reader, server_writer)
            await asyncio.gather(
                client_hs.initiate(),
                server_hs.respond(),
            )
            latency_ms = (time.perf_counter() - start) * 1000.0
            return True, latency_ms, ""
        except Exception as e:
            return False, None, str(e)
        finally:
            if client_writer is not None:
                client_writer.close()
            if server_writer is not None:
                server_writer.close()
            server.close()
            await server.wait_closed()

    async def _run_openconnect_handshake(self) -> tuple[bool, float | None, str]:
        """在环回 TCP 上执行一次真实 OpenConnect 握手（TLS + CSTP CONNECT）。

        Returns:
            (是否成功, 握手延迟毫秒, 错误信息)。
        """
        queue: asyncio.Queue[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = asyncio.Queue()

        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await queue.put((reader, writer))

        try:
            contexts = create_tls_contexts()
            server = await asyncio.start_server(handle_client, "127.0.0.1", 0, ssl=contexts.server)
        except Exception as e:
            return False, None, f"TLS 服务端启动失败: {e}"

        client_writer: asyncio.StreamWriter | None = None
        server_writer: asyncio.StreamWriter | None = None
        try:
            port = server.sockets[0].getsockname()[1]
            start = time.perf_counter()
            client_reader, client_writer = await asyncio.open_connection(
                "127.0.0.1", port, ssl=contexts.client
            )
            server_reader, server_writer = await queue.get()

            client_hs = OpenConnectHandshake(client_reader, client_writer)
            server_hs = OpenConnectHandshake(server_reader, server_writer)
            await asyncio.gather(
                client_hs.initiate(),
                server_hs.respond(),
            )
            latency_ms = (time.perf_counter() - start) * 1000.0
            return True, latency_ms, ""
        except Exception as e:
            return False, None, str(e)
        finally:
            if client_writer is not None:
                client_writer.close()
            if server_writer is not None:
                server_writer.close()
            server.close()
            await server.wait_closed()

    async def _run_vxlan_roundtrip(self) -> tuple[bool, float | None, str]:
        """在环回 UDP 上做一次真实 VXLAN 封装/解封装往返。

        Returns:
            (是否成功, 往返延迟毫秒, 错误信息)。
        """
        vni = 100
        try:
            async with (
                UdpSocket("127.0.0.1", 0) as client_sock,
                UdpSocket("127.0.0.1", 0) as server_sock,
            ):
                server_addr = server_sock.local_address
                client_addr = client_sock.local_address
                if server_addr is None or client_addr is None:
                    return False, None, "套接字未绑定"
                client_t = VXLANTransport(client_sock, vni, vni)
                server_t = VXLANTransport(server_sock, vni, vni)
                payload = b"VXLAN data-plane roundtrip payload"

                start = time.perf_counter()
                await client_t.send_data(server_addr, payload)
                if await server_t.recv_data() != payload:
                    return False, None, "VXLAN 明文不一致"
                await server_t.send_data(client_addr, payload)
                if await client_t.recv_data() != payload:
                    return False, None, "VXLAN 回环明文不一致"
                latency_ms = (time.perf_counter() - start) * 1000.0
                return True, latency_ms, ""
        except Exception as e:
            return False, None, str(e)

    async def _measure_throughput(self, packets: int = 100, size: int = 1024) -> float:
        """在环回地址上做真实 UDP 单向吞吐测量（Mbps）。"""
        payload = bytes(size)
        async with (
            UdpSocket("127.0.0.1", 0) as sender,
            UdpSocket("127.0.0.1", 0) as receiver,
        ):
            target = receiver.local_address
            if target is None:
                raise RuntimeError("接收方套接字未绑定")

            start = time.perf_counter()
            for _ in range(packets):
                await sender.sendto(payload, target)
            received = 0
            for _ in range(packets):
                data, _ = await receiver.recvfrom(timeout=5.0)
                received += len(data)
            elapsed = time.perf_counter() - start

        return (received * 8) / elapsed / 1e6

    # ------------------------------------------------------------------
    # 查询 / 历史
    # ------------------------------------------------------------------
    async def get_result(self, result_id: str) -> dict[str, Any] | None:
        """获取指定验证结果。"""
        async with self._db_manager.session() as session:
            record = await session.get(ValidationRecord, result_id)
        return self._record_to_dict(record) if record else None

    async def history(
        self,
        protocol: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """列出验证历史（按时间倒序）。"""
        async with self._db_manager.session() as session:
            stmt = (
                select(ValidationRecord).order_by(ValidationRecord.created_at.desc()).limit(limit)
            )
            if protocol:
                stmt = stmt.where(ValidationRecord.protocol == protocol)
            result = await session.execute(stmt)
            records = result.scalars().all()
        return [self._record_to_dict(r) for r in records]

    async def batch(
        self,
        protocols: list[str] | None = None,
        configs: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """批量验证多个协议（默认 6 种）。"""
        protocols = protocols or SUPPORTED_PROTOCOLS
        configs = configs or {}
        results = []
        for protocol in protocols:
            config = configs.get(protocol, {"port": _DEFAULT_PORTS.get(protocol, 0)})
            try:
                result = await self.validate(protocol, config)
                results.append(result.to_dict())
            except ValueError as e:
                results.append({"protocol": protocol, "status": "fail", "error": str(e)})
        return results

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    async def _insert_record(self, result: ValidationResult) -> None:
        record = ValidationRecord(
            id=result.id,
            protocol=result.protocol,
            config=result.config,
            status=result.status,
            steps=[s.to_dict() for s in result.steps],
            metrics=result.metrics,
            created_at=result.created_at,
        )
        async with self._db_manager.session() as session:
            session.add(record)

    @staticmethod
    def _record_to_dict(record: ValidationRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "protocol": record.protocol,
            "config": record.config,
            "status": record.status,
            "steps": record.steps,
            "metrics": record.metrics,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
