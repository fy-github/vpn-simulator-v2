"""Voice simulation service for VPN Simulator v2.

Provides VoIP call simulation with codec support, quality metrics
including MOS score calculation, and real-time monitoring.
"""

from __future__ import annotations

import asyncio
import random
import socket
import struct
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class VoiceCodec(str, Enum):
    """Supported voice codecs."""
    G711 = "g711"
    G729 = "g729"
    OPUS = "opus"


class CallState(str, Enum):
    """Call state enumeration."""
    INITIATING = "initiating"
    RINGING = "ringing"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CodecConfig:
    """Voice codec configuration."""
    id: str
    name: str
    description: str
    bitrate_kbps: float
    sample_rate_hz: int
    frame_size_ms: int
    packet_size_bytes: int
    bandwidth_range: tuple[float, float]  # (min_kbps, max_kbps)


@dataclass
class NetworkConditions:
    """Network condition parameters for simulation."""
    latency_ms: float = 50.0
    jitter_ms: float = 10.0
    packet_loss_percent: float = 0.0
    bandwidth_kbps: float = 1000.0


@dataclass
class QualityMetrics:
    """Voice quality metrics."""
    mos: float = 4.5
    r_factor: float = 93.2
    jitter_ms: float = 0.0
    packet_loss_percent: float = 0.0
    latency_ms: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mos": round(self.mos, 2),
            "r_factor": round(self.r_factor, 1),
            "jitter_ms": round(self.jitter_ms, 1),
            "packet_loss_percent": round(self.packet_loss_percent, 2),
            "latency_ms": round(self.latency_ms, 1),
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
        }


@dataclass
class VoiceCall:
    """Voice call instance."""
    call_id: str
    codec: VoiceCodec
    caller_ip: str
    callee_ip: str
    state: CallState = CallState.INITIATING
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    network_conditions: NetworkConditions = field(default_factory=NetworkConditions)
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _quality_history: list[dict[str, Any]] = field(default_factory=list, repr=False)


# Codec configurations
CODEC_CONFIGS: dict[VoiceCodec, CodecConfig] = {
    VoiceCodec.G711: CodecConfig(
        id="g711",
        name="G.711",
        description="Traditional telephony codec (PCM)",
        bitrate_kbps=64.0,
        sample_rate_hz=8000,
        frame_size_ms=20,
        packet_size_bytes=160,
        bandwidth_range=(64.0, 64.0),
    ),
    VoiceCodec.G729: CodecConfig(
        id="g729",
        name="G.729",
        description="Low bandwidth codec for VoIP",
        bitrate_kbps=8.0,
        sample_rate_hz=8000,
        frame_size_ms=20,
        packet_size_bytes=20,
        bandwidth_range=(8.0, 8.0),
    ),
    VoiceCodec.OPUS: CodecConfig(
        id="opus",
        name="Opus",
        description="Modern adaptive codec for WebRTC",
        bitrate_kbps=64.0,
        sample_rate_hz=48000,
        frame_size_ms=20,
        packet_size_bytes=320,
        bandwidth_range=(6.0, 510.0),
    ),
}


class VoiceService:
    """Voice simulation service.

    Manages VoIP call simulation with codec support,
    quality metrics calculation, and real-time monitoring.
    """

    def __init__(self) -> None:
        self._calls: dict[str, VoiceCall] = {}
        self._active_calls: int = 0
        self._total_calls: int = 0
        self._quality_update_interval: float = 1.0
        self._current_codec: VoiceCodec = VoiceCodec.G711

    def list_codecs(self) -> list[dict[str, Any]]:
        """List supported voice codecs.

        Returns:
            List of codec configuration dictionaries.
        """
        result = []
        for codec_enum, config in CODEC_CONFIGS.items():
            result.append({
                "id": config.id,
                "name": config.name,
                "description": config.description,
                "bitrate_kbps": config.bitrate_kbps,
                "sample_rate_hz": config.sample_rate_hz,
                "frame_size_ms": config.frame_size_ms,
                "packet_size_bytes": config.packet_size_bytes,
                "bandwidth_range": {
                    "min_kbps": config.bandwidth_range[0],
                    "max_kbps": config.bandwidth_range[1],
                },
            })
        return result

    async def start_call(
        self,
        codec: str = "g711",
        caller_ip: str = "192.168.1.100",
        callee_ip: str = "10.0.0.50",
        latency_ms: float = 50.0,
        jitter_ms: float = 10.0,
        packet_loss_percent: float = 0.0,
        bandwidth_kbps: float = 1000.0,
    ) -> dict[str, Any]:
        """Start a simulated voice call.

        Args:
            codec: Voice codec to use.
            caller_ip: Caller IP address.
            callee_ip: Callee IP address.
            latency_ms: Network latency in ms.
            jitter_ms: Network jitter in ms.
            packet_loss_percent: Packet loss percentage.
            bandwidth_kbps: Available bandwidth in kbps.

        Returns:
            Call start confirmation with call ID.

        Raises:
            ValueError: If codec is invalid.
        """
        # Validate codec
        try:
            codec_enum = VoiceCodec(codec.lower())
        except ValueError:
            raise ValueError(f"Invalid codec '{codec}'. Valid: {[c.value for c in VoiceCodec]}")

        call_id = f"call_{uuid.uuid4().hex[:12]}"

        network_conditions = NetworkConditions(
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss_percent=packet_loss_percent,
            bandwidth_kbps=bandwidth_kbps,
        )

        call = VoiceCall(
            call_id=call_id,
            codec=codec_enum,
            caller_ip=caller_ip,
            callee_ip=callee_ip,
            state=CallState.INITIATING,
            network_conditions=network_conditions,
        )

        self._calls[call_id] = call
        self._total_calls += 1

        # Start call simulation task
        call._task = asyncio.create_task(self._run_call_simulation(call))
        call.started_at = time.time()
        call.state = CallState.ACTIVE
        self._active_calls += 1

        codec_config = CODEC_CONFIGS[codec_enum]
        return {
            "call_id": call_id,
            "codec": codec_config.name,
            "caller_ip": caller_ip,
            "callee_ip": callee_ip,
            "state": call.state.value,
            "message": f"Call started with {codec_config.name} codec",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def stop_call(self, call_id: str) -> dict[str, Any]:
        """Stop a voice call.

        Args:
            call_id: Call ID to stop.

        Returns:
            Call stop confirmation with final metrics.

        Raises:
            ValueError: If call not found.
        """
        call = self._calls.get(call_id)
        if call is None:
            raise ValueError(f"Call '{call_id}' not found")

        # Cancel simulation task
        if call._task and not call._task.done():
            call._task.cancel()
            try:
                await call._task
            except asyncio.CancelledError:
                pass

        call.state = CallState.COMPLETED
        call.ended_at = time.time()
        self._active_calls = max(0, self._active_calls - 1)

        return {
            "call_id": call_id,
            "state": call.state.value,
            "duration_seconds": round(call.ended_at - call.started_at, 1) if call.started_at else 0,
            "final_metrics": call.quality_metrics.to_dict(),
            "message": "Call ended successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_call_status(self, call_id: str) -> Optional[dict[str, Any]]:
        """Get call status.

        Args:
            call_id: Call ID.

        Returns:
            Call status dictionary, or None if not found.
        """
        call = self._calls.get(call_id)
        if call is None:
            return None

        codec_config = CODEC_CONFIGS[call.codec]
        uptime = time.time() - call.started_at if call.started_at else 0

        return {
            "call_id": call.call_id,
            "codec": codec_config.name,
            "caller_ip": call.caller_ip,
            "callee_ip": call.callee_ip,
            "state": call.state.value,
            "started_at": call.started_at,
            "uptime_seconds": round(uptime, 1),
            "network_conditions": {
                "latency_ms": call.network_conditions.latency_ms,
                "jitter_ms": call.network_conditions.jitter_ms,
                "packet_loss_percent": call.network_conditions.packet_loss_percent,
                "bandwidth_kbps": call.network_conditions.bandwidth_kbps,
            },
            "quality_metrics": call.quality_metrics.to_dict(),
        }

    async def get_call_quality(self, call_id: str) -> Optional[dict[str, Any]]:
        """Get real-time quality metrics for a call.

        Args:
            call_id: Call ID.

        Returns:
            Quality metrics dictionary, or None if not found.
        """
        call = self._calls.get(call_id)
        if call is None:
            return None

        return {
            "call_id": call.call_id,
            "codec": call.codec.value,
            "quality_metrics": call.quality_metrics.to_dict(),
            "quality_history": call._quality_history[-60:],  # Last 60 data points
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_statistics(self) -> dict[str, Any]:
        """Get overall voice simulation statistics.

        Returns:
            Statistics summary dictionary.
        """
        active_calls = []
        for call in self._calls.values():
            if call.state == CallState.ACTIVE:
                active_calls.append({
                    "call_id": call.call_id,
                    "codec": call.codec.value,
                    "uptime_seconds": round(time.time() - call.started_at, 1) if call.started_at else 0,
                    "mos": call.quality_metrics.mos,
                })

        return {
            "active_calls": self._active_calls,
            "total_calls": self._total_calls,
            "active_call_list": active_calls,
            "supported_codecs": [c.value for c in VoiceCodec],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def update_network_conditions(
        self,
        call_id: str,
        latency_ms: Optional[float] = None,
        jitter_ms: Optional[float] = None,
        packet_loss_percent: Optional[float] = None,
        bandwidth_kbps: Optional[float] = None,
    ) -> dict[str, Any]:
        """Update network conditions for a call.

        Args:
            call_id: Call ID.
            latency_ms: New latency value.
            jitter_ms: New jitter value.
            packet_loss_percent: New packet loss value.
            bandwidth_kbps: New bandwidth value.

        Returns:
            Updated conditions dictionary.

        Raises:
            ValueError: If call not found.
        """
        call = self._calls.get(call_id)
        if call is None:
            raise ValueError(f"Call '{call_id}' not found")

        if latency_ms is not None:
            call.network_conditions.latency_ms = latency_ms
        if jitter_ms is not None:
            call.network_conditions.jitter_ms = jitter_ms
        if packet_loss_percent is not None:
            call.network_conditions.packet_loss_percent = packet_loss_percent
        if bandwidth_kbps is not None:
            call.network_conditions.bandwidth_kbps = bandwidth_kbps

        return {
            "call_id": call_id,
            "network_conditions": {
                "latency_ms": call.network_conditions.latency_ms,
                "jitter_ms": call.network_conditions.jitter_ms,
                "packet_loss_percent": call.network_conditions.packet_loss_percent,
                "bandwidth_kbps": call.network_conditions.bandwidth_kbps,
            },
            "message": "Network conditions updated",
        }

    def _calculate_r_factor(self, conditions: NetworkConditions) -> float:
        """Calculate R-factor based on ITU-T G.107.

        R-factor ranges from 0 to 100, where:
        - 90+: Excellent quality
        - 80-90: Good quality
        - 70-80: Fair quality
        - 60-70: Poor quality
        - Below 60: Bad quality

        Args:
            conditions: Network conditions.

        Returns:
            R-factor value (0-100).
        """
        # Base R-factor (perfect conditions)
        r0 = 93.2

        # Delay impairment
        delay = conditions.latency_ms
        if delay <= 100:
            id = 0.024 * delay + 0.11 * (delay - 17.73) if delay > 17.73 else 0.0
        else:
            id = 0.024 * delay + 0.11 * (delay - 17.73) + 0.001 * (delay - 100) ** 1.5
        id = max(0.0, id)

        # Equipment impairment (codec + packet loss)
        codec_impairment = {
            VoiceCodec.G711: 0.0,
            VoiceCodec.G729: 11.0,
            VoiceCodec.OPUS: 2.0,
        }
        ie_codec = codec_impairment.get(self._current_codec, 0.0)

        # Packet loss impairment
        loss = conditions.packet_loss_percent
        burst_factor = 1.0  # Assume random loss
        ie_loss = ie_codec + (95 - ie_codec) * (loss / (loss + burst_factor * 15)) if loss > 0 else 0.0

        # Jitter impairment
        jitter_impairment = conditions.jitter_ms * 0.02 if conditions.jitter_ms > 20 else 0.0

        # Calculate R-factor
        r = r0 - id - ie_loss - jitter_impairment

        # Add some randomness for realism
        r += random.uniform(-2, 2)

        return max(0.0, min(100.0, r))

    def _calculate_mos(self, r_factor: float) -> float:
        """Calculate MOS (Mean Opinion Score) from R-factor.

        MOS ranges from 1 to 5:
        - 4.5+: Excellent
        - 4.0-4.5: Good
        - 3.5-4.0: Fair
        - 3.0-3.5: Poor
        - Below 3.0: Bad

        Args:
            r_factor: R-factor value (0-100).

        Returns:
            MOS score (1-5).
        """
        if r_factor < 0:
            mos = 1.0
        elif r_factor > 100:
            mos = 4.5
        else:
            # ITU-T G.107 conversion formula
            if r_factor < 6.5:
                mos = 1.0
            else:
                mos = 1.0 + 0.035 * r_factor + 7e-6 * r_factor * (r_factor - 60) * (100 - r_factor)

        # Add slight randomness
        mos += random.uniform(-0.1, 0.1)
        return max(1.0, min(5.0, mos))

    async def _run_call_simulation(self, call: VoiceCall) -> None:
        codec_config = CODEC_CONFIGS[call.codec]
        self._current_codec = call.codec
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rtp_seq = 0
        rtp_timestamp = 0
        rtp_ssrc = random.randint(0, 0xFFFFFFFF)

        try:
            while call.state == CallState.ACTIVE:
                conditions = call.network_conditions
                packet_size = codec_config.packet_size_bytes

                rtp_header = struct.pack('!BBHII',
                    0x80,
                    0x00,
                    rtp_seq & 0xFFFF,
                    rtp_timestamp,
                    rtp_ssrc,
                )
                audio_payload = bytes(random.randint(0, 255) for _ in range(max(0, packet_size - 12)))
                rtp_packet = rtp_header + audio_payload

                send_time = time.monotonic()
                try:
                    sock.sendto(rtp_packet, ('127.0.0.1', 10000 + (hash(call.call_id) % 1000)))
                    call.quality_metrics.packets_sent += 1
                    call.quality_metrics.bytes_sent += len(rtp_packet)
                except Exception:
                    call.quality_metrics.packets_lost += 1

                if random.random() * 100 < conditions.packet_loss_percent:
                    call.quality_metrics.packets_lost += 1
                else:
                    call.quality_metrics.packets_received += 1
                    call.quality_metrics.bytes_received += len(rtp_packet)

                actual_latency = conditions.latency_ms + random.uniform(
                    -conditions.jitter_ms, conditions.jitter_ms
                )
                call.quality_metrics.latency_ms = max(0, actual_latency)
                call.quality_metrics.jitter_ms = conditions.jitter_ms

                if call.quality_metrics.packets_sent > 0:
                    call.quality_metrics.packet_loss_percent = (
                        call.quality_metrics.packets_lost / call.quality_metrics.packets_sent * 100
                    )

                r_factor = self._calculate_r_factor(conditions)
                call.quality_metrics.r_factor = r_factor
                call.quality_metrics.mos = self._calculate_mos(r_factor)

                call._quality_history.append({
                    "timestamp": time.time(),
                    "mos": call.quality_metrics.mos,
                    "r_factor": r_factor,
                    "jitter_ms": call.quality_metrics.jitter_ms,
                    "packet_loss_percent": call.quality_metrics.packet_loss_percent,
                    "latency_ms": call.quality_metrics.latency_ms,
                })

                if len(call._quality_history) > 300:
                    call._quality_history = call._quality_history[-300:]

                rtp_seq = (rtp_seq + 1) & 0xFFFF
                rtp_timestamp += codec_config.sample_rate_hz * codec_config.frame_size_ms // 1000

                await asyncio.sleep(codec_config.frame_size_ms / 1000.0)

        except asyncio.CancelledError:
            pass
        except Exception:
            call.state = CallState.FAILED
        finally:
            sock.close()


# Global service instance
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create the global voice service instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
