# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat built-in default implementations — ready-to-use reference implementations.

All zero external dependencies (pure Python dict/list), for rapid prototyping and testing.
For production, replace with meowagent or custom real organ implementations.

v2.0: Default + Renovated merged into a single set of default organs.
"""

from meowcat.defaults.factory import _UNSET, create_cat
from meowcat.defaults.organs import (
    DefaultAmygdala,
    DefaultAnomalyGrowth,
    DefaultBrainstem,
    DefaultCerebellum,
    DefaultCerebrum,
    DefaultCorrectionGrowth,
    DefaultCortex,
    DefaultCrystallizer,
    DefaultEars,
    DefaultEyes,
    DefaultFrontal,
    DefaultHippocampus,
    DefaultHypothalamus,
    DefaultMouth,
    DefaultPaws,
    DefaultPurr,
    DefaultRoleEmergence,
    DefaultTail,
    DefaultThalamus,
    DefaultWhiskers,
)
from meowcat.defaults.presets import (
    KW_BILINGUAL,
    KW_EN,
    KW_ZH,
    PROMPT_DEFAULT,
    PROMPT_ZH,
    KeywordPreset,
    OrganPrompt,
    PromptPreset,
)
from meowcat.defaults.stages import (
    BaseStage,
    DefaultCompressStage,
    DefaultExecuteStage,
    DefaultIngestStage,
    DefaultLocateStage,
    DefaultPostStage,
    DefaultRouteStage,
    build_default_pipeline,
)
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
)

__all__ = [
    "create_cat",
    "_UNSET",
    "DefaultAmygdala",
    "DefaultBrainstem",
    "DefaultFrontal",
    "DefaultHypothalamus",
    "DefaultCortex",
    "DefaultCerebrum",
    "DefaultCerebellum",
    "DefaultEars",
    "DefaultEyes",
    "DefaultMouth",
    "DefaultPaws",
    "DefaultPurr",
    "DefaultTail",
    "DefaultWhiskers",
    "DefaultThalamus",
    "DefaultHippocampus",
    "DefaultAnomalyGrowth",
    "DefaultCorrectionGrowth",
    "DefaultCrystallizer",
    "DefaultRoleEmergence",
    # Keyword & Prompt presets
    "KeywordPreset",
    "PromptPreset",
    "OrganPrompt",
    "KW_EN",
    "KW_ZH",
    "KW_BILINGUAL",
    "PROMPT_DEFAULT",
    "PROMPT_ZH",
    # Pipeline Stages
    "BaseStage",
    "DefaultIngestStage",
    "DefaultLocateStage",
    "DefaultRouteStage",
    "DefaultExecuteStage",
    "DefaultPostStage",
    "DefaultCompressStage",
    "build_default_pipeline",
    "InMemoryGraphStore",
    "InMemoryL6Store",
    "InMemoryVectorStore",
    "InMemorySharedStore",
]
