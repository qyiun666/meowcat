# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) sense organ implementations — 3 classes."""

from __future__ import annotations

import re
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopEars,
    NoopEyes,
    NoopWhiskers,
)
from meowcat.defaults.presets import (
    KW_BILINGUAL,
    KeywordPreset,
)

from ._helpers import _detect_language, _extract_keywords

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
        self,
        output: str,
        expected_schema: dict[str, Any] | None = None,
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
        self,
        reply: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"hallucination": False}
        for _name, r in self._run_plugs_sync("check_hallucination", reply, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result
