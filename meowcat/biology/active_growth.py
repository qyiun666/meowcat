# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ActiveGrowth — cat's self-driven growth: curiosity, tool evolution, reflex evolution.

Note: The module name ``active_growth`` is a domain category (not a class name).
It aggregates three closely-related growth components — see :class:`ActiveGrowthPack`
for one-line install.

v1.1.26: Three active growth pillars that make the cat self-improving:

- **BlindSpotDetector**: curiosity-driven — detects knowledge gaps from queries
- **ToolFailureLearner**: tool evolution — learns from execution failures
- **HotPathObserver**: reflex evolution — promotes frequently used paths to reflexes

All three are Pluggable (socket-style): framework provides default algorithms,
app-layer can swap any component.

Usage::

    from meowcat.biology.active_growth import (
        BlindSpotDetector, ToolFailureLearner, HotPathObserver,
    )

    # Curiosity: detect what the cat doesn't know
    bsd = BlindSpotDetector()
    spots = bsd.detect(["How does Kubernetes work?", "What is Redis?"],
                        known_topics=["Python", "SQL"])
    # → [{"topic": "Kubernetes", "novelty": 0.8}, ...]

    # Tool evolution: learn from failures
    tfl = ToolFailureLearner()
    tfl.record("read_file", {"path": "/nonexistent"}, "FileNotFound", 120)
    failures = tfl.hotspots()  # → [("read_file", 1)]

    # Reflex evolution: observe hot paths
    hpo = HotPathObserver()
    hpo.record("text_dialogue")
    hpo.record("text_dialogue")
    hpo.record("text_dialogue")
    promoted = hpo.detect()  # → ["text_dialogue"]
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from meowcat.pluggable import Pluggable

# ════════════════════════════════════════════════════════════════════
# BlindSpotDetector — curiosity-driven knowledge gap detection
# ════════════════════════════════════════════════════════════════════


class BlindSpotDetector(Pluggable):
    """Curiosity-driven blind spot detector.

    Analyses recent user queries against known topics to surface
    knowledge gaps — topics the cat should explore and learn about.

    Framework layer: provides ``detect()`` algorithm + plugin slot.
    App layer: decides when to call (after each session? daily?) and
    what to do with results (auto-learn? suggest to user?).

    Args:
        novelty_threshold: Minimum novelty score (0.0-1.0) to flag as blind spot.
            Default 0.5 — anything half-unfamiliar counts.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "detector": {"in": "queries: list[str], known: list[str]", "out": "list[dict] | None"},
    }

    __slots__ = ("_novelty_threshold",)

    def __init__(self, novelty_threshold: float = 0.5) -> None:
        super().__init__()
        self._novelty_threshold = novelty_threshold

    # -- Core API ------------------------------------------------------

    async def detect(
        self,
        recent_queries: list[str],
        known_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect blind spots from recent queries.

        Compares query keywords against known topics. Terms that appear
        frequently in queries but are missing from known topics are
        flagged as blind spots.

        Args:
            recent_queries: List of recent user queries or conversation topics.
            known_topics: Topics the cat already knows. If None, treats
                everything as novel.

        Returns:
            List of ``{topic, novelty, evidence}`` dicts sorted by novelty desc.
        """
        # Plugin slot
        async for _name, r in self._run_plugs("detector", recent_queries, known_topics or []):
            if isinstance(r, list):
                return r

        return _default_blind_spot_detect(
            recent_queries,
            known_topics or [],
            self._novelty_threshold,
        )

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "novelty_threshold": self._novelty_threshold,
            "plugs": self.list_plugs(),
        }


def _default_blind_spot_detect(
    queries: list[str],
    known: list[str],
    threshold: float,
) -> list[dict[str, Any]]:
    """Default blind spot detection: keyword-based novelty analysis.

    Extracts capitalized nouns, technical terms (CamelCase/snake_case),
    and domain keywords from queries. Flags those absent from known topics.
    """
    if not queries:
        return []

    known_lower = {k.lower() for k in known}

    # Extract candidate terms: CamelCase, snake_case, tech acronyms, 2+ char words
    term_counter: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)

    tech_pattern = re.compile(
        r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b"  # CamelCase
        r"|\b([a-z]+(?:_[a-z]+)+)\b"  # snake_case
        r"|\b([A-Z]{2,})\b"  # ACRONYMS
        r"|\b([A-Z][a-z]+)\b",  # Proper nouns
    )

    for q in queries:
        for m in tech_pattern.finditer(q):
            term = next(g for g in m.groups() if g is not None)
            term_counter[term] += 1
            evidence[term].append(q[:80])

    # Filter: not in known, above threshold
    total_queries = len(queries)
    spots: list[dict[str, Any]] = []
    for term, count in term_counter.most_common():
        if term.lower() in known_lower:
            continue
        novelty = min(count / max(total_queries, 1), 1.0)
        if novelty < threshold:
            continue
        spots.append(
            {
                "topic": term,
                "novelty": round(novelty, 2),
                "count": count,
                "evidence": evidence[term][:3],
            }
        )

    return spots


# ════════════════════════════════════════════════════════════════════
# ToolFailureLearner — learn from tool execution failures
# ════════════════════════════════════════════════════════════════════


class ToolFailureLearner(Pluggable):
    """Tool evolution learner — records and analyses tool failure patterns.

    Tracks which tools fail, how often, and under what conditions.
    Surfaces hotspots that need attention or deprecation.

    Framework layer: provides ``record()`` + ``hotspots()`` + plugin slot.
    App layer: calls ``record()`` from PawsEngine on failure, decides
    corrective action (retry strategy, tool deprecation, user alert).

    Args:
        max_records: Maximum failure records to keep (FIFO).
    """

    HOOKS: dict[str, dict[str, str]] = {
        "on_failure": {"in": "tool: str, params: dict, error: str, elapsed: float", "out": "None"},
    }

    __slots__ = ("_records", "_max_records")

    def __init__(self, max_records: int = 200) -> None:
        super().__init__()
        self._max_records = max_records
        self._records: list[dict[str, Any]] = []

    # -- Core API ------------------------------------------------------

    async def record(
        self,
        tool_name: str,
        params: dict[str, Any],
        error: str,
        elapsed_ms: float = 0,
    ) -> None:
        """Record a tool execution failure.

        Args:
            tool_name: Name of the failed tool.
            params: Parameters that were passed.
            error: Error message or exception string.
            elapsed_ms: Execution time before failure.
        """
        # Plugin hook — fire-and-forget
        async for _name, _r in self._run_plugs(
            "on_failure",
            tool_name,
            params,
            error,
            elapsed_ms,
        ):
            pass

        self._records.append(
            {
                "tool": tool_name,
                "params": {k: str(v)[:100] for k, v in params.items()},
                "error": error[:200],
                "elapsed_ms": elapsed_ms,
            }
        )

        # FIFO eviction
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

    def hotspots(self, min_failures: int = 2) -> list[tuple[str, int, dict[str, Any]]]:
        """Return tools ranked by failure count.

        Args:
            min_failures: Minimum failure count to surface.

        Returns:
            List of ``(tool_name, failure_count, latest_error)`` tuples.
        """
        counter: Counter[str] = Counter()
        latest: dict[str, dict[str, Any]] = {}
        for r in self._records:
            t = r["tool"]
            counter[t] += 1
            latest[t] = r

        result = [
            (tool, count, latest[tool])
            for tool, count in counter.most_common()
            if count >= min_failures
        ]
        return result

    def fail_count(self, tool_name: str | None = None) -> int:
        """Count failures for a specific tool or all tools.

        Args:
            tool_name: Specific tool, or None for total.

        Returns:
            Failure count.
        """
        if tool_name:
            return sum(1 for r in self._records if r["tool"] == tool_name)
        return len(self._records)

    def reset(self) -> None:
        """Clear all failure records."""
        self._records.clear()

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "total_failures": len(self._records),
            "hotspots": [(t, c) for t, c, _ in self.hotspots(min_failures=1)],
            "plugs": self.list_plugs(),
        }


# ════════════════════════════════════════════════════════════════════
# HotPathObserver — reflex arc evolution via frequency observation
# ════════════════════════════════════════════════════════════════════


class HotPathObserver(Pluggable):
    """Reflex evolution observer — promotes frequently used paths.

    Tracks reflex trigger frequency and detects hot paths that should
    be optimised into dedicated reflex arcs.

    Framework layer: provides ``record()`` + ``detect()`` + plugin slot.
    App layer: calls ``record()`` from ReflexArc.perceive(), uses
    ``detect()`` to decide which paths to promote.

    Args:
        min_triggers: Minimum trigger count to promote to hot path (default 5).
    """

    HOOKS: dict[str, dict[str, str]] = {
        "observer": {"in": "counts: dict[str,int], total: int", "out": "list[str] | None"},
    }

    __slots__ = ("_counts", "_total", "_min_triggers")

    def __init__(self, min_triggers: int = 5) -> None:
        super().__init__()
        self._min_triggers = min_triggers
        self._counts: dict[str, int] = {}
        self._total: int = 0

    # -- Core API ------------------------------------------------------

    def record(self, reflex_name: str) -> None:
        """Record a reflex trigger event.

        Args:
            reflex_name: Name of the triggered reflex (e.g. "text_dialogue").
        """
        self._counts[reflex_name] = self._counts.get(reflex_name, 0) + 1
        self._total += 1

    async def detect(self, min_triggers: int | None = None) -> list[str]:
        """Detect hot paths — reflexes that exceed the trigger threshold.

        Args:
            min_triggers: Override the default minimum trigger count.

        Returns:
            List of reflex names sorted by trigger count descending.
        """
        threshold = min_triggers if min_triggers is not None else self._min_triggers

        # Plugin slot
        async for _name, r in self._run_plugs("observer", dict(self._counts), self._total):
            if isinstance(r, list):
                return r

        return [
            name
            for name, count in sorted(self._counts.items(), key=lambda x: -x[1])
            if count >= threshold
        ]

    def stats(self) -> dict[str, int]:
        """Return current per-reflex trigger counts (read-only copy)."""
        return dict(self._counts)

    @property
    def total(self) -> int:
        """Total trigger events recorded."""
        return self._total

    def reset(self) -> None:
        """Clear all trigger records."""
        self._counts.clear()
        self._total = 0

    async def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "total_triggers": self._total,
            "unique_reflexes": len(self._counts),
            "hot_paths": await self.detect(),
            "counts": dict(self._counts),
            "plugs": self.list_plugs(),
        }


__all__ = ["BlindSpotDetector", "ToolFailureLearner", "HotPathObserver"]
