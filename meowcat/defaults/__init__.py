"""meowcat built-in default implementations — ready-to-use reference implementations.

All zero external dependencies (pure Python dict/list), for rapid prototyping and testing.
For production, replace with meowagent or custom real organ implementations.
"""
# (c) 2025-2026 Axonant. MIT License.


from meowcat.defaults.factory import _UNSET, create_cat
from meowcat.defaults.organs import (
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
)
from meowcat.defaults.presets import (
    KW_BILINGUAL, KW_EN, KW_EDUCATION, KW_FINANCE, KW_LEGAL, KW_MEDICAL, KW_TECH, KW_ZH,
    KW_PRESETS,
    KeywordPreset,
    PROMPT_DEFAULT, PROMPT_EDUCATION, PROMPT_FINANCE, PROMPT_LEGAL, PROMPT_MEDICAL, PROMPT_TECH, PROMPT_ZH,
    PROMPT_PRESETS,
    PromptPreset,
)
from meowcat.defaults.renovated import (
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
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
)

__all__ = [
    "create_cat", "_UNSET",
    "NoopAmygdala", "NoopBrainstem", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopCerebrum", "NoopCerebellum",
    "NoopEars", "NoopEyes", "NoopMouth", "NoopPaws", "NoopPurr", "NoopTail", "NoopWhiskers",
    "NoopThalamus", "NoopHippocampus",
    # v1.0.16 Growth organs
    "NoopAnomalyGrowth", "NoopCorrectionGrowth", "NoopCrystallizer", "NoopRoleEmergence",
    # Renovated organs (简装修)
    "RenovatedAmygdala", "RenovatedBrainstem", "RenovatedFrontal",
    "RenovatedHypothalamus", "RenovatedCortex",
    "RenovatedCerebrum", "RenovatedCerebellum",
    "RenovatedEars", "RenovatedEyes", "RenovatedMouth", "RenovatedPaws",
    "RenovatedPurr", "RenovatedTail", "RenovatedWhiskers",
    "RenovatedThalamus", "RenovatedHippocampus",
    "RenovatedAnomalyGrowth", "RenovatedCorrectionGrowth",
    "RenovatedCrystallizer", "RenovatedRoleEmergence",
    "RENOVATED_ORGAN_MAP",
    # Keyword & Prompt presets (二语 行业 可挂载)
    "KeywordPreset", "PromptPreset",
    "KW_EN", "KW_ZH", "KW_BILINGUAL",
    "KW_TECH", "KW_FINANCE", "KW_MEDICAL", "KW_LEGAL", "KW_EDUCATION",
    "PROMPT_DEFAULT", "PROMPT_ZH",
    "PROMPT_TECH", "PROMPT_FINANCE", "PROMPT_MEDICAL", "PROMPT_LEGAL", "PROMPT_EDUCATION",
    "KW_PRESETS", "PROMPT_PRESETS",
    # v1.0.17 Pipeline Stages
    "BaseStage",
    "NoopIngestStage", "NoopLocateStage", "NoopRouteStage",
    "NoopExecuteStage", "NoopPostStage", "NoopCompressStage",
    "build_default_pipeline",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
]
