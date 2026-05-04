"""meowcat brain-area protocols — neural organ interfaces for cerebrum,
cerebellum, brainstem, hippocampus, etc.

All typing.Protocol (duck typing), zero third-party dependencies.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from meowcat.models import LocateResultShape

__all__ = [
    "Diagnosable", "OrganProtocol",
    "BrainStemProtocol", "HippocampusProtocol", "ThalamusProtocol",
    "LLMBrainProtocol", "AmygdalaProtocol", "FrontalCortexProtocol",
    "HypothalamusProtocol", "CortexProtocol",
    "LLMProviderProtocol",
    "AnomalyGrowthProtocol", "CorrectionGrowthProtocol",
    "CrystallizerProtocol", "RoleEmergenceProtocol",
]

# -- Basic --------------------------------------------------------


@runtime_checkable
class Diagnosable(Protocol):
    """Organ diagnostic interface — read-only snapshot, return value MUST be
    a plain dict.

    Framework-level ``probe()`` is only allowed to call this method;
    any write/side-effect operations are forbidden.

    **Coordinate**: None (base protocol, occupies no organ coordinate)
    **Inbound**: ``probe()`` calls from any wired organ can reach this
    **Outbound**: None
    **Reflex**: None
    **Implementor**: All organ implementations (must implement diagnose())
    """

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class OrganProtocol(Diagnosable, Protocol):
    """Organ base protocol — all organs must implement name + diagnose().

    v0.5.14: OrganProtocol inherits Diagnosable, enforcing all organs
    are probe-able.

    **Coordinate**: None (base protocol, organ coords assigned via wiring)
    **Inbound**: Determined by wiring-assembled allowed edges
    **Outbound**: Determined by wiring-assembled allowed edges
    **Reflex**: Depends on app-layer reflex arc paths
    **Implementor**: Noop* classes in meowcat/defaults/ (default stubs)
    """

    name: str

# -- LLM ----------------------------------------------------------


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """LLM unified calling interface (LiteLLM wrapper).

    **Coordinate**: None (model layer, occupies no organ coordinate)
    **Inbound**: Held directly by Cerebrum/Cerebellum, not called via wiring
    **Outbound**: None
    **Reflex**: None
    **Implementor**: Application layer (LLM Provider)
    """

    async def completion(self, messages: list[dict[str, str]], temperature: float | None = None, max_tokens: int |
                         None = None, tools: list[dict[str, Any]] | None = None, tool_choice: str | None = None) -> dict[str, Any]: ...
    async def stream_completion(self, messages: list[dict[str, str]], temperature: float |
                                None = None, max_tokens: int | None = None) -> AsyncIterator[str]: ...

# -- Brain Areas ----------------------------------------------------


@runtime_checkable
class BrainStemProtocol(Protocol):
    """Brainstem — master dispatch hub, connects all brain areas and sensors.

    v0.5.12: process/process_stream removed.
    BrainStem degrades to a helper method provider for Pipeline Stages,
    no longer serving as the main loop entry point. Retains
    build_system_prompt and cancel_current as the minimal external contract.

    **Coordinate**: ``("brain", "brainstem")``
    **Inbound**: THALAMUS
    **Outbound**: THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA,
    FRONTAL, HYPOTHALAMUS, CORTEX + all SENSORS + all VOICES
    **Reflex**: text_dialogue (EARS->THALAMUS->BRAINSTEM->CEREBRUM->...)
    **Implementor**: Application layer (brain-area organ)
    """

    async def build_system_prompt(self, route: str) -> str: ...
    def cancel_current(self) -> bool: ...


@runtime_checkable
class HippocampusProtocol(Protocol):
    """Hippocampus — entanglement graph memory encoding and retrieval.

    **Coordinate**: ``("brain", "hippocampus")``
    **Inbound**: CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM
    **Outbound**: CEREBRUM, CORTEX
    **Reflex**: No direct reflex arc; indirectly participates in text_dialogue
    via BRAINSTEM
    **Implementor**: Application layer (brain-area organ)
    """
    entities: dict[str, Any]  # EntityShape
    episodes: list[Any]  # EpisodeShape
    async def remember(self, user_msg: str, ai_reply: str,
                       cat_id: str, model: str) -> Any: ...

    def decay(self, now: Any | None = None) -> int: ...
    def add_episode(self, episode: Any) -> None: ...  # EpisodeShape
    def add_entity(self, entity: Any) -> None: ...  # EntityShape
    def fts_search(self, cat_id: str, keywords: str,
                   limit: int) -> list[dict[str, Any]]: ...

    def get_entity(self, entity_id: str) -> Any | None: ...  # EntityShape
    def get_by_name(self, name: str) -> Any | None: ...  # EntityShape
    def get_all(self) -> list[Any]: ...  # list[EntityShape]

    def get_related(
        self, entity_id: str) -> list[Any]: ...  # list[EntityShape]
    def connect(self, from_id: str, to_id: str,
                relation: str, strength: float) -> None: ...

    def weaken_connections(self, entity_id: str, factor: float) -> None: ...
    def cleanup_orphan_connections(self, days_threshold: int = 7) -> int: ...
    def stats(self, session_id: str | None = None) -> dict[str, Any]: ...
    def to_dict(self) -> dict[str, Any]: ...
    def from_dict(self, d: dict[str, Any]) -> None: ...

    # v0.5.26 Wrapper methods (replace bare field access)
    def record_access(self, entity_id: str, delta: int = 1) -> None: ...
    def set_dormant(self, entity_id: str, dormant: bool) -> None: ...
    def append_content(self, entity_id: str, text: str,
                       max_total: int | None = None) -> None: ...

    def update_importance(self, entity_id: str, importance: float) -> None: ...
    def set_last_seen(self, entity_id: str, ts: str) -> None: ...

    # v1.0.15: Long-running workflow queries
    def list_active_workflows(self, cat_id: str) -> list[dict[str, Any]]: ...

    # v1.1.21: Cross-cat memory search + delegation snapshot
    def set_colony_memory(self, memory_pool: Any) -> None: ...

    def snapshot(self, *topics: str,
                 scope: str = "colony") -> dict[str, Any]: ...
    def locate(self, query: str,
               scope: str = "self") -> list[dict[str, Any]]: ...


@runtime_checkable
class ThalamusProtocol(Protocol):
    """Thalamus — sensory relay and routing decision.
    All sensory input is filtered and dispatched to cerebrum/brainstem/amygdala.

    **Coordinate**: ``("brain", "thalamus")``
    **Inbound**: EARS, EYES, WHISKERS (all SENSORS)
    **Outbound**: CEREBRUM, BRAINSTEM, AMYGDALA
    **Reflex**: text_dialogue, visual, danger, action_order
    **Implementor**: Application layer (brain-area organ)
    """

    async def locate(self, msg: str, session_id: str) -> LocateResultShape: ...  # type: ignore[name-defined]  # noqa: F821

    def decide_route(self, **kwargs: Any) -> dict[str, Any]: ...


@runtime_checkable
class LLMBrainProtocol(Protocol):
    """Shared LLM protocol for cerebrum and cerebellum.
    Cerebrum/Cerebellum differ only in constructor params (model, temperature).

    **Coordinate** (CEREBRUM): ``("brain", "cerebrum")`` — Inbound: THALAMUS,
    HIPPOCAMPUS, FRONTAL, BRAINSTEM; Outbound: HIPPOCAMPUS, CEREBELLUM, FRONTAL
    **Coordinate** (CEREBELLUM): ``("brain", "cerebellum")`` — Inbound:
    CEREBRUM, AMYGDALA, BRAINSTEM; Outbound: EFFECTORS (PAWS, MOUTH, PURR, TAIL)
    **Reflex**: text_dialogue, visual, action_order
    **Implementor**: Application layer (brain-area organ)
    """
    name: str

    async def generate(self, prompt: str, system_prompt: str | None = None,
                       temperature: float = 0.7, max_tokens: int | None = None) -> str: ...
    async def stream_generate(self, prompt: str, system_prompt: str | None = None,
                              temperature: float = 0.7, max_tokens: int | None = None) -> AsyncIterator[str]: ...

    def reload_config(self) -> None: ...


@runtime_checkable
class AmygdalaProtocol(Protocol):
    """Amygdala — rejection correction and safety fallback.
    Can bypass the cerebrum to directly trigger effectors (stress reflex).

    **Coordinate**: ``("brain", "amygdala")``
    **Inbound**: THALAMUS, BRAINSTEM
    **Outbound**: CEREBELLUM, MOUTH
    **Reflex**: danger (EARS->THALAMUS->AMYGDALA->MOUTH), action_order
    **Implementor**: Application layer (brain-area organ)
    """

    def is_rejection(self, msg: str) -> bool: ...
    def classify_rejection(self, msg: str) -> str: ...
    def parse_correction(self, msg: str) -> tuple[str, str] | None: ...

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any) -> str: ...
    async def handle_correction(
        self, msg: str, hippocampus: Any) -> tuple[str, str] | None: ...

    async def assess_safety(self, user_input: str) -> dict[str, Any]: ...

    async def assess_tool_risk(
        self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class FrontalCortexProtocol(Protocol):
    """Frontal lobe — focus system (working memory).
    Topic shift detection, focus archiving and updates.

    **Coordinate**: ``("brain", "frontal")``
    **Inbound**: CEREBRUM, BRAINSTEM
    **Outbound**: CEREBRUM, HIPPOCAMPUS
    **Reflex**: No direct reflex arc
    **Implementor**: Application layer (brain-area organ)
    """

    def detect_shift(self, msg: str) -> bool: ...
    def is_continue(self, msg: str) -> bool: ...
    def archive_focus(self) -> None: ...
    def update_focus(self, result: Any) -> None: ...
    def save(self, path: Any | None = None) -> None: ...
    def load(self, path: Any | None = None) -> None: ...


@runtime_checkable
class HypothalamusProtocol(Protocol):
    """Hypothalamus — homeostasis maintenance.
    Responsible for memory decay, orphan cleanup, and other background
    self-maintenance.

    **Coordinate**: ``("brain", "hypothalamus")``
    **Inbound**: BRAINSTEM
    **Outbound**: HYPOTHALAMUS (self-loop), HIPPOCAMPUS, CORTEX
    **Reflex**: No direct reflex arc
    **Implementor**: Application layer (brain-area organ)
    """

    async def run_maintenance(
        self, country_code: str | None = None) -> Any: ...

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]: ...
    def compress_long_history(self) -> dict[str, Any]: ...


@runtime_checkable
class CortexProtocol(Protocol):
    """Cerebral cortex — four-layer worldview (axioms/others/values/self).

    **Coordinate**: ``("brain", "cortex")``
    **Inbound**: HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM
    **Outbound**: None (terminal organ, only read, never actively calls)
    **Reflex**: None
    **Implementor**: Application layer (brain-area organ)
    """

    def ingest(self, source: str, layer: str,
               key: str, value: Any) -> None: ...

    def record_weakness(self, kind: str, detail: str) -> None: ...
    def weaknesses(self) -> list[dict[str, Any]]: ...
    def synthesize(self, max_tokens: int = 400) -> str: ...

# -- Growth Organs — v1.0.8 named ---------------------------------


@runtime_checkable
class AnomalyGrowthProtocol(OrganProtocol, Protocol):
    """Anomaly growth — records anomaly patterns, drives evolutionary learning.

    **Coordinate**: ``("growth", "anomaly_growth")``
    **Inbound**: BRAINSTEM, AMYGDALA, WHISKERS (v1.0.8 added secure direct)
    **Outbound**: HIPPOCAMPUS, CORTEX
    **Reflex**: No direct reflex arc; triggered via BRAINSTEM
    **Implementor**: Application layer (growth organ)
    """
    name: str

    def record(self, reason: str, snippet: str, confidence: float = 0.8,
               phase: str = "input", session_id: str = "") -> Any: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class CorrectionGrowthProtocol(OrganProtocol, Protocol):
    """Correction growth — records user corrections, crystallizes experience.

    **Coordinate**: ``("growth", "correction_growth")``
    **Inbound**: BRAINSTEM, AMYGDALA (v1.0.8 added secure direct)
    **Outbound**: HIPPOCAMPUS, CORTEX
    **Reflex**: No direct reflex arc; triggered via BRAINSTEM
    **Implementor**: Application layer (growth organ)
    """
    name: str

    def record(self, wrong: str, correct: str, session_id: str = "",
               topic: str = "") -> Any: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class CrystallizerProtocol(OrganProtocol, Protocol):
    """Crystallizer — solidifies high-frequency operations into Skills/Tools.

    **Coordinate**: ``("growth", "crystallizer")``
    **Inbound**: BRAINSTEM
    **Outbound**: None (terminal organ)
    **Reflex**: No direct reflex arc
    **Implementor**: Application layer (growth organ)
    """
    name: str

    def crystallize(self, slug: str, hit_count: int) -> bool: ...
    def hotspots(self, threshold: int |
                 None = None) -> list[tuple[str, int]]: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class RoleEmergenceProtocol(OrganProtocol, Protocol):
    """Role emergence — extracts implicit roles from behavior patterns.

    **Coordinate**: ``("growth", "role_emergence")``
    **Inbound**: BRAINSTEM
    **Outbound**: None (terminal organ)
    **Reflex**: No direct reflex arc
    **Implementor**: Application layer (growth organ)
    """
    name: str

    def record(self, pattern: str, evidence: str) -> Any: ...
    def diagnose(self) -> dict[str, Any]: ...
