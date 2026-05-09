# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.2.21 — Observability layer (telemetry) tests.

Tests the Tracer + Metrics + Nervous telemetry integration:
- default off (backward compatible)
- span lifecycle (start/end, trace_id, status)
- metrics: latency stats, error counts, call counts
- EventBus integration: TelemetryEvent.SPAN emitted
- bounded buffer (max_spans)
- clear/reset
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import EventBus, Nervous, OrganHost, biology
from meowcat.events import TelemetryEvent
from meowcat.telemetry import SignalSpan, Tracer


class _SimpleOrgan:
    def __init__(self, name: str) -> None:
        self.name = name

    async def act(self, msg: str) -> str:
        return f"{self.name}:{msg}"


class _FailingOrgan:
    def __init__(self, name: str, fail_after: int = 0) -> None:
        self.name = name
        self._count = 0
        self._fail_after = fail_after

    async def act(self, msg: str) -> str:
        self._count += 1
        if self._count > self._fail_after:
            raise RuntimeError(f"{self.name} boom")
        return f"{self.name}:{msg}"


def _build(enable_telemetry: bool = False):
    host = OrganHost("tele-test")
    events = EventBus()
    nervous = Nervous(host, events, enable_telemetry=enable_telemetry)
    return host, events, nervous


# -- Default off -------------------------------------------------------------

def test_telemetry_disabled_by_default():
    """When enable_telemetry=False (default), tracer and metrics are None."""
    host, events, nervous = _build()
    assert nervous.tracer is None
    assert nervous.metrics is None


def test_no_spans_when_disabled():
    """Signals produce no spans when telemetry is off."""
    host, events, nervous = _build(enable_telemetry=False)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    for _ in range(5):
        anyio.run(nervous.signal, ("brain", "a"), ("brain", "b"), "act", "hi")

    assert nervous.tracer is None
    assert nervous.metrics is None


# -- Span lifecycle ----------------------------------------------------------

def test_span_created_and_finalized_on_success():
    """A successful signal produces a span with status='ok'."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    anyio.run(nervous.signal, ("brain", "a"), ("brain", "b"), "act", "hello")

    spans = nervous.tracer.spans()
    assert len(spans) == 1
    span = spans[0]
    assert isinstance(span.trace_id, str)
    assert len(span.trace_id) == 16
    assert span.from_organ == ("brain", "a")
    assert span.to_organ == ("brain", "b")
    assert span.method == "act"
    assert span.started_at > 0
    assert span.finished_at is not None
    assert span.finished_at >= span.started_at
    assert span.status == "ok"
    assert span.error is None


def test_span_created_and_finalized_on_error():
    """A failing signal produces a span with status='error'."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _FailingOrgan("b", fail_after=0))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    with pytest.raises(RuntimeError):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", "fail")

    spans = nervous.tracer.spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status == "error"
    assert span.error is not None
    assert "RuntimeError" in span.error


def test_multiple_signals_produce_multiple_spans():
    """Each signal() call produces one span."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    for i in range(5):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", f"msg{i}")

    spans = nervous.tracer.spans()
    assert len(spans) == 5
    trace_ids = {s.trace_id for s in spans}
    assert len(trace_ids) == 5  # unique trace_ids


# -- Metrics: latency stats -------------------------------------------------

def test_metrics_latency_stats():
    """Metrics.latency_stats() returns correct count/avg/min/max."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    for i in range(3):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", f"msg{i}")

    stats = nervous.metrics.latency_stats()
    key = (("brain", "a"), ("brain", "b"), "act")
    assert key in stats
    assert stats[key]["count"] == 3
    assert stats[key]["avg"] > 0
    assert stats[key]["min"] > 0
    assert stats[key]["max"] >= stats[key]["avg"]


# -- Metrics: error counts --------------------------------------------------

def test_metrics_error_counts():
    """Metrics tracks errors by (from, to, method, error_type)."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _FailingOrgan("b", fail_after=0))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    with pytest.raises(RuntimeError):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", "fail")

    errors = nervous.metrics.error_counts()
    assert len(errors) >= 1
    # key = (from, to, method, error_type)
    err_key = (("brain", "a"), ("brain", "b"), "act", "RuntimeError")
    assert err_key in errors
    assert errors[err_key] == 1


# -- Metrics: call counts ---------------------------------------------------

def test_metrics_call_counts():
    """Metrics.call_counts() counts both successful and failed calls."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _FailingOrgan("b", fail_after=1))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 1 success, 1 failure
    anyio.run(nervous.signal, ("brain", "a"), ("brain", "b"), "act", "ok")
    with pytest.raises(RuntimeError):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", "fail")

    counts = nervous.metrics.call_counts()
    key = (("brain", "a"), ("brain", "b"), "act")
    assert counts[key] == 2


# -- EventBus integration ---------------------------------------------------

def test_telemetry_event_emitted_on_span():
    """When Tracer has an event_bus, TelemetryEvent.SPAN is emitted."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    received_payloads: list[dict] = []
    events.on(TelemetryEvent.SPAN, lambda p: received_payloads.append(p))

    anyio.run(nervous.signal, ("brain", "a"), ("brain", "b"), "act", "hello")

    assert len(received_payloads) == 1
    payload = received_payloads[0]
    assert payload["trace_id"] is not None
    assert payload["from"] == ("brain", "a")
    assert payload["to"] == ("brain", "b")
    assert payload["method"] == "act"
    assert payload["status"] == "ok"
    assert payload["error"] is None


def test_telemetry_event_emitted_on_error():
    """TelemetryEvent.SPAN is emitted even on failure, with error info."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _FailingOrgan("b", fail_after=0))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    received_payloads: list[dict] = []
    events.on(TelemetryEvent.SPAN, lambda p: received_payloads.append(p))

    with pytest.raises(RuntimeError):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", "fail")

    assert len(received_payloads) == 1
    payload = received_payloads[0]
    assert payload["status"] == "error"
    assert "RuntimeError" in payload["error"]


# -- Tracer max_spans --------------------------------------------------------

def test_tracer_bounded_buffer():
    """Tracer evicts oldest spans when max_spans exceeded."""
    tracer = Tracer(max_spans=3)
    from_org = ("brain", "a")
    to_org = ("brain", "b")

    for _i in range(5):
        span = tracer.start_span(from_org, to_org, "act")
        tracer.end_span(span)

    spans = tracer.spans()
    assert len(spans) == 3
    assert spans[0].trace_id != spans[-1].trace_id


# -- Tracer clear ------------------------------------------------------------

def test_tracer_clear():
    """Tracer.clear() removes all spans."""
    tracer = Tracer(max_spans=10)
    for _ in range(3):
        span = tracer.start_span(("brain", "a"), ("brain", "b"), "act")
        tracer.end_span(span)

    assert len(tracer.spans()) == 3
    tracer.clear()
    assert len(tracer.spans()) == 0


# -- Metrics clear -----------------------------------------------------------

def test_metrics_clear():
    """Metrics.clear() resets all counters."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    anyio.run(nervous.signal, ("brain", "a"), ("brain", "b"), "act", "hello")

    assert len(nervous.metrics.call_counts()) > 0
    nervous.metrics.clear()
    assert len(nervous.metrics.call_counts()) == 0
    assert len(nervous.metrics.latency_stats()) == 0
    assert len(nervous.metrics.error_counts()) == 0


# -- SignalSpan dataclass ---------------------------------------------------

def test_signal_span_defaults():
    """SignalSpan has correct defaults."""
    span = SignalSpan(
        trace_id="abc123",
        from_organ=("brain", "a"),
        to_organ=("brain", "b"),
        method="act",
        started_at=1.0,
    )
    assert span.trace_id == "abc123"
    assert span.from_organ == ("brain", "a")
    assert span.to_organ == ("brain", "b")
    assert span.method == "act"
    assert span.started_at == 1.0
    assert span.finished_at is None
    assert span.status == "ok"
    assert span.error is None


# -- Interaction: telemetry does not affect signal behaviour -----------------

def test_telemetry_does_not_change_signal_result():
    """Enabling telemetry should not change signal() return values."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _SimpleOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    result = anyio.run(
        nervous.signal, ("brain", "a"), ("brain", "b"), "act", "hello",
    )
    assert result == "b:hello"


def test_telemetry_does_not_suppress_errors():
    """Enabling telemetry should not suppress signal() errors."""
    host, events, nervous = _build(enable_telemetry=True)
    host.mount("brain", "a", _SimpleOrgan("a"))
    host.mount("brain", "b", _FailingOrgan("b", fail_after=0))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    with pytest.raises(RuntimeError, match="boom"):
        anyio.run(nervous.signal, ("brain", "a"),
                  ("brain", "b"), "act", "fail")

