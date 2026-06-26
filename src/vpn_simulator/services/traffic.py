"""Traffic capture service for VPN Simulator v2.

Provides simulated traffic generation and statistics for visualization
including packet generation, protocol filtering, and real-time metrics.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Protocol(str, Enum):
    """Supported network protocols."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    ARP = "arp"


@dataclass
class Packet:
    """Simulated network packet."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    protocol: Protocol = Protocol.TCP
    src_ip: str = "192.168.1.1"
    dst_ip: str = "10.0.0.1"
    src_port: int = 0
    dst_port: int = 0
    size: int = 64
    ttl: int = 64
    flags: list[str] = field(default_factory=list)
    payload_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert packet to dictionary."""
        return {
            "id": self.id,
            "timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "protocol": self.protocol.value,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "size": self.size,
            "ttl": self.ttl,
            "flags": self.flags,
            "payload_preview": self.payload_preview,
        }


@dataclass
class TrafficStats:
    """Real-time traffic statistics."""
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
    total_packets: int = 0
    total_bytes: int = 0
    protocol_counts: dict[str, int] = field(default_factory=dict)
    active_flows: int = 0
    capture_duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "packets_per_second": round(self.packets_per_second, 2),
            "bytes_per_second": round(self.bytes_per_second, 2),
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "protocol_counts": self.protocol_counts,
            "active_flows": self.active_flows,
            "capture_duration": round(self.capture_duration, 2),
        }


# Protocol-specific packet generation profiles
_PROTOCOL_PROFILES: dict[Protocol, dict[str, Any]] = {
    Protocol.TCP: {
        "base_size": 128,
        "size_variance": 512,
        "common_ports": [80, 443, 8080, 3000, 5000],
        "flags_options": [["SYN"], ["SYN", "ACK"], ["ACK"], ["FIN", "ACK"], ["PSH", "ACK"]],
        "weight": 0.5,
    },
    Protocol.UDP: {
        "base_size": 64,
        "size_variance": 256,
        "common_ports": [53, 123, 5060, 51820, 1194],
        "flags_options": [],
        "weight": 0.3,
    },
    Protocol.ICMP: {
        "base_size": 28,
        "size_variance": 64,
        "common_ports": [],
        "flags_options": [["echo_request"], ["echo_reply"], ["dest_unreachable"]],
        "weight": 0.15,
    },
    Protocol.ARP: {
        "base_size": 28,
        "size_variance": 0,
        "common_ports": [],
        "flags_options": [["request"], ["reply"]],
        "weight": 0.05,
    },
}

# Simulated IP address ranges
_IP_RANGES = [
    ("192.168.1.", 1, 254),
    ("10.0.0.", 1, 254),
    ("172.16.0.", 1, 254),
    ("100.64.0.", 1, 254),
]


class TrafficService:
    """Traffic capture and simulation service."""

    def __init__(self) -> None:
        self._capturing = False
        self._capture_start_time: Optional[float] = None
        self._packets: list[Packet] = []
        self._stats = TrafficStats()
        self._protocol_filter: Optional[set[Protocol]] = None
        self._packet_buffer: asyncio.Queue[Packet] = asyncio.Queue(maxsize=1000)
        self._generation_task: Optional[asyncio.Task] = None
        self._stats_update_task: Optional[asyncio.Task] = None
        self._recent_packets: list[Packet] = []
        self._max_recent_packets = 100

    def _generate_random_ip(self) -> str:
        """Generate a random IP address from simulated ranges."""
        prefix, start, end = random.choice(_IP_RANGES)
        return f"{prefix}{random.randint(start, end)}"

    def _generate_packet(self) -> Packet:
        """Generate a single simulated packet."""
        # Select protocol based on weights
        protocols = list(_PROTOCOL_PROFILES.keys())
        weights = [_PROTOCOL_PROFILES[p]["weight"] for p in protocols]
        protocol = random.choices(protocols, weights=weights, k=1)[0]

        profile = _PROTOCOL_PROFILES[protocol]

        # Generate packet size
        size = profile["base_size"] + random.randint(0, profile["size_variance"])

        # Generate ports for TCP/UDP
        src_port = random.choice(profile["common_ports"]) if profile["common_ports"] else 0
        dst_port = random.randint(1024, 65535) if profile["common_ports"] else 0

        # Select flags
        flags = random.choice(profile["flags_options"]) if profile["flags_options"] else []

        # Generate payload preview
        payload_preview = ""
        if protocol in (Protocol.TCP, Protocol.UDP):
            payload_preview = f"{random.randint(0, 255):02x}" * min(16, size)

        return Packet(
            protocol=protocol,
            src_ip=self._generate_random_ip(),
            dst_ip=self._generate_random_ip(),
            src_port=src_port,
            dst_port=dst_port,
            size=size,
            ttl=random.choice([64, 128, 255]),
            flags=flags,
            payload_preview=payload_preview,
        )

    async def _packet_generation_loop(self) -> None:
        """Continuously generate packets while capturing."""
        while self._capturing:
            try:
                # Generate 1-5 packets per iteration
                packet_count = random.randint(1, 5)
                for _ in range(packet_count):
                    if not self._capturing:
                        break

                    packet = self._generate_packet()

                    # Apply protocol filter
                    if self._protocol_filter and packet.protocol not in self._protocol_filter:
                        continue

                    # Add to collections
                    self._packets.append(packet)
                    self._recent_packets.append(packet)

                    # Trim recent packets
                    if len(self._recent_packets) > self._max_recent_packets:
                        self._recent_packets = self._recent_packets[-self._max_recent_packets:]

                    # Add to buffer for streaming
                    try:
                        self._packet_buffer.put_nowait(packet)
                    except asyncio.QueueFull:
                        # Drop oldest packet if buffer is full
                        try:
                            self._packet_buffer.get_nowait()
                            self._packet_buffer.put_nowait(packet)
                        except asyncio.QueueEmpty:
                            pass

                # Update statistics
                self._update_stats()

                # Variable delay to simulate realistic traffic
                delay = random.uniform(0.01, 0.1)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.1)

    def _update_stats(self) -> None:
        """Update traffic statistics."""
        if not self._packets:
            return

        now = time.time()
        if self._capture_start_time:
            self._stats.capture_duration = now - self._capture_start_time

        # Count packets in last second for PPS/BPS
        recent_cutoff = now - 1.0
        recent_packets = [p for p in self._packets if p.timestamp > recent_cutoff]

        self._stats.packets_per_second = len(recent_packets)
        self._stats.bytes_per_second = sum(p.size for p in recent_packets)
        self._stats.total_packets = len(self._packets)
        self._stats.total_bytes = sum(p.size for p in self._packets)

        # Update protocol counts
        protocol_counts: dict[str, int] = {}
        for p in self._packets:
            protocol_counts[p.protocol.value] = protocol_counts.get(p.protocol.value, 0) + 1
        self._stats.protocol_counts = protocol_counts

        # Simulate active flows
        self._stats.active_flows = random.randint(5, 50)

    async def start_capture(self, protocols: Optional[list[str]] = None) -> dict[str, Any]:
        """Start traffic capture.

        Args:
            protocols: Optional list of protocol names to filter

        Returns:
            Capture start confirmation
        """
        if self._capturing:
            return {"status": "already_capturing", "message": "Capture is already in progress"}

        # Set protocol filter
        if protocols:
            self._protocol_filter = {Protocol(p.lower()) for p in protocols if p.lower() in [e.value for e in Protocol]}
        else:
            self._protocol_filter = None

        # Reset state
        self._packets.clear()
        self._recent_packets.clear()
        self._stats = TrafficStats()
        self._capture_start_time = time.time()
        self._capturing = True

        # Start generation task
        self._generation_task = asyncio.create_task(self._packet_generation_loop())

        return {
            "status": "started",
            "message": "Traffic capture started",
            "protocols": list(self._protocol_filter) if self._protocol_filter else "all",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def stop_capture(self) -> dict[str, Any]:
        """Stop traffic capture.

        Returns:
            Capture stop confirmation with final statistics
        """
        if not self._capturing:
            return {"status": "not_capturing", "message": "No capture in progress"}

        self._capturing = False

        # Cancel generation task
        if self._generation_task:
            self._generation_task.cancel()
            try:
                await self._generation_task
            except asyncio.CancelledError:
                pass

        # Final stats update
        self._update_stats()

        return {
            "status": "stopped",
            "message": "Traffic capture stopped",
            "statistics": self._stats.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get current traffic statistics.

        Returns:
            Current traffic statistics
        """
        self._update_stats()
        return {
            "capturing": self._capturing,
            "statistics": self._stats.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_recent_packets(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent packets.

        Args:
            limit: Maximum number of packets to return

        Returns:
            List of recent packet dictionaries
        """
        packets = self._recent_packets[-limit:]
        return [p.to_dict() for p in reversed(packets)]

    async def get_packet_stream(self):
        """Async generator for streaming packets.

        Yields:
            Packet data as dictionaries
        """
        while True:
            try:
                packet = await asyncio.wait_for(self._packet_buffer.get(), timeout=1.0)
                yield packet.to_dict()
            except asyncio.TimeoutError:
                # Send keepalive
                yield {"type": "keepalive", "timestamp": datetime.now(timezone.utc).isoformat()}
            except asyncio.CancelledError:
                break

    @property
    def is_capturing(self) -> bool:
        """Check if capture is active."""
        return self._capturing

    @property
    def packet_count(self) -> int:
        """Get total captured packet count."""
        return len(self._packets)


# Global service instance
_traffic_service: Optional[TrafficService] = None


def get_traffic_service() -> TrafficService:
    """Get or create the global traffic service instance."""
    global _traffic_service
    if _traffic_service is None:
        _traffic_service = TrafficService()
    return _traffic_service
