# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat create_cat() factory — create a complete cat with one line of code.

Auto-assembly: mount organs → wiring → reflex → freeze.
Unprovided organs automatically use Noop* / InMemory* default implementations.

v2.0: Noop + Renovated merged — all organs have real behavior by default.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.colony import Colony  # noqa: F401

from meowcat.assembly import CatBase, CatHook, mount_known_organs
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
    NoopThalamus,
    NoopWhiskers,
)
from meowcat.defaults.presets import KeywordPreset, PromptPreset
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemorySharedStore,
    InMemoryVectorStore,
)
from meowcat.protocols import (
    AmygdalaProtocol,
    BrainStemProtocol,
    CortexProtocol,
    EarsProtocol,
    EyesProtocol,
    FrontalCortexProtocol,
    GraphStorageProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    LLMBrainProtocol,
    PawsProtocol,
    SharedStorageProtocol,
    ThalamusProtocol,
    VectorStorageProtocol,
    WhiskersProtocol,
)
from meowcat.reflex import Reflex

_UNSET = object()

# -- Organ category constants (consistent with biology.py) --------------------------

BRAIN = "brain"
SENSE = "sense"
VOICE = "voice"


def _maybe_register_hippo_lifecycle(cat: CatBase) -> None:
    """Register hippocampus lifecycle hooks when episode_store is configured."""
    hippo = cat.hippocampus
    episode_store = getattr(hippo, "_episode_store", None)
    if episode_store is None:
        return

    async def _hippo_on_start(c: CatBase) -> None:
        c.hippocampus.cat_uid = c.cat_uid
        await c.hippocampus._load_from_store()

    async def _hippo_on_shutdown(c: CatBase) -> None:
        await c.hippocampus._flush_to_store()

    cat.on_start(_hippo_on_start)
    cat.on_shutdown(_hippo_on_shutdown)


def _maybe_register_frontal_lifecycle(cat: CatBase) -> None:
    """Register frontal lifecycle hooks when focus_store is configured."""
    frontal = cat.frontal
    focus_store = getattr(frontal, "_focus_store", None)
    if focus_store is None:
        return

    async def _frontal_on_start(c: CatBase) -> None:
        await c.frontal._load_from_store()

    async def _frontal_on_shutdown(c: CatBase) -> None:
        await c.frontal._save_to_store()

    cat.on_start(_frontal_on_start)
    cat.on_shutdown(_frontal_on_shutdown)


def create_cat(
    *,
    cat: CatBase | None = None,
    # Required when cat=None; inferred from cat otherwise
    container: Colony | None = None,  # noqa: F821
    # ━━ Required: LLM organs ━━
    cerebrum: LLMBrainProtocol,
    cerebellum: LLMBrainProtocol | None = _UNSET,  # type: ignore[assignment]
    # ━━ Keyword & Prompt presets ━━
    keyword: KeywordPreset | None = None,
    prompt: PromptPreset | None = None,
    name: str | None = None,
    # ━━ Optional: brain regions ━━
    hippocampus: HippocampusProtocol | None = None,
    thalamus: ThalamusProtocol | None = None,
    amygdala: AmygdalaProtocol | None = None,
    frontal: FrontalCortexProtocol | None = None,
    focus_store: Any | None = None,  # FocusStore | None (lazy import)
    hypothalamus: HypothalamusProtocol | None = None,
    cortex: CortexProtocol | None = None,
    brainstem: BrainStemProtocol | None = None,
    # ━━ Optional: senses ━━
    ears: EarsProtocol | None = None,
    eyes: EyesProtocol | None = None,
    whiskers: WhiskersProtocol | None = None,
    paws: PawsProtocol | None = None,
    # ━━ Optional: outputs ━━
    mouth: Any = None,
    purr: Any = None,
    tail: Any = None,
    # ━━ Growth organs ━━
    anomaly_growth: Any = None,
    correction_growth: Any = None,
    crystallizer: Any = None,
    role_emergence: Any = None,
    # ━━ Organ tuning (passed to default constructors) ━━
    dangerous_tools: set[str] | None = None,
    dangerous_paths: list[str] | None = None,
    frontal_threshold: float = 0.3,
    crystallize_threshold: int = 5,
    hotspot_threshold: int = 3,
    # ━━ Storage ━━
    graph_store: GraphStorageProtocol | None = None,
    vector_store: VectorStorageProtocol | None = None,
    shared_store: SharedStorageProtocol | None = None,
    # ━━ Reflex arcs ━━
    reflexes: list[Reflex] | None = None,
    # ━━ Assembly hooks ━━
    on_before_mount: CatHook | None = None,
    on_before_freeze: CatHook | None = None,
    on_assembled: CatHook | None = None,
    # ━━ Default registration switches (v1.2.10) ━━
    register_default_paths: bool = True,
    register_default_chains: bool = True,
    register_default_loops: bool = True,
    register_default_tools: bool = True,
) -> CatBase:
    """Create a fully assembled cat with one line of code.

    ``cat_uid`` is auto-generated by the colony (2-digit increment).

    All organs use merged (Noop+Renovated) defaults — safety regex,
    keyword routing, memory store, tool integration all work out of
    the box. Production apps extend/replace individual organs as needed.

    Args:
        cat: Pre-existing CatBase subclass instance. When provided, skips
            ``container.create_cat()`` and assembles directly on ``cat``.
            ``container`` is inferred from ``cat.container``, and
            ``register_default_*`` flags are taken from the instance.
            Default ``None`` (create new CatBase).
        container: Colony instance. Required when ``cat=None``; inferred
            from ``cat.container`` otherwise.
        cerebrum: **Required** A-brain instance (satisfying LLMBrainProtocol).
        cerebellum: B-brain instance, defaults to same instance as cerebrum.
        keyword: KeywordPreset for routing, safety, focus, ears.
        prompt: PromptPreset for brainstem system prompt.
        name: Optional display name for the cat.
        brainstem: Brainstem dispatcher, not mounted when None.
        reflexes: Reflex arc list.
        on_before_mount: Sync hook called after organ defaults are set,
            before ``mount_known_organs()``. Use for replacing default organs
            with custom implementations (e.g. cross-organ dependency injection).
        on_before_freeze: Sync hook called after wiring + reflex registration,
            before freeze. Use for injecting extra organs / wiring paths.
        on_assembled: Sync hook called after freeze, before return.
            Use for registering Path/Chain/Loop, setting runtime attributes.
        register_default_paths: When False, BUILTIN_PATHS are not auto-registered.
        register_default_chains: When False, BUILTIN_CHAINS are not auto-registered.
        register_default_loops: When False, BUILTIN_LOOPS are not auto-registered.
        register_default_tools: When False, BUILTIN_TOOLS are not auto-registered.
        Other organs: Optional, default implementations created when None.

    Returns:
        A CatBase instance with mount + wiring + reflex + freeze completed.

    Example::

        from meowcat.defaults import create_cat
        from my_impl import MyCerebrum

        # Default: safety, memory, routing all work out of the box
        cat = create_cat(container=colony, cerebrum=MyCerebrum(model="gpt-4"))

        # Custom organs override defaults
        cat = create_cat(container=colony, cerebrum=MyCerebrum(), amygdala=MySafety())
    """

    if cat is None:
        if container is None:
            raise TypeError(
                "create_cat() requires 'container' when 'cat' is None")
        cat = container.create_cat(
            name=name,
            register_default_paths=register_default_paths,
            register_default_chains=register_default_chains,
            register_default_loops=register_default_loops,
            register_default_tools=register_default_tools,
        )
    else:
        # Pre-existing instance (CatBase subclass): register in colony
        # and set up colony memory hook (normally done by Colony.create_cat)
        container = cat.container
        container.register(cat)
        cat.on_organs_mounted(lambda c: container._inject_colony_memory(c))

    # -- Brain regions ----------------------------------------------------
    # type: ignore[attr-defined]
    cat.hippocampus = hippocampus or NoopHippocampus()
    _maybe_register_hippo_lifecycle(cat)
    # type: ignore[attr-defined]
    cat.thalamus = thalamus or NoopThalamus(keyword=keyword)
    # type: ignore[attr-defined]
    cat.amygdala = amygdala or NoopAmygdala(
        keyword=keyword,
        dangerous_tools=dangerous_tools,
        dangerous_paths=dangerous_paths,
    )
    # type: ignore[attr-defined]
    cat.frontal = frontal or NoopFrontal(
        keyword=keyword,
        threshold=frontal_threshold,
        focus_store=focus_store,
    )
    _maybe_register_frontal_lifecycle(cat)
    # type: ignore[attr-defined]
    cat.hypothalamus = hypothalamus or NoopHypothalamus()
    # type: ignore[attr-defined]
    cat.cerebellum = cerebrum if cerebellum is _UNSET else cerebellum
    cat.cerebrum = cerebrum  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat.cortex = cortex or NoopCortex()
    cat.brainstem = brainstem  # type: ignore[attr-defined]

    # -- Senses ----------------------------------------------------------
    # type: ignore[attr-defined]
    cat.ears = ears or NoopEars(keyword=keyword)
    # type: ignore[attr-defined]
    cat.eyes = eyes or NoopEyes()
    # type: ignore[attr-defined]
    cat.whiskers = whiskers or NoopWhiskers()
    # type: ignore[attr-defined]
    cat.paws = paws or NoopPaws()

    # -- Outputs ---------------------------------------------------------
    # type: ignore[attr-defined]
    cat.mouth = mouth or NoopMouth()
    # type: ignore[attr-defined]
    cat.purr = purr or NoopPurr()
    # type: ignore[attr-defined]
    cat.tail = tail or NoopTail()

    # -- Growth organs ---------------------------------------------------
    from meowcat.defaults.organs import NoopAnomalyGrowth
    from meowcat.defaults.organs import NoopCorrectionGrowth
    from meowcat.defaults.organs import NoopCrystallizer
    from meowcat.defaults.organs import NoopRoleEmergence

    # type: ignore[attr-defined]
    cat.anomaly_growth = anomaly_growth or NoopAnomalyGrowth()
    # type: ignore[attr-defined]
    cat.correction_growth = correction_growth or NoopCorrectionGrowth()
    # type: ignore[attr-defined]
    cat.crystallizer = crystallizer or NoopCrystallizer(
        crystallize_threshold=crystallize_threshold,
        hotspot_threshold=hotspot_threshold,
    )
    # type: ignore[attr-defined]
    cat.role_emergence = role_emergence or NoopRoleEmergence()

    # -- Storage ---------------------------------------------------------
    # type: ignore[attr-defined]
    cat._graph_store = graph_store or InMemoryGraphStore()
    # type: ignore[attr-defined]
    cat._vector_store = vector_store or InMemoryVectorStore()
    # type: ignore[attr-defined]
    cat._shared_store = shared_store or InMemorySharedStore()

    # -- Assembly hook: before mount (override default organs) --
    if on_before_mount:
        on_before_mount(cat)

    # -- Auto-assembly ---------------------------------------------------
    mount_known_organs(cat)

    # Nervous system
    cat.wire_default_nervous_system()

    # Builtin tools (v2.0: moved to application layer)
    # Application layer should register tools via cat.tool_registry.register()
    if register_default_tools:
        pass  # no-op: BUILTIN_TOOLS removed in v2.0

    # Reflex arcs
    if reflexes is not None:
        for ref in reflexes:
            cat.register_reflex(ref)
    else:
        from meowcat.defaults.stages import build_default_pipeline
        from meowcat.reflex import BUILTIN_REFLEX_PATHS

        cat.register_reflex(
            Reflex(
                name="text_dialogue",
                trigger=lambda x: isinstance(x, str),
                path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                stages=build_default_pipeline(),  # type: ignore[arg-type]
                priority=0,
            )
        )

    # -- Assembly hook: before freeze (inject extra organs / wiring) --
    if on_before_freeze:
        on_before_freeze(cat)

    # Freeze
    cat.freeze_nervous_system()

    # -- Assembly hook: after freeze (register paths / set runtime attrs) --
    if on_assembled:
        on_assembled(cat)

    return cat
