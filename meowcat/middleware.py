"""meowcat 内置信号中间件 — 日志、追踪、限流、超时。

所有中间件实现 :class:`SignalMiddleware` Protocol，可直接通过
``cat.use_middleware(...)`` 注册使用。
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import logging
import time
from typing import Any

from meowcat.nervous import SignalCall, SignalMiddleware

_logger = logging.getLogger("meowcat.signal")


class SignalLogger:
    """记录每次 signal(from, to, method, duration)。

    日志级别为 DEBUG，内容包含调用方、目标、方法名和耗时（毫秒）。

    Example:

        cat.use_middleware(SignalLogger())
    """

    async def after(self, ctx: SignalCall, result: Any) -> Any:
        duration_ms = (time.monotonic() - ctx.timestamp) * 1000
        _logger.debug(
            "signal %s → %s.%s  (%.1fms)",
            ctx.from_organ, ctx.to_organ, ctx.method, duration_ms,
        )
        return result

    async def on_error(self, ctx: SignalCall, error: Exception) -> None:
        duration_ms = (time.monotonic() - ctx.timestamp) * 1000
        _logger.debug(
            "signal %s → %s.%s  ERROR %s: %s  (%.1fms)",
            ctx.from_organ, ctx.to_organ, ctx.method,
            type(error).__name__, error, duration_ms,
        )


class RateLimiter:
    """限制特定 organ 方法的调用频率。

    基于滑动窗口：在 ``window_seconds`` 内最多 ``max_calls`` 次。

    Args:
        max_calls: 窗口内最大调用次数
        window_seconds: 时间窗口（秒）

    Example:

        # 每个 organ.method 组合每秒最多 10 次
        cat.use_middleware(RateLimiter(max_calls=10, window_seconds=1.0))
    """

    def __init__(self, max_calls: int = 100, window_seconds: float = 1.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._buckets: dict[tuple, list[float]] = {}

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        key = (ctx.to_organ, ctx.method)
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, [])
        # 清理过期记录
        cutoff = now - self._window
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= self._max_calls:
            return None  # 短路：超过限流
        bucket.append(now)
        return ctx


class TimeoutGuard:
    """超时自动 abort。

    ``before`` 钩子在 signal 执行前检查当前时间是否已超过截止时间。
    适用于为整个 signal 调用链设置截止时间。

    Args:
        deadline: 截止时间（time.monotonic() 时间戳）

    Example:

        # 2 秒后所有 signal 都会被阻止
        cat.use_middleware(TimeoutGuard(deadline=time.monotonic() + 2.0))
    """

    def __init__(self, deadline: float) -> None:
        self._deadline = deadline

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        if time.monotonic() >= self._deadline:
            return None  # 短路：超时
        return ctx


class ContextInjector:
    """自动将额外上下文注入每次 signal 的 kwargs。

    用于 Gateway 将 SignalContext 注入到 signal 调用中。

    设计说明：此中间件只做注入，不关心 context 的内容结构。
    注入的键值通过构造参数传入。

    Args:
        inject: 要注入到 kwargs 的键值对

    Example:

        injector = ContextInjector(inject={"session_id": "cli-001", "platform": "cli"})
        cat.use_middleware(injector)
    """

    def __init__(self, inject: dict[str, Any]) -> None:
        self._inject = dict(inject)

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        # 将注入值合并到 kwargs（已有键不覆盖）
        for key, value in self._inject.items():
            if key not in ctx.kwargs:
                ctx.kwargs[key] = value
        return ctx


__all__ = ["SignalLogger", "RateLimiter", "TimeoutGuard", "ContextInjector"]
