# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) brainstem — customizable system prompt builder with lifecycle logging."""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import NoopBrainstem
from meowcat.defaults.presets import (
    PROMPT_DEFAULT,
    OrganPrompt,
    PromptPreset,
)


class RenovatedBrainstem(NoopBrainstem):
    """简装修 brainstem: customizable system prompt builder + lifecycle logging.

    v1.3.6: 新增 per-organ prompt 拼装链路 + CatSelf 自动注入。

    Accepts a :class:`PromptPreset` for route-specific prompt templates,
    pre/post prompts, and variable substitution. Accepts
    ``organ_prompts`` dict mapping organ name → :class:`OrganPrompt`
    for per-organ identity/perspective/output_format injection.

    7-step assembly chain:
        1. Plugin override (full replacement)
        2. PromptPreset.pre_prompt
        3. OrganPrompt.identity + perspective
        4. Route template (OrganPrompt → PromptPreset → fallback)
        5. CatSelf injection (personality + beliefs + capabilities)
        6. OrganPrompt.output_format
        7. PromptPreset.post_prompt

    Variable substitution: {name}, {language}, {domain}, {route}, {organ}, {tone}
    """

    name: str = "renovated_brainstem"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    # ── v1.3.6: CatSelf injection control ──
    inject_cat_self: bool = True

    def __init__(
        self,
        prompt: PromptPreset | None = None,
        cat_name: str = "MeowCat",
        language: str = "zh/en",
        domain: str = "general",
        organ_prompts: dict[str, OrganPrompt] | None = None,
    ) -> None:
        NoopBrainstem.__init__(self)
        self._prompt = prompt or PROMPT_DEFAULT
        self._cat_name = cat_name
        self._language = language
        self._domain = domain
        self._organ_prompts = organ_prompts or {}
        self._start_time: float = _time.time()

    @property
    def organ_prompts(self) -> dict[str, OrganPrompt]:
        """Per-organ prompt slot map (v1.3.6)."""
        return self._organ_prompts

    def diagnose(self) -> dict[str, Any]:
        return {
            "uptime_seconds": _time.time() - self._start_time,
            "organ": "brainstem",
            "renovated": True,
            "prompt_preset": self._prompt.name,
            "organ_prompts": list(self._organ_prompts.keys()),
            "inject_cat_self": self.inject_cat_self,
        }

    async def build_system_prompt(
        self,
        organ: str,
        route: str,
        cat_self_snapshot: Any | None = None,
    ) -> str:
        """Build system prompt with 7-step assembly chain (v1.3.6).

        Args:
            organ: Organ name, e.g. ``"cerebrum"``, ``"cerebellum"``.
            route: Route name, e.g. ``"chat"``, ``"tool"``.
            cat_self_snapshot: Optional :class:`SelfSnapshot` for
                CatSelf injection. ``None`` skips injection.

        Returns:
            Assembled system prompt string.
        """
        parts: list[str] = []

        # 1. Plugin chain (allow full override)
        async for _name, r in self._run_plugs(
            "build_system_prompt",
            organ,
            route,
            cat_self_snapshot,
        ):
            if isinstance(r, str) and r:
                parts.append(r)
        if parts:
            return "\n".join(parts)

        # 2. PromptPreset.pre_prompt
        if self._prompt.pre_prompt:
            parts.append(self._fill_vars(self._prompt.pre_prompt))

        # 3. OrganPrompt identity + perspective
        op = self._organ_prompts.get(organ)
        if op is not None:
            if op.identity:
                parts.append(self._fill_vars(op.identity))
            if op.perspective:
                parts.append(self._fill_vars(op.perspective))

        # 4. Route template (OrganPrompt override → PromptPreset → fallback)
        route_tmpl: str = ""
        if op is not None:
            route_tmpl = op.route_templates.get(route, "")
        if not route_tmpl:
            route_tmpl = self._prompt.templates.get(
                route, self._prompt.fallback)
        if not route_tmpl:
            route_tmpl = "You are MeowCat, a helpful AI assistant."
        parts.append(self._fill_vars(route_tmpl))

        # 5. CatSelf injection
        if self.inject_cat_self and cat_self_snapshot is not None:
            parts.append(self._inject_cat_self(cat_self_snapshot))

        # 6. OrganPrompt.output_format
        if op is not None and op.output_format:
            parts.append(self._fill_vars(op.output_format))

        # 7. PromptPreset.post_prompt
        if self._prompt.post_prompt:
            parts.append(self._fill_vars(self._prompt.post_prompt))

        return "\n\n".join(parts)

    # ── Helpers ────────────────────────────────────────────────────

    def _fill_vars(self, template: str) -> str:
        """Substitute {name} {language} {domain} {route} {organ} variables."""
        return (
            template.replace("{name}", self._cat_name)
            .replace("{language}", self._language)
            .replace("{domain}", self._domain)
        )

    def _inject_cat_self(self, snap: Any) -> str:
        """Generate CatSelf injection block from snapshot.

        Reads personality, beliefs (Cortex L2), and capabilities
        (Metacognition L3) from the snapshot and formats them
        as a self-awareness block.  Language-aware: uses Chinese
        labels when ``_language`` starts with ``"zh"``, English otherwise.
        """
        is_zh = (self._language or "").startswith("zh")

        lines: list[str] = []
        lines = ["## 自我认知", ""] if is_zh else ["## Self-Awareness", ""]

        # Personality
        personality = getattr(snap, "personality", None) or {}
        tone = personality.get("tone", "")
        lang = personality.get("language", "")
        if tone and lang:
            if is_zh:
                lines.append(f"性格：{tone} 的语气，使用 {lang} 交流。")
            else:
                lines.append(
                    f"Personality: {tone} tone, communicates in {lang}.")
        elif tone:
            if is_zh:
                lines.append(f"性格：{tone} 的语气。")
            else:
                lines.append(f"Personality: {tone} tone.")

        # Beliefs (Cortex L2)
        beliefs = getattr(snap, "beliefs", None) or []
        if beliefs:
            lines.append("")
            if is_zh:
                lines.append("坚信的法则：")
            else:
                lines.append("Core Beliefs:")
            for item in beliefs[:10]:
                if isinstance(item, (tuple, list)) and len(item) >= 2:
                    value = str(item[1])
                    conf = item[2] if len(item) >= 3 else 1.0
                    if is_zh:
                        lines.append(f"- {value} (确信度: {conf:.0%})")
                    else:
                        lines.append(f"- {value} (confidence: {conf:.0%})")

        # Capable domains (Metacognition L3)
        capable = getattr(snap, "capable_domains", None) or []
        if capable:
            lines.append("")
            domains = ", ".join(str(d) for d in capable[:10])
            if is_zh:
                lines.append(f"擅长的领域：{domains}")
            else:
                lines.append(f"Capable domains: {domains}")

        # Incapable domains
        incapable = getattr(snap, "incapable_domains", None) or []
        if incapable:
            domains = ", ".join(str(d) for d in incapable[:10])
            if is_zh:
                lines.append(f"不擅长的领域：{domains}")
            else:
                lines.append(f"Incapable domains: {domains}")

        return "\n".join(lines)
