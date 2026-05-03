"""meowcat create_cat() factory — create a complete cat with one line of code.

Auto-assembly: mount organs → wiring → reflex → freeze.
Unprovided organs automatically use Noop* / InMemory* default implementations.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import Any

import anyio

from meowcat.assembly import CatBase, CatHook, mount_known_organs
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopBrainstem,
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
from meowcat.defaults.renovated import (
    RenovatedAmygdala,
    RenovatedAnomalyGrowth,
    RenovatedBrainstem,
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
from meowcat.defaults.presets import KeywordPreset, PromptPreset

_UNSET = object()
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
)
from meowcat.events import EventBus
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
from meowcat.wiring import Wiring

# -- Organ category constants (consistent with biology.py) --------------------------

BRAIN = "brain"
SENSE = "sense"
VOICE = "voice"


def create_cat(
    cat_id: str,
    *,
    container: "Colony",  # Colony instance (mandatory since v1.1.3)
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
    cat_name: str = "MeowCat",
    # ━━ Optional: brain regions ━━
    hippocampus: HippocampusProtocol | None = None,
    thalamus: ThalamusProtocol | None = None,
    amygdala: AmygdalaProtocol | None = None,
    frontal: FrontalCortexProtocol | None = None,
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
    # ━━ Storage ━━
    graph_store: GraphStorageProtocol | None = None,
    l6_store: L6StorageProtocol | None = None,
    vector_store: VectorStorageProtocol | None = None,
    shared_store: SharedStorageProtocol | None = None,
    # ━━ Reflex arcs ━━
    reflexes: list[Reflex] | None = None,
    # ━━ Assembly hooks ━━
    on_before_freeze: CatHook | None = None,
    on_assembled: CatHook | None = None,
) -> CatBase:
    """Create a fully assembled cat with one line of code.

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
        cat_id: Unique ID of the cat.
        cerebrum: **Required** A-brain instance (satisfying LLMBrainProtocol).
        cerebellum: B-brain instance, defaults to same instance as cerebrum.
        renovated: Use简装修 (True) or毛坯 (False). Default True.
        bare_organs: Organ names to keep as毛坯 when renovated=True.
        renovate_organs: Organ names to upgrade to简装修 when renovated=False.
        brainstem: Brainstem dispatcher, not mounted when None.
        reflexes: Reflex arc list.
        on_before_freeze: Async hook called after wiring + reflex registration,
            before freeze. Use for injecting extra organs / wiring paths.
        on_assembled: Async hook called after freeze, before return.
            Use for registering Path/Chain/Loop, setting runtime attributes.
        Other organs: Optional, defaults determined by ``renovated`` mode.

    Returns:
        A CatBase instance with mount + wiring + reflex + freeze completed.

    Example::

        from meowcat.defaults import create_cat
        from my_impl import MyCerebrum

        # 简装修 (default): safety, memory, routing all work
        cat = create_cat("bot", cerebrum=MyCerebrum(model="gpt-4"))

        # 毛坯: only cerebrum is real, others are stubs
        cat = create_cat("bot", cerebrum=MyCerebrum(), renovated=False)

        # 简装修 but keep amygdala as bare (no safety checks)
        cat = create_cat("bot", cerebrum=MyCerebrum(), bare_organs={"amygdala"})
    """

    _bare = bare_organs or set()
    _reno = renovate_organs or set()

    def _pick_no_init(bare_cls: type, reno_cls: type, organ_name: str, **reno_kw: Any) -> Any:
        if renovated:
            return reno_cls(**reno_kw) if organ_name not in _bare else bare_cls()
        else:
            return reno_cls(**reno_kw) if organ_name in _reno else bare_cls()

    cat = CatBase(cat_id, container=container)

    # -- Brain regions ----------------------------------------------------
    # type: ignore[attr-defined]
    cat.hippocampus = hippocampus or _pick_no_init(NoopHippocampus, RenovatedHippocampus, "hippocampus")
    cat.thalamus = thalamus or _pick_no_init(NoopThalamus, RenovatedThalamus, "thalamus", keyword=keyword)  # type: ignore[attr-defined]
    cat.amygdala = amygdala or _pick_no_init(NoopAmygdala, RenovatedAmygdala, "amygdala", keyword=keyword)  # type: ignore[attr-defined]
    cat.frontal = frontal or _pick_no_init(NoopFrontal, RenovatedFrontal, "frontal", keyword=keyword)  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat.hypothalamus = hypothalamus or _pick_no_init(NoopHypothalamus, RenovatedHypothalamus, "hypothalamus")
    # type: ignore[attr-defined]
    cat.cerebellum = cerebrum if cerebellum is _UNSET else cerebellum
    cat.cerebrum = cerebrum  # type: ignore[attr-defined]
    cat.cortex = cortex or _pick_no_init(NoopCortex, RenovatedCortex, "cortex")  # type: ignore[attr-defined]
    cat.brainstem = brainstem  # type: ignore[attr-defined]

    # -- Senses ----------------------------------------------------------
    cat.ears = ears or _pick_no_init(NoopEars, RenovatedEars, "ears", keyword=keyword)  # type: ignore[attr-defined]
    cat.eyes = eyes or _pick_no_init(NoopEyes, RenovatedEyes, "eyes")  # type: ignore[attr-defined]
    cat.whiskers = whiskers or _pick_no_init(NoopWhiskers, RenovatedWhiskers, "whiskers")  # type: ignore[attr-defined]
    cat.paws = paws or _pick_no_init(NoopPaws, RenovatedPaws, "paws")  # type: ignore[attr-defined]

    # -- Outputs ---------------------------------------------------------
    cat.mouth = mouth or _pick_no_init(NoopMouth, RenovatedMouth, "mouth")  # type: ignore[attr-defined]
    cat.purr = purr or _pick_no_init(NoopPurr, RenovatedPurr, "purr")  # type: ignore[attr-defined]
    cat.tail = tail or _pick_no_init(NoopTail, RenovatedTail, "tail")  # type: ignore[attr-defined]

    # -- Growth organs ---------------------------------------------------
    from meowcat.defaults.organs import (
        NoopAnomalyGrowth as _NoopAG,
        NoopCorrectionGrowth as _NoopCG,
        NoopCrystallizer as _NoopCr,
        NoopRoleEmergence as _NoopRE,
    )
    # type: ignore[attr-defined]
    cat.anomaly_growth = anomaly_growth or _pick_no_init(_NoopAG, RenovatedAnomalyGrowth, "anomaly_growth")
    # type: ignore[attr-defined]
    cat.correction_growth = correction_growth or _pick_no_init(_NoopCG, RenovatedCorrectionGrowth, "correction_growth")
    # type: ignore[attr-defined]
    cat.crystallizer = crystallizer or _pick_no_init(_NoopCr, RenovatedCrystallizer, "crystallizer")
    # type: ignore[attr-defined]
    cat.role_emergence = role_emergence or _pick_no_init(_NoopRE, RenovatedRoleEmergence, "role_emergence")

    # -- Storage ---------------------------------------------------------
    # type: ignore[attr-defined]
    cat._graph_store = graph_store or InMemoryGraphStore()
    cat._l6_store = l6_store or InMemoryL6Store()  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat._vector_store = vector_store or InMemoryVectorStore()
    # type: ignore[attr-defined]
    cat._shared_store = shared_store or InMemorySharedStore()

    # -- Auto-assembly ---------------------------------------------------
    mount_known_organs(cat)

    # Nervous system
    cat.wire_default_nervous_system()

    # Reflex arcs (caller injects)
    if reflexes:
        for ref in reflexes:
            cat.register_reflex(ref)

    # -- Assembly hook: before freeze (inject extra organs / wiring) --
    if on_before_freeze:
        anyio.run(on_before_freeze, cat)

    # Freeze
    cat.freeze_nervous_system()

    # -- Assembly hook: after freeze (register paths / set runtime attrs) --
    if on_assembled:
        anyio.run(on_assembled, cat)

    return cat


