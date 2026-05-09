# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat built-in default implementations — ready-to-use reference implementations.

All zero external dependencies (pure Python dict/list), for rapid prototyping and testing.
For production, replace with meowagent or custom real organ implementations.

v2.0: Noop + Renovated merged into a single set of default organs.
"""

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
    "create_cat",
    "_UNSET",
    "NoopAmygdala",
    "NoopBrainstem",
    "NoopFrontal",
    "NoopHypothalamus",
    "NoopCortex",
    "NoopCerebrum",
    "NoopCerebellum",
    "NoopEars",
    "NoopEyes",
    "NoopMouth",
    "NoopPaws",
    "NoopPurr",
    "NoopTail",
    "NoopWhiskers",
    "NoopThalamus",
    "NoopHippocampus",
    "NoopAnomalyGrowth",
    "NoopCorrectionGrowth",
    "NoopCrystallizer",
    "NoopRoleEmergence",
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
    "NoopIngestStage",
    "NoopLocateStage",
    "NoopRouteStage",
    "NoopExecuteStage",
    "NoopPostStage",
    "NoopCompressStage",
    "build_default_pipeline",
    "InMemoryGraphStore",
    "InMemoryL6Store",
    "InMemoryVectorStore",
    "InMemorySharedStore",
]
