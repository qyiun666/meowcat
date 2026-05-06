# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus Crystallizer L1+L2+L3 — tool-usage detection → auto-crystallize Skills/Chains/Knowledge.

Three-layer crystallisation:

- **L1**: frequency hotspots → promote to Skills (``record`` + ``detect``)
- **L2**: repeated Path sequences → auto-register Chains (``record_sequence`` + ``detect_patterns``)
- **L3**: high-confidence corrections → permanent knowledge entities (``record_correction`` + ``detect_knowledge``)

Pluggable design: swap detector, threshold, or pattern/knowledge logic.

Usage::

    from meowcat.plus.crystallizer import Crystallizer

    c = Crystallizer(threshold=0.6)

    # L1: tool frequency
    c.record("read_file")
    c.record("read_file")
    c.hotspots()  # → [("read_file", 2)]
    c.detect()    # → ["read_file"]

    # L2: Path-sequence patterns
    c.record_sequence(["locate", "deep_reason", "speak"])
    c.record_sequence(["locate", "deep_reason", "speak"])
    c.record_sequence(["locate", "deep_reason", "speak"])
    c.detect_patterns()  # → [(('locate','deep_reason','speak'), 3)]

    # L3: high-confidence corrections
    c.record_correction("python_version", "3.13", 0.95)
    c.detect_knowledge()  # → [{"key": "python_version", "value": "3.13", "confidence": 0.95}]

    # Pluggable: swap detector or threshold
    c.plug("detector", my_custom_detector)
    c.plug("threshold", 0.8)
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DefaultDetector:
    """Default crystallization detector: simple frequency heuristic.

    Crystallizes a slug when its usage ratio exceeds threshold.
    """

    def __call__(self, hits: dict[str, int], total: int, threshold: float) -> list[str]:
        if total < 1:
            return []
        return [slug for slug, count in hits.items()
                if count / total >= threshold]


class Crystallizer:
    """Tool-usage frequency tracker → auto-crystallize Skills.

    Records tool/skill usage, detects hotspots, and identifies candidates
    for crystallization into reusable skills.

    Args:
        threshold: Minimum frequency ratio to trigger crystallization (default 0.6).
        min_samples: Minimum records before detection kicks in (default 3).

    Pluggable slots:
        ``"detector"`` — custom ``(hits, total, threshold) → list[str]`` function.
        ``"threshold"`` — override threshold value (float).

    .. note:: (v1.2.33)

        Maintains its own internal hook/plugin wiring pattern rather
        than inheriting :class:`meowcat.pluggable.Pluggable`.
        Migration tracked in roadmap B31.
    """

    def __init__(self, *, threshold: float = 0.6, min_samples: int = 3) -> None:
        self._threshold = threshold
        self._min_samples = min_samples
        self._hits: dict[str, int] = {}
        self._total: int = 0
        # L2: sequence patterns
        self._sequences: dict[tuple[str, ...], int] = {}
        # L3: knowledge corrections
        self._corrections: dict[str, dict[str, Any]] = {}
        self._plugs: dict[str, Any] = {}

    # ── Pluggable slots ──────────────────────────────────────────

    def plug(self, slot: str, handler: Any) -> None:
        """Insert a custom handler. Slots: ``"detector"``, ``"threshold"``."""
        self._plugs[slot] = handler

    def unplug(self, slot: str) -> None:
        """Remove a custom handler."""
        self._plugs.pop(slot, None)

    # ── Core API ─────────────────────────────────────────────────

    def record(self, slug: str) -> None:
        """Record a tool/skill usage."""
        self._hits[slug] = self._hits.get(slug, 0) + 1
        self._total += 1

    def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        """Return slugs ranked by usage count, above *threshold* (default min_samples)."""
        t = threshold if threshold is not None else self._min_samples
        result = [(k, v) for k, v in self._hits.items() if v >= t]
        result.sort(key=lambda x: -x[1])
        return result

    def detect(self) -> list[str]:
        """Detect slugs that should crystallize into Skills.

        Runs the detector (default or plugged) against current usage data.
        """
        detector: Callable[..., list[str]] = self._plugs.get(
            "detector", DefaultDetector())
        thresh = self._resolve_threshold()
        return detector(self._hits, self._total, thresh)
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    # ── L2: Pattern Crystallization ─────────────────────────────────

    def record_sequence(self, seq: list[str]) -> None:
        """Record a Path sequence (ordered slug list).

        When the same sequence repeats 3+ times, ``detect_patterns()``
        suggests registering a ``meowcat.chain.Chain``.
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


        Args:
            seq: Ordered list of tool/skill/path slugs.
        """
        key = tuple(seq)
        self._sequences[key] = self._sequences.get(key, 0) + 1

    def detect_patterns(self, min_repeat: int = 3) -> list[tuple[tuple[str, ...], int]]:
        """Detect Path sequences that have repeated at least *min_repeat* times.

        Returns:
            List of ``(sequence, count)`` sorted by count descending.
        """
        result = [
            (seq, cnt) for seq, cnt in self._sequences.items()
            if cnt >= min_repeat
        ]
        result.sort(key=lambda x: -x[1])
        return result

    # ── L3: Knowledge Crystallization ───────────────────────────────

    def record_correction(
        self, key: str, value: Any, confidence: float = 0.5,
    ) -> None:
        """Record a correction event with confidence.

        When confidence exceeds 0.8, ``detect_knowledge()`` recommends
        writing a permanent entity to Cortex.

        Args:
            key: Knowledge key (e.g. snake_case topic).
            value: Correct value.
            confidence: Confidence score 0.0-1.0.
        """
        existing = self._corrections.get(key)
        if existing:
            existing["count"] = existing.get("count", 1) + 1
            if confidence > existing["confidence"]:
                existing["confidence"] = confidence
                existing["value"] = value
        else:
            self._corrections[key] = {
                "key": key, "value": value,
                "confidence": confidence, "count": 1,
            }

    def detect_knowledge(
        self, min_confidence: float = 0.8,
    ) -> list[dict[str, Any]]:
        """Detect high-confidence corrections ready for permanent Cortex storage.

        Args:
            min_confidence: Minimum confidence threshold (default 0.8).

        Returns:
            List of ``{key, value, confidence, count}`` dicts.
        """
        result = [
            v for v in self._corrections.values()
            if v["confidence"] >= min_confidence
        ]
        result.sort(key=lambda x: -x["confidence"])
        return result

    # ── Reset ───────────────────────────────────────────────────────

    def reset(self) -> None:
        """Clear all counters (L1 + L2 + L3)."""
        self._hits.clear()
        self._total = 0
        self._sequences.clear()
        self._corrections.clear()

    # ── Properties ───────────────────────────────────────────────

    @property
    def threshold(self) -> float:
        return self._resolve_threshold()

    @property
    def total(self) -> int:
        return self._total

    @property
    def unique_tools(self) -> int:
        return len(self._hits)

    # ── Internal ─────────────────────────────────────────────────

    def _resolve_threshold(self) -> float:
        plug = self._plugs.get("threshold")
        if plug is not None:
            return float(plug() if callable(plug) else plug)
        return self._threshold

