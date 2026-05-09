# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default sense organ implementations — merged renovated behavior.

Each Noop* class extends Pluggable (v1.0.7), providing mount_plug / unmount_plug /
_run_plugs plugin capability. HOOKS class variable declares mountable hooks and their
suggested signatures.

Three execution modes:
- A First-hit override: first non-default value is returned directly
- B Merge enhancement: all plugin results are merged into the default value
- C Full replacement: first plugin completely replaces default behavior

Renovated behavior merged in:
  NoopEars   — text normalization + keyword extraction + language detection
  NoopEyes   — image format detection via magic bytes
  NoopWhiskers — input/output sensing + drift + injection/negation/correction detection
"""

from __future__ import annotations

import re
import string as _string
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.presets import KW_BILINGUAL, KeywordPreset
from meowcat.pluggable import Pluggable


# =========================================================================
# Ears — hear + keyword extraction + language detection
# =========================================================================


class NoopEars(Pluggable):
    """Ears: text normalization + keyword extraction + language detection.

    Accepts a :class:`KeywordPreset` for configurable stop words and keyword extraction.
    Default: bilingual (zh+en).

    Strips extra whitespace, limits excessive length, extracts keywords,
    and auto-detects zh/en.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "hear": {"in": "raw: str|bytes", "out": "dict[str, Any]"},
        "extract_keywords": {"in": "text: str, top_k: int", "out": "list[str]"},
    }

    name: str = "renovated_ears"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self, max_length: int = 32000, keyword: KeywordPreset | None = None
    ) -> None:
        Pluggable.__init__(self)
        self._max_length = max_length
        self._keyword = keyword or KW_BILINGUAL

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        text = (
            raw_input.decode("utf-8", errors="replace")
            if isinstance(raw_input, bytes)
            else raw_input
        )
        text = text.strip()
        if len(text) > self._max_length:
            text = text[: self._max_length] + "..."
        kws = _extract_keywords(text, stop_words=self._keyword.stop_words)
        lang = _detect_language(text)
        result: dict[str, Any] = {
            "text": text,
            "keywords": kws,
            "language": lang,
        }
        async for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:  # type: ignore[override]
        result = _extract_keywords(
            text, top_k=top_k, stop_words=self._keyword.stop_words
        )
        for _name, r in self._run_plugs_sync("extract_keywords", text, top_k):
            if isinstance(r, list):
                result.extend(r)
        return result

    def detect_language(self, text: str) -> str:
        return _detect_language(text)

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]:
        """Default emotion tagging: return as-is, no modification."""
        return episode


# =========================================================================
# Eyes — see images, detect format via magic bytes
# =========================================================================


class NoopEyes(Pluggable):
    """Eyes: image format detection + basic metadata extraction.

    Reads magic bytes to identify PNG/JPEG/GIF/BMP/WebP formats.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "see": {"in": "image: bytes, mime: str", "out": "dict[str, Any]"},
    }

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
        Pluggable.__init__(self)

    async def see(
        self, image_data: bytes, mime_type: str = "image/png"
    ) -> dict[str, Any]:
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


# =========================================================================
# Whiskers — input/output sensing + drift + injection/negation/correction
# =========================================================================


class NoopWhiskers(Pluggable):
    """Whiskers: input/output sensing + drift + injection/negation/correction detection.

    Tracks recent outputs, detects simple drift patterns (repetition, length anomaly),
    and provides seed-level input feature analysis: prompt injection detection,
    user negation/correction parsing, and general-purpose text analysis algorithms.

    All detection methods support Pluggable mode B (merge enhancement) — app layer
    can append custom markers or override detection logic via hooks.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "feel_input": {"in": "text: str", "out": "dict[str, Any]"},
        "feel_output": {"in": "output: str, schema: dict", "out": "dict[str, Any]"},
        "check_hallucination": {
            "in": "reply: str, session_id: str|None",
            "out": "dict[str, Any]",
        },
        "detect_blind_spot": {
            "in": "queries: list[str], known: list[str]",
            "out": "list[dict]",
        },
    }

    name: str = "renovated_whiskers"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    # -- Seed markers (framework defaults, app can extend via Pluggable) -----

    INJECTION_MARKERS: list[str] = [
        # Chinese injection
        "忽略之前的",
        "忘记之前的",
        "不要管之前的",
        "你现在是",
        "你的新身份",
        "扮演",
        "伪装",
        "忽略系统提示",
        "覆盖之前的指令",
        # English injection
        "ignore previous",
        "forget previous",
        "disregard prior",
        "you are now",
        "your new identity",
        "act as",
        "system prompt",
        "system:",
        "override prompt",
        "DAN mode",
        "jailbreak",
        "pretend to be",
    ]

    NEGATION_MARKERS: list[str] = [
        # Chinese negation
        "不对",
        "不是",
        "错了",
        "你错了",
        "搞错了",
        "你理解错了",
        "不是这样的",
        "不正确",
        "错误",
        # English negation
        "wrong",
        "incorrect",
        "not correct",
        "that's not right",
        "you're wrong",
        "you misunderstood",
        "that is wrong",
    ]

    # Regular expressions for correction parsing
    _RE_CORRECTION_ZH = re.compile(
        r"(?:不(?:是|对)|错(?:了|误)?)[，,。\s]*(.+?)(?:，|,)?\s*(?:是|而是|应该是|应该是|就是|应为)(.+)",
    )
    _RE_CORRECTION_EN = re.compile(
        r"(?:it'?s?\s+not|that'?s?\s+not|not)\s+(.+?),?\s+(?:it'?s?|that'?s?|but)\s+(.+)",
        re.IGNORECASE,
    )

    def __init__(self, max_recent: int = 20) -> None:
        Pluggable.__init__(self)
        self._recent_outputs: list[str] = []
        self._max_recent = max_recent

    # -- Input feature analysis ----------------------------------------------

    def is_injection(self, text: str) -> bool:
        """Check if text contains prompt injection markers.

        Case-insensitive substring match against INJECTION_MARKERS.
        App layer can extend via Pluggable hooks.
        """
        lower = text.lower()
        return any(marker.lower() in lower for marker in self.INJECTION_MARKERS)

    def is_negation(self, text: str) -> bool:
        """Check if user is negating/correcting the agent.

        Excludes interrogative sentences (ending with ?, ？, 吗, 吧).
        App layer can extend via Pluggable hooks.
        """
        stripped = text.strip()
        if stripped.endswith(("?", "？", "吗", "吧")):
            return False
        lower = stripped.lower()
        return any(marker.lower() in lower for marker in self.NEGATION_MARKERS)

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

    # -- Core sensing --------------------------------------------------------

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
                "wrong": correction[0],
                "correct": correction[1],
            }
        async for _name, r in self._run_plugs("feel_input", text):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def feel_output(
        self,
        output: str,
        expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "length": len(output),
            "empty": not output.strip(),
        }
        self._recent_outputs.append(output)
        if len(self._recent_outputs) > self._max_recent:
            self._recent_outputs.pop(0)
        async for _name, r in self._run_plugs(
            "feel_output", output, expected_schema
        ):
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

    def check_hallucination(  # type: ignore[override]
        self,
        reply: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"hallucination": False}
        for _name, r in self._run_plugs_sync("check_hallucination", reply, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result

    # v1.1.26: curiosity-driven blind spot detection
    async def detect_blind_spot(
        self,
        recent_queries: list[str],
        known_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Default: returns empty — no blind spots detected.

        App layer can mount a ``"detect_blind_spot"`` plug to enable.
        """
        async for _name, r in self._run_plugs(
            "detect_blind_spot",
            recent_queries,
            known_topics or [],
        ):
            if isinstance(r, list):
                return r
        return []


# =========================================================================
# Helper utilities
# =========================================================================


def _extract_keywords(
    text: str, top_k: int = 5, stop_words: frozenset[str] | None = None
) -> list[str]:
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
    """CJK detection: returns "zh" if >30% CJK characters, else "en"."""
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if cjk > len(text) * 0.3:
        return "zh"
    return "en"


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
        g = text[i : i + n]
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
    printable = set(_string.printable)
    nonprint = sum(1 for c in text if c not in printable)
    return nonprint / len(text)


def _jaccard(a: str, b: str, n: int = 3) -> float:
    """n-gram Jaccard similarity between two strings.

    Useful for drift detection — compare current vs historical output.
    """

    def _ngrams(s: str) -> set[str]:
        return {s[i : i + n] for i in range(len(s) - n + 1)}

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
    patterns = [
        re.compile(r"\b\d+\s*(?:KB|MB|GB|ms|s|px|%)\b"),  # numeric+unit
        re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b"),  # CamelCase
        re.compile(
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
            re.IGNORECASE,
        ),  # months
        re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # ISO date
        re.compile(r"[/\\][\w./\\-]+\b"),  # file paths
    ]
    return any(p.search(text) for p in patterns)
