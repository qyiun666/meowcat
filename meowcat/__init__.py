"""meowcat — 猫框架（猫的生物学蓝图）。依赖 pydantic>=2.0 + anyio>=4.0，零 meowagent import。"""

__version__ = "0.2.0"

from meowcat import biology as biology
from meowcat.assembly import CatBase, KittenBase
from meowcat.errors import (
    IllegalNeuralPathError,
    LoopFailedError,
    MeowCatError,
    NoReflexMatchedError,
    OrganNotMountedError,
    OrganProtocolMismatchError,
    ReflexPathInvalidError,
    StageTimeoutError,
)
from meowcat.events import EventBus
from meowcat.loop import (
    ALL_EVENTS,
    GrowthEvent,
    KittenEvent,
    Lifecycle,
    LocateEvent,
    NerveEvent,
    OrchestrateEvent,
    RememberEvent,
)
from meowcat.models import (
    CandidateShape,
    ConnectionShape,
    EntityShape,
    EpisodeShape,
    FocusShape,
    KittenCapability,
    LocateResultShape,
    LoopEvent,
    MaintenanceReportShape,
    MergeProposalShape,
    OrchestratorReportShape,
    PipelineContext,
    StageEvent,
    SubTaskShape,
    TaskResultShape,
)
from meowcat.perception import Modality, PerceptionContext, infer_modality
from meowcat.pipeline import Pipeline
from meowcat.protocols import (
    AmygdalaProtocol,
    BrainStemProtocol,
    CatProtocol,
    CortexProtocol,
    EarsProtocol,
    EyesProtocol,
    FrontalCortexProtocol,
    GraphStorageProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    KittenProtocol,
    L6StorageProtocol,
    LLMBrainProtocol,
    LLMProviderProtocol,
    OrchestratorProtocol,
    OrganProtocol,
    PawsProtocol,
    SettingsProtocol,
    SharedStorageProtocol,
    StageProtocol,
    ThalamusProtocol,
    VectorStorageProtocol,
    WhiskersProtocol,
)
from meowcat.reflex import Reflex, ReflexRegistry, Trigger
from meowcat.wiring import Edge, Organ, Wiring, WiringSnapshot

# -- 内置默认实现 ----------------------------------------------------------
from meowcat.defaults import (
    InMemoryGraphStore,
    InMemoryL6Store,
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
    create_cat,
)

__all__ = [
    # Protocols
    "OrchestratorProtocol", "SettingsProtocol", "OrganProtocol", "CatProtocol", "KittenProtocol", "BrainStemProtocol",
    "HippocampusProtocol", "ThalamusProtocol", "LLMBrainProtocol",
    "AmygdalaProtocol", "FrontalCortexProtocol", "HypothalamusProtocol",
    "CortexProtocol", "EarsProtocol", "EyesProtocol", "WhiskersProtocol",
    "PawsProtocol", "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol", "StageProtocol",
    "LLMProviderProtocol",
    # Models
    "EntityShape", "ConnectionShape", "EpisodeShape", "FocusShape",
    "SubTaskShape", "TaskResultShape", "OrchestratorReportShape",
    "CandidateShape", "LocateResultShape", "MaintenanceReportShape",
    "StageEvent", "PipelineContext", "LoopEvent",
    "MergeProposalShape", "KittenCapability",
    # Errors
    "MeowCatError", "OrganNotMountedError", "LoopFailedError",
    "StageTimeoutError",
    "IllegalNeuralPathError", "ReflexPathInvalidError",
    "NoReflexMatchedError", "OrganProtocolMismatchError",
    # 骨架
    "CatBase", "KittenBase", "EventBus", "Pipeline",
    # 闭环事件名
    "LocateEvent", "RememberEvent", "OrchestrateEvent", "GrowthEvent",
    "Lifecycle", "KittenEvent", "NerveEvent", "ALL_EVENTS",
    # v0.5.1 神经系统
    "Wiring", "WiringSnapshot", "Organ", "Edge",
    "Reflex", "ReflexRegistry", "Trigger",
    "PerceptionContext", "Modality", "infer_modality",
    "biology",
    # 内置默认实现
    "create_cat",
    "NoopAmygdala", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopEars", "NoopEyes", "NoopWhiskers",
    "NoopMouth", "NoopPurr", "NoopTail",
    "InMemoryGraphStore", "InMemoryL6Store",
]
