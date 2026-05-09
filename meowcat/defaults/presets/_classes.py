# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat preset dataclass definitions — KeywordPreset, PromptPreset, OrganPrompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# =========================================================================
# KeywordPreset — 关键词预设 (挂载到 Ears/Thalamus/Amygdala/Frontal)
# =========================================================================


@dataclass
class KeywordPreset:
    """关键词预设 — language, domain, and safety keyword configuration.

    Mounted into: RenovatedEars, RenovatedThalamus, RenovatedAmygdala, RenovatedFrontal.
    Each organ picks the subset it needs (stop_words → Ears, commands → Thalamus, etc.)

    Attributes:
        name: Preset identifier, e.g. ``"zh_tech"``
        stop_words: Keywords to filter out during extraction
        command_patterns: ``{trigger_word: route}`` routing map
        danger_patterns: Compiled regex patterns for safety scanning
        topic_keywords: Domain-specific topic keywords by category
        priority_keywords: High-priority keywords that always match first
    """

    name: str = ""
    stop_words: frozenset[str] = field(default_factory=frozenset)
    command_patterns: dict[str, str] = field(default_factory=dict)
    danger_patterns: list[re.Pattern] = field(default_factory=list)
    topic_keywords: dict[str, list[str]] = field(default_factory=dict)
    priority_keywords: list[str] = field(default_factory=list)

    def merge(self, other: KeywordPreset) -> KeywordPreset:
        """Merge another preset into this one (other takes priority on conflict)."""
        return KeywordPreset(
            name=f"{self.name}+{other.name}",
            stop_words=self.stop_words | other.stop_words,
            command_patterns={**self.command_patterns, **other.command_patterns},
            danger_patterns=self.danger_patterns + other.danger_patterns,
            topic_keywords={**self.topic_keywords, **other.topic_keywords},
            priority_keywords=self.priority_keywords + other.priority_keywords,
        )


# =========================================================================
# PromptPreset — 提示词预设 (挂载到 Brainstem/Cerebrum)
# =========================================================================


@dataclass
class PromptPreset:
    """提示词预设 — system prompt templates by route, project, or industry.

    Mounted into: RenovatedBrainstem, RenovatedCerebrum.

    Attributes:
        name: Preset identifier, e.g. ``"zh_medical"``
        templates: ``{route: prompt_template}`` — variables: {name}, {language}, {domain}
        fallback: Default template when no route match
        pre_prompt: Prepended before every system prompt (e.g. role, constraints)
        post_prompt: Appended after every system prompt (e.g. safety instructions)
    """

    name: str = ""
    templates: dict[str, str] = field(default_factory=dict)
    fallback: str = ""
    pre_prompt: str = ""
    post_prompt: str = ""

    def build(self, route: str, **variables: str) -> str:
        """Build a system prompt for the given route with variable substitution."""
        template = self.templates.get(route, self.fallback)
        if not template:
            template = "You are MeowCat, a helpful AI assistant."
        prompt = template
        for key, val in variables.items():
            prompt = prompt.replace(f"{{{key}}}", val)
        parts = []
        if self.pre_prompt:
            parts.append(self.pre_prompt)
        parts.append(prompt)
        if self.post_prompt:
            parts.append(self.post_prompt)
        return "\n".join(parts)

    def merge(self, other: PromptPreset) -> PromptPreset:
        """Merge another preset into this one (other takes priority on conflict)."""
        return PromptPreset(
            name=f"{self.name}+{other.name}",
            templates={**self.templates, **other.templates},
            fallback=other.fallback or self.fallback,
            pre_prompt=self.pre_prompt + "\n" + other.pre_prompt
            if other.pre_prompt
            else self.pre_prompt,
            post_prompt=self.post_prompt + "\n" + other.post_prompt
            if other.post_prompt
            else self.post_prompt,
        )


# =========================================================================
# OrganPrompt — per-organ 提示词插槽 (v1.3.6 挂载到 Cerebrum/Cerebellum)
# =========================================================================


@dataclass
class OrganPrompt:
    """Per-organ prompt slot — 每个 LLM 器官的提示词配置.

    v1.3.6: 框架层定义插槽形状。应用层填充内容。
    每个 LLM-bearing 器官（cerebrum/cerebellum）挂一个 OrganPrompt 实例。

    Attributes:
        identity: 身份描述，这个器官是谁、承担什么角色.
            e.g. ``"你是 {name} 的大脑皮层，负责深度推理和决策。"``
        perspective: 视角声明，这个器官以什么视角看世界.
            e.g. ``"你可以访问所有工具和记忆。"``
        output_format: 输出格式约束，期望的输出结构.
            e.g. ``"<thinking>...</thinking>\\n<response>...</response>"``
        route_templates: per-route 模板覆盖（可选），覆盖 PromptPreset 的路由模板.
            e.g. ``{"chat": "...", "tool": "..."}``
    """

    identity: str = ""
    perspective: str = ""
    output_format: str = ""
    route_templates: dict[str, str] = field(default_factory=dict)
