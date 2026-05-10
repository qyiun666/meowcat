# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat reflex arcs — stimulus→response execution contract.

:class:`Reflex` three elements:
- ``trigger``: when to fire (callable(input)→bool)
- ``path``: organ sequence the neural signal travels through (for validation)
- ``stages``: optional Stage list (if present, runs Pipeline; otherwise only emits EventBus along path)

:class:`ReflexRegistry` stores by priority descending; ``match(input)`` returns the first hit.

:class:`ReflexArc` (v0.5.9) encapsulates registry + events + optional nervous, providing
``perceive()`` reflex entry point. Can be instantiated independently, no CatBase dependency.

At startup, ``cat.freeze_nervous_system()`` calls ``validate(wiring)`` to check each Reflex's
path adjacency hops are legal in wiring; illegal raises :class:`ReflexPathInvalidError`.
"""

from __future__ import annotations

import bisect
import logging
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from pydantic import BaseModel, ConfigDict, Field

# v1.0.18: built-in reflex path structures
from meowcat.anatomy import (
    AMYGDALA,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    EARS,
    MOUTH,
    THALAMUS,
)
from meowcat.errors import NoReflexMatchedError, ReflexPathInvalidError
from meowcat.events import EventBus, Lifecycle, NerveEvent
from meowcat.perception import PerceptionContext, infer_modality
from meowcat.pipeline import Pipeline
from meowcat.protocols import StageProtocol
from meowcat.wiring import Organ, Wiring

if TYPE_CHECKING:
    from meowcat.nervous import Nervous

Trigger = Callable[[Any], bool]


class Reflex(BaseModel):
    """A single reflex arc."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    """Reflex name (e.g. ``text_dialogue`` / ``visual`` / ``danger`` / ``action_order``)."""

    trigger: Trigger
    """Function that determines whether input triggers this reflex."""

    path: tuple[Organ, ...]
    """Organ sequence the neural signal travels through, at least 2 hops. Used for wiring legality validation."""

    stages: list[StageProtocol] = Field(default_factory=list)
    """Optional: concrete Pipeline Stage list.

    - non-empty: ``cat.perceive`` drives via Pipeline
    - empty   : ``cat.perceive`` emits ``nerve.signal`` events hop-by-hop along path (for business handlers)
    """

    priority: int = 0
    """Priority when multiple reflexes match; higher matches first."""

    def hops(self) -> list[tuple[Organ, Organ]]:
        """Path adjacency hop sequence: ``[(p0,p1), (p1,p2), ...]``."""
        return list(zip(self.path[:-1], self.path[1:], strict=False))


class ReflexRegistry:
    """Reflex registry."""

    def __init__(self) -> None:
        # v1.2.15: dict + priority-sorted list instead of single list for O(1) lookup + O(log n) insert
        self._by_name: dict[str, Reflex] = {}
        self._by_priority: list[Reflex] = []  # always sorted by priority desc
        # v1.1.26: hot path observation — per-reflex trigger counters
        self._trigger_counts: dict[str, int] = {}
        self._total_triggers: int = 0

    # -- Write API ------------------------------------------------------

    def register(self, reflex: Reflex) -> None:
        """Register a reflex. Inserts by priority descending for linear scan during match."""
        if len(reflex.path) < 2:
            raise ValueError(
                f"Reflex '{reflex.name}' path must have at least 2 hops",
            )
        # name is unique: replace if name already exists
        old = self._by_name.pop(reflex.name, None)
        if old is not None:
            self._by_priority.remove(old)
        self._by_name[reflex.name] = reflex
        bisect.insort(self._by_priority, reflex, key=lambda r: -r.priority)

    def unregister(self, name: str) -> bool:
        """Remove by name, returns False if not found."""
        reflex = self._by_name.pop(name, None)
        if reflex is None:
            return False
        self._by_priority.remove(reflex)
        return True

    # -- Query API ----------------------------------------------------

    def get(self, name: str) -> Reflex | None:
        """Retrieve reflex by name, returns None if not found."""
        return self._by_name.get(name)

    def match(self, input: Any) -> Reflex | None:
        """From high to low priority, return first reflex whose trigger matches, or None."""
        for r in self._by_priority:
            try:
                if r.trigger(input):
                    return r
            except Exception:
                logger.warning(
                    "Reflex trigger %r raised an exception", r.name, exc_info=True
                )
                continue
        return None

    def all(self) -> list[Reflex]:
        """Return snapshot of all registered reflexes."""
        return list(self._by_priority)

    # -- Hot path observation (v1.1.26) -----------------------------

    def _record_trigger(self, reflex_name: str) -> None:
        """Internal: increment trigger counter for hot path tracking."""
        self._trigger_counts[reflex_name] = self._trigger_counts.get(reflex_name, 0) + 1
        self._total_triggers += 1

    def observe_hot_paths(self, min_triggers: int = 5) -> list[tuple[str, int]]:
        """Observe frequently triggered reflex paths for promotion.

        Returns reflexes whose trigger count exceeds *min_triggers*,
        sorted descending by trigger frequency. These are candidates
        for optimisation into dedicated fast-path reflex arcs.

        Args:
            min_triggers: Minimum trigger count to qualify as a hot path.

        Returns:
            List of ``(reflex_name, trigger_count)`` tuples.
        """
        result = [
            (name, count) for name, count in self._trigger_counts.items() if count >= min_triggers
        ]
        result.sort(key=lambda x: -x[1])
        return result

    def trigger_stats(self) -> dict[str, int]:
        """Return per-reflex trigger counts (read-only copy)."""
        return dict(self._trigger_counts)

    # -- Validation --------------------------------------------------------

    def validate(self, wiring: Wiring) -> None:
        """Validate each reflex's path adjacency hops are legal in wiring.

        Raises :class:`ReflexPathInvalidError` immediately on any illegal hop.
        """
        for reflex in self._by_priority:
            for hop in reflex.hops():
                frm, to = hop
                if not wiring.is_allowed(frm, to):
                    raise ReflexPathInvalidError(reflex.name, hop)


class ReflexArc:
    """Reflex arc subsystem (v0.5.9) — registry + perceive entry + path validation.

    Dependencies explicitly injected:

    - ``events``: :class:`EventBus`, required, perceive emits lifecycle events throughout
    - ``nervous``: :class:`Nervous` optional, only used for ``validate_paths()`` to read
      ``nervous.wiring`` for reflex.path validation. Skipped when ``None``.

    Can be instantiated independently, no CatBase needed::

        arc = ReflexArc(EventBus())
        arc.register(Reflex(name="x", trigger=..., path=(...)))
        async for ev in arc.perceive("hi", cat=None):
            ...
    """

    def __init__(
        self,
        events: EventBus,
        nervous: Nervous | None = None,
    ) -> None:
        self.events = events
        self.nervous = nervous
        self.registry = ReflexRegistry()

    # -- Registration proxy ------------------------------------------------

    def register(self, reflex: Reflex) -> None:
        """Register a reflex arc."""
        self.registry.register(reflex)

    def unregister(self, name: str) -> bool:
        """Remove reflex by name."""
        return self.registry.unregister(name)

    def match(self, input: Any) -> Reflex | None:
        """Return the first matching reflex."""
        return self.registry.match(input)

    # -- Validation --------------------------------------------------------

    def validate_paths(self) -> None:
        """Validate all registered reflex.path are legal in nervous.wiring.

        Skip validation if no ``nervous`` (standalone mode).
        """
        if self.nervous is None:
            return
        self.registry.validate(self.nervous.wiring)

    # -- Perception entry ------------------------------------------------

    async def perceive(
        self,
        input: Any,
        *,
        cat: Any = None,
        **extras: Any,
    ) -> AsyncIterator[Any]:
        """Reflex arc entry: give a stimulus, automatically follows the matching neural pathway.

        Flow:

        1. ``match(input)`` finds first matching reflex; raises
           :class:`NoReflexMatchedError` if none
        2. Build :class:`PerceptionContext`, emit ``lifecycle.perceive_start``
        3. If ``reflex.stages`` non-empty: drive via :class:`Pipeline` and yield events
           Otherwise: emit ``nerve.signal`` hop-by-hop along ``reflex.path`` (for business handlers)
        4. emit ``lifecycle.perceive_end``

        Args:
            input: external stimulus (any type, trigger self-judges)
            cat: passed to :class:`PerceptionContext.cat` for Stage access to the whole cat.
                Pass ``None`` in standalone mode.
            **extras: goes into ``PerceptionContext.extras``

        Yields:
            Intermediate events from Pipeline or reflex path
        """
        reflex = self.registry.match(input)
        if reflex is None:
            raise NoReflexMatchedError(repr(input))

        ctx = PerceptionContext(
            input=input,
            modality=infer_modality(input),
            reflex_name=reflex.name,
            cat=cat,
            extras=dict(extras),
        )

        # v1.1.26: record trigger for hot path observation
        self.registry._record_trigger(reflex.name)

        await self.events.emit(
            Lifecycle.PERCEIVE_START,
            {"input": input, "reflex_name": reflex.name},
        )

        if reflex.stages:
            pipeline = Pipeline(list(reflex.stages))
            async for ev in pipeline.execute(ctx):
                yield ev
        else:
            # No Stages: only broadcast hop-by-hop along path for business handlers to pick up
            for frm, to in reflex.hops():
                await self.events.emit(
                    NerveEvent.SIGNAL,
                    {"from": frm, "to": to, "method": "__perceive__"},
                )

        await self.events.emit(
            Lifecycle.PERCEIVE_END,
            {"reflex_name": reflex.name, "reply": ctx.final_reply},
        )


# -- Built-in reflex path structures (v1.0.18) -------------------------

BUILTIN_REFLEX_PATHS: dict[str, tuple[Organ, ...]] = {
    "text_dialogue": (EARS, THALAMUS, BRAINSTEM, CEREBRUM, CEREBELLUM, MOUTH),
    "danger": (EARS, THALAMUS, AMYGDALA, MOUTH),
}
"""Predefined reflex path structures. Applications use these as ``path=``
arguments when registering ``Reflex`` instances. The ``trigger`` callable
is always supplied by the application layer."""


__all__ = ["Reflex", "ReflexRegistry", "ReflexArc", "Trigger", "BUILTIN_REFLEX_PATHS"]
