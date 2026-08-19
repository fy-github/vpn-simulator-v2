"""PCAP 回放服务（F3）。

解析 PCAP/PCAPNG 文件，按原始时序（可变速 0.5x-10x、可按协议过滤）把
报文回放进 `traffic` 流（前端流量可视化 + packets 流）。

Example:
    >>> service = PcapService(config_manager)
    >>> info = await service.upload(pcap_bytes, "capture.pcap")
    >>> session = await service.start_replay(info.id, speed=2.0, protocol_filter="tcp")
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

import structlog
from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.l2 import ARP
from scapy.utils import rdpcap

from vpn_simulator.core.config import ConfigManager
from vpn_simulator.domain.pcap import PcapFileInfo, ReplaySession
from vpn_simulator.services.traffic import get_traffic_service

logger = structlog.get_logger(__name__)

MIN_SPEED = 0.5
MAX_SPEED = 10.0


def _packet_protocol(pkt: Any) -> str:
    """归一化 scapy 报文到简单协议名。"""
    if pkt.haslayer(TCP):
        return "tcp"
    if pkt.haslayer(UDP):
        return "udp"
    if pkt.haslayer(ICMP):
        return "icmp"
    if pkt.haslayer(ARP):
        return "arp"
    if pkt.haslayer(IP):
        return "ip"
    return "other"


class PcapService:
    """PCAP 回放服务。"""

    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager
        self._files: dict[str, PcapFileInfo] = {}
        self._packets: dict[str, list[dict[str, Any]]] = {}
        self._sessions: dict[str, ReplaySession] = {}

    # ------------------------------------------------------------------
    # 上传 / 解析
    # ------------------------------------------------------------------
    async def upload(self, data: bytes, filename: str) -> PcapFileInfo:
        """解析上传的 PCAP/PCAPNG 数据并登记文件。

        Args:
            data: PCAP 文件字节。
            filename: 原始文件名。

        Returns:
            PcapFileInfo 元数据。

        Raises:
            ValueError: 文件无法解析或无报文。
        """
        packets, protocols, duration = await asyncio.to_thread(self._parse, data)

        info = PcapFileInfo(
            filename=filename,
            packet_count=len(packets),
            protocols=sorted(protocols),
            duration_seconds=duration,
            size_bytes=len(data),
        )
        self._files[info.id] = info
        self._packets[info.id] = packets
        logger.info("pcap_uploaded", file_id=info.id, filename=filename, packets=len(packets))
        return info

    def _parse(self, data: bytes) -> tuple[list[dict[str, Any]], set[str], float]:
        """用 scapy 解析 PCAP 字节，返回 (报文元数据列表, 协议集合, 时长)。"""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcap")
        try:
            tmp.write(data)
            tmp.close()
            raw_packets = rdpcap(tmp.name)
        except Exception as e:
            raise ValueError(f"无法解析 PCAP 文件: {e}") from e
        finally:
            os.unlink(tmp.name)

        if not raw_packets:
            raise ValueError("PCAP 文件不含任何报文")

        parsed: list[dict[str, Any]] = []
        protocols: set[str] = set()
        for pkt in raw_packets:
            protocol = _packet_protocol(pkt)
            protocols.add(protocol)
            src_ip = dst_ip = ""
            src_port = dst_port = 0
            if pkt.haslayer(IP):
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
            if pkt.haslayer(TCP):
                src_port = int(pkt[TCP].sport)
                dst_port = int(pkt[TCP].dport)
            elif pkt.haslayer(UDP):
                src_port = int(pkt[UDP].sport)
                dst_port = int(pkt[UDP].dport)
            parsed.append(
                {
                    "time": float(pkt.time),
                    "protocol": protocol,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "src_port": src_port,
                    "dst_port": dst_port,
                    "size": len(bytes(pkt)),
                    "payload_preview": bytes(pkt).hex()[:32],
                }
            )

        duration = (
            float(raw_packets[-1].time) - float(raw_packets[0].time)
            if len(raw_packets) > 1
            else 0.0
        )
        return parsed, protocols, max(0.0, duration)

    # ------------------------------------------------------------------
    # 查询 / 统计
    # ------------------------------------------------------------------
    def list_files(self) -> list[dict[str, Any]]:
        """列出已上传文件。"""
        return [f.to_dict() for f in self._files.values()]

    def stats(self, file_id: str) -> dict[str, Any] | None:
        """返回文件的回放统计。"""
        info = self._files.get(file_id)
        if info is None:
            return None
        packets = self._packets.get(file_id, [])
        by_protocol: dict[str, int] = {}
        for p in packets:
            by_protocol[p["protocol"]] = by_protocol.get(p["protocol"], 0) + 1
        return {**info.to_dict(), "by_protocol": by_protocol}

    # ------------------------------------------------------------------
    # 回放
    # ------------------------------------------------------------------
    async def start_replay(
        self,
        file_id: str,
        speed: float = 1.0,
        protocol_filter: str | None = None,
    ) -> ReplaySession:
        """启动一次回放会话（后台任务）。

        Args:
            file_id: PCAP 文件 ID。
            speed: 回放速度（0.5x-10x）。
            protocol_filter: 协议过滤（如 "tcp"）。

        Returns:
            ReplaySession。

        Raises:
            ValueError: 文件不存在或速度越界。
        """
        if file_id not in self._files:
            raise ValueError(f"PCAP file '{file_id}' not found")
        if not MIN_SPEED <= speed <= MAX_SPEED:
            raise ValueError(f"speed must be in [{MIN_SPEED}, {MAX_SPEED}]")

        packets = self._packets[file_id]
        if protocol_filter:
            packets = [p for p in packets if p["protocol"] == protocol_filter]

        session = ReplaySession(
            pcap_file_id=file_id,
            speed=speed,
            protocol_filter=protocol_filter,
            status="running",
            total_packets=len(packets),
            started_at=datetime.now(),
        )
        self._sessions[session.id] = session
        session_task = asyncio.create_task(self._replay_task(session, packets))
        # 保存任务引用，防止被垃圾回收
        session_task.add_done_callback(lambda _: None)
        self._replay_tasks: dict[str, asyncio.Task] = getattr(self, "_replay_tasks", {})
        self._replay_tasks[session.id] = session_task
        logger.info("pcap_replay_started", session_id=session.id, file_id=file_id, speed=speed)
        return session

    async def _replay_task(self, session: ReplaySession, packets: list[dict[str, Any]]) -> None:
        """按原始时序（/速度）回放报文到 traffic 流。"""
        traffic = get_traffic_service()
        prev_time: float | None = None
        try:
            for pkt in packets:
                if session.status != "running":
                    break
                if prev_time is not None:
                    delay = (pkt["time"] - prev_time) / session.speed
                    if delay > 0:
                        await asyncio.sleep(delay)
                traffic.record_external_packet(
                    src_ip=pkt["src_ip"],
                    dst_ip=pkt["dst_ip"],
                    src_port=pkt["src_port"],
                    dst_port=pkt["dst_port"],
                    size=pkt["size"],
                    payload_preview=pkt["payload_preview"],
                )
                session.packets_replayed += 1
                prev_time = pkt["time"]
        except asyncio.CancelledError:
            session.status = "stopped"
            session.finished_at = datetime.now()
            raise
        finally:
            if session.status == "running":
                session.status = "completed"
                session.finished_at = datetime.now()
            logger.info(
                "pcap_replay_finished",
                session_id=session.id,
                status=session.status,
                replayed=session.packets_replayed,
            )

    def status(self, session_id: str) -> dict[str, Any] | None:
        """返回会话状态。"""
        session = self._sessions.get(session_id)
        return session.to_dict() if session else None

    async def stop_replay(self, session_id: str) -> dict[str, Any] | None:
        """停止回放会话。"""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.status = "stopped"
        task = getattr(self, "_replay_tasks", {}).get(session_id)
        if task is not None:
            task.cancel()
        session.finished_at = datetime.now()
        return session.to_dict()

    async def wait_for_completion(
        self, session_id: str, timeout: float = 30.0
    ) -> dict[str, Any] | None:
        """等待回放会话结束（测试/同步用）。"""
        task = getattr(self, "_replay_tasks", {}).get(session_id)
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        return self.status(session_id)
