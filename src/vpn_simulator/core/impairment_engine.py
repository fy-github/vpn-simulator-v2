"""ImpairmentEngine — 把时间变化损伤参数作用于真实报文流。

`ImpairmentService.current_params()` 只计算各已激活损伤的当前参数值
（如 ``{"delay_ms": 150.0, "loss_rate": 0.3}``），本引擎在 packetio 的
出站路径上把这些参数落地为真实的网络行为：

- ``delay_ms`` / ``jitter_ms`` → 发送前延迟（引入延迟与抖动）。
- ``loss_rate`` → 按概率丢弃报文。
- ``corrupt_probability`` / ``corrupt_bytes`` → 按概率翻转报文字节（损坏）。
- ``duplicate_probability`` → 按概率重复发送（一次变两份）。
- ``reorder_probability`` → 按概率与下一报文交换顺序（乱序）。
- ``bandwidth_kbps`` → 令牌桶限速（按报文比特数折算等待时间）。

参数名与 6 类故障插件保持一致（latency / packet_loss / corrupt / duplicate /
reorder / bandwidth）。

Example:
    >>> engine = ImpairmentEngine(service.current_params)
    >>> sock = UdpSocket("127.0.0.1", 0, impairment=engine)
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

ParamsProvider = Callable[[], dict[str, float]]


@dataclass
class OutboundDecision:
    """一个待发报文的损伤决策。

    Attributes:
        drop: 是否丢弃该报文（丢包）。
        data: 修改后的报文字节；``None`` 表示保持原样（未损坏）。
        delay_ms: 发送前需等待的总毫秒数（延迟/抖动 + 带宽限速折算）。
        duplicate: 是否重复发送（一次变两份）。
        reorder: 是否与下一报文交换顺序（乱序）。
    """

    drop: bool = False
    data: bytes | None = None
    delay_ms: float = 0.0
    duplicate: bool = False
    reorder: bool = False


class ImpairmentEngine:
    """损伤参数执行引擎。

    Attributes:
        _params_provider: 无参可调用对象，返回当前损伤参数 ``{param: value}``。
            默认返回空字典（无损伤）。
    """

    def __init__(self, params_provider: ParamsProvider | None = None) -> None:
        self._params_provider = params_provider or (lambda: {})
        self._tokens = 0.0
        self._last_refill = time.monotonic()

    def current_params(self) -> dict[str, float]:
        """返回当前损伤参数字典。"""
        return self._params_provider()

    async def apply_outbound(self, data: bytes) -> OutboundDecision:
        """对一个待发报文应用损伤，返回 `OutboundDecision`。

        延迟/抖动与带宽限速都折算进 ``delay_ms``，由调用方在发送前 sleep。
        """
        params = self.current_params()
        decision = OutboundDecision()

        # 丢包
        loss_rate = float(params.get("loss_rate", 0.0))
        if loss_rate > 0.0 and random.random() < loss_rate:
            decision.drop = True
            return decision

        # 损坏：翻转若干字节
        corrupt_prob = float(params.get("corrupt_probability", 0.0))
        if corrupt_prob > 0.0 and random.random() < corrupt_prob:
            corrupt_bytes = int(params.get("corrupt_bytes", 1))
            decision.data = self._corrupt(data, corrupt_bytes)

        # 重复发送
        duplicate_prob = float(params.get("duplicate_probability", 0.0))
        if duplicate_prob > 0.0 and random.random() < duplicate_prob:
            decision.duplicate = True

        # 乱序
        reorder_prob = float(params.get("reorder_probability", 0.0))
        if reorder_prob > 0.0 and random.random() < reorder_prob:
            decision.reorder = True

        # 延迟 / 抖动
        delay_ms = float(params.get("delay_ms", 0.0))
        jitter_ms = float(params.get("jitter_ms", 0.0))
        total_ms = delay_ms + (random.uniform(0.0, jitter_ms) if jitter_ms > 0.0 else 0.0)

        # 带宽限速（令牌桶）：按报文比特数折算等待时间
        bandwidth_kbps = float(params.get("bandwidth_kbps", 0.0))
        if bandwidth_kbps > 0.0:
            payload = decision.data if decision.data is not None else data
            total_ms += self._apply_bandwidth(len(payload), bandwidth_kbps)

        decision.delay_ms = max(0.0, total_ms)
        return decision

    @staticmethod
    def _corrupt(data: bytes, corrupt_bytes: int) -> bytes:
        """翻转 `corrupt_bytes` 个随机字节（异或一个非零值）。"""
        buffer = bytearray(data)
        n = min(max(int(corrupt_bytes), 0), len(buffer))
        if n <= 0:
            return data
        for _ in range(n):
            index = random.randrange(len(buffer))
            buffer[index] ^= random.randrange(1, 256)
        return bytes(buffer)

    def _apply_bandwidth(self, data_len: int, bandwidth_kbps: float) -> float:
        """令牌桶限速：返回为凑齐该报文所需等待的毫秒数。

        令牌以 bit 计，按 `bandwidth_kbps` 速率随时间补充；突发上限为 1 秒
        的令牌量。等待时间由调用方在发送前 sleep 落地。
        """
        bits = max(data_len, 0) * 8
        rate_bps = bandwidth_kbps * 1000.0

        now = time.monotonic()
        self._tokens += (now - self._last_refill) * rate_bps
        self._last_refill = now
        self._tokens = min(self._tokens, rate_bps)  # 突发上限 1 秒

        if self._tokens >= bits:
            self._tokens -= bits
            return 0.0

        deficit = bits - self._tokens
        self._tokens = 0.0
        return (deficit / rate_bps) * 1000.0
