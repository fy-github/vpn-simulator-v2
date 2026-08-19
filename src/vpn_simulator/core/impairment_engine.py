"""ImpairmentEngine — 把时间变化损伤参数作用于真实报文流。

`ImpairmentService.current_params()` 只计算各已激活损伤的当前参数值
（如 ``{"delay_ms": 150.0, "loss_rate": 0.3}``），本引擎在 packetio 的
出站路径上把这些参数落地为真实的网络行为：

- ``delay_ms`` / ``jitter_ms`` → 发送前 `asyncio.sleep`（引入延迟与抖动）。
- ``loss_rate`` → 按概率丢弃报文。

其余故障类型（corrupt / reorder / duplicate / bandwidth）需修改报文字节、
缓冲重排或令牌桶限速，暂不在真实报文层落地（保持故障插件状态语义不变）。

Example:
    >>> engine = ImpairmentEngine(service.current_params)
    >>> sock = UdpSocket("127.0.0.1", 0, impairment=engine)
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable

ParamsProvider = Callable[[], dict[str, float]]


class ImpairmentEngine:
    """损伤参数执行引擎。

    Attributes:
        _params_provider: 无参可调用对象，返回当前损伤参数 ``{param: value}``。
            默认返回空字典（无损伤）。
    """

    def __init__(self, params_provider: ParamsProvider | None = None) -> None:
        self._params_provider = params_provider or (lambda: {})

    def current_params(self) -> dict[str, float]:
        """返回当前损伤参数字典。"""
        return self._params_provider()

    async def apply_outbound(self) -> bool:
        """对一个待发报文应用损伤。

        返回 False 表示该报文应被丢弃（丢包）；返回 True 表示可继续发送。
        延迟/抖动在返回 True 之前通过 sleep 施加。
        """
        params = self.current_params()

        loss_rate = float(params.get("loss_rate", 0.0))
        if loss_rate > 0.0 and random.random() < loss_rate:
            return False

        delay_ms = float(params.get("delay_ms", 0.0))
        jitter_ms = float(params.get("jitter_ms", 0.0))
        total_ms = delay_ms + (random.uniform(0.0, jitter_ms) if jitter_ms > 0.0 else 0.0)
        if total_ms > 0.0:
            await asyncio.sleep(total_ms / 1000.0)

        return True
