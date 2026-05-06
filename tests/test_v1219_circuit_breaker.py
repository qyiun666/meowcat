# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.2.19 — Signal circuit breaker tests.

Tests the circuit breaker embedded in Nervous.signal():
- default off (backward compatible)
- circuit opens after consecutive failures reach threshold
- circuit resets on first success
- half-open probe: success → close, failure → re-open
- only the failed (to_organ, method) pair is affected
- CircuitOpenError carries diagnostics
"""

from __future__ import annotations

import time

import anyio
import pytest

from meowcat import EventBus, Nervous, OrganHost, biology
from meowcat.errors import CircuitOpenError
from meowcat.nervous import CircuitState


class _FragileOrgan:
    """An organ that fails a given number of times before succeeding."""

    def __init__(self, name: str, fail_count: int = 0) -> None:
        self.name = name
        self._fail_remaining = fail_count
        self.call_count = 0

    async def act(self, msg: str) -> str:
        self.call_count += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise RuntimeError(f"{self.name} failed ({self.call_count})")
        return f"{self.name}:{msg}"


class _AlwaysFailOrgan:
    def __init__(self, name: str) -> None:
        self.name = name

    async def act(self, msg: str) -> str:
        raise RuntimeError(f"{self.name} always fails")


def _build(circuit_breaker: bool = False, cb_threshold: int = 5,
           cb_timeout: float = 30.0) -> tuple[OrganHost, EventBus, Nervous]:
    host = OrganHost("cb-test")
    events = EventBus()
    nervous = Nervous(
        host, events,
        circuit_breaker=circuit_breaker,
        cb_threshold=cb_threshold,
        cb_timeout=cb_timeout,
    )
    return host, events, nervous


# -- Default off ------------------------------------------------------------

def test_circuit_breaker_disabled_by_default() -> None:
    """When circuit_breaker=False (default), failures never open circuits."""
    host, _, nervous = _build()
    host.mount("brain", "a", _FragileOrgan("a", fail_count=99))
    host.mount("brain", "b", _AlwaysFailOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 10 failures on the same pair — no CircuitOpenError
    for _ in range(10):
        with pytest.raises(RuntimeError, match="always fails"):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", "hi",
            )


# -- Circuit opens ----------------------------------------------------------

def test_circuit_opens_after_threshold() -> None:
    """After cb_threshold consecutive failures, the next call raises CircuitOpenError."""
    host, _, nervous = _build(circuit_breaker=True, cb_threshold=3)
    host.mount("brain", "a", _FragileOrgan("a"))
    host.mount("brain", "b", _AlwaysFailOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 3 failures (threshold)
    for i in range(3):
        with pytest.raises(RuntimeError):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", f"msg{i}",
            )

    # 4th call → CircuitOpenError
    with pytest.raises(CircuitOpenError) as exc_info:
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "after-open",
        )
    err = exc_info.value
    assert err.to_organ == ("brain", "b")
    assert err.method == "act"
    assert err.failures == 3
    assert err.retry_after > 0


# -- Circuit resets on success ----------------------------------------------

def test_circuit_resets_on_success() -> None:
    """Failures below threshold reset when a call succeeds."""
    host, _, nervous = _build(circuit_breaker=True, cb_threshold=5)
    host.mount("brain", "a", _FragileOrgan("a"))
    host.mount("brain", "b", _FragileOrgan("b", fail_count=2))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 2 failures
    for _ in range(2):
        with pytest.raises(RuntimeError):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", "fail",
            )

    # 1 success → counter resets
    result = anyio.run(
        nervous.signal,
        ("brain", "a"), ("brain", "b"),
        "act", "ok",
    )
    assert result == "b:ok"

    # After reset, threshold restarts — mount a new failing organ
    host.mount("brain", "b", _FragileOrgan("b", fail_count=1))
    # 1 failure — below threshold of 5, should NOT raise CircuitOpenError
    with pytest.raises(RuntimeError):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "fail-again",
        )
    # only 1 failure since reset, circuit still closed


# -- Half-open probe success ------------------------------------------------

def test_half_open_probe_succeeds() -> None:
    """After timeout, a probe call that succeeds closes the circuit."""
    host, _, nervous = _build(
        circuit_breaker=True, cb_threshold=2, cb_timeout=0.1,
    )
    host.mount("brain", "a", _FragileOrgan("a"))
    host.mount("brain", "b", _AlwaysFailOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 2 failures → circuit opens
    for _ in range(2):
        with pytest.raises(RuntimeError):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", "boom",
            )

    # Verify circuit is open
    with pytest.raises(CircuitOpenError):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "blocked",
        )

    # Wait for timeout
    time.sleep(0.15)

    # Mount a working organ — probe should succeed
    host.mount("brain", "b", _FragileOrgan("b", fail_count=0))
    result = anyio.run(
        nervous.signal,
        ("brain", "a"), ("brain", "b"),
        "act", "probe",
    )
    assert result == "b:probe"

    # Circuit should now be closed — further calls work
    result2 = anyio.run(
        nervous.signal,
        ("brain", "a"), ("brain", "b"),
        "act", "after-close",
    )
    assert result2 == "b:after-close"


# -- Half-open probe failure ------------------------------------------------

def test_half_open_probe_fails() -> None:
    """After timeout, a probe call that fails re-opens the circuit."""
    host, _, nervous = _build(
        circuit_breaker=True, cb_threshold=2, cb_timeout=0.1,
    )
    host.mount("brain", "a", _FragileOrgan("a"))
    host.mount("brain", "b", _AlwaysFailOrgan("b"))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))

    # 2 failures → circuit opens
    for _ in range(2):
        with pytest.raises(RuntimeError):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", "boom",
            )

    # Wait for timeout → half-open
    time.sleep(0.15)

    # Probe call — still fails (organ unchanged)
    with pytest.raises(RuntimeError, match="always fails"):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "probe-fail",
        )

    # Circuit re-opens — next call blocked
    with pytest.raises(CircuitOpenError):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "blocked-again",
        )


# -- Isolation --------------------------------------------------------------

def test_only_failed_pair_is_affected() -> None:
    """Other (to_organ, method) pairs are not affected by a tripped circuit."""
    host, _, nervous = _build(circuit_breaker=True, cb_threshold=2)
    host.mount("brain", "a", _FragileOrgan("a"))
    host.mount("brain", "b", _AlwaysFailOrgan("b"))
    host.mount("brain", "c", _FragileOrgan("c", fail_count=0))
    biology.apply_default_wiring(nervous.wiring)
    nervous.wiring.connect(("brain", "a"), ("brain", "b"))
    nervous.wiring.connect(("brain", "a"), ("brain", "c"))

    # Trip (a → b).act
    for _ in range(2):
        with pytest.raises(RuntimeError):
            anyio.run(
                nervous.signal,
                ("brain", "a"), ("brain", "b"),
                "act", "boom",
            )

    # (a → b).act is blocked
    with pytest.raises(CircuitOpenError):
        anyio.run(
            nervous.signal,
            ("brain", "a"), ("brain", "b"),
            "act", "blocked",
        )

    # (a → c).act is fine
    result = anyio.run(
        nervous.signal,
        ("brain", "a"), ("brain", "c"),
        "act", "still-ok",
    )
    assert result == "c:still-ok"


# -- CircuitState dataclass -------------------------------------------------

def test_circuit_state_defaults() -> None:
    cs = CircuitState()
    assert cs.failures == 0
    assert cs.last_failure == 0.0
    assert cs.open_until == 0.0

