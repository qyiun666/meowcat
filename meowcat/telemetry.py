# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat observability layer — Tracer + Metrics for signal paths.

Zero external dependencies. Emits span-completion events through EventBus
so application layers can subscribe for logging, dashboards, or forwarding
to external systems (OpenTelemetry, Prometheus, etc.).

Default off — enable via ``Nervous(enable_telemetry=True)`` for zero
overhead when not needed.

Design:
- :class:`Tracer` creates and collects :class:`SignalSpan` in memory.
- :class:`Metrics` tracks latency histogram and error counters per
  ``(from_organ, to_organ, method)`` key.
- Both emit ``TelemetryEvent.SPAN`` after each signal completes.

Copyright (c) 2026 Axonant. SPDX-License-Identifier: MIT.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from meowcat.wiring import Organ

if TYPE_CHECKING:
    from meowcat.events import EventBus


@dataclass
class SignalSpan:
    """A single ``signal()`` call trace span.

    Created by :meth:`Tracer.start_span` before signal execution and
    finalized by :meth:`Tracer.end_span` after the call completes
    (success or failure).
    """

    trace_id: str
    from_organ: Organ
    to_organ: Organ
    method: str
    started_at: float
    finished_at: float | None = None
    status: str = "ok"
    error: str | None = None


class Tracer:
    """Lightweight in-process tracer for ``Nervous.signal()`` calls.

    Collects :class:`SignalSpan` objects in a bounded in-memory buffer.
    Optionally emits ``TelemetryEvent.SPAN`` through an :class:`EventBus`
    for external subscribers.

    Args:
        max_spans: maximum number of completed spans to retain (oldest
            evicted when exceeded). Default 10,000.
        event_bus: optional EventBus for telemetry span events.
    """

    def __init__(
        self, max_spans: int = 10_000, event_bus: EventBus | None = None
    ) -> None:
        self._spans: list[SignalSpan] = []
        self._max_spans = max_spans
        self._event_bus = event_bus

    def start_span(
        self, from_organ: Organ, to_organ: Organ, method: str
    ) -> SignalSpan:
        """Create a span marking the start of a signal call.

        Returns a :class:`SignalSpan` to be passed to :meth:`end_span`
        when the call completes.
        """
        return SignalSpan(
            trace_id=uuid.uuid4().hex[:16],
            from_organ=from_organ,
            to_organ=to_organ,
            method=method,
            started_at=time.monotonic(),
        )

    def end_span(self, span: SignalSpan, error: Exception | None = None) -> None:
        """Finalize a span when the signal call completes.
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


        Records ``finished_at``, sets ``status`` and ``error`` fields,
        appends to the internal buffer, and optionally emits a
        ``TelemetryEvent.SPAN`` event.
        """
        span.finished_at = time.monotonic()
        if error is not None:
            span.status = "error"
            span.error = f"{type(error).__name__}: {error}"
        self._spans.append(span)
        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans:]

        if self._event_bus is not None:
            from meowcat.events import TelemetryEvent  # noqa: PLC0415
            self._event_bus.emit_nowait(
                TelemetryEvent.SPAN,
                {
                    "trace_id": span.trace_id,
                    "from": span.from_organ,
                    "to": span.to_organ,
                    "method": span.method,
                    "started_at": span.started_at,
                    "finished_at": span.finished_at,
                    "status": span.status,
                    "error": span.error,
                },
            )

    def spans(self) -> list[SignalSpan]:
        """Return a snapshot of all completed spans (newest last)."""
        return list(self._spans)
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    def clear(self) -> None:
        """Discard all collected spans."""
        self._spans.clear()


class Metrics:
    """Simple in-memory metrics collector for ``Nervous.signal()`` calls.

    Tracks per ``(from_organ, to_organ, method)`` key:
    - **Latency** (seconds): count, avg, min, max
    - **Error count**: broken down by error type
    - **Call count**: total successful + failed calls

    All metrics are purely in-process; no external system required.
    """

    def __init__(self) -> None:
        self._latency: dict[tuple[Organ, Organ, str],
                            list[float]] = defaultdict(list)
        self._errors: dict[tuple[Organ, Organ,
                                 str, str], int] = defaultdict(int)
        self._call_count: dict[tuple[Organ, Organ, str],
                               int] = defaultdict(int)

    def record(self, span: SignalSpan) -> None:
        """Record metrics from a completed :class:`SignalSpan`.

        Should be called after :meth:`Tracer.end_span`.
        """
        key = (span.from_organ, span.to_organ, span.method)
        self._call_count[key] += 1
        if span.finished_at is not None:
            self._latency[key].append(span.finished_at - span.started_at)
        if span.status == "error" and span.error:
            err_type = span.error.split(
                ":")[0] if ":" in span.error else span.error
            error_key = (*key, err_type)
            self._errors[error_key] += 1

    def latency_stats(self) -> dict[tuple, dict[str, float | int]]:
        """Return latency statistics per ``(from, to, method)`` key.

        Each value is a dict with ``count``, ``avg``, ``min``, ``max``.
        """
        result: dict[tuple, dict[str, float | int]] = {}
        for key, values in self._latency.items():
            if values:
                result[key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        return result

    def error_counts(self) -> dict[tuple[Organ, Organ, str, str], int]:
        """Return error counts per ``(from, to, method, error_type)`` key."""
        return dict(self._errors)

    def call_counts(self) -> dict[tuple[Organ, Organ, str], int]:
        """Return total call counts per ``(from, to, method)`` key."""
        return dict(self._call_count)

    def clear(self) -> None:
        """Reset all metrics to zero."""
        self._latency.clear()
        self._errors.clear()
        self._call_count.clear()


__all__ = ["SignalSpan", "Tracer", "Metrics"]

