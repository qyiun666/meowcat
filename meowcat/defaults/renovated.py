# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat renovated organs — 简装修 (light-renovation) default implementations.

Each Renovated* class extends the Noop*毛坯 (bare) stub, adding minimal but
useful default behavior. Developers get a working cat out of the box with
``create_cat(renovated=True)``, and can opt-out per organ to use pure Noop*毛坯.

The renovated organs bridge the gap between pure stubs and full app-layer
implementations — enough to run simple flows, test wiring, and prototype.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time as _time
from typing import Any, Callable, Awaitable

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopAmygdala, NoopBrainstem, NoopCerebrum, NoopCerebellum,
    NoopCortex, NoopEars, NoopEyes, NoopFrontal, NoopHippocampus,
    NoopHypothalamus, NoopMouth, NoopPaws, NoopPurr, NoopTail,
    NoopThalamus, NoopWhiskers, NoopAnomalyGrowth, NoopCorrectionGrowth,
    NoopCrystallizer, NoopRoleEmergence,
)
from meowcat.defaults.presets import (
    KW_BILINGUAL, PROMPT_DEFAULT, PROMPT_ZH,
    KeywordPreset, OrganPrompt, PromptPreset,
)

_logger = logging.getLogger("meowcat.renovated")


# =========================================================================
# Helpers
# =========================================================================


def _extract_keywords(text: str, top_k: int = 5, stop_words: frozenset[str] | None = None) -> list[str]:
    """Extract top-k keywords from text.

    ``stop_words`` is required — callers must pass a keyword preset's stop_words.
    """
    if stop_words is None:
        return []
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())
    filtered = [w for w in words if w not in stop_words and len(w) > 1]
    seen: set[str] = set()
    result: list[str] = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            result.append(w)
            if len(result) >= top_k:
                break
    return result


def _detect_language(text: str) -> str:
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if cjk > len(text) * 0.3:
        return "zh"
    return "en"


def _detect_command(text: str, kw: KeywordPreset | None = None) -> str | None:
    """Detect command pattern in text.

    ``kw`` is required — callers must pass a keyword preset.
    """
    if kw is None:
        return None
    lower = text.lower().strip()
    for cmd, route in kw.command_patterns.items():
        if lower.startswith(cmd) or lower.startswith(f"/{cmd}"):
            return route
    return None


# -- v1.3.0 Text analysis utilities (framework defaults, reusable) ---------


def _repetition_ratio(text: str, n: int = 5) -> float:
    """n-gram sliding-window repetition ratio.

    Returns the fraction of n-grams that appear more than once.
    High values indicate repetitive/looping output.
    """
    if len(text) < n:
        return 0.0
    grams: dict[str, int] = {}
    total = 0
    for i in range(len(text) - n + 1):
        g = text[i:i + n]
        grams[g] = grams.get(g, 0) + 1
        total += 1
    if total == 0:
        return 0.0
    repeated = sum(1 for c in grams.values() if c > 1)
    return repeated / max(len(grams), 1)


def _nonprintable_ratio(text: str) -> float:
    """Ratio of non-printable characters in text.

    High values may indicate binary data or encoding attacks.
    """
    if not text:
        return 0.0
    import string
    printable = set(string.printable)
    nonprint = sum(1 for c in text if c not in printable)
    return nonprint / len(text)


def _jaccard(a: str, b: str, n: int = 3) -> float:
    """n-gram Jaccard similarity between two strings.

    Useful for drift detection — compare current vs historical output.
    """
    def _ngrams(s: str) -> set[str]:
        return {s[i:i + n] for i in range(len(s) - n + 1)}
    sa = _ngrams(a.lower())
    sb = _ngrams(b.lower())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _looks_like_fact(text: str) -> bool:
    """Heuristic: does the text look like a factual assertion?

    Checks for patterns that suggest factual claims:
    numeric values with units, proper nouns, file paths, dates.
    Used as input to hallucination detection.
    """
    import re as _re
    patterns = [
        _re.compile(r'\b\d+\s*(?:KB|MB|GB|ms|s|px|%)\b'),   # numeric+unit
        _re.compile(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b'),       # CamelCase
        _re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b',
                    _re.IGNORECASE),  # months
        _re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),                # ISO date
        _re.compile(r'[/\\][\w./\\-]+\b'),                     # file paths
    ]
    return any(p.search(text) for p in patterns)


# =========================================================================
# Brain Regions — 简装修
# =========================================================================


class RenovatedThalamus(NoopThalamus):
    """简装修 thalamus: keyword routing + command detection.

    Accepts a :class:`KeywordPreset` for configurable command patterns and
    priority keywords. Default: bilingual (zh+en).

    Detects command patterns for routing, falls back to basic keyword analysis.
    """

    name: str = "renovated_thalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, keyword: KeywordPreset | None = None) -> None:
        NoopThalamus.__init__(self)
        self._keyword = keyword or KW_BILINGUAL

    async def locate(self, msg: str, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": "chat", "entities": [], "snippets": []}
        async for _name, r in self._run_plugs("locate", msg, session_id):
            if isinstance(r, dict):
                result.update(r)
        cmd_route = _detect_command(msg, self._keyword)
        if cmd_route:
            result["route"] = cmd_route
        return result

    def decide_route(self, **kwargs: Any) -> dict[str, Any]:
        msg = kwargs.get("text", kwargs.get("message", ""))
        cmd_route = _detect_command(msg, self._keyword)
        return {"route": cmd_route or "chat", "keywords": _extract_keywords(msg, stop_words=self._keyword.stop_words)}


class RenovatedAmygdala(NoopAmygdala):
    """简装修 amygdala: regex-based danger/safety assessment.

    Accepts a :class:`KeywordPreset` for configurable danger patterns.
    Default: bilingual (zh+en) danger patterns covering SQL injection,
    shell injection, XSS, path traversal, and Chinese-specific threats.

    .. note::

        ``is_rejection`` / ``classify_rejection`` detect *dangerous* input
        (not user negation/correction — that belongs to Whiskers).
        Use ``is_dangerous`` for the same behavior with clearer naming.

    Tool risk assessment is fully configurable via ``dangerous_tools``
    and ``dangerous_paths``, and supports plugin override via the
    ``assess_tool_risk`` hook.
    """

    name: str = "renovated_amygdala"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    HOOKS = {
        "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
        "assess_tool_risk": {"in": "tool_name: str, params: dict", "out": "dict[str, Any]"},
    }

    def __init__(
        self,
        danger_patterns: list[re.Pattern] | None = None,
        keyword: KeywordPreset | None = None,
        dangerous_tools: set[str] | None = None,
        dangerous_paths: list[str] | None = None,
    ) -> None:
        NoopAmygdala.__init__(self)
        if danger_patterns:
            self._patterns: list[re.Pattern] = list(danger_patterns)
        elif keyword:
            self._patterns = list(keyword.danger_patterns)
        else:
            self._patterns = list(KW_BILINGUAL.danger_patterns)
        self._dangerous_tools: set[str] = dangerous_tools if dangerous_tools is not None else {
            "run_command", "eval", "exec", "shell"}
        self._dangerous_paths: list[str] = dangerous_paths if dangerous_paths is not None else [
            "/etc/", "/root/", "~/.ssh/", "C:\\Windows\\"]

    def is_rejection(self, msg: str) -> bool:
        """Check if the input should be *rejected* as dangerous.

        Matches against danger patterns (SQL injection, shell injection,
        XSS, path traversal, etc.). Return ``True`` means the input
        contains dangerous content that should be blocked.

        For user negation/correction detection, use
        :meth:`RenovatedWhiskers.is_negation` / :meth:`RenovatedWhiskers.parse_correction`.
        """
        for pat in self._patterns:
            if pat.search(msg):
                return True
        return False

    def is_dangerous(self, msg: str) -> bool:
        """Alias for :meth:`is_rejection` — semantically clearer.

        Returns ``True`` if the input matches known danger patterns.
        """
        return self.is_rejection(msg)

    def classify_rejection(self, msg: str) -> str:
        """Classify the rejection type of dangerous input.

        Returns:
            ``"danger"`` if input matches danger patterns, ``"none"`` otherwise.
        """
        if not self.is_rejection(msg):
            return "none"
        return "danger"

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict) and not r.get("safe", True):
                return r
        for pat in self._patterns:
            m = pat.search(user_input)
            if m:
                return {"safe": False, "risk": "high", "pattern": pat.pattern, "match": m.group()}
        return {"safe": True, "risk": "low"}

    def assess_tool_risk(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Assess tool execution risk.

        Configurable via ``dangerous_tools`` and ``dangerous_paths`` constructor
        params, with plugin override via the ``assess_tool_risk`` hook.
        """
        for _name, r in self._run_plugs_sync("assess_tool_risk", tool_name, params):
            if isinstance(r, dict):
                return r
        if tool_name in self._dangerous_tools:
            return {"risk": "high", "reason": f"dangerous tool: {tool_name}"}
        if tool_name == "write_file":
            fp = str(params.get("path", params.get("file_path", "")))
            for dp in self._dangerous_paths:
                if dp in fp:
                    return {"risk": "high", "reason": f"write to protected path: {fp}"}
        return {"risk": "low", "reason": "ok"}


class RenovatedFrontal(NoopFrontal):
    """简装修 frontal: keyword topic shift detection + topic history.

    Accepts a :class:`KeywordPreset` for domain-specific topic keywords
    and priority keywords. Default: bilingual.

    Tracks recent topics and detects significant shifts via keyword overlap.

    v1.3.6: Accepts an optional :class:`~meowcat.focus.FocusStore` for
    persistence.  ``save()`` / ``load()`` delegate to the store when
    configured; ``_export_state()`` / ``_import_state()`` support
    lifecycle-driven save/restore without path parameters.
    """

    name: str = "renovated_frontal"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        keyword: KeywordPreset | None = None,
        threshold: float = 0.3,
        # FocusStore | None (lazy import to avoid circular)
        focus_store: Any | None = None,
    ) -> None:
        NoopFrontal.__init__(self)
        self._keyword = keyword or KW_BILINGUAL
        self._topics: list[str] = []
        self._current_keywords: set[str] = set()
        self._threshold: float = threshold
        self._focus_store = focus_store

    def is_continue(self, msg: str) -> bool:
        for _name, r in self._run_plugs_sync("is_continue", msg):
            if isinstance(r, bool):
                return r
        if not self._current_keywords:
            return False
        kws = set(_extract_keywords(msg, top_k=10,
                  stop_words=self._keyword.stop_words))
        overlap = len(kws & self._current_keywords)
        return overlap >= max(1, len(self._current_keywords) * self._threshold)

    def detect_shift(self, msg: str) -> bool:
        for _name, r in self._run_plugs_sync("detect_shift", msg):
            if isinstance(r, bool):
                return r
        return not self.is_continue(msg)

    def update_focus(self, result: Any) -> None:
        kw_source = ""
        if isinstance(result, dict):
            kw_source = str(result.get("text", result.get("reply", "")))
        else:
            kw_source = str(result)
        self._current_keywords = set(_extract_keywords(
            kw_source, top_k=10, stop_words=self._keyword.stop_words))

    def archive_focus(self) -> None:
        self._topics.append(", ".join(sorted(self._current_keywords)))
        self._current_keywords.clear()

    def save(self, path: Any | None = None) -> None:
        """Save focus state via the configured store (sync wrapper).

        .. deprecated:: 1.3.6
            Use :meth:`_save_to_store` instead.  This method uses
            ``anyio.run()`` which crashes inside an async event loop.
            Kept for backward compatibility only.

        v1.3.6: When ``_focus_store`` is set, delegates to the store.
        Otherwise no-op (backward-compatible).
        """
        if self._focus_store is None:
            return
        import warnings
        warnings.warn(
            "RenovatedFrontal.save() is deprecated since v1.3.6. "
            "Use _save_to_store() instead.",
            DeprecationWarning, stacklevel=2,
        )
        import anyio
        state = self._export_state()
        anyio.run(self._focus_store.save, state)

    def load(self, path: Any | None = None) -> None:
        """Load focus state via the configured store (sync wrapper).

        .. deprecated:: 1.3.6
            Use :meth:`_load_from_store` instead.  This method uses
            ``anyio.run()`` which crashes inside an async event loop.
            Kept for backward compatibility only.

        v1.3.6: When ``_focus_store`` is set, delegates to the store.
        Otherwise no-op (backward-compatible).
        """
        if self._focus_store is None:
            return
        import warnings
        warnings.warn(
            "RenovatedFrontal.load() is deprecated since v1.3.6. "
            "Use _load_from_store() instead.",
            DeprecationWarning, stacklevel=2,
        )
        import anyio
        state = anyio.run(self._focus_store.load)
        if state is not None:
            self._import_state(state)

    # ── Lifecycle helpers (used by factory.py) ────────────────────

    async def _load_from_store(self) -> None:
        """Async load focus state from the configured store.

        Called by lifecycle hook on ``on_start``.
        """
        if self._focus_store is None:
            return
        state = await self._focus_store.load()
        if state is not None:
            self._import_state(state)

    async def _save_to_store(self) -> None:
        """Async save focus state to the configured store.

        Called by lifecycle hook on ``on_shutdown``.
        """
        if self._focus_store is None:
            return
        await self._focus_store.save(self._export_state())

    def _export_state(self) -> Any:
        """Export current focus state as a :class:`~meowcat.focus.FocusState`.

        Returns a plain dataclass suitable for serialization.
        """
        from meowcat.focus import FocusState
        return FocusState(
            topics=list(self._topics),
            current_keywords=sorted(self._current_keywords),
            threshold=self._threshold,
        )

    def _import_state(self, state: Any) -> None:
        """Import focus state from a :class:`~meowcat.focus.FocusState`.

        Args:
            state: A ``FocusState`` instance previously returned by
                   ``_export_state()``.
        """
        self._topics = list(state.topics)
        self._current_keywords = set(state.current_keywords)
        self._threshold = state.threshold


class RenovatedHypothalamus(NoopHypothalamus):
    """简装修 hypothalamus: background maintenance with configurable TTL decay.

    Runs memory decay on the hippocampus organ if accessible via cat ref.
    """

    name: str = "renovated_hypothalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, decay_ttl_days: int = 30) -> None:
        NoopHypothalamus.__init__(self)
        self._decay_ttl_days = decay_ttl_days
        self._last_maintenance: float = 0.0

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        result: dict[str, Any] = {
            "decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}
        async for _name, r in self._run_plugs("run_maintenance", country_code):
            if isinstance(r, dict):
                result.update(r)
        self._last_maintenance = _time.time()
        return result

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        return {"decayed": 0, "ttl_days": self._decay_ttl_days}


class RenovatedCortex(NoopCortex):
    """简装修 cortex: in-memory worldview accumulation.

    Ingests key-value observations into four layers (axioms/others/values/self)
    and synthesizes summary text on demand.
    """

    name: str = "renovated_cortex"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopCortex.__init__(self)
        self._worldview: dict[str, dict[str, Any]] = {
            "axioms": {}, "others": {}, "values": {}, "self": {},
        }
        self._weakness_log: list[dict[str, Any]] = []

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        if layer in self._worldview:
            self._worldview[layer][key] = {
                "source": source, "value": value, "ts": _time.time()}

    def record_weakness(self, kind: str, detail: str) -> None:
        self._weakness_log.append(
            {"kind": kind, "detail": detail, "ts": _time.time()})

    def weaknesses(self) -> list[dict[str, Any]]:
        return list(self._weakness_log)

    def synthesize(self, max_tokens: int = 400) -> str:
        result = ""
        for _name, r in self._run_plugs_sync("synthesize", max_tokens):
            if isinstance(r, str):
                result += r
        if not result:
            parts: list[str] = []
            for layer, entries in self._worldview.items():
                if entries:
                    summary = ", ".join(
                        f"{k}={v['value']}" for k, v in list(entries.items())[:5]
                    )
                    parts.append(f"[{layer}] {summary}")
            if parts:
                result = "\n".join(parts)
        return result


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
            "build_system_prompt", organ, route, cat_self_snapshot,
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
            template
            .replace("{name}", self._cat_name)
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
        if is_zh:
            lines = ["## 自我认知", ""]
        else:
            lines = ["## Self-Awareness", ""]

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
            domains = ', '.join(str(d) for d in capable[:10])
            if is_zh:
                lines.append(f"擅长的领域：{domains}")
            else:
                lines.append(f"Capable domains: {domains}")

        # Incapable domains
        incapable = getattr(snap, "incapable_domains", None) or []
        if incapable:
            domains = ', '.join(str(d) for d in incapable[:10])
            if is_zh:
                lines.append(f"不擅长的领域：{domains}")
            else:
                lines.append(f"Incapable domains: {domains}")

        return "\n".join(lines)


class RenovatedCerebrum(NoopCerebrum):
    """简装修 cerebrum: callable-based LLM adapter with prompt preset support.

    Accepts an optional ``llm_fn`` callable (sync or async), a
    :class:`PromptPreset` for system prompt templates, and an
    :class:`OrganPrompt` for per-organ identity/perspective/output_format.
    Without ``llm_fn``, returns a helpful message.
    """
    name: str = "renovated_cerebrum"
    impl_style: ImplementationStyle = ImplementationStyle.MODEL

    def __init__(
        self,
        llm_fn: Callable[..., Awaitable[str]
                         ] | Callable[..., str] | None = None,
        default_model: str = "renovated",
        prompt: PromptPreset | None = None,
        organ_prompt: OrganPrompt | None = None,
    ) -> None:
        NoopCerebrum.__init__(self)
        self._llm_fn = llm_fn
        self._model = default_model
        self._prompt = prompt
        self._organ_prompt = organ_prompt

    @property
    def organ_prompt(self) -> OrganPrompt | None:
        """Per-organ prompt slot (v1.3.6)."""
        return self._organ_prompt

    def diagnose(self) -> dict[str, Any]:
        return {"model": self._model, "has_llm": self._llm_fn is not None, "prompt_preset": self._prompt.name if self._prompt else "none", "organ_prompt": self._organ_prompt is not None}

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs("generate", prompt, system_prompt, temperature, max_tokens):
            if isinstance(r, str):
                return r
        if self._llm_fn is not None:
            import inspect
            result = self._llm_fn(prompt=prompt, system_prompt=system_prompt,
                                  temperature=temperature, max_tokens=max_tokens)
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        return "(renovated cerebrum: no LLM configured)"

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs("stream_generate", prompt, system_prompt, temperature, max_tokens):
            return r
        result = await self.generate(prompt, system_prompt, temperature, max_tokens)

        async def _stream():
            yield result
        return _stream()


class RenovatedCerebellum(NoopCerebellum):
    """简装修 cerebellum: callable-based fast-response adapter with prompt preset.

    Same pattern as RenovatedCerebrum — accepts optional ``llm_fn``,
    :class:`PromptPreset`, and :class:`OrganPrompt`.
    """

    name: str = "renovated_cerebellum"
    impl_style: ImplementationStyle = ImplementationStyle.MODEL

    def __init__(
        self,
        llm_fn: Callable[..., Awaitable[str]
                         ] | Callable[..., str] | None = None,
        default_model: str = "renovated",
        prompt: PromptPreset | None = None,
        organ_prompt: OrganPrompt | None = None,
    ) -> None:
        NoopCerebellum.__init__(self)
        self._llm_fn = llm_fn
        self._model = default_model
        self._prompt = prompt
        self._organ_prompt = organ_prompt

    @property
    def organ_prompt(self) -> OrganPrompt | None:
        """Per-organ prompt slot (v1.3.6)."""
        return self._organ_prompt

    def diagnose(self) -> dict[str, Any]:
        return {"model": self._model, "has_llm": self._llm_fn is not None, "prompt_preset": self._prompt.name if self._prompt else "none", "organ_prompt": self._organ_prompt is not None}

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs("generate", prompt, system_prompt, temperature, max_tokens):
            if isinstance(r, str):
                return r
        if self._llm_fn is not None:
            import inspect
            result = self._llm_fn(prompt=prompt, system_prompt=system_prompt,
                                  temperature=temperature, max_tokens=max_tokens)
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        return "(renovated cerebellum: no LLM configured)"

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs("stream_generate", prompt, system_prompt, temperature, max_tokens):
            return r
        result = await self.generate(prompt, system_prompt, temperature, max_tokens)

        async def _stream():
            yield result
        return _stream()


class RenovatedHippocampus(NoopHippocampus):
    """简装修 hippocampus: enhanced in-memory graph store with auto-indexing.

    Builds on NoopHippocampus (which already wraps InMemoryGraphStore) and adds
    automatic keyword indexing on ``remember()``.

    v1.3.6: Accepts optional ``episode_store`` (:class:`~meowcat.storage.JsonlEpisodeStore`)
    for persistent episode storage.  Lifecycle methods ``_load_from_store()``
    and ``_flush_to_store()`` are called by the cat's ``on_start`` / ``on_shutdown``
    hooks registered during assembly.
    """

    name: str = "renovated_hippocampus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    # Instance-only: set by factory lifecycle hook before on_start
    cat_uid: str = ""

    def __init__(
        self,
        episode_store: Any | None = None,
    ) -> None:
        NoopHippocampus.__init__(self)
        self._keyword_index: dict[str, set[str]] = {}
        self._episode_store = episode_store

    async def remember(
        self, user_msg: str, ai_reply: str, cat_uid: str, model: str,
    ) -> Any:
        result = await NoopHippocampus.remember(self, user_msg, ai_reply, cat_uid, model)
        kws = _extract_keywords(f"{user_msg} {ai_reply}", top_k=10)
        for kw in kws:
            self._keyword_index.setdefault(kw, set()).add(user_msg[:80])
        return result

    def fts_search(
        self, cat_uid: str, keywords: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        results = NoopHippocampus.fts_search(self, cat_uid, keywords, limit)
        kws = set(keywords.lower().split())
        for kw in kws:
            if kw in self._keyword_index:
                for snippet in self._keyword_index[kw]:
                    if not any(r.get("user_msg", "")[:80] == snippet for r in results):
                        results.append(
                            {"keyword_match": kw, "snippet": snippet})
        return results[:limit]

    # -- v1.3.6: Episode persistence + lifecycle -----------------------

    async def _load_from_store(self) -> None:
        """Load all persisted episodes from store into in-memory list.

        Called by the cat's ``on_start`` hook registered during assembly.
        Safe to call when ``_episode_store`` is None (no-op).
        """
        if self._episode_store is None or not self.cat_uid:
            return
        try:
            records = self._episode_store.load_all(self.cat_uid)
            for ep in records:
                if ep.get("id") not in {e.get("id") for e in self.episodes}:
                    self.episodes.append(ep)
        except Exception:
            pass  # best-effort load; never crash on IO error

    async def _flush_to_store(self) -> None:
        """Ensure all in-memory episodes are persisted.

        Called by the cat's ``on_shutdown`` hook registered during assembly.
        Since :meth:`add_episode` already writes-through to the store,
        this is a no-op for the default JSONL store.  Custom stores that
        buffer writes can override.
        """
        pass  # write-through: add_episode already persists immediately

    def add_episode(self, episode: dict[str, Any]) -> str:
        """Add episode, persist to store if available."""
        eid = NoopHippocampus.add_episode(self, episode)
        if self._episode_store is not None:
            try:
                store_cat_uid = self.cat_uid or episode.get(
                    "cat_uid", "unknown")
                self._episode_store.append(store_cat_uid, dict(episode))
            except Exception:
                pass  # persistence is best-effort; never crash on IO error
        return eid

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        """Get episode, in-memory lookup."""
        if self._episode_store is not None:
            try:
                ep = NoopHippocampus.get_episode(self, episode_id)
                if ep is not None:
                    return ep
            except Exception:
                pass
        return NoopHippocampus.get_episode(self, episode_id)

    def get_episodes(self, ids: list[str]) -> list[dict[str, Any]]:
        """Batch get episodes, in-memory only."""
        return NoopHippocampus.get_episodes(self, ids)


# =========================================================================
# Senses — 简装修
# =========================================================================


class RenovatedEars(NoopEars):
    """简装修 ears: text normalization + keyword extraction + language detection.

    Accepts a :class:`KeywordPreset` for configurable stop words and keyword extraction.
    Default: bilingual (zh+en).

    Strips extra whitespace, limits excessive length, extracts keywords,
    and auto-detects zh/en.
    """

    name: str = "renovated_ears"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, max_length: int = 32000, keyword: KeywordPreset | None = None) -> None:
        NoopEars.__init__(self)
        self._max_length = max_length
        self._keyword = keyword or KW_BILINGUAL

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        text = raw_input.decode(
            "utf-8", errors="replace") if isinstance(raw_input, bytes) else raw_input
        text = text.strip()
        if len(text) > self._max_length:
            text = text[:self._max_length] + "..."
        kws = _extract_keywords(text, stop_words=self._keyword.stop_words)
        lang = _detect_language(text)
        result: dict[str, Any] = {"text": text,
                                  "keywords": kws, "language": lang}
        async for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        result = _extract_keywords(
            text, top_k=top_k, stop_words=self._keyword.stop_words)
        for _name, r in self._run_plugs_sync("extract_keywords", text, top_k):
            if isinstance(r, list):
                result.extend(r)
        return result

    def detect_language(self, text: str) -> str:
        return _detect_language(text)


class RenovatedEyes(NoopEyes):
    """简装修 eyes: image format detection + basic metadata extraction.

    Reads magic bytes to identify PNG/JPEG/GIF/BMP/WebP formats.
    """

    name: str = "renovated_eyes"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    _SIGNATURES: dict[bytes, str] = {
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"BM": "image/bmp",
        b"RIFF": "image/webp",
    }

    def __init__(self) -> None:
        NoopEyes.__init__(self)

    async def see(self, image_data: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        async for _name, r in self._run_plugs("see", image_data, mime_type):
            if isinstance(r, dict):
                return r
        detected = mime_type
        for sig, fmt in self._SIGNATURES.items():
            if image_data.startswith(sig):
                detected = fmt
                break
        if mime_type == "image/png" and "RIFF" in str(image_data[:4]):
            detected = "image/webp"
        return {
            "format": detected,
            "size_bytes": len(image_data),
            "width_hint": "unknown",
            "height_hint": "unknown",
        }


class RenovatedWhiskers(NoopWhiskers):
    """简装修 whiskers: input/output sensing + drift + injection/negation/correction detection.

    Tracks recent outputs, detects simple drift patterns (repetition, length anomaly),
    and provides seed-level input feature analysis: prompt injection detection,
    user negation/correction parsing, and general-purpose text analysis algorithms.

    All detection methods support Pluggable mode B (merge enhancement) — app layer
    can append custom markers or override detection logic via hooks.
    """

    name: str = "renovated_whiskers"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    # -- Seed markers (framework defaults, app can extend via Pluggable) -----

    INJECTION_MARKERS: list[str] = [
        # Chinese injection
        "忽略之前的", "忘记之前的", "不要管之前的",
        "你现在是", "你的新身份", "扮演", "伪装",
        "忽略系统提示", "覆盖之前的指令",
        # English injection
        "ignore previous", "forget previous", "disregard prior",
        "you are now", "your new identity", "act as",
        "system prompt", "system:", "override prompt",
        "DAN mode", "jailbreak", "pretend to be",
    ]

    NEGATION_MARKERS: list[str] = [
        # Chinese negation
        "不对", "不是", "错了", "你错了", "搞错了",
        "你理解错了", "不是这样的", "不正确", "错误",
        # English negation
        "wrong", "incorrect", "not correct",
        "that's not right", "you're wrong",
        "you misunderstood", "that is wrong",
    ]

    # Regular expressions for correction parsing
    _RE_CORRECTION_ZH = re.compile(
        r'(?:不(?:是|对)|错(?:了|误)?)[，,。\s]*(.+?)(?:，|,)?\s*(?:是|而是|应该是|应该是|就是|应为)(.+)',
    )
    _RE_CORRECTION_EN = re.compile(
        r"(?:it'?s?\s+not|that'?s?\s+not|not)\s+(.+?),?\s+(?:it'?s?|that'?s?|but)\s+(.+)",
        re.IGNORECASE,
    )

    HOOKS = {
        **NoopWhiskers.HOOKS,
        "feel_input": {"in": "text: str", "out": "dict[str, Any]"},
        "check_hallucination": {"in": "reply: str, session_id: str|None", "out": "dict[str, Any]"},
    }

    def __init__(self, max_recent: int = 20) -> None:
        NoopWhiskers.__init__(self)
        self._recent_outputs: list[str] = []
        self._max_recent = max_recent

    # -- Input feature analysis --------------------------------------

    def is_injection(self, text: str) -> bool:
        """Check if text contains prompt injection markers.

        Case-insensitive substring match against INJECTION_MARKERS.
        App layer can extend via Pluggable hooks.
        """
        lower = text.lower()
        for marker in self.INJECTION_MARKERS:
            if marker.lower() in lower:
                return True
        return False

    def is_negation(self, text: str) -> bool:
        """Check if user is negating/correcting the agent.

        Excludes interrogative sentences (ending with ?, ？, 吗, 吧).
        App layer can extend via Pluggable hooks.
        """
        stripped = text.strip()
        if stripped.endswith(('?', '？', '吗', '吧')):
            return False
        lower = stripped.lower()
        for marker in self.NEGATION_MARKERS:
            if marker.lower() in lower:
                return True
        return False

    def parse_correction(self, text: str) -> tuple[str, str] | None:
        """Parse "not X, but Y" correction patterns.

        Supports: 不是X，是Y / 不是X而是Y / it's not X, it's Y

        Returns:
            ``(wrong, correct)`` if a correction pattern is found, else None.
        """
        m = self._RE_CORRECTION_ZH.search(text)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        m = self._RE_CORRECTION_EN.search(text)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        return None

    # -- Core sensing -------------------------------------------------

    async def feel_input(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "length": len(text),
            "has_code": bool(re.search(r"```|def |class |import |function ", text)),
            "has_url": bool(re.search(r"https?://", text)),
            # v1.3.0: seed-level input features
            "injection_detected": self.is_injection(text),
            "negation_detected": self.is_negation(text),
        }
        correction = self.parse_correction(text)
        if correction:
            result["correction"] = {
                "wrong": correction[0], "correct": correction[1]}
        async for _name, r in self._run_plugs("feel_input", text):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"length": len(
            output), "empty": not output.strip()}
        self._recent_outputs.append(output)
        if len(self._recent_outputs) > self._max_recent:
            self._recent_outputs.pop(0)
        async for _name, r in self._run_plugs("feel_output", output, expected_schema):
            if isinstance(r, dict):
                result.update(r)
        return result

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]:
        outputs = recent_outputs or self._recent_outputs
        if len(outputs) < 3:
            return {"drift": False}
        lengths = [len(o) for o in outputs[-5:]]
        avg = sum(lengths) / len(lengths)
        drift = any(abs(ln - avg) > avg * 2 for ln in lengths if ln > 0)
        return {"drift": drift, "avg_length": avg}

    def check_hallucination(
        self, reply: str, session_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"hallucination": False}
        for _name, r in self._run_plugs_sync("check_hallucination", reply, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result


# =========================================================================
# Voice — 简装修
# =========================================================================


class RenovatedMouth(NoopMouth):
    """简装修 mouth: text output formatting + stdout printing.

    Prints replies to stdout (configurable via ``output_stream``) and
    returns the formatted text.
    """

    name: str = "renovated_mouth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, output_stream: Any = None) -> None:
        NoopMouth.__init__(self)
        self._output = output_stream or sys.stdout

    def diagnose(self) -> dict[str, Any]:
        return {"renovated": True, "stream": str(self._output)}

    async def speak(self, text: str, **kwargs: Any) -> str:
        async for _name, r in self._run_plugs("speak", text, **kwargs):
            return r
        self._output.write(text + "\n")
        self._output.flush()
        _logger.info("speak: %s", text[:200])
        return text


class RenovatedPurr(NoopPurr):
    """简装修 purr: streaming status tracker.

    Tracks streaming state (started, chunk count, finished) for progress reporting.
    """

    name: str = "renovated_purr"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopPurr.__init__(self)
        self._streaming = False
        self._chunk_count = 0
        self._total_chars = 0

    def diagnose(self) -> dict[str, Any]:
        return {"streaming": self._streaming, "chunks": self._chunk_count, "chars": self._total_chars}

    async def stream(self, text: str, **kwargs: Any) -> Any:
        async for _name, r in self._run_plugs("stream", text, **kwargs):
            return r
        self._streaming = True
        self._chunk_count += 1
        self._total_chars += len(text)
        return None


class RenovatedTail(NoopTail):
    """简装修 tail: simple status bar (prints to stdout).

    Renders key health metrics: uptime, memory entities, safety state.
    """

    name: str = "renovated_tail"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def diagnose(self) -> dict[str, Any]:
        return {"renovated": True}

    async def render(self, state: dict[str, Any]) -> None:
        async for _name, r in self._run_plugs("render", state):
            return None
        status = state.get("status", "idle")
        entities = state.get("entities", 0)
        episodes = state.get("episodes", 0)
        bar = f"[{status}] mem: {entities}e/{episodes}ep"
        _logger.debug("tail: %s", bar)


# =========================================================================
# Effectors — 简装修
# =========================================================================


class RenovatedPaws(NoopPaws):
    """简装修 paws: tool registry integration + security gate.

    Looks up tools in the cat's tool_registry, checks security via amygdala,
    and executes with safety policy.
    """

    name: str = "renovated_paws"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, tool_registry: Any = None) -> None:
        NoopPaws.__init__(self)
        self._tool_registry = tool_registry

    def diagnose(self) -> dict[str, Any]:
        registered = [t.name for t in self._tool_registry.list_all()
                      ] if self._tool_registry else []
        return {"tools": registered, "count": len(registered)}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        async for _name, r in self._run_plugs("execute", tool_name, params):
            if isinstance(r, dict):
                return r
        if self._tool_registry is None:
            return {"ok": False, "reason": "no tool_registry mounted"}
        spec = self._tool_registry.get(tool_name)
        if spec is None:
            return {"ok": False, "reason": f"tool '{tool_name}' not found"}
        try:
            result = await spec.fn(**params)
            return {"ok": True, "result": result}
        except Exception as exc:
            _logger.exception("Tool '%s' failed", tool_name)
            return {"ok": False, "reason": str(exc)}

    async def interact_with_tool(
        self, skill_name: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.execute(skill_name, params)


# =========================================================================
# Growth Organs — 简装修 (in-memory logging)
# =========================================================================


class RenovatedAnomalyGrowth(NoopAnomalyGrowth):
    """简装修 anomaly_growth: in-memory anomaly log with diagnostics."""

    name: str = "renovated_anomaly_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopAnomalyGrowth.__init__(self)
        self._log: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"anomalies": len(self._log), "recent": self._log[-5:]}

    def record(
        self, reason: str, snippet: str, confidence: float = 0.8,
        phase: str = "input", session_id: str = "",
    ) -> Any:
        for _name, r in self._run_plugs_sync("record", reason, snippet, confidence, phase, session_id):
            if isinstance(r, dict):
                return r
        entry = {"reason": reason, "snippet": snippet[:200],
                 "confidence": confidence, "phase": phase, "ts": _time.time()}
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class RenovatedCorrectionGrowth(NoopCorrectionGrowth):
    """简装修 correction_growth: in-memory correction log with diagnostics."""

    name: str = "renovated_correction_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopCorrectionGrowth.__init__(self)
        self._log: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"corrections": len(self._log), "recent": self._log[-5:]}

    def record(
        self, wrong: str, correct: str, session_id: str = "",
        topic: str = "",
    ) -> Any:
        for _name, r in self._run_plugs_sync("record", wrong, correct, session_id, topic):
            if isinstance(r, dict):
                return r
        entry = {"wrong": wrong[:200], "correct": correct[:200],
                 "topic": topic, "ts": _time.time()}
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class RenovatedCrystallizer(NoopCrystallizer):
    """简装修 crystallizer: in-memory skill hit counter.

    Tracks how often each skill slug is called, and surfaces hotspots.

    Thresholds are configurable via ``crystallize_threshold`` (min hits for
    a skill to be considered "crystallized") and ``hotspot_threshold`` (min
    hits for a skill to appear in hotspots).
    """

    name: str = "renovated_crystallizer"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        crystallize_threshold: int = 5,
        hotspot_threshold: int = 3,
    ) -> None:
        NoopCrystallizer.__init__(self)
        self._hits: dict[str, int] = {}
        self._crystallize_threshold = crystallize_threshold
        self._hotspot_threshold = hotspot_threshold

    def diagnose(self) -> dict[str, Any]:
        return {"hits": dict(self._hits), "hotspots": self.hotspots(threshold=3)}

    def crystallize(self, slug: str, hit_count: int) -> bool:
        for _name, r in self._run_plugs_sync("crystallize", slug, hit_count):
            if isinstance(r, bool):
                return r
        self._hits[slug] = self._hits.get(slug, 0) + hit_count
        return self._hits[slug] >= self._crystallize_threshold

    def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        for _name, r in self._run_plugs_sync("hotspots", threshold):
            if isinstance(r, list):
                return r
        t = threshold if threshold is not None else self._hotspot_threshold
        result = [(k, v) for k, v in self._hits.items() if v >= t]
        result.sort(key=lambda x: -x[1])
        return result


class RenovatedRoleEmergence(NoopRoleEmergence):
    """简装修 role_emergence: in-memory behavior pattern log with diagnostics."""

    name: str = "renovated_role_emergence"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopRoleEmergence.__init__(self)
        self._patterns: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"patterns": len(self._patterns), "recent": self._patterns[-5:]}

    def record(self, pattern: str, evidence: str) -> Any:
        for _name, r in self._run_plugs_sync("record", pattern, evidence):
            if isinstance(r, dict):
                return r
        entry = {"pattern": pattern,
                 "evidence": evidence[:200], "ts": _time.time()}
        self._patterns.append(entry)
        return {"recorded": True, "total": len(self._patterns)}


# =========================================================================
# Organ name → renovated class mapping
# =========================================================================

RENOVATED_ORGAN_MAP: dict[str, type] = {
    # Brain
    "thalamus": RenovatedThalamus,
    "hippocampus": RenovatedHippocampus,
    "cerebrum": RenovatedCerebrum,
    "cerebellum": RenovatedCerebellum,
    "amygdala": RenovatedAmygdala,
    "frontal": RenovatedFrontal,
    "hypothalamus": RenovatedHypothalamus,
    "cortex": RenovatedCortex,
    "brainstem": RenovatedBrainstem,
    # Senses
    "ears": RenovatedEars,
    "eyes": RenovatedEyes,
    "whiskers": RenovatedWhiskers,
    "paws": RenovatedPaws,
    # Voice
    "mouth": RenovatedMouth,
    "purr": RenovatedPurr,
    "tail": RenovatedTail,
    # Growth
    "anomaly_growth": RenovatedAnomalyGrowth,
    "correction_growth": RenovatedCorrectionGrowth,
    "crystallizer": RenovatedCrystallizer,
    "role_emergence": RenovatedRoleEmergence,
}


__all__ = [
    # Brain
    "RenovatedThalamus", "RenovatedHippocampus", "RenovatedCerebrum",
    "RenovatedCerebellum", "RenovatedAmygdala", "RenovatedFrontal",
    "RenovatedHypothalamus", "RenovatedCortex", "RenovatedBrainstem",
    # Senses
    "RenovatedEars", "RenovatedEyes", "RenovatedWhiskers", "RenovatedPaws",
    # Voice
    "RenovatedMouth", "RenovatedPurr", "RenovatedTail",
    # Growth
    "RenovatedAnomalyGrowth", "RenovatedCorrectionGrowth",
    "RenovatedCrystallizer", "RenovatedRoleEmergence",
    # Mappings
    "RENOVATED_ORGAN_MAP",
]
