# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat public API — centralized ``__all__`` and lazy-load mapping.

This module exists so ``import meowcat`` only loads this tiny file + ``__init__.py``.
All actual modules are imported on first attribute access via :func:`__getattr__`.
"""

from __future__ import annotations

# -- Public API surface -------------------------------------------------------
# fmt: off
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
    "PawsProtocol", "GraphStorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol", "StageProtocol",
    "LLMProviderProtocol", "Diagnosable",
    # Models
    "EntityShape", "ConnectionShape", "EpisodeShape", "FocusShape",
    "SubTaskShape", "TaskResultShape", "OrchestratorReportShape",
    "CandidateShape", "LocateResultShape", "MaintenanceReportShape",
    "StageEvent", "PipelineContext", "LoopEvent",
    "MergeProposalShape", "KittenCapability", "WorkflowShape", "ModelConfig",
    # v2.0 Models
    "TreeNode",
    # Errors
    "MeowCatError", "OrganNotMountedError", "LoopFailedError",
    "StageTimeoutError",
    "IllegalNeuralPathError", "ReflexPathInvalidError",
    "NoReflexMatchedError", "OrganProtocolMismatchError", "StandaloneCatError",
    "CircuitOpenError",
    "OrganDelegateError",
    # Skeleton
    "CatBase", "CatHook", "Colony", "ColonyConfig", "ColonyOwner", "ColonyRules", "EventBus", "Pipeline",
    # v0.5.9 Subsystems
    "OrganHost", "Nervous", "assemble_default_cat",
    # v0.5.20 Shared mount
    "mount_known_organs",
    # Loop event names
    "LocateEvent", "RememberEvent", "OrchestrateEvent", "GrowthEvent",
    "Lifecycle", "KittenEvent", "NerveEvent", "SelfEvent", "FusionEvent", "ALL_EVENTS",
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
    "DANGER_RESPONSE_LOOP", "MAINTENANCE_LOOP", "DIAGNOSTIC_LOOP",
    # v1.0.4 Loop sequences
    "LoopSequence", "LoopSequenceRegistry", "DAILY_MAINTENANCE_SEQ",
    # v0.5.23 Tools system
    "Tool", "ToolSpec", "RiskLevel", "ToolRegistry",
    "Skill", "SkillSpec", "SkillRegistry",
    "PawsEngine",
    # Builtin defaults
    "create_cat",
    "DefaultAmygdala", "DefaultBrainstem", "DefaultFrontal", "DefaultHypothalamus", "DefaultCortex",
    "DefaultCerebrum", "DefaultCerebellum",
    "DefaultEars", "DefaultEyes", "DefaultWhiskers",
    "DefaultMouth", "DefaultPaws", "DefaultPurr", "DefaultTail",
    "DefaultThalamus", "DefaultHippocampus",
    # v1.0.16 Growth organs
    "DefaultAnomalyGrowth", "DefaultCorrectionGrowth", "DefaultCrystallizer", "DefaultRoleEmergence",
    # v1.0.17 Pipeline Stages
    "BaseStage",
    "DefaultIngestStage", "DefaultLocateStage", "DefaultRouteStage",
    "DefaultExecuteStage", "DefaultPostStage", "DefaultCompressStage",
    "build_default_pipeline",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
    # v1.0.7 Pluggable
    "Pluggable",
    # v1.0.10 Gateway
    "Gateway", "SignalContext",
    "IoAdapterProtocol", "FrontDeskProtocol", "GatewayProtocol",
    "DefaultFrontDesk",
    # v1.0.13 Signal Middleware
    "SignalCall", "SignalMiddleware",
    "SignalLogger", "RateLimiter", "TimeoutGuard", "ContextInjector",
    "CircuitState",
    # v1.1.15 SKILL.md Loader
    "SkillLoader",
    # v1.1.16 General Tools
    "ChromaStore", "get_shared_client", "close_shared_client",
    # v1.1.17 Crystallizer
    "Crystallizer", "DefaultDetector",
    # v1.1.18 SharedStore + Log
    "SharedStore", "MeowLog",
    # v1.1.19 Persistent Storage
    "SqliteGraphStore", "JsonlL6Store", "JsonlEpisodeStore",
    # v1.1.20 Vector Store + Shared Memory
    "VectorStore", "SharedMemoryPool",
    # v1.1.22 Collective Growth + Emergence
    "CollectiveGrowth", "CollectiveEmergence",
    # v1.1.23 ScribblePad
    "ScribblePad", "DefaultScribbleFilter", "DefaultScribbleLogger",
    "DefaultScribblePersister",
    # v1.1.24 PinealGland
    "PinealGland", "Insight",
    "DefaultMerger", "DefaultContradiction", "DefaultInsightFilter",
    # v1.1.25 Cortex worldview L1
    "Cortex", "DefaultRuleExtractor",
    # v1.1.26 active growth
    "BlindSpotDetector", "ToolFailureLearner", "HotPathObserver",
    "ActiveGrowthPack",
    # v2.0 CatSelf + unified ReflectionLoop
    "CatSelf", "SelfSnapshot", "ReflectionLoop",
    # v1.1.29 skeleton abstraction
    "AsyncApprovalGate", "ApprovalRequest", "ApprovalStatus",  # deprecated v2.3.0
    "KeywordToolMatcher",
    "BaseWorker", "CheckpointStore", "InMemoryCheckpointStore",
    "WorkerState", "WorkerStatus", "WorkerScheduler",
    # v1.2.8 Presets
    "KeywordPreset", "PromptPreset", "OrganPrompt",
    "KW_EN", "KW_ZH", "KW_BILINGUAL",
    "PROMPT_DEFAULT", "PROMPT_ZH",
    "KW_PRESETS", "PROMPT_PRESETS",
    "ImplementationStyle",
    # v1.2.14 Organ adapters
    "AgentOrgan",
    "CerebrumAgent", "CerebellumAgent", "ThalamusAgent",
    "HippocampusAgent", "AmygdalaAgent", "BrainstemAgent",
    "FrontalAgent", "HypothalamusAgent", "CortexAgent",
    "EarsAgent", "EyesAgent", "WhiskersAgent", "PawsAgent",
    "MouthAgent", "PurrAgent", "TailAgent",
    # v1.2.21 Telemetry
    "SignalSpan", "Tracer", "Metrics",
    "TelemetryEvent",
    # v1.3.6 Model shelf
    "ProviderEntry", "BUILTIN_PROVIDERS", "ModelShelf", "FallbackChain",
    # v1.3.6 Compression manager
    "CompressionManager", "CompressionConfig",
    # v1.3.6 Remember policy
    "RememberPolicy", "RememberConfig",
    # v1.3.6 Clarify manager
    "ClarifyManager", "ClarifyConfig", "ClarifyResult",
    # v1.3.6 Budget tracker
    "BudgetTracker", "BudgetConfig",
    # v1.3.6 Noise filter
    "NoiseFilter", "NoiseFilterConfig",
    # v1.3.6 Topic closure detector
    "TopicClosureDetector", "TopicClosureConfig", "TopicClosureResult",
    # v1.3.6 Checkpoint store
    "CheckpointConfig", "JsonCheckpointStore",
    # v1.3.6 Focus store
    "FocusStore", "JsonFocusStore", "FocusState",
    # v1.3.6 Plan reviser
    "PlanReviser", "PlanReviserConfig", "RevisionStrategy", "RevisionContext", "RevisionResult",
    # v1.3.6 Task orchestrator
    "TaskOrchestrator", "TaskNode", "TaskStatus", "TaskResult", "TaskExecutor",
    # v1.3.6 Periodic scheduler
    "PeriodicScheduler", "PeriodicConfig", "PeriodicTask",
    # v2.1.0 RuleSet
    "Rule", "RuleSet",
    # v2.2.0 TaskPad + do_task + spawn_worker
    "TaskPad", "TaskItem", "TaskPadStatus",
    "ToolCall", "DoTaskResult", "XmlToolCallParser",
    # v2.5.0 Persona
    "Persona", "Belief", "KnowledgeSeed", "ConnectionSpec", "ReflexSpec",
]
# fmt: on


# -- Lazy import map: imported from _lazy_map.py (v1.3.9) ----------
from meowcat._lazy_map import _LAZY_MAP  # noqa: F401 (re-export for backward compat)

# — Submodule names (lazy via importlib) —
_SUBMODULES: frozenset[str] = frozenset({"anatomy", "biology", "organ_roles"})
