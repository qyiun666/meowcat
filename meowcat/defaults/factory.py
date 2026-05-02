"""meowcat create_cat() 工厂 — 一行代码创建完整猫。

自动装配：mount 器官 → wiring → reflex → freeze。
未提供的器官自动使用 Noop* / InMemory* 默认实现。
"""

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

# -- 器官类别常量 (与 biology.py 保持一致) -----------------------------------

BRAIN = "brain"
SENSE = "sense"
VOICE = "voice"


def create_cat(
    cat_id: str,
    *,
    # ━━ 必选: LLM 器官（无默认，必须提供）━━
    cerebrum: LLMBrainProtocol,
    cerebellum: LLMBrainProtocol | None = None,
    # ━━ 可选: 脑区 ━━
    hippocampus: HippocampusProtocol | None = None,
    thalamus: ThalamusProtocol | None = None,
    amygdala: AmygdalaProtocol | None = None,
    frontal: FrontalCortexProtocol | None = None,
    hypothalamus: HypothalamusProtocol | None = None,
    cortex: CortexProtocol | None = None,
    brainstem: BrainStemProtocol | None = None,
    # ━━ 可选: 感官 ━━
    ears: EarsProtocol | None = None,
    eyes: EyesProtocol | None = None,
    whiskers: WhiskersProtocol | None = None,
    paws: PawsProtocol | None = None,
    # ━━ 可选: 输出 ━━
    mouth: Any = None,
    purr: Any = None,
    tail: Any = None,
    # ━━ 存储 ━━
    graph_store: GraphStorageProtocol | None = None,
    l6_store: L6StorageProtocol | None = None,
    vector_store: VectorStorageProtocol | None = None,
    shared_store: SharedStorageProtocol | None = None,
    # ━━ 反射弧 ━━
    reflexes: list[Reflex] | None = None,
) -> CatBase:
    """一行代码创建完整装配的猫。

    Args:
        cat_id: 猫的唯一 ID。
        cerebrum: **必选** A 脑实例（满足 LLMBrainProtocol）。
        cerebellum: B 脑实例，默认使用 cerebrum 同实例。
        brainstem: 脑干总调度，None 时不挂载（minimal 猫不需要）。
        reflexes: 反射弧列表，None 时不注册任何 reflex（调用方自行注入）。
        其余器官: 可选，未提供则使用 Noop* / InMemory* 默认。

    Returns:
        已完成 mount + wiring + reflex + freeze 的 CatBase 实例。

    Example::

        from meowcat.defaults import create_cat
        from my_impl import MyCerebrum

        cat = create_cat("my-bot", cerebrum=MyCerebrum(model="gpt-4"))
        await cat.start()
        reply = await cat.perceive("你好")
    """

    cat = CatBase(cat_id)

    # -- 脑区 ----------------------------------------------------------
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

    # -- 感官 ----------------------------------------------------------
    cat.ears = ears or NoopEars()  # type: ignore[attr-defined]
    cat.eyes = eyes or NoopEyes()  # type: ignore[attr-defined]
    cat.whiskers = whiskers or NoopWhiskers()  # type: ignore[attr-defined]
    cat.paws = paws or NoopPaws()  # type: ignore[attr-defined]

    # -- 输出 ----------------------------------------------------------
    cat.mouth = mouth or NoopMouth()  # type: ignore[attr-defined]
    cat.purr = purr or NoopPurr()  # type: ignore[attr-defined]
    cat.tail = tail or NoopTail()  # type: ignore[attr-defined]

    # -- 存储 ----------------------------------------------------------
    # type: ignore[attr-defined]
    cat._graph_store = graph_store or InMemoryGraphStore()
    cat._l6_store = l6_store or InMemoryL6Store()  # type: ignore[attr-defined]
    # type: ignore[attr-defined]
    cat._vector_store = vector_store or InMemoryVectorStore()
    # type: ignore[attr-defined]
    cat._shared_store = shared_store or InMemorySharedStore()

    # -- 自动装配 ------------------------------------------------------
    # mount 所有已设属性（共用 assembly.mount_known_organs）
    mount_known_organs(cat)

    # 神经系统
    cat.wire_default_nervous_system()

    # 反射弧（调用方注入）
    if reflexes:
        for ref in reflexes:
            cat.register_reflex(ref)

    # 冻结
    cat.freeze_nervous_system()

    return cat
