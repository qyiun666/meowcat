"""meowcat three-loop event name constant table.

Corresponds to the three loops defined in ``docs/architecture/00-meowcat-framework.md``:

- **Loop A (remember→find→deliver core cycle)**: locate/route/memory/compress hooks per dialogue turn
- **Loop B (orchestration)**: TaskOrchestrator start/end hooks
- **Loop C (growth/crystallization)**: anomaly/correction/crystallize/role-emergence hooks

Also includes :class:`Lifecycle` for Cat start/stop events.

**Discipline**: this file only defines string constants, no business logic, zero third-party dependencies.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import Final


# -- Loop A: remember→find→deliver core cycle ----------------------------------

class LocateEvent:
    """Thalamus locate (find) related hooks."""

    PRE: Final[str] = "locate.pre"
    """Fired before Thalamus.locate() executes, payload ``{msg, session_id}``."""

    POST: Final[str] = "locate.post"
    """Fired after Thalamus.locate() returns, payload ``{msg, result}``."""

    ROUTE_DECIDED: Final[str] = "route.decided"
    """Fired when route decision is complete, payload ``{route, confidence}``."""


class RememberEvent:
    """Hippocampus write (remember) + hypothalamus compression related hooks."""

    PRE: Final[str] = "remember.pre"
    POST: Final[str] = "remember.post"

    COMPRESS_PRE: Final[str] = "compress.pre"
    COMPRESS_POST: Final[str] = "compress.post"


# -- Loop B: Orchestration ----------------------------------------------

class OrchestrateEvent:
    """TaskOrchestrator related hooks."""

    START: Final[str] = "orchestrate.start"
    """Payload ``{orchestration_id, plan}``."""

    END: Final[str] = "orchestrate.end"
    """Payload ``{orchestration_id, report}``."""


# -- Loop C: Growth/Crystallization --------------------------------------

class GrowthEvent:
    """Anomaly/correction/crystallize/role emergence hooks."""

    ANOMALY: Final[str] = "growth.anomaly"
    CORRECTION: Final[str] = "growth.correction"
    CRYSTALLIZE: Final[str] = "crystallize.emit"
    ROLE_EMERGE: Final[str] = "role.emerge"


# -- Lifecycle ---------------------------------------------------

class Lifecycle:
    """Cat lifecycle start/shutdown events."""

    START: Final[str] = "lifecycle.start"
    SHUTDOWN: Final[str] = "lifecycle.shutdown"

    # v0.5.1 Perception entry lifecycle
    PERCEIVE_START: Final[str] = "lifecycle.perceive_start"
    """Fired at ``cat.perceive(input)`` start, payload ``{input, reflex_name}``."""

    PERCEIVE_END: Final[str] = "lifecycle.perceive_end"
    """Fired at ``cat.perceive(input)`` end, payload ``{reflex_name, reply}``."""


# -- Nerve synapse ---------------------------------------------------

class NerveEvent:
    """Neural potential event triggered during ``cat.signal()`` dispatch."""

    SIGNAL: Final[str] = "nerve.signal"
    """Broadcast on every legal signal call, payload ``{from, to, method}``.

    Illegal calls raise :class:`IllegalNeuralPathError` directly, this event is not emitted."""


# -- Kitten lifecycle -----------------------------------------

class KittenEvent:
    """Kitten spawn/execute/reclaim hooks. See design.md §12.9."""

    SPAWNED: Final[str] = "kitten.spawned"
    """Kitten spawned, payload ``{kitten_id, parent_id, task, role}``."""

    EXECUTING: Final[str] = "kitten.executing"
    """Kitten starts executing, payload ``{kitten_id, task_id}``."""

    COMPLETED: Final[str] = "kitten.completed"
    """Kitten completed task, payload ``{kitten_id, result}``."""

    STUCK: Final[str] = "kitten.stuck"
    """Kitten stuck, payload ``{kitten_id, error_detail}``."""

    DISMISSED: Final[str] = "kitten.dismissed"
    """Kitten dismissed, payload ``{kitten_id}``."""

    MERGE_ABSORBED: Final[str] = "kitten.merge_absorbed"
    """Main cat absorbed MergeProposal, payload ``{kitten_id, proposal}``."""


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
)

__all__ = [
    "LocateEvent", "RememberEvent",
    "OrchestrateEvent", "GrowthEvent", "Lifecycle",
    "NerveEvent",
    "KittenEvent", "ALL_EVENTS",
]
