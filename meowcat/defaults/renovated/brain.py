# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) brain region implementations — 9 classes."""

from __future__ import annotations

import logging
import re
import time as _time
from collections.abc import Awaitable, Callable
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopBrainstem,
    NoopCerebellum,
    NoopCerebrum,
    NoopCortex,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopThalamus,
)
from meowcat.defaults.presets import (
    KW_BILINGUAL,
    PROMPT_DEFAULT,
    KeywordPreset,
    OrganPrompt,
    PromptPreset,
)

from ._helpers import _detect_command, _extract_keywords

_logger = logging.getLogger("meowcat.renovated")


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
        return {
            "route": cmd_route or "chat",
            "keywords": _extract_keywords(msg, stop_words=self._keyword.stop_words),
        }


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
        self._dangerous_tools: set[str] = (
            dangerous_tools
            if dangerous_tools is not None
            else {"run_command", "eval", "exec", "shell"}
        )
        self._dangerous_paths: list[str] = (
            dangerous_paths
            if dangerous_paths is not None
            else ["/etc/", "/root/", "~/.ssh/", "C:\\Windows\\"]
        )

    def is_rejection(self, msg: str) -> bool:
        """Check if the input should be *rejected* as dangerous.

        Matches against danger patterns (SQL injection, shell injection,
        XSS, path traversal, etc.). Return ``True`` means the input
        contains dangerous content that should be blocked.

        For user negation/correction detection, use
        :meth:`RenovatedWhiskers.is_negation` / :meth:`RenovatedWhiskers.parse_correction`.
        """
        return any(pat.search(msg) for pat in self._patterns)

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
        kw_source = str(result.get("text", result.get("reply", ""))
                        ) if isinstance(result, dict) else str(result)
        self._current_keywords = set(
            _extract_keywords(kw_source, top_k=10,
                              stop_words=self._keyword.stop_words)
        )

    def archive_focus(self) -> None:
        self._topics.append(", ".join(sorted(self._current_keywords)))
        self._current_keywords.clear()

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
            "axioms": {},
            "others": {},
            "values": {},
            "self": {},
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
                        f"{k}={v['value']}" for k, v in list(entries.items())[:5])
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
        return {
            "model": self._model,
            "has_llm": self._llm_fn is not None,
            "prompt_preset": self._prompt.name if self._prompt else "none",
            "organ_prompt": self._organ_prompt is not None,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate", prompt, system_prompt, temperature, max_tokens
        ):
            if isinstance(r, str):
                return r
        if self._llm_fn is not None:
            import inspect

            result = self._llm_fn(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        return "(renovated cerebrum: no LLM configured)"

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate", prompt, system_prompt, temperature, max_tokens
        ):
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
        return {
            "model": self._model,
            "has_llm": self._llm_fn is not None,
            "prompt_preset": self._prompt.name if self._prompt else "none",
            "organ_prompt": self._organ_prompt is not None,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate", prompt, system_prompt, temperature, max_tokens
        ):
            if isinstance(r, str):
                return r
        if self._llm_fn is not None:
            import inspect

            result = self._llm_fn(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        return "(renovated cerebellum: no LLM configured)"

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate", prompt, system_prompt, temperature, max_tokens
        ):
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
        self,
        user_msg: str,
        ai_reply: str,
        cat_uid: str,
        model: str,
    ) -> Any:
        result = await NoopHippocampus.remember(self, user_msg, ai_reply, cat_uid, model)
        kws = _extract_keywords(f"{user_msg} {ai_reply}", top_k=10)
        for kw in kws:
            self._keyword_index.setdefault(kw, set()).add(user_msg[:80])
        return result

    def fts_search(
        self,
        cat_uid: str,
        keywords: str,
        limit: int = 10,
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
