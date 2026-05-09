# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) brain region implementations — 5 classes.

The remaining 4 brain classes live in sibling modules:
- RenovatedBrainstem → .brainstem
- RenovatedCerebrum, RenovatedCerebellum → .cerebrum
- RenovatedHippocampus → .hippocampus
"""

from __future__ import annotations

import re
import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopCortex,
    NoopFrontal,
    NoopHypothalamus,
    NoopThalamus,
)
from meowcat.defaults.presets import (
    KW_BILINGUAL,
    KeywordPreset,
)

from ._helpers import _detect_command, _extract_keywords
from .brainstem import RenovatedBrainstem  # noqa: F401
from .cerebrum import RenovatedCerebellum, RenovatedCerebrum  # noqa: F401
from .hippocampus import RenovatedHippocampus  # noqa: F401


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
