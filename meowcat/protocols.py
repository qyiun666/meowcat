# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat protocol layer — blueprint of cat anatomical structure.

All typing.Protocol (duck typing), zero third-party dependencies.

v1.0.5: storage/brain/sense protocols split into sub-modules; this file re-exports for compatibility.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

# v1.0.5: re-export from sub-modules, keep from meowcat import ... fully compatible
from meowcat.protocols_brain import (
    AmygdalaProtocol,
    AnomalyGrowthProtocol,
    BrainStemProtocol,
    CorrectionGrowthProtocol,
    CortexProtocol,
    CrystallizerProtocol,
    Diagnosable,
    FrontalCortexProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    LLMBrainProtocol,
    LLMProviderProtocol,
    OrganProtocol,
    RoleEmergenceProtocol,
    ThalamusProtocol,
)
from meowcat.protocols_sense import (
    EarsProtocol,
    EyesProtocol,
    PawsProtocol,
    WhiskersProtocol,
)
from meowcat.protocols_storage import (
    FederationTransport,
    GraphStorageProtocol,
    L6StorageProtocol,
    SharedStorageProtocol,
    VectorStorageProtocol,
)
from meowcat.protocols_voice import (
    MouthProtocol,
    PurrProtocol,
    TailProtocol,
)

if TYPE_CHECKING:
    from meowcat.models import (
        KittenCapability,
        MergeProposalShape,
        PipelineContext,
        StageEvent,
        SubTaskShape,
    )

__all__ = [
    "Diagnosable",
    "OrganProtocol",
    "FederationTransport",
    "GraphStorageProtocol",
    "L6StorageProtocol",
    "VectorStorageProtocol",
    "SharedStorageProtocol",
    "LLMProviderProtocol",
    "BrainStemProtocol",
    "HippocampusProtocol",
    "ThalamusProtocol",
    "LLMBrainProtocol",
    "AmygdalaProtocol",
    "FrontalCortexProtocol",
    "HypothalamusProtocol",
    "CortexProtocol",
    "EarsProtocol",
    "EyesProtocol",
    "WhiskersProtocol",
    "PawsProtocol",
    "AnomalyGrowthProtocol",
    "CorrectionGrowthProtocol",
    "CrystallizerProtocol",
    "RoleEmergenceProtocol",
    "MouthProtocol",
    "PurrProtocol",
    "TailProtocol",
    "StageProtocol",
    "KittenProtocol",  # doc-only, not @runtime_checkable; isinstance() raises TypeError
    "OrchestratorProtocol",
    "SettingsProtocol",
    "CatProtocol",
    "AdapterProtocol",
    "SecurityPolicyProtocol",
]

# -- Pipeline -----------------------------------------------------


@runtime_checkable
class StageProtocol(Protocol):
    """Pipeline Stage protocol — each Stage is a pluggable processing step.

    **Position**: none (Pipeline layer, each Stage identified by name, no organ coordinate)
    **Inbound**: driven by PipelineRunner in sequence, not via wiring
    **Outbound**: yields StageEvent to PipelineRunner
    **Reflex Arc**: none direct; Stage can call signal() via ctx.cat internally
    **Implemented by**: app layer (Pipeline Stage)
    """

    name: str

    async def run(self, ctx: PipelineContext) -> AsyncIterator[StageEvent]: ...


# -- Security (v1.0.18) -----------------------------------------------


@runtime_checkable
class SecurityPolicyProtocol(Protocol):
    """Security policy interface — each cat can mount a different policy.

    Framework provides no default danger patterns;
    an empty cat defaults to ``is_danger → False``.
    """

    def is_danger(self, input: str) -> bool: ...
    def assess_tool_risk(
        self, name: str, params: dict[str, Any]) -> dict[str, str]: ...


# -- Kitten blueprint ------------------------------------------------


class KittenProtocol(Protocol):
    """Kitten blueprint — doc-only Protocol (v1.0.1 downgraded, no longer @runtime_checkable).

    Kitten = CatBase(parent_id=..., allowed_organs={...}, forbidden_methods={...}).
    Permissions controlled by CatBase ``allowed_organs`` + ``forbidden_methods``.

    See ``docs/v0.5.0/design.md`` section 12. Preserved here as doc reference,
    showing recommended kitten configuration:

    **Organs only**: cerebellum, cerebrum, paws, whiskers, amygdala
    **Lifecycle**: execute → propose_merge → dismiss
    **Isolation**: parent_id is a string identifier only, no parent cat object reference

    **Implemented by**: app layer (KittenAgent implementation)
    """

    parent_id: str  # parent cat_uid, string identifier only
    task: SubTaskShape
    role: str
    workspace: Any
    capability: KittenCapability
    # read-only memory snapshot injected at spawn
    memory_snapshot: dict[str, Any]

    # organs only
    cerebellum: LLMBrainProtocol
    cerebrum: LLMBrainProtocol
    paws: PawsProtocol
    whiskers: WhiskersProtocol
    amygdala: AmygdalaProtocol

    # lifecycle (execute returns MergeProposal directly, the only channel back)
    async def execute(self) -> MergeProposalShape: ...
    def propose_merge(self) -> MergeProposalShape: ...
    async def dismiss(self) -> None: ...


# -- Cat body -------------------------------------------------------


@runtime_checkable
class OrchestratorProtocol(Protocol):
    """Orchestrator interface — 6-step orchestration loop (plan→dispatch→execute→absorb→revise→fallback).

    **Position**: none (held directly by Cat, not called via wiring)
    **Inbound**: triggered by BrainStem/RouteDecideStage when orchestration needed
    **Outbound**: creates kittens via spawn_kitten, absorbs results via absorb_merge
    **Reflex Arc**: none direct; orchestration internally calls organs via signal (e.g. HIPPOCAMPUS)
    **Implemented by**: app layer (orchestrator implementation)
    """

    async def orchestrate(self, msg: str) -> Any: ...
    def should_orchestrate(self, msg: str, route: str) -> bool: ...


@runtime_checkable
class SettingsProtocol(Protocol):
    """Settings interface — exposes only data_dir to framework layer.

    **Position**: none (config layer, held directly by Cat)
    **Inbound**: accessed by all organs via cat.settings
    **Outbound**: none
    **Reflex Arc**: none
    **Implemented by**: app layer (settings implementation)
    """

    data_dir: Any


@runtime_checkable
class AdapterProtocol(Protocol):
    """Domain adapter — defines domain-specific retrieval weights and entity types.

    Exposes only the minimal contract the framework layer needs:
    - ``name``: unique adapter identifier
    - ``entity_types``: list of entity types for this domain
    - ``locate_weights``: retrieval weight config for locate()

    **Position**: none (domain config, no organ coordinate)
    **Inbound**: injected by app layer at init/runtime via cat.active_adapter
    **Outbound**: read by Thalamus.locate() / BrainStem.build_system_prompt()
    **Reflex Arc**: indirectly participates in text_dialogue (routing via locate weights)
    **Implemented by**: app layer (adapter config)
    """

    name: str
    entity_types: Any
    locate_weights: Any


@runtime_checkable
class CatProtocol(Protocol):
    """Cat body protocol — full external API of a complete cat. Composes all brain regions + senses + orchestration.

    **Position**: none (Cat is the assembly class, no single organ coordinate;
    organs registered independently via wiring)
    **Inbound**: external callers (CLI, Server, multi-platform adapters) trigger via process_message/perceive_stream
    **Outbound**: produces replies and actions coordinated by internal organs
    **Reflex Arc**: holds all reflex arcs registered by app layer
    **Lifecycle**: start() → event loop → shutdown()
    **Implemented by**: app layer (Cat assembly class)
    """

    cat_uid: str
    settings: Any
    data_dir: Any
    turn: int
    # brain regions
    hippocampus: HippocampusProtocol
    thalamus: ThalamusProtocol
    amygdala: AmygdalaProtocol
    frontal: FrontalCortexProtocol
    hypothalamus: HypothalamusProtocol
    cerebellum: LLMBrainProtocol
    cerebrum: LLMBrainProtocol
    brainstem: BrainStemProtocol
    # senses
    ears: EarsProtocol
    eyes: EyesProtocol
    whiskers: WhiskersProtocol
    paws: PawsProtocol
    # orchestration / approval / adapter
    orchestrator: OrchestratorProtocol
    approval: Any
    active_adapter: AdapterProtocol | None

    # nervous system (EventBus)
    async def emit(self, event: str, payload: Any = None) -> None: ...
    def on(self, event: str, handler: Any | None = None) -> Any: ...
    def off(self, event: str, handler: Any) -> bool: ...

    # external API
    async def process_message(self, msg: str) -> str: ...
    async def perceive_stream(
        self, msg: str) -> AsyncIterator[dict[str, str]]: ...

    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...

    # derived capability (main cat only; not in KittenProtocol → framework-level recursion guard)
    async def spawn_kitten(
        self,
        task: SubTaskShape,
        role: str,
        capability: KittenCapability | None = None,
    ) -> KittenProtocol: ...
    async def absorb_merge(self, proposal: MergeProposalShape) -> None: ...
