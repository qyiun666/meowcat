# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat event system — event bus + event name constants.

Contains :class:`EventBus` (pub/sub dispatch) and all framework event name
constants: lifecycle, nerve signals, kitten lifecycle, self-awareness,
insight fusion, and loop hooks.

Zero business semantics:
- Event names are strings (prefer the constants defined in this module)
- handlers can be sync or async; ``emit`` auto-awaits awaitable return values
- Failed handlers are not swallowed; exceptions propagate to caller (framework does not decide for business logic)

P-02 philosophy: minimal code. EventBus only does "event name → callback list" dispatch.

Type-safe payloads: :mod:`meowcat.events_payloads` provides TypedDict payload
types for each event.  Annotate handler signatures with e.g.
``def on_signal(payload: NerveSignalPayload) -> None`` for IDE autocompletion.
"""


from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Any, Callable, Final

_logger = logging.getLogger(__name__)


Handler = Callable[..., Any]


# -- Event name constants (三个闭环 + 生命周期 + 神经信号 + 自我 + 融合) ------


class Lifecycle:
    """Cat lifecycle start/shutdown events."""

    START: Final[str] = "lifecycle.start"
    """Fired on cat startup, payload :class:`~meowcat.events_payloads.LifecycleStartPayload`."""

    SHUTDOWN: Final[str] = "lifecycle.shutdown"
    """Fired on cat shutdown, payload :class:`~meowcat.events_payloads.LifecycleShutdownPayload`."""

    # v0.5.1 Perception entry lifecycle
    PERCEIVE_START: Final[str] = "lifecycle.perceive_start"
    """Fired at ``cat.perceive(input)`` start, payload :class:`~meowcat.events_payloads.PerceiveStartPayload`."""

    PERCEIVE_END: Final[str] = "lifecycle.perceive_end"
    """Fired at ``cat.perceive(input)`` end, payload :class:`~meowcat.events_payloads.PerceiveEndPayload`."""


class LocateEvent:
    """Thalamus locate (find) related hooks."""

    PRE: Final[str] = "locate.pre"
    """Fired before Thalamus.locate() executes, payload :class:`~meowcat.events_payloads.LocatePrePayload`."""

    POST: Final[str] = "locate.post"
    """Fired after Thalamus.locate() returns, payload :class:`~meowcat.events_payloads.LocatePostPayload`."""

    ROUTE_DECIDED: Final[str] = "route.decided"
    """Fired when route decision is complete, payload :class:`~meowcat.events_payloads.RouteDecidedPayload`."""


class RememberEvent:
    """Hippocampus write (remember) + hypothalamus compression related hooks."""

    PRE: Final[str] = "remember.pre"
    """Payload :class:`~meowcat.events_payloads.RememberPrePayload`."""

    POST: Final[str] = "remember.post"
    """Payload :class:`~meowcat.events_payloads.RememberPostPayload`."""

    COMPRESS_PRE: Final[str] = "compress.pre"
    """Payload :class:`~meowcat.events_payloads.CompressPrePayload`."""

    COMPRESS_POST: Final[str] = "compress.post"
    """Payload :class:`~meowcat.events_payloads.CompressPostPayload`."""


# -- Loop B: Orchestration ----------------------------------------------

class OrchestrateEvent:
    """TaskOrchestrator related hooks."""

    START: Final[str] = "orchestrate.start"
    """Payload :class:`~meowcat.events_payloads.OrchestrateStartPayload`."""

    END: Final[str] = "orchestrate.end"
    """Payload :class:`~meowcat.events_payloads.OrchestrateEndPayload`."""


# -- Loop C: Growth/Crystallization --------------------------------------

class GrowthEvent:
    """Anomaly/correction/crystallize/role emergence hooks."""

    ANOMALY: Final[str] = "growth.anomaly"
    """Payload :class:`~meowcat.events_payloads.GrowthAnomalyPayload`."""

    CORRECTION: Final[str] = "growth.correction"
    """Payload :class:`~meowcat.events_payloads.GrowthCorrectionPayload`."""

    CRYSTALLIZE: Final[str] = "crystallize.emit"
    """Payload :class:`~meowcat.events_payloads.CrystallizePayload`."""

    ROLE_EMERGE: Final[str] = "role.emerge"
    """Payload :class:`~meowcat.events_payloads.RoleEmergePayload`."""


# -- Nerve synapse ---------------------------------------------------

class NerveEvent:
    """Neural potential event triggered during ``cat.signal()`` dispatch."""

    SIGNAL: Final[str] = "nerve.signal"
    """Broadcast on every legal signal call, payload :class:`~meowcat.events_payloads.NerveSignalPayload`.

    Illegal calls raise :class:`~meowcat.errors.IllegalNeuralPathError` directly,
    this event is not emitted."""


# -- Kitten lifecycle -----------------------------------------

class KittenEvent:
    """Kitten spawn/execute/reclaim hooks. See design.md §12.9."""

    SPAWNED: Final[str] = "kitten.spawned"
    """Kitten spawned, payload :class:`~meowcat.events_payloads.KittenSpawnedPayload`."""

    EXECUTING: Final[str] = "kitten.executing"
    """Kitten starts executing, payload :class:`~meowcat.events_payloads.KittenExecutingPayload`."""

    COMPLETED: Final[str] = "kitten.completed"
    """Kitten completed task, payload :class:`~meowcat.events_payloads.KittenCompletedPayload`."""

    STUCK: Final[str] = "kitten.stuck"
    """Kitten stuck, payload :class:`~meowcat.events_payloads.KittenStuckPayload`."""

    DISMISSED: Final[str] = "kitten.dismissed"
    """Kitten dismissed, payload :class:`~meowcat.events_payloads.KittenDismissedPayload`."""

    MERGE_ABSORBED: Final[str] = "kitten.merge_absorbed"
    """Main cat absorbed MergeProposal, payload :class:`~meowcat.events_payloads.KittenMergeAbsorbedPayload`."""


# -- Self / Reflection lifecycle ---------------------------------------

class SelfEvent:
    """CatSelf self-awareness loop hooks."""

    SNAPSHOT: Final[str] = "self.snapshot"
    """Fired after ``CatSelf.before_act()`` builds SelfSnapshot, payload :class:`~meowcat.events_payloads.SelfSnapshotPayload`."""

    REFLECT: Final[str] = "self.reflect"
    """Fired after ``CatSelf.after_act()`` writes back, payload :class:`~meowcat.events_payloads.SelfReflectPayload`."""


# -- PinealGland insight fusion ----------------------------------------

class FusionEvent:
    """PinealGland insight fusion hooks."""

    FUSE_SELF: Final[str] = "fusion.self"
    """Fired when insights are fused into cat's own self, payload :class:`~meowcat.events_payloads.FusionSelfPayload`."""

    FUSE_COLONY: Final[str] = "fusion.colony"
    """Fired when insights are fused into colony shared knowledge, payload :class:`~meowcat.events_payloads.FusionColonyPayload`."""

    TRIGGER_START: Final[str] = "fusion.trigger_start"
    """Fired at ``PinealGland.trigger()`` start, payload :class:`~meowcat.events_payloads.FusionTriggerStartPayload`."""

    TRIGGER_END: Final[str] = "fusion.trigger_end"
    """Fired at ``PinealGland.trigger()`` end, payload :class:`~meowcat.events_payloads.FusionTriggerEndPayload`."""


# -- Telemetry / Observability (v1.2.21) -----------------------------------

class TelemetryEvent:
    """Observability trace events emitted by :class:`~meowcat.telemetry.Tracer`."""

    SPAN: Final[str] = "telemetry.span"
    """Emitted when a signal span completes, payload :class:`~meowcat.events_payloads.TelemetrySpanPayload`."""


# -- Summary (for CI / doc auto-generation) --------------------------

ALL_EVENTS: Final[tuple[str, ...]] = (
    # Loop A
    LocateEvent.PRE, LocateEvent.POST, LocateEvent.ROUTE_DECIDED,
    RememberEvent.PRE, RememberEvent.POST,
    RememberEvent.COMPRESS_PRE, RememberEvent.COMPRESS_POST,
    # Loop B
    OrchestrateEvent.START, OrchestrateEvent.END,
    # Loop C
    GrowthEvent.ANOMALY, GrowthEvent.CORRECTION,
    GrowthEvent.CRYSTALLIZE, GrowthEvent.ROLE_EMERGE,
    # Lifecycle
    Lifecycle.START, Lifecycle.SHUTDOWN,
    Lifecycle.PERCEIVE_START, Lifecycle.PERCEIVE_END,
    # Nerve synapse
    NerveEvent.SIGNAL,
    # Kitten
    KittenEvent.SPAWNED, KittenEvent.EXECUTING, KittenEvent.COMPLETED,
    KittenEvent.STUCK, KittenEvent.DISMISSED, KittenEvent.MERGE_ABSORBED,
    # Self / Fusion
    SelfEvent.SNAPSHOT, SelfEvent.REFLECT,
    FusionEvent.FUSE_SELF, FusionEvent.FUSE_COLONY,
    FusionEvent.TRIGGER_START, FusionEvent.TRIGGER_END,
    # Telemetry
    TelemetryEvent.SPAN,
)


__all__ = [
    "EventBus", "Handler",
    "Lifecycle",
    "LocateEvent", "RememberEvent",
    "OrchestrateEvent", "GrowthEvent",
    "NerveEvent",
    "KittenEvent",
    "SelfEvent", "FusionEvent",
    "TelemetryEvent",
    "ALL_EVENTS",
]


class EventBus:
    """Cat nervous system: event name ↔ handler list."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        # v1.2.15: precomputed handler info cache — id(handler) → {takes_payload, is_async}
        self._handler_info: dict[int, dict[str, bool]] = {}
        # v1.2.25: lock to protect handler list during concurrent emit
        self._lock = asyncio.Lock()

    # -- Registration --------------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """Register a handler.

        Two usages:

            bus.on("locate.pre", my_handler)

            @bus.on("locate.pre")
            def my_handler(payload): ...
        """
        if handler is None:
            def decorator(fn: Handler) -> Handler:
                self._handlers[event].append(fn)
                self._handler_info[id(fn)] = self._precompute(fn)
                return fn
            return decorator
        self._handlers[event].append(handler)
        self._handler_info[id(handler)] = self._precompute(handler)
        return handler

    def off(self, event: str, handler: Handler) -> bool:
        """Unregister a handler. Returns False if not found, never raises."""
        lst = self._handlers.get(event)
        if not lst or handler not in lst:
            return False
        lst.remove(handler)
        self._handler_info.pop(id(handler), None)
        return True

    def clear(self, event: str | None = None) -> None:
        """Clear handlers for a specific event or all events."""
        if event is None:
            for lst in self._handlers.values():
                for h in lst:
                    self._handler_info.pop(id(h), None)
            self._handlers.clear()
        else:
            lst = self._handlers.pop(event, None)
            if lst:
                for h in lst:
                    self._handler_info.pop(id(h), None)

    # -- Trigger --------------------------------------------------------

    async def emit(self, event: str, payload: Any = None) -> None:
        """Trigger handlers in registration order; auto-awaits awaitable return values.

        Handlers accept 0 or 1 parameter:
        - ``def h(): ...``         → called with no argument
        - ``def h(payload): ...``  → called with payload
        """
        async with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            info = self._handler_info.get(id(handler))
            if info is None:
                # Fallback: handler registered externally, compute on the fly
                result = self._invoke(handler, payload)
                if inspect.isawaitable(result):
                    await result
                continue
            if info["takes_payload"]:
                result = handler(payload)
            else:
                result = handler()
            if info["is_async"]:
                await result

    @staticmethod
    def _precompute(handler: Handler) -> dict[str, bool]:
        """Precompute handler metadata: whether it takes payload and whether it's async."""
        try:
            sig = inspect.signature(handler)
            takes_payload = len(sig.parameters) > 0
        except (TypeError, ValueError):
            takes_payload = True
        return {
            "takes_payload": takes_payload,
            "is_async": inspect.iscoroutinefunction(handler),
        }

    @staticmethod
    def _invoke(handler: Handler, payload: Any) -> Any:
        """Decide whether to pass payload based on handler parameter count."""
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            return handler(payload)
        if len(sig.parameters) == 0:
            return handler()
        return handler(payload)

    # -- Synchronous fire-and-forget (v1.2.21) ----------------------------

    def emit_nowait(self, event: str, payload: Any = None) -> None:
        """Synchronous best-effort emit for sync contexts (e.g. telemetry).

        Calls handlers synchronously; async handlers are called but NOT
        awaited (their return values / coroutines are discarded).
        This is intentional — telemetry events are fire-and-forget.

        Handler exceptions are logged at DEBUG level and never propagated.

        For normal (awaitable) event dispatch, use :meth:`emit`.
        """
        for handler in list(self._handlers.get(event, [])):
            info = self._handler_info.get(id(handler))
            if info is None:
                try:
                    handler(payload)
                except Exception:
                    _logger.debug("emit_nowait handler '%s' failed",
                                  getattr(handler, "__name__", handler),
                                  exc_info=True)
                continue
            if info["takes_payload"]:
                try:
                    handler(payload)
                except Exception:
                    _logger.debug("emit_nowait handler '%s' failed",
                                  getattr(handler, "__name__", handler),
                                  exc_info=True)
            else:
                try:
                    handler()
                except Exception:
                    _logger.debug("emit_nowait handler '%s' failed",
                                  getattr(handler, "__name__", handler),
                                  exc_info=True)

    # -- Introspection --------------------------------------------------------

    def handlers(self, event: str) -> list[Handler]:
        """Return a snapshot of registered handlers (for testing/debugging)."""
        return list(self._handlers.get(event, []))

    def events(self) -> list[str]:
        """Return names of all events that have handlers."""
        return [e for e, hs in self._handlers.items() if hs]

