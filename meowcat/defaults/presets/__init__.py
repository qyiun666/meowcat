# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat keyword & prompt presets — bilingual base presets, user-customizable.

二语 可挂载:
  关键词预设 → 注入 Ears/Thalamus/Amygdala/Frontal
  提示词预设 → 注入 Brainstem/Cerebrum
"""

from meowcat.defaults.presets._classes import (
    KeywordPreset,
    OrganPrompt,
    PromptPreset,
)
from meowcat.defaults.presets._data import (
    KW_BILINGUAL,
    KW_EN,
    KW_PRESETS,
    KW_ZH,
    PROMPT_DEFAULT,
    PROMPT_PRESETS,
    PROMPT_ZH,
)

__all__ = [
    "KeywordPreset",
    "PromptPreset",
    "OrganPrompt",
    "KW_EN",
    "KW_ZH",
    "KW_BILINGUAL",
    "PROMPT_DEFAULT",
    "PROMPT_ZH",
    "KW_PRESETS",
    "PROMPT_PRESETS",
]
