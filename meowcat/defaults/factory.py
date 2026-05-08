# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat create_cat() factory — create a complete cat with one line of code.

Auto-assembly: mount organs → wiring → reflex → freeze.
Unprovided organs automatically use Noop* / InMemory* default implementations.
"""

from __future__ import annotations

from typing import Any

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
from meowcat.defaults.renovated import (
    RenovatedAmygdala,
    RenovatedAnomalyGrowth,
    RenovatedCorrectionGrowth,
    RenovatedCortex,
    RenovatedCrystallizer,
    RenovatedEars,
    RenovatedEyes,
    RenovatedFrontal,
    RenovatedHippocampus,
    RenovatedHypothalamus,
    RenovatedMouth,
    RenovatedPaws,
    RenovatedPurr,
    RenovatedRoleEmergence,
    RenovatedTail,
    RenovatedThalamus,
    RenovatedWhiskers,
)
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemoryL6Store,
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
    L6StorageProtocol,
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
    """Register hippocampus lifecycle hooks when episode_store is configured.

    v1.3.6: Called by ``create_cat()`` after mounting hippocampus.
    Registers ``on_start`` (load episodes from store) and ``on_shutdown``
    (flush buffered episodes) hooks on the cat, reusing the async hook
    support added in D14/T-02.
    """
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
    """Register frontal lifecycle hooks when focus_store is configured.

    v1.3.6: Called by ``create_cat()`` after mounting frontal.
    Registers ``on_start`` (load focus from store) and ``on_shutdown``
    (save focus to store) hooks on the cat, reusing the async hook
    support added in D14/T-02.
    """
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
    # ━━ Renovation mode ━━
    renovated: bool = True,
    bare_organs: set[str] | None = None,
    renovate_organs: set[str] | None = None,
    # ━━ Keyword & Prompt presets (二语 行业 可挂载) ━━
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
    # ━━ Renovation tuning (passed to简装修 constructors) ━━
    dangerous_tools: set[str] | None = None,
    dangerous_paths: list[str] | None = None,
    frontal_threshold: float = 0.3,
    crystallize_threshold: int = 5,
    hotspot_threshold: int = 3,
    # ━━ Storage ━━
    graph_store: GraphStorageProtocol | None = None,
    l6_store: L6StorageProtocol | None = None,
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

    Two tiers of default organs:

    * **简装修** (renovated=True, default): pre-installed with useful defaults —
      safety regex, keyword routing, memory store, tool integration.
      Out-of-box working cat. Production apps extend/replace as needed.
    * **毛坯** (renovated=False): pure Noop* stubs — methods return empty/safe
      defaults. Use for full control or testing wiring.

    Per-organ overrides with ``bare_organs`` / ``renovate_organs``:
      - ``renovated=True``: add organ names to ``bare_organs`` to keep毛坯
      - ``renovated=False``: add organ names to ``renovate_organs`` to upgrade

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
        renovated: Use简装修 (True) or毛坯 (False). Default True.
        bare_organs: Organ names to keep as毛坯 when renovated=True.
        renovate_organs: Organ names to upgrade to简装修 when renovated=False.
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
            Call ``cat.register_default_paths()`` later. (v1.2.10)
        register_default_chains: When False, BUILTIN_CHAINS are not auto-registered.
            Call ``cat.register_default_chains()`` later. (v1.2.10)
        register_default_loops: When False, BUILTIN_LOOPS are not auto-registered.
            Call ``cat.register_default_loops()`` later. (v1.2.10)
        register_default_tools: When False, BUILTIN_TOOLS are not auto-registered.
            Call ``cat.register_default_tools()`` later. (v1.2.10)
        Other organs: Optional, defaults determined by ``renovated`` mode.

    Returns:
        A CatBase instance with mount + wiring + reflex + freeze completed.

    Example::

        from meowcat.defaults import create_cat
        from my_impl import MyCerebrum

        # 简装修 (default): safety, memory, routing all work
        cat = create_cat(container=colony, cerebrum=MyCerebrum(model="gpt-4"))

        # 毛坯: only cerebrum is real, others are stubs
        cat = create_cat(container=colony, cerebrum=MyCerebrum(), renovated=False)

        # 简装修 but keep amygdala as bare (no safety checks)
        cat = create_cat(container=colony, cerebrum=MyCerebrum(), bare_organs={"amygdala"})
    """

    _bare = bare_organs or set()
    _reno = renovate_organs or set()

    def _pick_no_init(bare_cls: type, reno_cls: type, organ_name: str, **reno_kw: Any) -> Any:
        if renovated:
            return reno_cls(**reno_kw) if organ_name not in _bare else bare_cls()
        else:
            return reno_cls(**reno_kw) if organ_name in _reno else bare_cls()

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
    cat.hippocampus = hippocampus or _pick_no_init(
        NoopHippocampus, RenovatedHippocampus, "hippocampus"
    )
    # v1.3.6: Register hippocampus lifecycle hooks (on_start load, on_shutdown flush)
    _maybe_register_hippo_lifecycle(cat)
    cat.thalamus = thalamus or _pick_no_init(
        # type: ignore[attr-defined]
        NoopThalamus,
        RenovatedThalamus,
        "thalamus",
        keyword=keyword,
    )
    cat.amygdala = amygdala or _pick_no_init(
        # type: ignore[attr-defined]
        NoopAmygdala,
        RenovatedAmygdala,
        "amygdala",
        keyword=keyword,
        dangerous_tools=dangerous_tools,
        dangerous_paths=dangerous_paths,
    )
    cat.frontal = frontal or _pick_no_init(
        # type: ignore[attr-defined]
        NoopFrontal,
        RenovatedFrontal,
        "frontal",
        keyword=keyword,
        threshold=frontal_threshold,
        focus_store=focus_store,
    )
    # v1.3.6 T-22: Register frontal lifecycle hooks (on_start load, on_shutdown save)
    _maybe_register_frontal_lifecycle(cat)
    # type: ignore[attr-defined]
    cat.hypothalamus = hypothalamus or _pick_no_init(
        NoopHypothalamus, RenovatedHypothalamus, "hypothalamus"
    )
    # type: ignore[attr-defined]
    cat.cerebellum = cerebrum if cerebellum is _UNSET else cerebellum
    cat.cerebrum = cerebrum  # type: ignore[attr-defined]
    cat.cortex = cortex or _pick_no_init(
        NoopCortex, RenovatedCortex, "cortex")  # type: ignore[attr-defined]
    cat.brainstem = brainstem  # type: ignore[attr-defined]

    # -- Senses ----------------------------------------------------------
    cat.ears = ears or _pick_no_init(
        # type: ignore[attr-defined]
        NoopEars,
        RenovatedEars,
        "ears",
        keyword=keyword,
    )
    cat.eyes = eyes or _pick_no_init(
        NoopEyes, RenovatedEyes, "eyes")  # type: ignore[attr-defined]
    cat.whiskers = whiskers or _pick_no_init(
        # type: ignore[attr-defined]
        NoopWhiskers,
        RenovatedWhiskers,
        "whiskers",
    )
    cat.paws = paws or _pick_no_init(
        NoopPaws, RenovatedPaws, "paws")  # type: ignore[attr-defined]

    # -- Outputs ---------------------------------------------------------
    cat.mouth = mouth or _pick_no_init(
        NoopMouth, RenovatedMouth, "mouth")  # type: ignore[attr-defined]
    cat.purr = purr or _pick_no_init(
        NoopPurr, RenovatedPurr, "purr")  # type: ignore[attr-defined]
    cat.tail = tail or _pick_no_init(
        NoopTail, RenovatedTail, "tail")  # type: ignore[attr-defined]

    # -- Growth organs ---------------------------------------------------
    from meowcat.defaults.organs import (
        NoopAnomalyGrowth as _NoopAG,
    )
    from meowcat.defaults.organs import (
        NoopCorrectionGrowth as _NoopCG,
    )
    from meowcat.defaults.organs import (
        NoopCrystallizer as _NoopCr,
    )
    from meowcat.defaults.organs import (
        NoopRoleEmergence as _NoopRE,
    )

    # type: ignore[attr-defined]
    cat.anomaly_growth = anomaly_growth or _pick_no_init(
        _NoopAG, RenovatedAnomalyGrowth, "anomaly_growth"
    )
    # type: ignore[attr-defined]
    cat.correction_growth = correction_growth or _pick_no_init(
        _NoopCG, RenovatedCorrectionGrowth, "correction_growth"
    )
    # type: ignore[attr-defined]
    cat.crystallizer = crystallizer or _pick_no_init(
        _NoopCr,
        RenovatedCrystallizer,
        "crystallizer",
        crystallize_threshold=crystallize_threshold,
        hotspot_threshold=hotspot_threshold,
    )
    # type: ignore[attr-defined]
    cat.role_emergence = role_emergence or _pick_no_init(
        _NoopRE, RenovatedRoleEmergence, "role_emergence"
    )

    # -- Storage ---------------------------------------------------------
    # type: ignore[attr-defined]
    cat._graph_store = graph_store or InMemoryGraphStore()
    cat._l6_store = l6_store or InMemoryL6Store()  # type: ignore[attr-defined]
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

    # Builtin tools (v1.2.10: optional, controlled by register_default_tools)
    if register_default_tools:
        from meowcat.plus.tools import BUILTIN_TOOLS

        for t in BUILTIN_TOOLS:
            cat.tool_registry.register(t)

    # Reflex arcs
    if reflexes is not None:
        for ref in reflexes:
            cat.register_reflex(ref)
    else:
        # v1.3.3: auto-register default text_dialogue reflex so perceive()
        # works out of the box with create_cat (renovated=True).
        # Stages are noop stubs — emit correct lifecycle events;
        # applications override with real Stage implementations.
        from meowcat.defaults.stages import build_default_pipeline
        from meowcat.reflex import BUILTIN_REFLEX_PATHS

        cat.register_reflex(
            Reflex(
                name="text_dialogue",
                trigger=lambda x: isinstance(x, str),
                path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                stages=build_default_pipeline(),
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
