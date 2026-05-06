# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat event payload type definitions — TypedDict for IDE type safety.

This module defines TypedDict payloads for every framework-level event constant
defined in :mod:`meowcat.events`.  Framework code that emits events uses plain
``dict`` (zero runtime overhead); user code that handles events imports these
TypedDict types for IDE autocompletion and type-checking.

Backward compatible: all existing handler signatures ``def h(payload: dict)``
continue to work.  New code can annotate ``def h(payload: NerveSignalPayload)``
for full type safety.

Copyright (c) 2026 Axonant. SPDX-License-Identifier: MIT.
"""

from __future__ import annotations

from typing import Any, TypedDict

from meowcat.wiring import Organ


# -- Lifecycle payloads --------------------------------------------------

class LifecycleStartPayload(TypedDict):
    """Payload for ``Lifecycle.START`` event."""
    cat: Any  # CatBase — circular import avoided


class LifecycleShutdownPayload(TypedDict):
    """Payload for ``Lifecycle.SHUTDOWN`` event."""
    cat: Any  # CatBase — circular import avoided


class PerceiveStartPayload(TypedDict):
    """Payload for ``Lifecycle.PERCEIVE_START`` event."""
    input: Any
    reflex_name: str


class PerceiveEndPayload(TypedDict):
    """Payload for ``Lifecycle.PERCEIVE_END`` event."""
    reflex_name: str
    reply: Any


# -- Nerve signal payload ------------------------------------------------

class NerveSignalPayload(TypedDict):
    """Payload for ``NerveEvent.SIGNAL`` event."""
    from_: Organ  # 'from' is reserved
    to: Organ
    method: str


# -- Locate (Thalamus) payloads ------------------------------------------

class LocatePrePayload(TypedDict):
    """Payload for ``LocateEvent.PRE`` event."""
    msg: str
    session_id: str


class LocatePostPayload(TypedDict):
    """Payload for ``LocateEvent.POST`` event."""
    msg: str
    result: Any


class RouteDecidedPayload(TypedDict):
    """Payload for ``LocateEvent.ROUTE_DECIDED`` event."""
    route: str
    confidence: float


# -- Remember (Hippocampus) payloads -------------------------------------

class RememberPrePayload(TypedDict, total=False):
    """Payload for ``RememberEvent.PRE`` event."""
    msg: str
    session_id: str


class RememberPostPayload(TypedDict, total=False):
    """Payload for ``RememberEvent.POST`` event."""
    msg: str
    result: Any


class CompressPrePayload(TypedDict, total=False):
    """Payload for ``RememberEvent.COMPRESS_PRE`` event."""
    pass


class CompressPostPayload(TypedDict, total=False):
    """Payload for ``RememberEvent.COMPRESS_POST`` event."""
    pass


# -- Orchestrate (Loop B) payloads ---------------------------------------

class OrchestrateStartPayload(TypedDict):
    """Payload for ``OrchestrateEvent.START`` event."""
    orchestration_id: str
    plan: Any


# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

class OrchestrateEndPayload(TypedDict):
    """Payload for ``OrchestrateEvent.END`` event."""
    orchestration_id: str
    report: Any


# -- Growth / Crystallization (Loop C) payloads --------------------------

class GrowthAnomalyPayload(TypedDict, total=False):
    """Payload for ``GrowthEvent.ANOMALY`` event."""
    anomaly_type: str
    detail: str
    severity: str


class GrowthCorrectionPayload(TypedDict, total=False):
    """Payload for ``GrowthEvent.CORRECTION`` event."""
    correction_type: str
    detail: str


class CrystallizePayload(TypedDict, total=False):
    """Payload for ``GrowthEvent.CRYSTALLIZE`` event."""
    skill_name: str
    skill_content: str


class RoleEmergePayload(TypedDict, total=False):
    """Payload for ``GrowthEvent.ROLE_EMERGE`` event."""
    role: str
    confidence: float


# -- Kitten lifecycle payloads -------------------------------------------

class KittenSpawnedPayload(TypedDict):
    """Payload for ``KittenEvent.SPAWNED`` event."""
    kitten_id: str
    parent_id: str
    task: Any
    role: str


class KittenExecutingPayload(TypedDict):
    """Payload for ``KittenEvent.EXECUTING`` event."""
    kitten_id: str
    task_id: str


class KittenCompletedPayload(TypedDict):
    """Payload for ``KittenEvent.COMPLETED`` event."""
    kitten_id: str
    result: Any


class KittenStuckPayload(TypedDict):
    """Payload for ``KittenEvent.STUCK`` event."""
    kitten_id: str
    error_detail: str


class KittenDismissedPayload(TypedDict):
    """Payload for ``KittenEvent.DISMISSED`` event."""
    kitten_id: str


class KittenMergeAbsorbedPayload(TypedDict):
    """Payload for ``KittenEvent.MERGE_ABSORBED`` event."""
    kitten_id: str
    proposal: Any


# -- Self / Reflection payloads ------------------------------------------

class SelfSnapshotPayload(TypedDict):
    """Payload for ``SelfEvent.SNAPSHOT`` event."""
    cat: Any  # CatBase
    snapshot: Any  # SelfSnapshot


class SelfReflectPayload(TypedDict):
    """Payload for ``SelfEvent.REFLECT`` event."""
    cat: Any  # CatBase
    result: Any


# -- PinealGland fusion payloads -----------------------------------------

class FusionSelfPayload(TypedDict):
    """Payload for ``FusionEvent.FUSE_SELF`` event."""
    insights: list[Any]
    fusion_id: str


class FusionColonyPayload(TypedDict):
    """Payload for ``FusionEvent.FUSE_COLONY`` event."""
    insights: list[Any]
    fusion_id: str


class FusionTriggerStartPayload(TypedDict, total=False):
    """Payload for ``FusionEvent.TRIGGER_START`` event."""
    reason: str


class FusionTriggerEndPayload(TypedDict):
    """Payload for ``FusionEvent.TRIGGER_END`` event."""
    insights_count: int


# -- Telemetry / Observability payloads (v1.2.21) -------------------

class TelemetrySpanPayload(TypedDict):
    """Payload for ``TelemetryEvent.SPAN`` event."""
    trace_id: str
    from_: Organ  # 'from' is reserved
    to: Organ
    method: str
    started_at: float
    finished_at: float
    status: str
    error: str | None


# -- Mapping: event name → TypedDict type ---------------------------------
# Used by documentation, introspection, and potential future typed emit().

EVENT_PAYLOAD_MAP: dict[str, type] = {
    # Lifecycle
    "lifecycle.start": LifecycleStartPayload,
    "lifecycle.shutdown": LifecycleShutdownPayload,
    "lifecycle.perceive_start": PerceiveStartPayload,
    "lifecycle.perceive_end": PerceiveEndPayload,
    # Nerve signal
    "nerve.signal": NerveSignalPayload,
    # Locate
    "locate.pre": LocatePrePayload,
    "locate.post": LocatePostPayload,
    "route.decided": RouteDecidedPayload,
    # Remember
    "remember.pre": RememberPrePayload,
    "remember.post": RememberPostPayload,
    "compress.pre": CompressPrePayload,
    "compress.post": CompressPostPayload,
    # Orchestrate
    "orchestrate.start": OrchestrateStartPayload,
    "orchestrate.end": OrchestrateEndPayload,
    # Growth
    "growth.anomaly": GrowthAnomalyPayload,
    "growth.correction": GrowthCorrectionPayload,
    "crystallize.emit": CrystallizePayload,
    "role.emerge": RoleEmergePayload,
    # Kitten
    "kitten.spawned": KittenSpawnedPayload,
    "kitten.executing": KittenExecutingPayload,
    "kitten.completed": KittenCompletedPayload,
    "kitten.stuck": KittenStuckPayload,
    "kitten.dismissed": KittenDismissedPayload,
    "kitten.merge_absorbed": KittenMergeAbsorbedPayload,
    # Self
    "self.snapshot": SelfSnapshotPayload,
    "self.reflect": SelfReflectPayload,
    # Fusion
    "fusion.self": FusionSelfPayload,
    "fusion.colony": FusionColonyPayload,
    "fusion.trigger_start": FusionTriggerStartPayload,
    "fusion.trigger_end": FusionTriggerEndPayload,
    # Telemetry
    "telemetry.span": TelemetrySpanPayload,
}


__all__ = [
    "LifecycleStartPayload", "LifecycleShutdownPayload",
    "PerceiveStartPayload", "PerceiveEndPayload",
    "NerveSignalPayload",
    "LocatePrePayload", "LocatePostPayload", "RouteDecidedPayload",
    "RememberPrePayload", "RememberPostPayload",
    "CompressPrePayload", "CompressPostPayload",
    "OrchestrateStartPayload", "OrchestrateEndPayload",
    "GrowthAnomalyPayload", "GrowthCorrectionPayload",
    "CrystallizePayload", "RoleEmergePayload",
    "KittenSpawnedPayload", "KittenExecutingPayload", "KittenCompletedPayload",
    "KittenStuckPayload", "KittenDismissedPayload", "KittenMergeAbsorbedPayload",
    "SelfSnapshotPayload", "SelfReflectPayload",
    "FusionSelfPayload", "FusionColonyPayload",
    "FusionTriggerStartPayload", "FusionTriggerEndPayload",
    "TelemetrySpanPayload",
    "EVENT_PAYLOAD_MAP",
]

