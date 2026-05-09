# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat data models — pydantic BaseModel shapes.

Zero ORM, zero business logic. Concrete implementations live in meowagent.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from meowcat.protocols import AdapterProtocol, BrainStemProtocol, CatProtocol

__all__ = [
    "EntityShape",
    "ConnectionShape",
    "EpisodeShape",
    "FocusShape",
    "SubTaskShape",
    "TaskResultShape",
    "OrchestratorReportShape",
    "MaintenanceReportShape",
    "CandidateShape",
    "LocateResultShape",
    "StageEvent",
    "PipelineContext",
    "LoopEvent",
    "MergeProposalShape",
    "KittenCapability",
    "WorkflowShape",
    "ModelConfig",
]

# -- Brain-area shapes ------------------------------------------------------


class EntityShape(BaseModel):
    """Entanglement graph entity."""

    id: str
    session_id: str
    name: str
    type: str = "topic"
    content: str = ""
    source: str = "user_stated"
    importance: float = 0.5
    emotion: float = 0.0
    protection: str = "normal"
    last_seen: str = ""
    access_count: int = 0
    is_dormant: bool = False
    is_corrected: bool = False
    corrected_to: str = ""
    l6_indices: list[int] = Field(default_factory=list)


class ConnectionShape(BaseModel):
    """Entanglement graph connection."""

    id: str
    from_id: str
    to_id: str
    relation: str = ""
    strength: float = 0.5
    confidence: float = 0.5
    source: str = "inferred"
    co_occurrence: int = 1
    session_ids: list[str] = Field(default_factory=list)


class EpisodeShape(BaseModel):
    """Entanglement graph episode."""

    id: str
    session_id: str = ""
    time: str = ""
    type: str = "chat"
    summary: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    turn: int = 0
    is_confirmed: bool = False


class FocusShape(BaseModel):
    """Working memory focus."""

    entity_id: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    turn_count: int = 0
    last_action: str = ""
    summary: str = ""
    context_snapshot: str = ""


# -- Worker / Orchestration -------------------------------------------------


class SubTaskShape(BaseModel):
    """Sub-task definition."""

    task_id: str
    role: str
    prompt: str
    dependencies: list[str] = Field(default_factory=list)
    status: str = "pending"
    context_keys: list[str] = Field(default_factory=list)


class TaskResultShape(BaseModel):
    """Sub-task execution result."""

    task_id: str
    role: str
    success: bool
    output: str = ""
    error: str | None = None
    duration: float = 0.0
    artifacts: dict[str, Any] = Field(default_factory=dict)


class OrchestratorReportShape(BaseModel):
    """Orchestrator complete report."""

    subtasks: list[SubTaskShape] = Field(default_factory=list)
    results: list[TaskResultShape] = Field(default_factory=list)
    synthesis: str = ""
    total_duration: float = 0.0
    workers_spawned: int = 0
    workers_succeeded: int = 0
    workers_failed: int = 0
    orchestration_id: str | None = None
    status: str = "completed"


# -- Maintenance / Locate --------------------------------------------------


class MaintenanceReportShape(BaseModel):
    """Steady-state maintenance report."""

    decayed: int = 0
    orphans_cleaned: int = 0
    woke: int = 0
    suggestions: list[str] = Field(default_factory=list)


class CandidateShape(BaseModel):
    """Retrieval candidate result. Concrete entity type lives in meowagent."""

    entity: EntityShape
    weight: float
    match_type: str


class LocateResultShape(BaseModel):
    """Locate result (formerly AlgorithmOutput, pure data)."""

    candidates: list[CandidateShape] = Field(default_factory=list)
    confidence: float = 0.0
    match_type: str = "none"
    is_ambiguous: bool = False


# -- Pipeline / Events ----------------------------------------------


_EventKind = Literal["thinking", "output", "short_circuit"]


class StageEvent(BaseModel):
    """Unified event produced by a Stage."""

    kind: _EventKind
    content: str = ""
    reply: str | None = None

    @classmethod
    def thinking(cls, step: str) -> StageEvent:
        return cls(kind="thinking", content=step)

    @classmethod
    def output(cls, token: str) -> StageEvent:
        return cls(kind="output", content=token)

    @classmethod
    def short_circuit(cls, reply: str) -> StageEvent:
        return cls(kind="short_circuit", content="", reply=reply)


# -- Companion BaseModel -----------------------------------------------


class PipelineContext(BaseModel):
    """Cross-Stage shared state."""

    model_config = {"arbitrary_types_allowed": True}

    msg: str
    brainstem: BrainStemProtocol  # BrainStemProtocol at runtime
    l6_history: str | None = None
    locate_result: LocateResultShape | None = None
    route: str | None = None
    context_text: str = ""
    prompt: str = ""
    system: str = ""
    reply: str = ""
    short_circuited: bool = False
    final_reply: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)
    # v1.0.1: third-party adaptation fields
    cat: CatProtocol | None = None
    turn: int = 0
    session_id: str = ""
    adapter: AdapterProtocol | None = None


class LoopEvent(BaseModel):
    """EventBus payload."""

    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


# -- Kitten ---------------------------------------------------------


class MergeProposalShape(BaseModel):
    """Sole channel for kitten to report back to parent.

    Kittens don't make decisions, only report; the parent decides
    whether to write hippocampus/entanglement graph/trigger growth/crystallize/role emergence.
    See design.md section 12.6.
    """

    kitten_id: str
    # parent cat_uid, validated at absorb_merge to prevent spoofing
    parent_id: str
    task_id: str
    status: str = "completed"  # completed / stuck / partial
    result: str = ""
    new_entities: list[dict[str, Any]] = Field(default_factory=list)
    updated_entities: list[dict[str, Any]] = Field(default_factory=list)
    tool_path: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_hits: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    error_detail: str = ""


class WorkflowShape(BaseModel):
    """Long-running workflow entity — task orchestration state persisted across sessions.

    Framework guarantees: state is never lost, restartable, memory-safe.
    Framework does NOT handle: step decomposition (LLM), kitten execution logic, trigger strategies.
    """

    entity_id: str
    cat_uid: str
    session_id: str
    status: str = "active"  # "active" | "awaiting_user" | "completed" | "failed"
    plan: list[str] = Field(default_factory=list)
    current_step: int = 0
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    kittens_spawned: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class KittenCapability(BaseModel):
    """Kitten capability configuration. Users can customize organ toggles + memory inheritance scope.

    **Iron rules** (untouchable, enforced rejection):

    1. ``can_spawn = False`` — kittens cannot spawn more cats
    2. ``can_promote = False`` — kittens cannot become a main cat
    3. ``has_paws = True`` — kittens are the "hands"; without paws, it's not a kitten
    4. Instances must be created by main cat spawn_kitten (parent reference enforced at Protocol layer)

    **Minimum guarantee**: at least one of ``has_cerebrum`` and ``has_cerebellum`` must be True,
    otherwise raises ValueError at construction (a brainless cat cannot work, cannot silently correct).

    **Inheritance semantics**: what is inherited is the main cat's **memory/state snapshot**, not organ instances.
    Main-cat-exclusive management capabilities (spawn/absorb/orchestrate) are not inheritable.

    See design.md section 12.10.
    """

    # ━━ Iron rules (untouchable) ━━
    can_spawn: bool = False
    can_promote: bool = False

    # ━━ Brain regions (user-configurable, at least one) ━━
    has_cerebrum: bool = True
    has_cerebellum: bool = True
    has_hippocampus: bool = False
    has_thalamus: bool = False
    has_frontal: bool = False
    has_amygdala: bool = True
    has_cortex: bool = False
    has_hypothalamus: bool = False

    # ━━ Senses (user-configurable) ━━
    has_ears: bool = False
    has_eyes: bool = False
    has_whiskers: bool = True
    has_paws: bool = True  # Iron rule: enforced True

    # ━━ Outputs (user-configurable) ━━
    has_mouth: bool = False
    has_purr: bool = False
    has_tail: bool = False

    # ━━ Orchestration (user-configurable) ━━
    can_remember: bool = False
    can_grow: bool = False

    # ━━ Memory inheritance (inherit state from main cat, full or partial) ━━
    inherit_memory: Literal["none", "partial", "full"] = "none"
    inherit_entity_ids: list[str] = Field(
        default_factory=list)  # specify for partial inheritance
    inherit_l6_recent: int = 0  # inherit most recent N L6 history entries
    inherit_focus: bool = False  # whether to inherit main cat current focus

    def model_post_init(self, __context: Any) -> None:
        """Iron rules silently enforced + minimum guarantee hard error."""
        object.__setattr__(self, "can_spawn", False)
        object.__setattr__(self, "can_promote", False)
        object.__setattr__(self, "has_paws", True)
        if not (self.has_cerebrum or self.has_cerebellum):
            raise ValueError(
                "KittenCapability: at least one brain required (cerebrum or cerebellum), kitten cannot be brainless"
            )


# -- LLM shelf (v1.1.5) --------------------------------------------------


# -- Model config (v1.1.29) — litellm-free model shape ---------------------


class ModelConfig(BaseModel):
    """Provider-agnostic model configuration — framework-layer canonical shape.

    Zero litellm dependency. Designed as the single source of truth for LLM
    model descriptors across workers, agents, and pipeline stages.  Application
    layer maps this to concrete provider SDK calls.

    .. versionchanged:: 1.2.12
        Added ``api_key``, ``base_url`` fields.

    Usage::

        from meowcat.models import ModelConfig
        cfg = ModelConfig(provider="openai", model="gpt-4o", temperature=0.7)
        worker = BaseWorker(model=cfg)
    """

    provider: str = "openai"
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    api_key: str = Field(default="", exclude=True)
    base_url: str = ""
    stop: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    def __repr__(self) -> str:
        d = self.model_dump()
        # api_key is excluded from model_dump; show placeholder
        d["api_key"] = "sk-***" if self.api_key else ""
        fields = ", ".join(f"{k}={v!r}" for k, v in d.items())
        return f"ModelConfig({fields})"
