"""meowcat — 猫框架（猫的生物学蓝图）。依赖 pydantic>=2.0 + anyio>=4.0，零 meowagent import。"""

from meowcat.defaults import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
    NoopAmygdala,
    NoopBrainstem,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
    NoopWhiskers,
    create_cat,
)
from meowcat.wiring import Edge, Organ, Wiring, WiringSnapshot
from meowcat.reflex import Reflex, ReflexArc, ReflexRegistry, Trigger
from meowcat.host import OrganHost
from meowcat.nervous import Nervous
from meowcat.organ_base import OrganMixin
from meowcat.protocols import (
    AdapterProtocol,
    AmygdalaProtocol,
    BrainStemProtocol,
    CatProtocol,
    CortexProtocol,
    Diagnosable,
    EarsProtocol,
    EyesProtocol,
    FrontalCortexProtocol,
    GraphStorageProtocol,
    GrowthProtocol,
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
from meowcat.pipeline import Pipeline
from meowcat.perception import Modality, PerceptionContext, infer_modality
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
from meowcat.events import EventBus
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
from meowcat.assembly import CatBase, assemble_default_cat, mount_known_organs
from meowcat.colony import Colony
from meowcat.diagnose import Stethoscope, render_wiring
from meowcat.inject import Needle, NeedleDisabledError
from meowcat.path import Path, PathRegistry, BUILTIN_PATHS, register_builtin_paths
from meowcat.chain import (
    Chain,
    ChainRegistry,
    BUILTIN_CHAINS,
    register_builtin_chains,
    MEMORY_SEARCH_CHAIN,
    FULL_REASONING_CHAIN,
    TOOL_EXEC_CHAIN,
    MAINTENANCE_CHAIN,
    DIAGNOSTIC_CHAIN,
)
from meowcat.loops import (
    Loop,
    LoopRegistry,
    BUILTIN_LOOPS,
    register_default_loops,
    CONVERSATION_LOOP,
    TOOL_EXECUTION_LOOP,
    DANGER_RESPONSE_LOOP,
    MAINTENANCE_LOOP,
    DIAGNOSTIC_LOOP,
    LoopSequence,
    LoopSequenceRegistry,
    DAILY_MAINTENANCE_SEQ,
)
from meowcat.tools import (
    BUILTIN_TOOLS,
    PawsEngine,
    RiskLevel,
    Skill,
    SkillRegistry,
    SkillSpec,
    Tool,
    ToolRegistry,
    ToolSpec,
)
from meowcat import anatomy as anatomy
from meowcat import biology as biology
from meowcat import organ_roles as organ_roles
from meowcat.biology import (
    OrganSpec,
    ANOMALY_GROWTH,
    CORRECTION_GROWTH,
    CRYSTALLIZER,
    ROLE_EMERGENCE,
)
from meowcat.organ_roles import ORGAN_ROLES
import re
import pathlib

_pyproject = pathlib.Path(__file__).resolve().parent / "pyproject.toml"
_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']',
                   _pyproject.read_text(encoding="utf-8"), re.MULTILINE)
__version__ = _match.group(1) if _match else "0.0.0"


# -- 内置默认实现 ----------------------------------------------------------

__all__ = [
    # Protocols
    "OrchestratorProtocol", "SettingsProtocol", "OrganProtocol", "CatProtocol", "KittenProtocol", "BrainStemProtocol",
    "HippocampusProtocol", "ThalamusProtocol", "LLMBrainProtocol",
    "AdapterProtocol",
    "AmygdalaProtocol", "FrontalCortexProtocol", "HypothalamusProtocol",
    "CortexProtocol", "EarsProtocol", "EyesProtocol", "WhiskersProtocol",
    "GrowthProtocol",
    "PawsProtocol", "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol", "StageProtocol",
    "LLMProviderProtocol", "Diagnosable",
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
    "CatBase", "Colony", "EventBus", "Pipeline",
    # v0.5.9 子系统（组合 + 门面）
    "OrganHost", "Nervous", "ReflexArc", "assemble_default_cat",
    # v0.5.20 共享挂载
    "mount_known_organs",
    # 闭环事件名
    "LocateEvent", "RememberEvent", "OrchestrateEvent", "GrowthEvent",
    "Lifecycle", "KittenEvent", "NerveEvent", "ALL_EVENTS",
    # v0.5.1 神经系统
    "Wiring", "WiringSnapshot", "Organ", "Edge",
    "Reflex", "ReflexRegistry", "Trigger",
    "PerceptionContext", "Modality", "infer_modality",
    "anatomy", "biology", "OrganSpec",
    "ANOMALY_GROWTH", "CORRECTION_GROWTH",
    "CRYSTALLIZER", "ROLE_EMERGENCE",
    "organ_roles", "ORGAN_ROLES",
    # v0.5.11 器官基类
    "OrganMixin",
    # v0.5.22 新增原语
    "Stethoscope", "Needle", "NeedleDisabledError",
    # v1.0.3 wiring 可视化
    "render_wiring",
    # v0.5.27 原子路径
    "Path", "PathRegistry", "BUILTIN_PATHS", "register_builtin_paths",
    # v0.5.28a 链路
    "Chain", "ChainRegistry", "BUILTIN_CHAINS", "register_builtin_chains",
    "MEMORY_SEARCH_CHAIN", "FULL_REASONING_CHAIN",
    "TOOL_EXEC_CHAIN", "MAINTENANCE_CHAIN", "DIAGNOSTIC_CHAIN",
    # v0.5.28b 闭环
    "Loop", "LoopRegistry", "BUILTIN_LOOPS", "register_default_loops",
    "CONVERSATION_LOOP", "TOOL_EXECUTION_LOOP",
    "DANGER_RESPONSE_LOOP", "MAINTENANCE_LOOP", "DIAGNOSTIC_LOOP",
    # v1.0.4 元闭环
    "LoopSequence", "LoopSequenceRegistry", "DAILY_MAINTENANCE_SEQ",
    # v0.5.23 工具系统
    "Tool", "ToolSpec", "RiskLevel", "ToolRegistry",
    "Skill", "SkillSpec", "SkillRegistry",
    "BUILTIN_TOOLS", "PawsEngine",
    # 内置默认实现
    "create_cat",
    "NoopAmygdala", "NoopBrainstem", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopEars", "NoopEyes", "NoopWhiskers",
    "NoopMouth", "NoopPaws", "NoopPurr", "NoopTail",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
]
