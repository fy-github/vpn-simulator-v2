"""DHCP 模拟服务。

封装 ``tools/dhcp_occupy_vlan.py`` 脚本，以子进程方式执行 DHCP 地址模拟
（伪造随机 MAC 并发获取地址）与显式释放，并流式捕获脚本输出，供 Web UI
实时展示运行日志与租约结果。

脚本本身含原始套接字 / BPF 收发（VLAN trunk 模式），需要特权时由其自行
报错，本服务只负责进程生命周期管理与输出采集。

Example:
    >>> from vpn_simulator.services.dhcp import DHCPService
    >>> service = DHCPService()
    >>> service.start({"count": 5, "iface": "en0", "vlan": 20})
    >>> service.status(after=0)["state"]
    'running'
"""

from __future__ import annotations

import asyncio
import json
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# 脚本与状态文件路径
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "tools" / "dhcp_occupy_vlan.py"
_STATE_DIR = Path(tempfile.gettempdir()) / "vpn-simulator-dhcp"
_STATE_FILE = _STATE_DIR / "dhcp-leases.json"

# 日志环形缓冲上限
_MAX_LOGS = 2000

# 任务状态常量
STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_STOPPING = "stopping"
STATE_COMPLETED = "completed"
STATE_ERROR = "error"


@dataclass
class _DHCPJob:
    """运行中的一次 DHCP 模拟任务。"""

    state: str = STATE_IDLE
    proc: subprocess.Popen[str] | None = None
    seq: int = 0
    logs: list[dict[str, Any]] = field(default_factory=list)
    started_at: float | None = None
    finished_at: float | None = None
    returncode: int | None = None


class DHCPService:
    """DHCP 模拟服务。

    维护单个模拟任务（UDP 68 端口独占，同一时刻仅允许一个任务），
    通过子进程调用底层脚本，并采集其标准输出作为实时日志。

    Attributes:
        _script_path: 底层脚本路径。
        _state_dir: 状态文件目录。
        _state_file: 租约状态文件路径。
        _job: 当前任务。
        _lock: 保护任务状态的线程锁。
    """

    def __init__(
        self,
        script_path: Path | None = None,
        state_file: Path | None = None,
    ) -> None:
        """初始化 DHCP 服务。

        Args:
            script_path: 底层脚本路径，默认使用内置脚本。
            state_file: 租约状态文件路径，默认写入系统临时目录。
        """
        self._script_path = Path(script_path) if script_path else _SCRIPT_PATH
        self._state_dir = Path(state_file).parent if state_file else _STATE_DIR
        self._state_file = Path(state_file) if state_file else _STATE_FILE
        self._job = _DHCPJob()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------

    def start(self, params: dict[str, Any]) -> dict[str, Any]:
        """启动一次 DHCP 模拟任务。

        Args:
            params: 模拟参数（count / iface / vlan / hold / ...）。

        Returns:
            包含任务状态的字典。

        Raises:
            RuntimeError: 已有任务在运行，或脚本启动失败。
        """
        with self._lock:
            if self._job.state in (STATE_RUNNING, STATE_STOPPING):
                raise RuntimeError("已有模拟任务在运行，请先停止或等待完成")

        self._state_dir.mkdir(parents=True, exist_ok=True)
        job = _DHCPJob(state=STATE_RUNNING, started_at=time.time())

        try:
            proc = subprocess.Popen(
                self._build_args(params),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self._append_log(job, f"启动脚本失败: {exc}")
            job.state = STATE_ERROR
            job.finished_at = time.time()
            with self._lock:
                self._job = job
            raise RuntimeError(str(exc)) from exc

        job.proc = proc
        with self._lock:
            self._job = job

        threading.Thread(target=self._reader, args=(job, proc), daemon=True).start()
        logger.info("dhcp_job_started", pid=proc.pid, params=params)
        return {"state": STATE_RUNNING, "message": "DHCP 模拟任务已启动"}

    def stop(self) -> dict[str, Any]:
        """停止当前任务。

        向脚本进程发送 SIGINT，触发其 KeyboardInterrupt 清理逻辑
        （回收别名、保存状态、打印汇总）。

        Returns:
            包含任务状态的字典。
        """
        with self._lock:
            job = self._job
            proc = job.proc
            if job.state not in (STATE_RUNNING, STATE_STOPPING) or proc is None:
                return {"state": job.state, "message": "没有正在运行的任务"}
            job.state = STATE_STOPPING

        try:
            proc.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
        logger.info("dhcp_job_stopping", pid=proc.pid)
        return {"state": STATE_STOPPING, "message": "已发送停止信号"}

    async def release(
        self,
        iface: str | None = None,
        vlan: int | None = None,
        server: str | None = None,
    ) -> dict[str, Any]:
        """显式释放状态文件中保存的全部模拟地址。

        Args:
            iface: 网卡名（VLAN 模式必填）。
            vlan: VLAN ID。
            server: DHCP 服务器 IP。

        Returns:
            包含脚本输出与剩余租约的字典。
        """
        args = [
            sys.executable,
            str(self._script_path),
            "--release",
            "--save",
            str(self._state_file),
        ]
        if iface:
            args += ["--iface", iface]
        if vlan is not None:
            args += ["--vlan", str(vlan)]
        if server:
            args += ["--server", server]

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(args, capture_output=True, text=True)

        result = await asyncio.to_thread(_run)
        output = (result.stdout + result.stderr).strip()
        logger.info("dhcp_release_finished", returncode=result.returncode)
        return {
            "state": STATE_IDLE,
            "message": output,
            "returncode": result.returncode,
            "leases": self._read_leases(),
        }

    def status(self, after: int = 0) -> dict[str, Any]:
        """获取当前任务状态与增量日志。

        Args:
            after: 日志游标，仅返回 seq 大于该值的日志行。

        Returns:
            包含状态、增量日志与当前租约的字典。
        """
        with self._lock:
            job = self._job
            logs = [line for line in job.logs if line["seq"] > after]
            state = job.state
            seq = job.seq
            returncode = job.returncode
            started_at = job.started_at
            finished_at = job.finished_at

        return {
            "state": state,
            "seq": seq,
            "logs": logs,
            "leases": self._read_leases(),
            "returncode": returncode,
            "started_at": started_at,
            "finished_at": finished_at,
        }

    def leases(self) -> list[dict[str, Any]]:
        """读取当前租约状态文件。"""
        return self._read_leases()

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _build_args(self, params: dict[str, Any]) -> list[str]:
        """将参数字典转换为脚本命令行参数。"""
        args = [sys.executable, str(self._script_path)]
        args += ["-n", str(int(params.get("count", 5)))]
        args += ["--interval", str(float(params.get("interval", 0.5)))]
        args += ["--timeout", str(float(params.get("timeout", 6.0)))]
        args += ["--attempts", str(int(params.get("attempts", 3)))]

        if params.get("iface"):
            args += ["--iface", str(params["iface"])]
        if params.get("vlan") is not None:
            args += ["--vlan", str(int(params["vlan"]))]
        if params.get("source_mac") == "real":
            args += ["--source-mac", "real"]
        if params.get("server"):
            args += ["--server", str(params["server"])]
        if params.get("pool"):
            args += ["--pool", str(params["pool"])]
        if params.get("blind"):
            args += ["--blind"]
        if params.get("raw"):
            args += ["--raw"]
        if params.get("hold"):
            args += ["--hold"]
        if params.get("duration"):
            args += ["--duration", str(float(params["duration"]))]
        if params.get("verbose"):
            args += ["-v"]
        args += ["--save", str(self._state_file)]
        return args

    def _reader(self, job: _DHCPJob, proc: subprocess.Popen[str]) -> None:
        """后台线程：逐行采集脚本输出并在结束后更新任务状态。"""
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip("\n").rstrip("\r")
                if line:
                    self._append_log(job, line)
        finally:
            proc.wait()
            with self._lock:
                job.proc = None
                job.returncode = proc.returncode
                job.finished_at = time.time()
                if job.state == STATE_STOPPING:
                    job.state = STATE_COMPLETED
                elif proc.returncode == 0:
                    job.state = STATE_COMPLETED
                else:
                    job.state = STATE_ERROR
            logger.info("dhcp_job_finished", returncode=proc.returncode, state=job.state)

    def _append_log(self, job: _DHCPJob, line: str) -> None:
        """追加一行日志（带序号与时间戳）。"""
        with self._lock:
            job.seq += 1
            job.logs.append(
                {
                    "seq": job.seq,
                    "line": line,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                }
            )
            if len(job.logs) > _MAX_LOGS:
                job.logs = job.logs[-_MAX_LOGS:]

    def _read_leases(self) -> list[dict[str, Any]]:
        """读取租约状态文件（不存在或解析失败返回空列表）。"""
        try:
            if not self._state_file.exists():
                return []
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return data.get("leases", [])
        except (OSError, json.JSONDecodeError):
            return []
