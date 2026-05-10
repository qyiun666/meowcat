# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat loops — Loop dataclass + LoopRegistry + LoopSequence + built-in registries.

Loop = Chain + trigger event + exit event.  LoopSequence composes multiple loops sequentially or
event-driven.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from meowcat.chain import (
    DIAGNOSTIC_CHAIN as _DC,
)
from meowcat.chain import (
    GROWTH_CHAIN as _GC,
)
from meowcat.chain import (
    MAINTENANCE_CHAIN as _MC,
)
from meowcat.chain import (
    REFLECTION_CHAIN as _RC,
)
from meowcat.chain import (
    Chain,
)
from meowcat.events import Lifecycle

logger = logging.getLogger(__name__)


# -- Lookup reusable Chains from BUILTIN_CHAINS -------------------------

_MAINTENANCE_CHAIN: Chain = _MC
_DIAGNOSTIC_CHAIN: Chain = _DC
_GROWTH_CHAIN: Chain = _GC
_REFLECTION_CHAIN: Chain = _RC


# -- Loop dataclass -------------------------------------------------


@dataclass(frozen=True)
class Loop:
    """A named loop: Chain + trigger/exit events.

    A Loop encapsulates a :class:`Chain` execution plus lifecycle event triggers.
    Trigger event is emitted before chain execution, exit event after.

    Attributes:
        name: Unique loop name, e.g. ``"conversation"``
        description: Human-readable description
        chain: Associated chain
        trigger: Trigger event name (None means manual trigger)
        exit_event: Exit event name (None means no exit event)
    """

    name: str
    description: str
    chain: Chain
    trigger: str | None = None
    exit_event: str | None = None


# -- 5 default loops -------------------------------------------------

# 🔻 降级为内部实现（v2.4.0）：不再作为公开 API 导出。
# 应用层应使用 cat.perceive()。cat.run_loop("conversation") 仍可用但不再教学。
CONVERSATION_LOOP: Loop = Loop(
    "conversation",
    "Standard conversation loop — hear→reason→speak (internal, use cat.perceive() instead)",
    chain=Chain(
        "conversation_chain",
        ("hear", "deep_reason", "speak"),
        "Conversation chain",
    ),
    trigger=Lifecycle.PERCEIVE_START,
)

# 🔻 降级为内部实现（v2.4.0）：不再作为公开 API 导出。
# 应用层应使用 cat.do_task()。cat.run_loop("tool_execution") 仍可用但不再教学。
TOOL_EXECUTION_LOOP: Loop = Loop(
    "tool_execution",
    "Tool execution loop — hear→execute→speak (internal, use cat.do_task() instead)",
    chain=Chain(
        "tool_loop_chain",
        ("hear", "execute_tool", "speak"),
        "Tool chain",
    ),
    trigger="orchestrate.start",
)

DANGER_RESPONSE_LOOP: Loop = Loop(
    "danger_response",
    "Danger response loop — safety assessment",
    chain=Chain(
        "danger_chain",
        ("assess_safety",),
        "Danger chain",
    ),
    trigger="amygdala.alert",
)

MAINTENANCE_LOOP: Loop = Loop(
    "maintenance",
    "Self-maintenance loop — decay+cleanup",
    chain=_MAINTENANCE_CHAIN,
    trigger="heartbeat.tick",
)

DIAGNOSTIC_LOOP: Loop = Loop(
    "diagnostic",
    "Diagnostic loop — run crystallizer hotspots + usage stats",
    chain=_DIAGNOSTIC_CHAIN,
    trigger=None,  # manual trigger
)

# -- v1.3.0 Growth loops ---------------------------------------------------

GROWTH_LOOP: Loop = Loop(
    "growth",
    "Growth loop — learn from anomalies → crystallize",
    chain=_GROWTH_CHAIN,
    trigger="post_action",
)

REFLECTION_LOOP: Loop = Loop(
    "reflection",
    "Reflection loop — post-execution skill review",
    chain=_REFLECTION_CHAIN,
    trigger="tool_executed",
)

BUILTIN_LOOPS: tuple[Loop, ...] = (
    CONVERSATION_LOOP,
    TOOL_EXECUTION_LOOP,
    DANGER_RESPONSE_LOOP,
    MAINTENANCE_LOOP,
    DIAGNOSTIC_LOOP,
    GROWTH_LOOP,
    REFLECTION_LOOP,
)


def register_default_loops(
    loop_registry: LoopRegistry,
    chain_registry: Any,
) -> None:
    """Register the 5 default loops and their associated Chains into the registries.

    For each built-in loop:
    1. If its Chain is not yet registered, register the Chain first
    2. Register the Loop

    Args:
        loop_registry: Loop registry instance
        chain_registry: Chain registry instance (must support register/get)
    """
    for lp in BUILTIN_LOOPS:
        if chain_registry.get(lp.chain.name) is None:
            chain_registry.register(lp.chain)
        loop_registry.register(lp)


# -- LoopRegistry ---------------------------------------------------


def _register_item(registry: dict, registry_list: list, item: Any, expected_type: type) -> None:
    """Register an item in dict + list registry, overwriting by name if exists."""
    if not isinstance(item, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__} instance, got {type(item).__name__}")
    name = item.name
    if name in registry:
        registry_list.remove(registry[name])
    registry[name] = item
    registry_list.append(item)


@dataclass
class LoopRegistry:
    """Loop registry — manages Loop registration, lookup, and execution.

    Usage::

        registry = LoopRegistry()
        register_default_loops(registry, cat.chain_registry)

        # Lookup
        loop = registry.get("conversation")
        all_loops = registry.list_all()

        # Execute
        result = await registry.run(cat, "conversation", message="hello")
    """

    _loops: dict[str, Loop] = field(default_factory=dict, init=False)
    _loops_list: list[Loop] = field(default_factory=list, init=False)

    def register(self, loop: Loop) -> None:
        """Register a loop. Same name overwrites."""
        _register_item(self._loops, self._loops_list, loop, Loop)

    def get(self, name: str) -> Loop | None:
        """Look up a loop by name.

        Args:
            name: Loop name

        Returns:
            Loop object, None if not found
        """
        return self._loops.get(name)

    def list_all(self) -> list[Loop]:
        """Return all registered items (registration order)."""
        return list(self._loops_list)

    async def run(self, cat: Any, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a loop: trigger event → run chain → exit event.

        Args:
            cat: CatBase instance (must support emit/chain_registry.run)
            name: Loop name
            **initial_input: Initial input

        Returns:
            Chain execution result (dict)

        Raises:
            KeyError: Loop not found, or chain not found
        """
        loop = self.get(name)
        if loop is None:
            raise KeyError(f"Loop '{name}' not found in registry")

        # Trigger event
        if loop.trigger:
            await cat.emit(loop.trigger, initial_input)

        # Execute chain
        result = await cat.chain_registry.run(
            cat,
            loop.chain.name,
            **initial_input,
        )

        # Exit event
        if loop.exit_event:
            await cat.emit(loop.exit_event, result)

        return result


# -- LoopSequence dataclass (v1.0.4) ----------------------------------


@dataclass(frozen=True)
class LoopSequence:
    """Meta-loop — sequential/event-driven composition of multiple Loops.

    Composition: Path → Chain → Loop → LoopSequence.

    Attributes:
        name: Unique meta-loop name.
        description: Human-readable description.
        loops: Sequence of registered ``Loop`` names.
        mode: ``"sequential"`` (pass result to next) or ``"event_driven"`` (concurrent).
        stop_on_error: ``True`` — any failure raises; ``False`` — skip and continue.
    """

    name: str
    description: str = ""
    loops: tuple[str, ...] = ()
    mode: str = "sequential"
    stop_on_error: bool = True

    def __post_init__(self) -> None:
        if self.mode not in ("sequential", "event_driven"):
            raise ValueError(
                f"mode must be 'sequential' or 'event_driven', got {self.mode!r}")


# -- Built-in LoopSequence -----------------------------------------------

DAILY_MAINTENANCE_SEQ: LoopSequence = LoopSequence(
    "daily_maintenance",
    "Daily maintenance — self-maintenance then checkup",
    loops=("maintenance", "diagnostic"),
    mode="sequential",
)

BUILTIN_LOOPSEQS: tuple[LoopSequence, ...] = (DAILY_MAINTENANCE_SEQ,)


# -- LoopSequenceRegistry (v1.0.4) ------------------------------------


@dataclass
class LoopSequenceRegistry:
    """Meta-loop registry — manages LoopSequence registration, lookup, and execution.

    Usage::

        registry = LoopSequenceRegistry()
        registry.register(DAILY_MAINTENANCE_SEQ)

        # Execute
        result = await registry.run(cat, "daily_maintenance")
    """

    _seqs: dict[str, LoopSequence] = field(default_factory=dict, init=False)
    _seqs_list: list[LoopSequence] = field(default_factory=list, init=False)

    def register(self, seq: LoopSequence) -> None:
        """Register a meta-loop. Same name overwrites."""
        _register_item(self._seqs, self._seqs_list, seq, LoopSequence)

    def get(self, name: str) -> LoopSequence | None:
        """Look up a meta-loop by name.

        Args:
            name: Meta-loop name

        Returns:
            LoopSequence object, None if not found
        """
        return self._seqs.get(name)

    def list_all(self) -> list[LoopSequence]:
        """Return all registered items (registration order)."""
        return list(self._seqs_list)

    async def run(
        self,
        cat: Any,
        name: str,
        **initial_input: Any,
    ) -> dict[str, Any]:
        """Execute a meta-loop.

        **sequential**: execute in order, previous result → next step kwargs.
        **event_driven**: all loops concurrently, same ``initial_input``.

        Returns:
            Last result dict (sequential) or ``{loop_name: result}`` (event_driven).

        Raises:
            KeyError: Meta-loop or referenced Loop not found.
        """

        seq = self.get(name)
        if seq is None:
            raise KeyError(f"LoopSequence '{name}' not found in registry")

        if not seq.loops:
            return {"": dict(initial_input)}

        if seq.mode == "sequential":
            return await self._run_sequential(
                cat,
                seq,
                **initial_input,
            )
        return await self._run_event_driven(
            cat,
            seq,
            **initial_input,
        )

    async def _run_sequential(
        self,
        cat: Any,
        seq: LoopSequence,
        **initial_input: Any,
    ) -> dict[str, Any]:
        """Execute loops sequentially, passing previous result to next step."""
        current_input: dict[str, Any] = dict(initial_input)
        last_result: Any = current_input

        for loop_name in seq.loops:
            try:
                last_result = await cat.loop_registry.run(
                    cat,
                    loop_name,
                    **current_input,
                )
                current_input = last_result if isinstance(last_result, dict) else {
                    "_result": last_result}
            except Exception:
                logger.warning(
                    "Loop %r failed in LoopSequence, skipping", loop_name, exc_info=True
                )
                if seq.stop_on_error:
                    raise
                current_input = dict(initial_input)

        if isinstance(last_result, dict):
            return last_result
        return {"_result": last_result}

    async def _run_event_driven(
        self,
        cat: Any,
        seq: LoopSequence,
        **initial_input: Any,
    ) -> dict[str, Any]:
        """Execute loops concurrently, each receives the same initial_input."""
        import asyncio

        async def _run_one(loop_name: str) -> tuple[str, Any]:
            try:
                result = await cat.loop_registry.run(
                    cat,
                    loop_name,
                    **initial_input,
                )
                return (loop_name, result)
            except Exception as e:
                if seq.stop_on_error:
                    raise
                return (loop_name, {"_error": str(e)})

        pending = {asyncio.ensure_future(_run_one(ln)): ln for ln in seq.loops}
        results: dict[str, Any] = {}

        if seq.stop_on_error:
            # gather mode: any failure propagates exception, remaining tasks cancelled
            gathered = await asyncio.gather(*pending)
            for loop_name, result in gathered:
                results[loop_name] = result
        else:
            # tolerate errors: wait one by one, collect all results
            for fut in asyncio.as_completed(pending):
                loop_name, result = await fut
                results[loop_name] = result

        return results


__all__ = [
    "Loop",
    "LoopRegistry",
    "DANGER_RESPONSE_LOOP",
    "MAINTENANCE_LOOP",
    "DIAGNOSTIC_LOOP",
    "GROWTH_LOOP",
    "REFLECTION_LOOP",
    "BUILTIN_LOOPS",
    "register_default_loops",
    "LoopSequence",
    "LoopSequenceRegistry",
    "DAILY_MAINTENANCE_SEQ",
    "BUILTIN_LOOPSEQS",
]


# -- Import protection: redirect wrong imports to correct path ------

_EVENTS_HELD_IN_MEOWCAT_EVENTS: frozenset[str] = frozenset({
    "LocateEvent", "RememberEvent", "OrchestrateEvent", "GrowthEvent",
    "Lifecycle", "KittenEvent", "NerveEvent", "SelfEvent",
    "FusionEvent", "TelemetryEvent", "EventBus", "Handler", "ALL_EVENTS",
})


def __getattr__(name: str):
    if name in _EVENTS_HELD_IN_MEOWCAT_EVENTS:
        raise AttributeError(
            f"{name!r} is not in meowcat.loops. Use: from meowcat.events import {name}"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
