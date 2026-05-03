"""meowcat renovated organs — 简装修 (light-renovation) default implementations.

Each Renovated* class extends the Noop*毛坯 (bare) stub, adding minimal but
useful default behavior. Developers get a working cat out of the box with
``create_cat(renovated=True)``, and can opt-out per organ to use pure Noop*毛坯.

The renovated organs bridge the gap between pure stubs and full app-layer
implementations — enough to run simple flows, test wiring, and prototype.
"""
# (c) 2025-2026 Axonant. MIT License.

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
    KW_BILINGUAL, KW_EN, PROMPT_DEFAULT, PROMPT_ZH,
    KeywordPreset, PromptPreset,
)

_logger = logging.getLogger("meowcat.renovated")


# =========================================================================
# Helpers
# =========================================================================

_DANGER_PATTERNS: list[re.Pattern] = KW_EN.danger_patterns

_STOP_WORDS: frozenset[str] = KW_EN.stop_words

_COMMAND_PATTERNS: dict[str, str] = KW_EN.command_patterns


def _extract_keywords(text: str, top_k: int = 5, stop_words: frozenset[str] | None = None) -> list[str]:
    sw = stop_words if stop_words is not None else _STOP_WORDS
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())
    filtered = [w for w in words if w not in sw and len(w) > 1]
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
    patterns = kw.command_patterns if kw else _COMMAND_PATTERNS
    lower = text.lower().strip()
    for cmd, route in patterns.items():
        if lower.startswith(cmd) or lower.startswith(f"/{cmd}"):
            return route
    return None


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
        result: dict[str, Any] = {"route": "chat", "entities": [], "snippets": []}
        for _name, r in self._run_plugs("locate", msg, session_id):
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
    """简装修 amygdala: regex-based safety patterns.

    Accepts a :class:`KeywordPreset` for configurable danger patterns.
    Default: bilingual (zh+en) danger patterns covering SQL injection,
    shell injection, XSS, path traversal, and Chinese-specific threats.

    Scans input against common dangerous patterns. Configurable via
    ``danger_patterns`` or ``keyword`` preset.
    """

    name: str = "renovated_amygdala"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        danger_patterns: list[re.Pattern] | None = None,
        keyword: KeywordPreset | None = None,
    ) -> None:
        NoopAmygdala.__init__(self)
        if danger_patterns:
            self._patterns: list[re.Pattern] = list(danger_patterns)
        elif keyword:
            self._patterns = list(keyword.danger_patterns)
        else:
            self._patterns = list(KW_BILINGUAL.danger_patterns)

    def is_rejection(self, msg: str) -> bool:
        for pat in self._patterns:
            if pat.search(msg):
                return True
        return False

    def classify_rejection(self, msg: str) -> str:
        if not self.is_rejection(msg):
            return "none"
        return "danger"

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict) and not r.get("safe", True):
                return r
        for pat in self._patterns:
            m = pat.search(user_input)
            if m:
                return {"safe": False, "risk": "high", "pattern": pat.pattern, "match": m.group()}
        return {"safe": True, "risk": "low"}

    @staticmethod
    def assess_tool_risk(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        dangerous_tools = {"run_command", "eval", "exec", "shell"}
        if tool_name in dangerous_tools:
            return {"risk": "high", "reason": f"dangerous tool: {tool_name}"}
        if tool_name == "write_file":
            fp = str(params.get("path", params.get("file_path", "")))
            dangerous_paths = ["/etc/", "/root/", "~/.ssh/", "C:\\Windows\\"]
            for dp in dangerous_paths:
                if dp in fp:
                    return {"risk": "high", "reason": f"write to protected path: {fp}"}
        return {"risk": "low", "reason": "ok"}


class RenovatedFrontal(NoopFrontal):
    """简装修 frontal: keyword topic shift detection + topic history.

    Accepts a :class:`KeywordPreset` for domain-specific topic keywords
    and priority keywords. Default: bilingual.

    Tracks recent topics and detects significant shifts via keyword overlap.
    """

    name: str = "renovated_frontal"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, keyword: KeywordPreset | None = None) -> None:
        NoopFrontal.__init__(self)
        self._keyword = keyword or KW_BILINGUAL
        self._topics: list[str] = []
        self._current_keywords: set[str] = set()
        self._threshold: float = 0.3

    def is_continue(self, msg: str) -> bool:
        for _name, r in self._run_plugs("is_continue", msg):
            if isinstance(r, bool):
                return r
        if not self._current_keywords:
            return False
        kws = set(_extract_keywords(msg, top_k=10, stop_words=self._keyword.stop_words))
        overlap = len(kws & self._current_keywords)
        return overlap >= max(1, len(self._current_keywords) * self._threshold)

    def detect_shift(self, msg: str) -> bool:
        for _name, r in self._run_plugs("detect_shift", msg):
            if isinstance(r, bool):
                return r
        return not self.is_continue(msg)

    def update_focus(self, result: Any) -> None:
        kw_source = ""
        if isinstance(result, dict):
            kw_source = str(result.get("text", result.get("reply", "")))
        else:
            kw_source = str(result)
        self._current_keywords = set(_extract_keywords(kw_source, top_k=10, stop_words=self._keyword.stop_words))

    def archive_focus(self) -> None:
        self._topics.append(", ".join(sorted(self._current_keywords)))
        self._current_keywords.clear()

    def save(self, path: Any | None = None) -> None:
        pass

    def load(self, path: Any | None = None) -> None:
        pass


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
        result: dict[str, Any] = {"decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}
        for _name, r in self._run_plugs("run_maintenance", country_code):
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
            self._worldview[layer][key] = {"source": source, "value": value, "ts": _time.time()}

    def record_weakness(self, kind: str, detail: str) -> None:
        self._weakness_log.append({"kind": kind, "detail": detail, "ts": _time.time()})

    def weaknesses(self) -> list[dict[str, Any]]:
        return list(self._weakness_log)

    def synthesize(self, max_tokens: int = 400) -> str:
        result = ""
        for _name, r in self._run_plugs("synthesize", max_tokens):
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

    Accepts a :class:`PromptPreset` for route-specific prompt templates,
    pre/post prompts, and variable substitution. Default: bilingual-aware.

    Constructs system prompts from templates with variable interpolation
    ({name}, {language}, {domain}, {route}).
    """

    name: str = "renovated_brainstem"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, prompt: PromptPreset | None = None, cat_name: str = "MeowCat") -> None:
        NoopBrainstem.__init__(self)
        self._prompt = prompt or PROMPT_DEFAULT
        self._cat_name = cat_name
        self._start_time: float = _time.time()

    def diagnose(self) -> dict[str, Any]:
        return {
            "uptime_seconds": _time.time() - self._start_time,
            "organ": "brainstem",
            "renovated": True,
            "prompt_preset": self._prompt.name,
        }

    async def build_system_prompt(self, route: str) -> str:
        parts: list[str] = []
        for _name, r in self._run_plugs("build_system_prompt", route):
            if isinstance(r, str) and r:
                parts.append(r)
        if not parts:
            parts.append(
                self._prompt.build(
                    route,
                    name=self._cat_name,
                    language="zh/en",
                    domain="general",
                    route=route,
                )
            )
        return "\n".join(parts)


class RenovatedCerebrum(NoopCerebrum):
    """简装修 cerebrum: callable-based LLM adapter with prompt preset support.

    Accepts an optional ``llm_fn`` callable (sync or async) and a
    :class:`PromptPreset` for system prompt templates.
    Without ``llm_fn``, returns a helpful message.
    """

    name: str = "renovated_cerebrum"
    impl_style: ImplementationStyle = ImplementationStyle.MODEL

    def __init__(
        self,
        llm_fn: Callable[..., Awaitable[str]] | Callable[..., str] | None = None,
        default_model: str = "renovated",
        prompt: PromptPreset | None = None,
    ) -> None:
        NoopCerebrum.__init__(self)
        self._llm_fn = llm_fn
        self._model = default_model
        self._prompt = prompt

    def diagnose(self) -> dict[str, Any]:
        return {"model": self._model, "has_llm": self._llm_fn is not None, "prompt_preset": self._prompt.name if self._prompt else "none"}

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        for _name, r in self._run_plugs("generate", prompt, system_prompt, temperature, max_tokens):
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
        for _name, r in self._run_plugs("stream_generate", prompt, system_prompt, temperature, max_tokens):
            return r
        result = await self.generate(prompt, system_prompt, temperature, max_tokens)
        async def _stream():
            yield result
        return _stream()


class RenovatedCerebellum(NoopCerebellum):
    """简装修 cerebellum: callable-based fast-response adapter with prompt preset.

    Same pattern as RenovatedCerebrum — accepts optional ``llm_fn`` and
    :class:`PromptPreset`.
    """

    name: str = "renovated_cerebellum"
    impl_style: ImplementationStyle = ImplementationStyle.MODEL

    def __init__(
        self,
        llm_fn: Callable[..., Awaitable[str]] | Callable[..., str] | None = None,
        default_model: str = "renovated",
        prompt: PromptPreset | None = None,
    ) -> None:
        NoopCerebellum.__init__(self)
        self._llm_fn = llm_fn
        self._model = default_model
        self._prompt = prompt

    def diagnose(self) -> dict[str, Any]:
        return {"model": self._model, "has_llm": self._llm_fn is not None, "prompt_preset": self._prompt.name if self._prompt else "none"}

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        for _name, r in self._run_plugs("generate", prompt, system_prompt, temperature, max_tokens):
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
        for _name, r in self._run_plugs("stream_generate", prompt, system_prompt, temperature, max_tokens):
            return r
        result = await self.generate(prompt, system_prompt, temperature, max_tokens)
        async def _stream():
            yield result
        return _stream()


class RenovatedHippocampus(NoopHippocampus):
    """简装修 hippocampus: enhanced in-memory graph store with auto-indexing.

    Builds on NoopHippocampus (which already wraps InMemoryGraphStore) and adds
    automatic keyword indexing on ``remember()``.
    """

    name: str = "renovated_hippocampus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopHippocampus.__init__(self)
        self._keyword_index: dict[str, set[str]] = {}

    async def remember(
        self, user_msg: str, ai_reply: str, cat_id: str, model: str,
    ) -> Any:
        result = await NoopHippocampus.remember(self, user_msg, ai_reply, cat_id, model)
        kws = _extract_keywords(f"{user_msg} {ai_reply}", top_k=10)
        for kw in kws:
            self._keyword_index.setdefault(kw, set()).add(user_msg[:80])
        return result

    def fts_search(
        self, cat_id: str, keywords: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        results = NoopHippocampus.fts_search(self, cat_id, keywords, limit)
        kws = set(keywords.lower().split())
        for kw in kws:
            if kw in self._keyword_index:
                for snippet in self._keyword_index[kw]:
                    if not any(r.get("user_msg", "")[:80] == snippet for r in results):
                        results.append({"keyword_match": kw, "snippet": snippet})
        return results[:limit]


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
        text = raw_input.decode("utf-8", errors="replace") if isinstance(raw_input, bytes) else raw_input
        text = text.strip()
        if len(text) > self._max_length:
            text = text[:self._max_length] + "..."
        kws = _extract_keywords(text, stop_words=self._keyword.stop_words)
        lang = _detect_language(text)
        result: dict[str, Any] = {"text": text, "keywords": kws, "language": lang}
        for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        result = _extract_keywords(text, top_k=top_k, stop_words=self._keyword.stop_words)
        for _name, r in self._run_plugs("extract_keywords", text, top_k):
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
        for _name, r in self._run_plugs("see", image_data, mime_type):
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
    """简装修 whiskers: basic input/output sensing + drift detection.

    Tracks recent outputs and detects simple drift patterns (repetition, length anomaly).
    """

    name: str = "renovated_whiskers"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, max_recent: int = 20) -> None:
        NoopWhiskers.__init__(self)
        self._recent_outputs: list[str] = []
        self._max_recent = max_recent

    async def feel_input(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "length": len(text),
            "has_code": bool(re.search(r"```|def |class |import |function ", text)),
            "has_url": bool(re.search(r"https?://", text)),
        }
        for _name, r in self._run_plugs("feel_input", text):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"length": len(output), "empty": not output.strip()}
        self._recent_outputs.append(output)
        if len(self._recent_outputs) > self._max_recent:
            self._recent_outputs.pop(0)
        for _name, r in self._run_plugs("feel_output", output, expected_schema):
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
        for _name, r in self._run_plugs("check_hallucination", reply, session_id):
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
        for _name, r in self._run_plugs("speak", text, **kwargs):
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
        for _name, r in self._run_plugs("stream", text, **kwargs):
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
        for _name, r in self._run_plugs("render", state):
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
        registered = list(self._tool_registry._names.keys()) if self._tool_registry else []
        return {"tools": registered, "count": len(registered)}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        for _name, r in self._run_plugs("execute", tool_name, params):
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
        for _name, r in self._run_plugs("record", reason, snippet, confidence, phase, session_id):
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
        for _name, r in self._run_plugs("record", wrong, correct, session_id, topic):
            if isinstance(r, dict):
                return r
        entry = {"wrong": wrong[:200], "correct": correct[:200],
                 "topic": topic, "ts": _time.time()}
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class RenovatedCrystallizer(NoopCrystallizer):
    """简装修 crystallizer: in-memory skill hit counter.

    Tracks how often each skill slug is called, and surfaces hotspots.
    """

    name: str = "renovated_crystallizer"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopCrystallizer.__init__(self)
        self._hits: dict[str, int] = {}

    def diagnose(self) -> dict[str, Any]:
        return {"hits": dict(self._hits), "hotspots": self.hotspots(threshold=3)}

    def crystallize(self, slug: str, hit_count: int) -> bool:
        for _name, r in self._run_plugs("crystallize", slug, hit_count):
            if isinstance(r, bool):
                return r
        self._hits[slug] = self._hits.get(slug, 0) + hit_count
        return self._hits[slug] >= 5

    def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        for _name, r in self._run_plugs("hotspots", threshold):
            if isinstance(r, list):
                return r
        t = threshold or 3
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
        for _name, r in self._run_plugs("record", pattern, evidence):
            if isinstance(r, dict):
                return r
        entry = {"pattern": pattern, "evidence": evidence[:200], "ts": _time.time()}
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
