# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""RememberPolicy — three-level backoff for memory writing with pre-filtering.

T-17 (v1.3.6): Framework-level base class providing a decision gate before
``Hippocampus.remember()``.  App layer configures thresholds and can override
individual tier methods for custom policies.

Three tiers:

- **Level 1 (ALWAYS)**:  Distinct new content, no similar entry in recent
  window → pass through unconditionally.
- **Level 2 (THROTTLE)**: Similar content exists in recent window but still
  below duplicate cap → apply cooldown before re-remembering.
- **Level 3 (SKIP)**:   Too many similar entries in recent window →
  skip entirely to avoid memory bloat.

Also applies pre-filtering — content length check and optional noise
pattern exclusion — before tier evaluation.

Usage::

    policy = RememberPolicy(
        cooldown_seconds=60.0,
        similarity_threshold=0.6,
        min_content_length=10,
    )

    if await policy.should_remember(user_msg, ai_reply):
        await hippocampus.remember(user_msg, ai_reply, cat_uid, model)
        policy.record(user_msg, ai_reply)
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class RememberConfig:
    """Three-level backoff thresholds and pre-filter settings.

    Attributes:
        cooldown_seconds:       Minimum interval (seconds) between
                                re-remembering similar content (Level 2).
        similarity_threshold:   Jaccard-like similarity ratio above which
                                two messages are considered similar (0..1).
        min_content_length:     Messages shorter than this (chars) are
                                skipped by pre-filter.
        max_recent_duplicates:  Number of similar entries allowed in recent
                                window before escalating to Level 3 (SKIP).
        recent_window_size:     How many recent entries to check for
                                similarity scoring.
        noise_patterns:         Optional list of regex patterns for content
                                that should always be filtered out (e.g.
                                pure acknowledgements like "OK", "Got it").
    """

    cooldown_seconds: float = 60.0
    similarity_threshold: float = 0.6
    min_content_length: int = 10
    max_recent_duplicates: int = 3
    recent_window_size: int = 20
    noise_patterns: list[str] = field(default_factory=list)


# ── RememberPolicy ────────────────────────────────────────────────────


class RememberPolicy:
    """Three-level backoff for memory writing with pre-filtering.

    Decision flow::

        pre_filter(user_msg, ai_reply)
          ├── rejected (too short / noise) → False
          └── passed
               └── _evaluate_tier(user_msg, ai_reply)
                     ├── Level 1: no similar in window → True
                     ├── Level 2: similar but below cap → cooldown check
                     └── Level 3: too many similar → False

    App layer can override ``_pre_filter``, ``_evaluate_tier``, or
    individual tier methods for custom logic.
    """

    def __init__(
        self,
        cooldown_seconds: float = 60.0,
        similarity_threshold: float = 0.6,
        min_content_length: int = 10,
        max_recent_duplicates: int = 3,
        recent_window_size: int = 20,
        noise_patterns: Sequence[str] | None = None,
    ) -> None:
        self._config = RememberConfig(
            cooldown_seconds=cooldown_seconds,
            similarity_threshold=similarity_threshold,
            min_content_length=min_content_length,
            max_recent_duplicates=max_recent_duplicates,
            recent_window_size=recent_window_size,
            noise_patterns=list(noise_patterns or []),
        )
        self._noise_re: list[re.Pattern[str]] = [
            re.compile(p) for p in self._config.noise_patterns
        ]
        # Internal tracking: list of (timestamp, user_msg, ai_reply)
        self._history: list[tuple[float, str, str]] = []

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> RememberConfig:
        """Current policy configuration (read-only copy)."""
        return RememberConfig(
            cooldown_seconds=self._config.cooldown_seconds,
            similarity_threshold=self._config.similarity_threshold,
            min_content_length=self._config.min_content_length,
            max_recent_duplicates=self._config.max_recent_duplicates,
            recent_window_size=self._config.recent_window_size,
            noise_patterns=list(self._config.noise_patterns),
        )

    # ── Main entry ─────────────────────────────────────────────────

    async def should_remember(self, user_msg: str, ai_reply: str) -> bool:
        """Decide whether to write this exchange to hippocampus.

        Args:
            user_msg:  The user's message.
            ai_reply:  The AI's reply.

        Returns:
            ``True`` if the exchange passes pre-filter and backoff checks.
        """
        # Pre-filter: noise + minimum content length
        if not self._pre_filter(user_msg, ai_reply):
            return False

        # Tier evaluation
        return self._evaluate_tier(user_msg, ai_reply)

    def record(self, user_msg: str, ai_reply: str) -> None:
        """Record an exchange that was written to memory.

        Call this **after** ``hippocampus.remember()`` so the policy
        tracks what has been persisted.

        Args:
            user_msg:  The user's message that was remembered.
            ai_reply:  The AI's reply that was remembered.
        """
        self._history.append((time.monotonic(), user_msg, ai_reply))
        # Trim history to recent window
        if len(self._history) > self._config.recent_window_size:
            self._history = self._history[-self._config.recent_window_size:]

    # ── Pre-filter (overridable) ───────────────────────────────────

    def _pre_filter(self, user_msg: str, ai_reply: str) -> bool:
        """Pre-filter: check content quality before tier evaluation.

        Returns ``False`` to reject immediately (noise / too short).
        Override to add custom quality checks.
        """
        combined = f"{user_msg} {ai_reply}".strip()

        # Minimum content length
        if len(combined) < self._config.min_content_length:
            return False

        # Noise pattern matching
        for pat in self._noise_re:
            if pat.search(combined):
                return False

        return True

    # ── Tier evaluation (overridable) ──────────────────────────────

    def _evaluate_tier(self, user_msg: str, ai_reply: str) -> bool:
        """Evaluate which backoff tier applies.

        Level 1 → ALWAYS (no similar in window)
        Level 2 → THROTTLE (similar but under cap)
        Level 3 → SKIP (too many similar)
        """
        similar_count, last_ts = self._count_similar(user_msg, ai_reply)

        if similar_count == 0:
            return self._level1_always(user_msg, ai_reply)

        if similar_count < self._config.max_recent_duplicates:
            return self._level2_throttle(user_msg, ai_reply, last_ts)

        return self._level3_skip(user_msg, ai_reply, similar_count)

    def _level1_always(self, user_msg: str, ai_reply: str) -> bool:
        """Level 1: distinct content — always remember."""
        return True

    def _level2_throttle(
        self,
        user_msg: str,
        ai_reply: str,
        last_similar_ts: float,
    ) -> bool:
        """Level 2: similar content exists — apply cooldown.

        Returns ``True`` only if cooldown period has elapsed since
        the last similar entry.
        """
        elapsed = time.monotonic() - last_similar_ts
        return elapsed >= self._config.cooldown_seconds

    def _level3_skip(
        self,
        user_msg: str,
        ai_reply: str,
        similar_count: int,
    ) -> bool:
        """Level 3: too many similar entries — skip."""
        return False

    # ── Similarity helpers ─────────────────────────────────────────

    def _count_similar(
        self, user_msg: str, ai_reply: str,
    ) -> tuple[int, float]:
        """Count similar entries in recent history.

        Returns:
            ``(count, last_timestamp)`` — count of similar entries and
            the monotonic timestamp of the most recent one.
        """
        count = 0
        last_ts = 0.0
        for ts, u, a in self._history:
            if self._is_similar(user_msg, ai_reply, u, a):
                count += 1
                last_ts = ts
        return count, last_ts

    def _is_similar(
        self,
        msg1: str, reply1: str,
        msg2: str, reply2: str,
    ) -> bool:
        """Check whether two exchanges are considered similar.

        Uses Jaccard-like word overlap on the concatenated text.
        Override for semantic similarity (embedding-based, etc.).
        """
        text1 = _normalize(f"{msg1} {reply1}")
        text2 = _normalize(f"{msg2} {reply2}")

        if not text1 or not text2:
            return False

        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 or not set2:
            return False

        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) >= self._config.similarity_threshold

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "cooldown_seconds": self._config.cooldown_seconds,
            "similarity_threshold": self._config.similarity_threshold,
            "min_content_length": self._config.min_content_length,
            "max_recent_duplicates": self._config.max_recent_duplicates,
            "recent_window_size": self._config.recent_window_size,
            "noise_patterns": list(self._config.noise_patterns),
            "history_size": len(self._history),
        }


# ── Internal helpers ─────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Lowercase + strip non-word chars for similarity comparison."""
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()
