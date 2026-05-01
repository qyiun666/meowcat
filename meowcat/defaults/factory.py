"""meowcat create_cat() 工厂 — 一行代码创建完整猫。

自动装配：mount 器官 → wiring → reflex → freeze。
未提供的器官自动使用 Noop* / InMemory* 默认实现。
"""

from __future__ import annotations

from typing import Any

from meowcat.assembly import CatBase
from meowcat.biology import DEFAULT_REFLEX_PATHS
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHypothalamus,
    NoopMouth,
    NoopPurr,
    NoopTail,
    NoopWhiskers,
)
from meowcat.defaults.stores import InMemoryGraphStore, InMemoryL6Store
from meowcat.events import EventBus
from meowcat.protocols import (
    AmygdalaProtocol,
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
    ThalamusProtocol,
    WhiskersProtocol,
)
from meowcat.reflex import Reflex, ReflexRegistry
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
) -> CatBase:
    """一行代码创建完整装配的猫。

    Args:
        cat_id: 猫的唯一 ID。
        cerebrum: **必选** A 脑实例（满足 LLMBrainProtocol）。
        cerebellum: B 脑实例，默认使用 cerebrum 同实例。
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
    cat.hippocampus = hippocampus  # type: ignore[attr-defined]
    cat.thalamus = thalamus  # type: ignore[attr-defined]
    cat.amygdala = amygdala or NoopAmygdala()  # type: ignore[attr-defined]
    cat.frontal = frontal or NoopFrontal()  # type: ignore[attr-defined]
    cat.hypothalamus = hypothalamus or NoopHypothalamus()  # type: ignore[attr-defined]
    cat.cerebellum = cerebellum or cerebrum  # type: ignore[attr-defined]
    cat.cerebrum = cerebrum  # type: ignore[attr-defined]
    cat.cortex = cortex or NoopCortex()  # type: ignore[attr-defined]

    # -- 感官 ----------------------------------------------------------
    cat.ears = ears or NoopEars()  # type: ignore[attr-defined]
    cat.eyes = eyes or NoopEyes()  # type: ignore[attr-defined]
    cat.whiskers = whiskers or NoopWhiskers()  # type: ignore[attr-defined]
    cat.paws = paws  # type: ignore[attr-defined]

    # -- 输出 ----------------------------------------------------------
    cat.mouth = mouth or NoopMouth()  # type: ignore[attr-defined]
    cat.purr = purr or NoopPurr()  # type: ignore[attr-defined]
    cat.tail = tail or NoopTail()  # type: ignore[attr-defined]

    # -- 存储 ----------------------------------------------------------
    cat._graph_store = graph_store or InMemoryGraphStore()  # type: ignore[attr-defined]
    cat._l6_store = l6_store or InMemoryL6Store()  # type: ignore[attr-defined]

    # -- 自动装配 ------------------------------------------------------
    # mount 所有已设属性
    _mount_all(cat)

    # 神经系统
    cat.wire_default_nervous_system()

    # 默认 text_dialogue reflex
    _register_default_reflex(cat)

    # 冻结
    cat.freeze_nervous_system()

    return cat


def _mount_all(cat: CatBase) -> None:
    """自动扫描 cat 上的器官属性并 mount 到 _organs。"""
    _BRAIN_NAMES = {
        "hippocampus", "thalamus", "amygdala", "frontal",
        "hypothalamus", "cerebellum", "cerebrum", "brainstem", "cortex",
    }
    _SENSE_NAMES = {"ears", "eyes", "whiskers", "paws"}
    _VOICE_NAMES = {"mouth", "purr", "tail"}

    for name in _BRAIN_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount(BRAIN, name, organ)

    for name in _SENSE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount(SENSE, name, organ)

    for name in _VOICE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount(VOICE, name, organ)


def _register_default_reflex(cat: CatBase) -> None:
    """注册默认 text_dialogue reflex（如果 biology.py 中已定义）。"""
    if "text_dialogue" not in DEFAULT_REFLEX_PATHS:
        return
    path = list(DEFAULT_REFLEX_PATHS["text_dialogue"])
    # 默认 trigger: 字符串输入且非命令
    reflex = Reflex(
        name="text_dialogue",
        trigger=lambda x: isinstance(x, str) and not x.startswith("/"),
        path=path,
        stages=[],  # 业务层自行填写 stages
    )
    cat.register_reflex(reflex)
