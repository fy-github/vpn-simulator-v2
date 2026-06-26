"""Metrics collection service for VPN Simulator v2.

Provides simulated performance metrics for visualization including
throughput, latency, packet loss, and connection counts.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


# Protocol baseline parameters for realistic simulation
_PROTOCOL_PROFILES: dict[str, dict[str, Any]] = {
    "pptp": {
        "throughput_base": 100.0,
        "throughput_variance": 30.0,
        "latency_base": 25.0,
        "latency_variance": 10.0,
        "packet_loss_base": 0.5,
        "packet_loss_variance": 0.3,
    },
    "l2tp": {
        "throughput_base": 90.0,
        "throughput_variance": 25.0,
        "latency_base": 30.0,
        "latency_variance": 12.0,
        "packet_loss_base": 0.6,
        "packet_loss_variance": 0.4,
    },
    "openvpn": {
        "throughput_base": 200.0,
        "throughput_variance": 60.0,
        "latency_base": 45.0,
        "latency_variance": 20.0,
        "packet_loss_base": 0.2,
        "packet_loss_variance": 0.15,
    },
    "ipsec": {
        "throughput_base": 350.0,
        "throughput_variance": 80.0,
        "latency_base": 20.0,
        "latency_variance": 8.0,
        "packet_loss_base": 0.15,
        "packet_loss_variance": 0.1,
    },
    "ikev2": {
        "throughput_base": 400.0,
        "throughput_variance": 90.0,
        "latency_base": 15.0,
        "latency_variance": 6.0,
        "packet_loss_base": 0.1,
        "packet_loss_variance": 0.08,
    },
    "wireguard": {
        "throughput_base": 600.0,
        "throughput_variance": 150.0,
        "latency_base": 8.0,
        "latency_variance": 3.0,
        "packet_loss_base": 0.05,
        "packet_loss_variance": 0.03,
    },
}

_PROTOCOLS = list(_PROTOCOL_PROFILES.keys())

# Simulated connection distribution across protocols
_CONNECTION_DISTRIBUTION: dict[str, dict[str, Any]] = {
    "pptp": {"base": 15, "variance": 8},
    "l2tp": {"base": 12, "variance": 6},
    "openvpn": {"base": 35, "variance": 15},
    "ipsec": {"base": 25, "variance": 10},
    "ikev2": {"base": 20, "variance": 8},
    "wireguard": {"base": 45, "variance": 20},
}

# Time range configurations in seconds
_TIME_RANGES: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}

# Data point intervals in seconds
_INTERVALS: dict[str, int] = {
    "1m": 2,
    "5m": 5,
    "15m": 15,
    "1h": 60,
}


class MetricsService:
    """Performance metrics collection service using real system data."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._last_net_bytes = (0, 0)
        self._last_net_time = time.time()

    def _get_real_network_throughput(self) -> float:
        """Get real network throughput in Mbps using psutil."""
        try:
            import psutil
            counters = psutil.net_io_counters()
            now = time.time()
            elapsed = now - self._last_net_time
            if elapsed < 0.1:
                elapsed = 0.1
            bytes_sent = counters.bytes_sent
            bytes_recv = counters.bytes_recv
            total_now = bytes_sent + bytes_recv
            total_prev = self._last_net_bytes[0] + self._last_net_bytes[1]
            throughput_bps = (total_now - total_prev) / elapsed
            self._last_net_bytes = (bytes_sent, bytes_recv)
            self._last_net_time = now
            return round(throughput_bps * 8 / 1_000_000, 2)
        except (ImportError, Exception):
            return 0.0

    def _get_real_latency(self) -> float:
        """Get simulated latency based on system load."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            base_latency = 5.0
            load_factor = cpu / 100.0
            return round(base_latency + load_factor * 20.0 + random.uniform(-2, 2), 1)
        except (ImportError, Exception):
            return round(random.uniform(5.0, 25.0), 1)

    def get_throughput_data(
        self,
        time_range: str = "5m",
        protocol: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get throughput time series data using real network I/O."""
        duration = _TIME_RANGES.get(time_range, 300)
        interval = _INTERVALS.get(time_range, 5)
        num_points = duration // interval
        now = datetime.now(timezone.utc)

        timestamps = []
        values = []

        real_throughput = self._get_real_network_throughput()

        for i in range(num_points):
            ts = now - timedelta(seconds=(num_points - i - 1) * interval)
            timestamps.append(ts.isoformat())
            if protocol and protocol.lower() in _PROTOCOL_PROFILES:
                profile = _PROTOCOL_PROFILES[protocol.lower()]
                base = profile["throughput_base"]
                var = profile["throughput_variance"]
                scale = max(0.1, real_throughput / 100.0) if real_throughput > 0 else 1.0
                time_factor = 1.0 + 0.3 * (i % 60) / 60.0
                noise = random.gauss(0, var * 0.1)
                value = max(0, base * time_factor * scale + noise)
            else:
                time_factor = 1.0 + 0.3 * (i % 60) / 60.0
                noise = random.gauss(0, real_throughput * 0.1) if real_throughput > 0 else random.gauss(0, 5)
                value = max(0, real_throughput * time_factor + noise)
            values.append(round(value, 2))

        return {
            "timestamps": timestamps,
            "values": values,
            "unit": "Mbps",
            "time_range": time_range,
            "protocol": protocol or "all",
        }

    def get_latency_data(
        self,
        time_range: str = "5m",
        protocol: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get latency time series data.

        Args:
            time_range: Time range (1m, 5m, 15m, 1h)
            protocol: Filter by protocol name, or None for average

        Returns:
            Latency data with timestamps and values
        """
        duration = _TIME_RANGES.get(time_range, 300)
        interval = _INTERVALS.get(time_range, 5)
        num_points = duration // interval
        now = datetime.now(timezone.utc)

        timestamps = []
        values = []
        min_values = []
        max_values = []

        real_latency = self._get_real_latency()

        for i in range(num_points):
            ts = now - timedelta(seconds=(num_points - i - 1) * interval)
            timestamps.append(ts.isoformat())
            if protocol and protocol.lower() in _PROTOCOL_PROFILES:
                profile = _PROTOCOL_PROFILES[protocol.lower()]
                base = profile["latency_base"]
                var = profile["latency_variance"]
                scale = real_latency / 15.0 if real_latency > 0 else 1.0
                spike = random.uniform(1.5, 3.0) if random.random() < 0.05 else 1.0
                noise = random.gauss(0, var * 0.15)
                avg = max(1.0, base * spike * scale + noise)
            else:
                spike = random.uniform(1.5, 3.0) if random.random() < 0.03 else 1.0
                noise = random.gauss(0, real_latency * 0.1)
                avg = max(1.0, real_latency * spike + noise)
            values.append(round(avg, 2))
            min_values.append(round(max(1.0, avg - random.uniform(2, 5)), 2))
            max_values.append(round(avg + random.uniform(3, 10), 2))

        return {
            "timestamps": timestamps,
            "values": values,
            "min_values": min_values,
            "max_values": max_values,
            "unit": "ms",
            "time_range": time_range,
            "protocol": protocol or "all",
        }

    def get_packet_loss_data(
        self,
        time_range: str = "5m",
        protocol: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get packet loss time series data.

        Args:
            time_range: Time range (1m, 5m, 15m, 1h)
            protocol: Filter by protocol name, or None for aggregate

        Returns:
            Packet loss data with timestamps and values
        """
        duration = _TIME_RANGES.get(time_range, 300)
        interval = _INTERVALS.get(time_range, 5)
        num_points = duration // interval
        now = datetime.now(timezone.utc)

        timestamps = []
        values = []

        if protocol and protocol.lower() in _PROTOCOL_PROFILES:
            profile = _PROTOCOL_PROFILES[protocol.lower()]
            for i in range(num_points):
                ts = now - timedelta(seconds=(num_points - i - 1) * interval)
                timestamps.append(ts.isoformat())
                base = profile["packet_loss_base"]
                var = profile["packet_loss_variance"]
                # Occasional burst loss
                burst = random.uniform(2.0, 5.0) if random.random() < 0.03 else 1.0
                noise = random.gauss(0, var * 0.1)
                value = max(0.0, min(100.0, base * burst + noise))
                values.append(round(value, 3))
        else:
            for i in range(num_points):
                ts = now - timedelta(seconds=(num_points - i - 1) * interval)
                timestamps.append(ts.isoformat())
                total = 0.0
                count = 0
                for name, p in _PROTOCOL_PROFILES.items():
                    conn_count = _CONNECTION_DISTRIBUTION[name]["base"]
                    burst = random.uniform(2.0, 5.0) if random.random() < 0.02 else 1.0
                    noise = random.gauss(0, p["packet_loss_variance"] * 0.1)
                    val = max(0.0, min(100.0, p["packet_loss_base"] * burst + noise))
                    total += val * conn_count
                    count += conn_count
                value = total / count if count > 0 else 0
                values.append(round(value, 3))

        return {
            "timestamps": timestamps,
            "values": values,
            "unit": "%",
            "time_range": time_range,
            "protocol": protocol or "all",
        }

    def get_connections_data(
        self,
        time_range: str = "5m",
    ) -> dict[str, Any]:
        """Get connection count time series data.

        Args:
            time_range: Time range (1m, 5m, 15m, 1h)

        Returns:
            Connection count data with per-protocol breakdown
        """
        duration = _TIME_RANGES.get(time_range, 300)
        interval = _INTERVALS.get(time_range, 5)
        num_points = duration // interval
        now = datetime.now(timezone.utc)

        timestamps = []
        protocols_data: dict[str, list[int]] = {p: [] for p in _PROTOCOLS}
        total_values = []

        for i in range(num_points):
            ts = now - timedelta(seconds=(num_points - i - 1) * interval)
            timestamps.append(ts.isoformat())

            total = 0
            # Simulate connection pattern with daily cycle
            hour_factor = 1.0 + 0.5 * (i % 120) / 120.0

            for name in _PROTOCOLS:
                cfg = _CONNECTION_DISTRIBUTION[name]
                base = int(cfg["base"] * hour_factor)
                variance = cfg["variance"]
                count = max(0, base + random.randint(-variance, variance))
                protocols_data[name].append(count)
                total += count

            total_values.append(total)

        return {
            "timestamps": timestamps,
            "total": total_values,
            "protocols": protocols_data,
            "unit": "connections",
            "time_range": time_range,
        }

    def get_protocol_distribution(self) -> dict[str, Any]:
        """Get current connection distribution across protocols.

        Returns:
            Protocol distribution data for pie chart
        """
        distribution = {}
        total = 0

        for name in _PROTOCOLS:
            cfg = _CONNECTION_DISTRIBUTION[name]
            count = max(0, cfg["base"] + random.randint(-cfg["variance"], cfg["variance"]))
            distribution[name] = count
            total += count

        percentages = {
            name: round((count / total * 100) if total > 0 else 0, 1)
            for name, count in distribution.items()
        }

        return {
            "protocols": list(distribution.keys()),
            "counts": list(distribution.values()),
            "percentages": list(percentages.values()),
            "total": total,
        }

    def get_statistics(
        self,
        time_range: str = "5m",
        protocol: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get aggregated statistics for the given time range.

        Args:
            time_range: Time range (1m, 5m, 15m, 1h)
            protocol: Filter by protocol name, or None for all

        Returns:
            Summary statistics for throughput, latency, packet loss, connections
        """
        throughput = self.get_throughput_data(time_range, protocol)
        latency = self.get_latency_data(time_range, protocol)
        packet_loss = self.get_packet_loss_data(time_range, protocol)
        connections = self.get_connections_data(time_range)

        def _calc_stats(values: list[float]) -> dict[str, float]:
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            return {
                "min": round(sorted_vals[0], 2),
                "max": round(sorted_vals[-1], 2),
                "avg": round(sum(sorted_vals) / n, 2),
                "p50": round(sorted_vals[n // 2], 2),
                "p95": round(sorted_vals[int(n * 0.95)], 2),
                "p99": round(sorted_vals[int(n * 0.99)], 2),
            }

        return {
            "throughput": {
                "stats": _calc_stats(throughput["values"]),
                "unit": "Mbps",
            },
            "latency": {
                "stats": _calc_stats(latency["values"]),
                "unit": "ms",
            },
            "packet_loss": {
                "stats": _calc_stats(packet_loss["values"]),
                "unit": "%",
            },
            "connections": {
                "current": connections["total"][-1] if connections["total"] else 0,
                "peak": max(connections["total"]) if connections["total"] else 0,
                "average": round(
                    sum(connections["total"]) / len(connections["total"])
                    if connections["total"]
                    else 0,
                    1,
                ),
            },
            "time_range": time_range,
            "protocol": protocol or "all",
            "data_points": len(throughput["values"]),
        }
