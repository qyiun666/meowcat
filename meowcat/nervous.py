# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat nervous system — Nervous subsystem (extracted in v0.5.9).

Communication conventions (v0.5.20+):
- signal(): formal channel with wiring validation
- probe(): read-only diagnostic, no wiring edge check
- inject(): bypass-validation writes via Needle (debug/admin only)
- direct call: allowed. As long as wiring has the corresponding edge,
  not all calls are forced through signal(). Direct calls are a performance optimization.

What truly needs to be prevented are FORBIDDEN paths absent from the wiring table.

Responsibility: holds :class:`Wiring`, adjudicates inter-organ access via ``signal()``,
read-only diagnostic via ``probe()``. Depends on explicitly injected :class:`OrganHost` +
:class:`EventBus`, can be instantiated independently for "signals only, no reflex arcs" scenarios::

    host = OrganHost("toy")
    events = EventBus()
    nervous = Nervous(host, events)
    nervous.wire_default()
    host.mount("brain", "cerebrum", brain)
    host.mount("brain", "hippocampus", hippo)
    nervous.freeze()
    await nervous.signal(
        ("brain", "cerebrum"), ("brain", "hippocampus"),
        "remember", msg="hi",
    )

Kitten scenario: pass ``forbidden_methods`` at construction to disable specific method names::

    nervous = Nervous(
        host, events,
        forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
    )
    await nervous.signal(..., "spawn_kitten")  # -> IllegalNeuralPathError
"""


from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from meowcat.errors import IllegalNeuralPathError, CircuitOpenError
from meowcat.events import EventBus
from meowcat.host import OrganHost
from meowcat.events import NerveEvent
from meowcat.telemetry import Tracer, Metrics, SignalSpan
from meowcat.wiring import Organ, Wiring


# -- Signal middleware types --------------------------------------------------

@dataclass(frozen=True)
class SignalCall:
    """Immutable context for a single signal() call."""
    from_organ: Organ
    to_organ: Organ
    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


# -- Circuit breaker types (v1.2.19) ---------------------------------------

@dataclass
class CircuitState:
    """Per-circuit failure tracking for signal circuit breaker.

    Keyed by ``(to_organ, method)``. Tracks consecutive failures and
    controls open/closed/half-open transitions.
    """
    failures: int = 0
    last_failure: float = 0.0
    open_until: float = 0.0


class SignalMiddleware(Protocol):
    """Signal middleware — executes before/after each signal() call.

    All methods are optional: implement only the hooks you need.
    """

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        """Called before signal execution. Return None to short-circuit (block execution).

        Returning a SignalCall instance means continue (ctx can be modified but framework
        ignores modifications; current version only supports None short-circuit semantics).
        """
        ...

    async def after(self, ctx: SignalCall, result: Any) -> Any:
        """Called after successful signal execution. Can modify/wrap return value."""
        ...

    async def on_error(self, ctx: SignalCall, error: Exception) -> None:
        """Called when signal raises an exception. Notification only; exception propagates."""
        ...


@lru_cache(maxsize=None)
def _build_organ_spec_index() -> dict[Organ, "OrganSpec"]:  # noqa: F821
    """Build ORGAN_SPECS coordinate→spec index (cached)."""
    from meowcat.biology import ORGAN_SPECS  # noqa: PLC0415
    return {s.coord: s for s in ORGAN_SPECS}


def _get_organ_spec(organ: Organ) -> "OrganSpec | None":  # noqa: F821
    """Look up spec in ORGAN_SPECS by organ coordinate."""
    return _build_organ_spec_index().get(organ)


@lru_cache(maxsize=None)
def _protocol_public_members(proto: type) -> frozenset[str]:
    """Return the set of public member names declared on a Protocol (cached).

    Used for signal contract validation: verify that `method` is declared
    on the target organ's Protocol. Excludes dunder/private attributes
    starting with ``_``, keeping only business API methods/fields.

    The cache keeps the 'member set' resident after the first validation
    per Protocol class; subsequent signal hot paths do only one dict lookup
    + one set membership check.
    """
    return frozenset(
        name for name in dir(proto) if not name.startswith("_")
    )


class Nervous:
    """Nervous system: signal dispatch + probe diagnostics + wiring lifecycle."""

    def __init__(
        self,
        host: OrganHost,
        events: EventBus,
        *,
        forbidden_methods: frozenset[str] = frozenset(),
        circuit_breaker: bool = False,
        cb_threshold: int = 5,
        cb_timeout: float = 30.0,
        enable_telemetry: bool = False,
    ) -> None:
        """Construct nervous system.

        Args:
            host: organ container (for resolving target organ instances)
            events: event bus (for emitting ``nerve.signal`` for debugging instrumentation)
            forbidden_methods: method-level blocklist. ``signal(..., method=X)`` raises
                :class:`IllegalNeuralPathError` when ``X in forbidden_methods``.
                Kittens use this to disable main-cat-only methods like ``spawn_kitten`` / ``absorb_merge``.
            circuit_breaker: enable signal-level circuit breaker (default False for
                backward compatibility). When enabled, consecutive failures on a
                ``(to_organ, method)`` pair will open the circuit after ``cb_threshold``
                failures, blocking further calls for ``cb_timeout`` seconds.
            cb_threshold: number of consecutive failures before circuit opens (default 5).
            cb_timeout: seconds the circuit stays open before transitioning to half-open
                to allow one probe call (default 30.0).
            enable_telemetry: enable observability tracing (default False for
                backward compatibility). When enabled, each ``signal()`` call produces
                a :class:`~meowcat.telemetry.SignalSpan` tracked by an internal
                :class:`~meowcat.telemetry.Tracer` and :class:`~meowcat.telemetry.Metrics`.
                Span-completion events are emitted through the event bus as
                ``TelemetryEvent.SPAN``.
        """
        self.host = host
        self.events = events
        self.wiring = Wiring()
        self.forbidden_methods = forbidden_methods
        self._middleware: list[SignalMiddleware] = []
        self._mw_info: list[dict[str, Any]] = []
        # circuit breaker (v1.2.19)
        self._cb_enabled = circuit_breaker
        self._cb_threshold = cb_threshold
        self._cb_timeout = cb_timeout
        self._circuits: dict[tuple[Organ, str], CircuitState] = {}
        self._cb_probing: set[tuple[Organ, str]] = set()

        # telemetry (v1.2.21)
        self._telemetry_enabled = enable_telemetry
        self.tracer: Tracer | None = Tracer(
            event_bus=events) if enable_telemetry else None
        self.metrics: Metrics | None = Metrics() if enable_telemetry else None

    # -- Synapse ------------------------------------------------------

    def use_middleware(self, mw: SignalMiddleware) -> None:
        """Register a signal middleware. Executed in registration order.

        Pre-classifies middleware capabilities on registration so the
        ``signal()`` hot path avoids repeated ``hasattr`` + ``isawaitable`` checks.
        """
        self._middleware.append(mw)
        info: dict[str, Any] = {"mw": mw}
        if hasattr(mw, "before"):
            info["has_before"] = True
            info["before_is_async"] = inspect.iscoroutinefunction(mw.before)
        if hasattr(mw, "after"):
            info["has_after"] = True
            info["after_is_async"] = inspect.iscoroutinefunction(mw.after)
        if hasattr(mw, "on_error"):
            info["has_on_error"] = True
            info["on_error_is_async"] = inspect.iscoroutinefunction(
                mw.on_error)
        self._mw_info.append(info)

    # -- Circuit breaker helpers (v1.2.19) ------------------------------

    def _cb_try_enter(self, to_organ: Organ, method: str) -> None:
        """Check circuit breaker before signal execution.

        Raises :class:`CircuitOpenError` if the circuit is open.
        Transitions from half-open to probing on first call after timeout.
        """
        if not self._cb_enabled:
            return
        key = (to_organ, method)
        state = self._circuits.get(key)
        if state is None:
            return  # no history, circuit closed

        now = time.monotonic()

        # Circuit is open → fast-fail (unless we are the probing call)
        if now < state.open_until:
            if key not in self._cb_probing:
                raise CircuitOpenError(
                    to_organ, method,
                    failures=state.failures,
                    retry_after=state.open_until - now,
                )
            # probing call: let it through
            return

        # Timeout expired, failures >= threshold → half-open
        if state.failures >= self._cb_threshold and key not in self._cb_probing:
            self._cb_probing.add(key)  # mark this call as probe

    def _cb_on_success(self, to_organ: Organ, method: str) -> None:
        """Record a successful signal call — reset the circuit."""
        if not self._cb_enabled:
            return
        key = (to_organ, method)
        self._circuits.pop(key, None)
        self._cb_probing.discard(key)

    def _cb_on_failure(self, to_organ: Organ, method: str) -> None:
        """Record a failed signal call — increment failures / open circuit."""
        if not self._cb_enabled:
            return
        key = (to_organ, method)
        now = time.monotonic()
        state = self._circuits.get(key)

        if state is None:
            state = CircuitState()
            self._circuits[key] = state

        state.last_failure = now

        # If this was a probing call, re-open immediately
        if key in self._cb_probing:
            self._cb_probing.discard(key)
            state.open_until = now + self._cb_timeout
            return

        state.failures += 1
        if state.failures >= self._cb_threshold:
            state.open_until = now + self._cb_timeout

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """The only legal channel for inter-organ calls.

        Flow:

        1. **Method blocklist**: ``method in forbidden_methods`` raises
           :class:`IllegalNeuralPathError`
        2. **Pathway validation**: ``wiring.assert_allowed(from, to)`` raises
           :class:`IllegalNeuralPathError` if illegal
        3. emit ``nerve.signal`` event (for debugging/instrumentation)
        4. Retrieve target organ from ``host.organ(*to_organ)``
        5. ``getattr(target, method)(*args, **kwargs)``, auto-awaits if awaitable

        Args:
            from_organ: caller organ coordinate ``(category, name)``
            to_organ: target organ coordinate ``(category, name)``
            method: method name to call on target
            *args, **kwargs: forwarded to target method

        Returns:
            target method's return value (already unwrapped if awaitable)
        """
        if method in self.forbidden_methods:
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=f"forbidden method '{method}'",
            )

        self.wiring.assert_allowed(from_organ, to_organ)

        # v0.5.11 Protocol contract validation: if target coordinate has a Protocol mapping,
        # verify method is declared on that Protocol. Skip if no mapping (preserving flexibility).
        from meowcat.biology import ORGAN_PROTOCOLS  # noqa: PLC0415
        protocol = ORGAN_PROTOCOLS.get(to_organ)
        if protocol is not None and method not in _protocol_public_members(protocol):
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=(
                    f"method '{method}' not declared on "
                    f"{protocol.__name__} for organ {to_organ}"
                ),
            )

        # v0.5.26 method-level write permission: non-write_callers calling write_method → raise
        spec = _get_organ_spec(to_organ)
        if spec and method in spec.write_methods and from_organ not in spec.write_callers:
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=(
                    f"'{method}' is a write method on {to_organ}, "
                    f"only {spec.write_callers} can call it"
                ),
            )

        # v1.2.19 circuit breaker: fast-fail if circuit is open
        self._cb_try_enter(to_organ, method)

        # v1.2.21 telemetry: start span
        span: SignalSpan | None = None
        if self._telemetry_enabled and self.tracer is not None:
            span = self.tracer.start_span(from_organ, to_organ, method)

        # build signal context
        ctx = SignalCall(
            from_organ=from_organ,
            to_organ=to_organ,
            method=method,
            args=args,
            kwargs=kwargs,
        )

        # before chain: any returns None → short-circuit
        for info in self._mw_info:
            if info.get("has_before"):
                before_result = info["mw"].before(ctx)
                if info["before_is_async"]:
                    before_result = await before_result
                if before_result is None:
                    return None

        await self.events.emit(
            NerveEvent.SIGNAL,
            {
                "from": from_organ,
                "to": to_organ,
                "method": method,
            },
        )

        target = self.host.organ(*to_organ)
        fn = getattr(target, method)
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            # v1.2.21 telemetry: end span with error
            if span is not None and self.tracer is not None:
                self.tracer.end_span(span, error=exc)
                if self.metrics is not None:
                    self.metrics.record(span)
            # v1.2.19 circuit breaker: record failure
            self._cb_on_failure(to_organ, method)
            for info in self._mw_info:
                if info.get("has_on_error"):
                    on_err = info["mw"].on_error(ctx, exc)
                    if info["on_error_is_async"]:
                        await on_err
            raise

        # v1.2.19 circuit breaker: reset on success
        self._cb_on_success(to_organ, method)

        # v1.2.21 telemetry: end span on success
        if span is not None and self.tracer is not None:
            self.tracer.end_span(span)
            if self.metrics is not None:
                self.metrics.record(span)

        # after chain: can modify/wrap return value
        for info in self._mw_info:
            if info.get("has_after"):
                after_result = info["mw"].after(ctx, result)
                if info["after_is_async"]:
                    result = await after_result
                else:
                    result = after_result

        return result

    # -- Stethoscope probe ------------------------------------------------

    async def probe(self, to_organ: Organ) -> dict[str, Any]:
        """Read-only diagnostic pathway.

        CLI, as a stethoscope, monitors wired organ state via this method. Unlike ``signal()``:

        - probe has no from_organ (CLI is not an organ), only checks to_organ is wired
        - only allows calling ``diagnose()`` (:class:`meowcat.protocols.Diagnosable`)
        - does not emit events (diagnostics are not neural signals)
        - return value must be dict

        Args:
            to_organ: target organ coordinate ``(category, name)``

        Returns:
            dict snapshot from organ's ``diagnose()``

        Raises:
            OrganNotMountedError: organ not mounted
            IllegalNeuralPathError: organ not in wiring
            TypeError: organ does not implement Diagnosable protocol or diagnose() returns non-dict
        """
        from meowcat.protocols import Diagnosable  # noqa: PLC0415

        if not self.wiring.is_organ_wired(to_organ):
            raise IllegalNeuralPathError(
                ("_probe", "_probe"), to_organ,
                reason="organ not wired — probe only allowed on wired organs",
            )

        target = self.host.organ(*to_organ)

        if not isinstance(target, Diagnosable):
            raise TypeError(
                f"Organ {to_organ} does not implement Diagnosable protocol"
            )

        fn = getattr(target, "diagnose")
        result = fn()
        if inspect.isawaitable(result):
            result = await result

        if not isinstance(result, dict):
            raise TypeError(
                f"Organ {to_organ}.diagnose() must return dict, "
                f"got {type(result).__name__}"
            )

        return result

    # -- Wiring lifecycle ----------------------------------------------

    def wire_default(self) -> None:
        """One-click assembly of the biological default neural pathway table.

        Equivalent to ``meowcat.biology.apply_default_wiring(self.wiring)``.
        Can be called at any time, can be called multiple times (wiring is a set, deduplicates).
        """
        from meowcat import biology  # noqa: PLC0415
        biology.apply_default_wiring(self.wiring)

    def freeze(self) -> None:
        """Freeze wiring. Subsequent ``wiring.connect/forbid`` raise :class:`MeowCatError`.

        Note: this method does **not validate reflexes**. Reflex-wiring consistency
        validation is handled by :class:`meowcat.reflex.ReflexArc.validate_paths`.
        Coordination is typically done by :meth:`CatBase.freeze_nervous_system`.
        """
        self.wiring.freeze()

    # -- Telemetry / CircuitBreaker public API (v1.3.6) -------------------

    def enable_telemetry(self) -> None:
        """Enable observability tracing at runtime.

        Creates :class:`~meowcat.telemetry.Tracer` and
        :class:`~meowcat.telemetry.Metrics` if not already present.
        Safe to call multiple times — subsequent calls are no-ops.
        """
        if not self._telemetry_enabled:
            self._telemetry_enabled = True
            if self.tracer is None:
                self.tracer = Tracer(event_bus=self.events)
            if self.metrics is None:
                self.metrics = Metrics()

    def disable_telemetry(self) -> None:
        """Disable observability tracing at runtime.

        Clears tracer and metrics. Subsequent ``signal()`` calls
        will not produce spans or collect metrics.
        """
        self._telemetry_enabled = False
        self.tracer = None
        self.metrics = None

    def enable_circuit_breaker(self) -> None:
        """Enable signal-level circuit breaker at runtime.

        Uses existing ``cb_threshold`` / ``cb_timeout`` values.
        Safe to call multiple times.
        """
        self._cb_enabled = True

    def disable_circuit_breaker(self) -> None:
        """Disable signal-level circuit breaker at runtime.

        Resets all circuit states. Subsequent ``signal()`` calls
        will not be blocked by circuit breaker.
        """
        self._cb_enabled = False
        self._circuits.clear()
        self._cb_probing.clear()


__all__ = ["Nervous", "SignalCall", "SignalMiddleware", "CircuitState"]
