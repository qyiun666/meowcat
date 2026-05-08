# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Helper utilities shared across renovated organ implementations."""

from __future__ import annotations

import re
import string as _string


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
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    if cjk > len(text) * 0.3:
        return "zh"
    return "en"


def _detect_command(text: str, kw) -> str | None:
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
        g = text[i: i + n]
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
        return {s[i: i + n] for i in range(len(s) - n + 1)}

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
        _re.compile(r"\b\d+\s*(?:KB|MB|GB|ms|s|px|%)\b"),  # numeric+unit
        _re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b"),  # CamelCase
        _re.compile(
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", _re.IGNORECASE
        ),  # months
        _re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # ISO date
        _re.compile(r"[/\\][\w./\\-]+\b"),  # file paths
    ]
    return any(p.search(text) for p in patterns)
