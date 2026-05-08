# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat tool matcher — keyword-based tool matching engine (v1.1.29).

Provides :class:`KeywordToolMatcher` — scores and ranks tools by keyword overlap
against user intent, with pluggable scoring strategy.

Separated from :class:`PawsEngine` so the matcher can be reused independently
(e.g., in command routing, reflex arc dispatch).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from meowcat.tools.tool import Tool, ToolRegistry

logger = logging.getLogger(__name__)


class KeywordToolMatcher:
    """Keyword-based tool matching engine.

    Scores tools by keyword overlap between user intent and tool metadata
    (name, description, category). Returns ranked results.

    Usage::

        matcher = KeywordToolMatcher(registry)
        results = matcher.match("read a file from disk")
        # → [Tool(name="read_file", score=15), Tool(name="read_dir", score=8), ...]

        top = matcher.best_match("read a file")
        # → Tool(name="read_file") or None

    **Pluggable scoring**::

        matcher.plug("scorer", my_custom_scorer)  # custom scoring function
        matcher.plug("filter", my_filter)          # pre-filter tools

    .. note:: (v1.2.33)

        Maintains its own ``_hooks`` / ``plug()`` / ``unplug()`` pattern
        that duplicates :class:`meowcat.pluggable.Pluggable`.
        Migration tracked in roadmap B31.
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    # -- Plugin system ---------------------------------------------------

    def plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """Register a hook callback ('scorer', 'filter')."""
        self._hooks.setdefault(hook, []).append(fn)

    def unplug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """Unregister hook callback(s)."""
        if hook not in self._hooks:
            return
        if fn is None:
            self._hooks.pop(hook, None)
        else:
            self._hooks[hook] = [f for f in self._hooks[hook] if f is not fn]

    # -- Core ------------------------------------------------------------

    def match(
        self,
        intent: str,
        *,
        top_n: int = 10,
        min_score: int = 1,
    ) -> list[tuple[Tool, int]]:
        """Match tools by keyword overlap, ranked by score descending.

        Returns:
            List of ``(tool, score)`` tuples, sorted highest score first.
        """
        if self.registry is None:
            return []

        q = intent.lower()
        query_keywords = set(_tokenize(q))

        results: list[tuple[int, Tool]] = []

        for tool in self.registry.list_all(enabled_only=True):
            # Run pre-filters
            skip = False
            for fn in self._hooks.get("filter", ()):
                if fn(tool):
                    skip = True
                    break
            if skip:
                continue

            # Run custom scorers first; if none, use default
            custom_scorers = self._hooks.get("scorer", [])
            if custom_scorers:
                score = 0
                for fn in custom_scorers:
                    score += fn(tool, query_keywords)
            else:
                score = self._default_score(tool, query_keywords)

            if score >= min_score:
                results.append((score, tool))

        # Sort by score descending, then by name for stability
        results.sort(key=lambda x: (-x[0], x[1].name))
        return [(t, s) for s, t in results[:top_n]]

    def best_match(self, intent: str) -> Tool | None:
        """Return the single best matching tool, or None."""
        results = self.match(intent, top_n=1)
        return results[0][0] if results else None

    # -- Default scoring --------------------------------------------------

    @staticmethod
    def _default_score(tool: Tool, query_keywords: set[str]) -> int:
        """Default keyword-overlap scoring.

        - Name exact match: +20
        - Name partial match: +10 per keyword
        - Description match: +5 per keyword
        - Category match: +3 per keyword
        """
        name_lower = tool.name.lower()
        desc_lower = tool.description.lower()
        cat_lower = tool.spec.category.lower()

        score = 0

        # Name scoring
        name_tokens = set(_tokenize(name_lower))
        name_overlap = query_keywords & name_tokens
        score += len(name_overlap) * 10

        # Exact name match bonus
        if name_lower == " ".join(query_keywords):
            score += 20

        # Description scoring
        desc_tokens = set(_tokenize(desc_lower))
        desc_overlap = query_keywords & desc_tokens
        score += len(desc_overlap) * 5

        # Category scoring
        cat_tokens = set(_tokenize(cat_lower))
        cat_overlap = query_keywords & cat_tokens
        score += len(cat_overlap) * 3

        return score


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: split on non-alphanumeric boundaries, filter short tokens."""
    import re

    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


__all__ = ["KeywordToolMatcher"]
