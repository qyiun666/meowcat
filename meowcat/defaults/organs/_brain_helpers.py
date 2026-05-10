# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Shared helpers for brain organ implementations (split from brain.py)."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meowcat.defaults.presets import KeywordPreset


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


def _detect_command(text: str, kw: "KeywordPreset | None") -> str | None:
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
