"""meowcat — An agent framework built on the biological blueprint of a cat. Depends on pydantic>=2.0 + anyio>=4.0, zero meowagent imports."""
# (c) 2025-2026 Axonant. MIT License.


from meowcat.defaults import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
    NoopAmygdala,
    NoopAnomalyGrowth,
    NoopBrainstem,
    NoopCerebellum,
    NoopCerebrum,
    NoopCorrectionGrowth,
    NoopCortex,
    NoopCrystallizer,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopRoleEmergence,
    NoopTail,
    NoopThalamus,
    NoopWhiskers,
    RENOVATED_ORGAN_MAP,
    RenovatedAmygdala,
    RenovatedAnomalyGrowth,
    RenovatedBrainstem,
    RenovatedCerebellum,
    RenovatedCerebrum,
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
    _UNSET,
    create_cat,
)
from meowcat.defaults.stages import (
    BaseStage,
    NoopCompressStage,
    NoopExecuteStage,
    NoopIngestStage,
    NoopLocateStage,
    NoopPostStage,
    NoopRouteStage,
    build_default_pipeline,
)
from meowcat.wiring import Edge, Organ, Wiring, WiringSnapshot
from meowcat.anatomy import ImplementationStyle
from meowcat.reflex import BUILTIN_REFLEX_PATHS, Reflex, ReflexArc, ReflexRegistry, Trigger
from meowcat.host import OrganHost
from meowcat.nervous import Nervous, SignalCall, SignalMiddleware
from meowcat.middleware import (
    ContextInjector,
    RateLimiter,
    SignalLogger,
    TimeoutGuard,
)
from meowcat.pluggable import Pluggable
from meowcat.organ_base import OrganMixin
from meowcat.protocols import (
    AdapterProtocol,
    AmygdalaProtocol,
    AnomalyGrowthProtocol,
    BrainStemProtocol,
    CatProtocol,
    CorrectionGrowthProtocol,
    CortexProtocol,
    CrystallizerProtocol,
    Diagnosable,
    EarsProtocol,
    EyesProtocol,
    FederationTransport,
    FrontalCortexProtocol,
    GraphStorageProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    KittenProtocol,
    L6StorageProtocol,
    LLMBrainProtocol,
    LLMProviderProtocol,
    MouthProtocol,
    OrchestratorProtocol,
    OrganProtocol,
    PawsProtocol,
    PurrProtocol,
    RoleEmergenceProtocol,
    SecurityPolicyProtocol,
    SettingsProtocol,
    SharedStorageProtocol,
    StageProtocol,
    TailProtocol,
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
    WorkflowShape,
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
from meowcat.assembly import CatBase, CatHook, assemble_default_cat, mount_known_organs
from meowcat.colony import Colony
from meowcat.colony_transports import TCPSocketTransport, RedisPubSubTransport
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
    WORKFLOW_CHAIN,
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
from meowcat.gateway import (
    CliAdapter,
    Gateway,
    HttpAdapter,
    IpcAdapter,
    WebhookAdapter,
    WsAdapter,
)
from meowcat.gateway.protocol import SignalContext, IoAdapterProtocol, GatewayProtocol
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

_pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']',
                   _pyproject.read_text(encoding="utf-8"), re.MULTILINE)
__version__ = _match.group(1) if _match else "0.0.0"


# -- Builtin Defaults ----------------------------------------------------------

__all__ = [
    # Protocols
    "OrchestratorProtocol", "SettingsProtocol", "OrganProtocol", "CatProtocol", "KittenProtocol", "BrainStemProtocol",
    "HippocampusProtocol", "ThalamusProtocol", "LLMBrainProtocol",
    "AdapterProtocol",
    "AmygdalaProtocol", "FrontalCortexProtocol", "HypothalamusProtocol",
    "CortexProtocol", "EarsProtocol", "EyesProtocol", "WhiskersProtocol",
    "MouthProtocol", "PurrProtocol", "TailProtocol",
    "AnomalyGrowthProtocol", "CorrectionGrowthProtocol",
    "CrystallizerProtocol", "RoleEmergenceProtocol",
    "SecurityPolicyProtocol",
    "PawsProtocol", "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol", "StageProtocol",
    "LLMProviderProtocol", "Diagnosable",
    # Models
    "EntityShape", "ConnectionShape", "EpisodeShape", "FocusShape",
    "SubTaskShape", "TaskResultShape", "OrchestratorReportShape",
    "CandidateShape", "LocateResultShape", "MaintenanceReportShape",
    "StageEvent", "PipelineContext", "LoopEvent",
    "MergeProposalShape", "KittenCapability", "WorkflowShape",
    # Errors
    "MeowCatError", "OrganNotMountedError", "LoopFailedError",
    "StageTimeoutError",
    "IllegalNeuralPathError", "ReflexPathInvalidError",
    "NoReflexMatchedError", "OrganProtocolMismatchError",
    # Skeleton
    "CatBase", "CatHook", "Colony", "EventBus", "Pipeline",
    # v0.5.9 Subsystems (composite + facade)
    "OrganHost", "Nervous", "ReflexArc", "assemble_default_cat",
    # v0.5.20 Shared mount
    "mount_known_organs",
    # Loop event names
    "LocateEvent", "RememberEvent", "OrchestrateEvent", "GrowthEvent",
    "Lifecycle", "KittenEvent", "NerveEvent", "ALL_EVENTS",
    # v0.5.1 Nervous system
    "Wiring", "WiringSnapshot", "Organ", "Edge",
    "Reflex", "ReflexArc", "ReflexRegistry", "Trigger",
    "BUILTIN_REFLEX_PATHS",
    "PerceptionContext", "Modality", "infer_modality",
    "anatomy", "biology", "OrganSpec",
    "ANOMALY_GROWTH", "CORRECTION_GROWTH",
    "CRYSTALLIZER", "ROLE_EMERGENCE",
    "organ_roles", "ORGAN_ROLES",
    # v0.5.11 Organ base class
    "OrganMixin",
    # v0.5.22 New primitives
    "Stethoscope", "Needle", "NeedleDisabledError",
    # v1.0.3 Wiring visualization
    "render_wiring",
    # v0.5.27 Atomic paths
    "Path", "PathRegistry", "BUILTIN_PATHS", "register_builtin_paths",
    # v0.5.28a Chains
    "Chain", "ChainRegistry", "BUILTIN_CHAINS", "register_builtin_chains",
    "MEMORY_SEARCH_CHAIN", "FULL_REASONING_CHAIN",
    "TOOL_EXEC_CHAIN", "MAINTENANCE_CHAIN", "DIAGNOSTIC_CHAIN",
    "WORKFLOW_CHAIN",
    # v0.5.28b Loops
    "Loop", "LoopRegistry", "BUILTIN_LOOPS", "register_default_loops",
    "CONVERSATION_LOOP", "TOOL_EXECUTION_LOOP",
    "DANGER_RESPONSE_LOOP", "MAINTENANCE_LOOP", "DIAGNOSTIC_LOOP",
    # v1.0.4 Loop sequences
    "LoopSequence", "LoopSequenceRegistry", "DAILY_MAINTENANCE_SEQ",
    # v0.5.23 Tools system
    "Tool", "ToolSpec", "RiskLevel", "ToolRegistry",
    "Skill", "SkillSpec", "SkillRegistry",
    "BUILTIN_TOOLS", "PawsEngine",
    # Builtin defaults
    "create_cat",
    "NoopAmygdala", "NoopBrainstem", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopCerebrum", "NoopCerebellum",
    "NoopEars", "NoopEyes", "NoopWhiskers",
    "NoopMouth", "NoopPaws", "NoopPurr", "NoopTail",
    "NoopThalamus", "NoopHippocampus",
    # v1.0.16 Growth organs
    "NoopAnomalyGrowth", "NoopCorrectionGrowth", "NoopCrystallizer", "NoopRoleEmergence",
    # v1.0.17 Pipeline Stages
    "BaseStage",
    "NoopIngestStage", "NoopLocateStage", "NoopRouteStage",
    "NoopExecuteStage", "NoopPostStage", "NoopCompressStage",
    "build_default_pipeline",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
    # v1.0.7 Pluggable
    "Pluggable",
    # v1.0.12 Colony federation
    "FederationTransport", "TCPSocketTransport", "RedisPubSubTransport",
    # v1.0.10 Gateway
    "Gateway", "SignalContext",
    "IoAdapterProtocol", "GatewayProtocol",
    "HttpAdapter", "WsAdapter", "WebhookAdapter", "CliAdapter", "IpcAdapter",
    # v1.0.13 Signal Middleware
    "SignalCall", "SignalMiddleware",
    "SignalLogger", "RateLimiter", "TimeoutGuard", "ContextInjector",
]
