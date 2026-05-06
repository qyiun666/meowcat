# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat built-in signal middleware — logging, tracing, rate limiting, timeout.

All middleware implements :class:`SignalMiddleware` Protocol, can be registered
directly via ``cat.use_middleware(...)``.
"""


from __future__ import annotations

import inspect
import logging
import time
from typing import Any, Callable

from meowcat.nervous import SignalCall, SignalMiddleware

_logger = logging.getLogger("meowcat.signal")


class SignalLogger:
    """Log every signal(from, to, method, duration).

    Log level is DEBUG, content includes caller, target, method name, and duration (milliseconds).

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
    """Limit call frequency for specific organ methods.

    Sliding window based: at most ``max_calls`` within ``window_seconds``.

    Args:
        max_calls: maximum calls within the window
        window_seconds: time window (seconds)

    Example:

        # at most 10 calls per second per organ.method pair
        cat.use_middleware(RateLimiter(max_calls=10, window_seconds=1.0))
    """

    def __init__(self, max_calls: int = 100, window_seconds: float = 1.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._buckets: dict[tuple, list[float]] = {}

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        key = (ctx.to_organ, ctx.method)
        now = time.monotonic()
        if key not in self._buckets:
            self._buckets[key] = []
        bucket = self._buckets[key]
        # purge expired entries
        cutoff = now - self._window
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= self._max_calls:
            return None  # short-circuit: rate limit exceeded
        bucket.append(now)
        return ctx


# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

class TimeoutGuard:
    """Auto-abort on timeout.

    The ``before`` hook checks whether the current time has exceeded the deadline
    before signal execution. Suitable for setting a deadline for entire signal call chains.

    Args:
        deadline: deadline time (time.monotonic() timestamp)
        on_timeout: optional callback invoked when timeout occurs.
            Receives :class:`SignalCall` ctx. Can be sync or async.
            Use to notify organs (e.g. Amygdala recording anomaly).
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    Example:

        # all signals blocked after 2 seconds
        cat.use_middleware(TimeoutGuard(deadline=time.monotonic() + 2.0))

        # with timeout notification
        cat.use_middleware(TimeoutGuard(
            deadline=time.monotonic() + 2.0,
            on_timeout=lambda ctx: cat.emit("paws_timeout", ctx),
        ))
    """

    def __init__(
        self,
        deadline: float,
        on_timeout: Callable[[SignalCall], Any] | None = None,
    ) -> None:
        self._deadline = deadline
        self._on_timeout = on_timeout

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        if time.monotonic() >= self._deadline:
            if self._on_timeout is not None:
                result = self._on_timeout(ctx)
                if inspect.isawaitable(result):
                    await result
            return None  # short-circuit: timeout
        return ctx


class ContextInjector:
    """Auto-inject extra context into kwargs of every signal.

    Used by Gateway to inject SignalContext into signal calls.

    Design note: this middleware only does injection, not concerned with context content structure.
    Injected key-values are passed via constructor arguments.

    Args:
        inject: key-value pairs to inject into kwargs

    Example:

        injector = ContextInjector(inject={"session_id": "cli-001", "platform": "cli"})
        cat.use_middleware(injector)
    """

    def __init__(self, inject: dict[str, Any]) -> None:
        self._inject = dict(inject)

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        # merge injected values into kwargs (existing keys not overwritten)
        for key, value in self._inject.items():
            if key not in ctx.kwargs:
                ctx.kwargs[key] = value
        return ctx


__all__ = ["SignalLogger", "RateLimiter", "TimeoutGuard", "ContextInjector"]

