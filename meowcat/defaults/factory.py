"""meowcat create_cat() factory — create a complete cat with one line of code.

Auto-assembly: mount organs → wiring → reflex → freeze.
Unprovided organs automatically use Noop* / InMemory* default implementations.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import Any

from meowcat.assembly import CatBase, mount_known_organs
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
    # ━━ Required: LLM organs (no default, must provide) ━━
    cerebrum: LLMBrainProtocol,
    cerebellum: LLMBrainProtocol | None = None,
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
    # ━━ Storage ━━
    graph_store: GraphStorageProtocol | None = None,
    l6_store: L6StorageProtocol | None = None,
    vector_store: VectorStorageProtocol | None = None,
    shared_store: SharedStorageProtocol | None = None,
    # ━━ Reflex arcs ━━
    reflexes: list[Reflex] | None = None,
) -> CatBase:
    """Create a fully assembled cat with one line of code.

    Args:
        cat_id: Unique ID of the cat.
        cerebrum: **Required** A-brain instance (satisfying LLMBrainProtocol).
        cerebellum: B-brain instance, defaults to same instance as cerebrum.
        brainstem: Brainstem dispatcher, not mounted when None (minimal cat doesn't need it).
        reflexes: Reflex arc list, no reflex registered when None (caller injects manually).
        Other organs: Optional, defaults to Noop* / InMemory* if not provided.

    Returns:
        A CatBase instance with mount + wiring + reflex + freeze completed.

    Example::

        from meowcat.defaults import create_cat
        from my_impl import MyCerebrum

        cat = create_cat("my-bot", cerebrum=MyCerebrum(model="gpt-4"))
        await cat.start()
        reply = await cat.perceive("hello")
    """

    cat = CatBase(cat_id)

    # -- Brain regions ----------------------------------------------------
    # type: ignore[attr-defined]
    cat.hippocampus = hippocampus or NoopHippocampus()
    cat.thalamus = thalamus or NoopThalamus()  # type: ignore[attr-defined]
    cat.amygdala = amygdala or NoopAmygdala()  # type: ignore[attr-defined]
    cat.frontal = frontal or NoopFrontal()  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat.hypothalamus = hypothalamus or NoopHypothalamus()
    cat.cerebellum = cerebellum or cerebrum  # type: ignore[attr-defined]
    cat.cerebrum = cerebrum  # type: ignore[attr-defined]
    cat.cortex = cortex or NoopCortex()  # type: ignore[attr-defined]
    cat.brainstem = brainstem  # type: ignore[attr-defined]

    # -- Senses ----------------------------------------------------------
    cat.ears = ears or NoopEars()  # type: ignore[attr-defined]
    cat.eyes = eyes or NoopEyes()  # type: ignore[attr-defined]
    cat.whiskers = whiskers or NoopWhiskers()  # type: ignore[attr-defined]
    cat.paws = paws or NoopPaws()  # type: ignore[attr-defined]

    # -- Outputs ---------------------------------------------------------
    cat.mouth = mouth or NoopMouth()  # type: ignore[attr-defined]
    cat.purr = purr or NoopPurr()  # type: ignore[attr-defined]
    cat.tail = tail or NoopTail()  # type: ignore[attr-defined]

    # -- Storage ---------------------------------------------------------
    # type: ignore[attr-defined]
    cat._graph_store = graph_store or InMemoryGraphStore()
    cat._l6_store = l6_store or InMemoryL6Store()  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat._vector_store = vector_store or InMemoryVectorStore()
    # type: ignore[attr-defined]
    cat._shared_store = shared_store or InMemorySharedStore()

    # -- Auto-assembly ---------------------------------------------------
    # mount all set attributes (shared assembly.mount_known_organs)
    mount_known_organs(cat)

    # Nervous system
    cat.wire_default_nervous_system()

    # Reflex arcs (caller injects)
    if reflexes:
        for ref in reflexes:
            cat.register_reflex(ref)

    # Freeze
    cat.freeze_nervous_system()

    return cat
