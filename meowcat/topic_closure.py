# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""TopicClosureDetector — topic closure detection and lifecycle management.

T-23 (v1.3.6): Framework-level base class providing a four-stage pipeline
for detecting, summarising, decaying, and injecting closed topics into the
cortex belief system.

Lifecycle hooks (called in order)::

    detect(user_msg, ai_reply)       → TopicClosureResult
    summarize(topic_context)         → summary: str
    decay(topic_id)                  → None
    inject_to_cortex(summary)        → None

The framework defines the hook signatures; the app layer registers signal
words (e.g. "好的", "谢谢", "OK", "bye") and optionally overrides each
hook for custom logic (LLM-based summarise, semantic decay, etc.).

Usage::

    detector = TopicClosureDetector(
        closure_signal_words=["好的", "谢谢", "bye", "OK", "明白了"],
        min_exchange_count=3,
        decay_cooldown=300.0,
    )

    result = detector.detect(user_msg, ai_reply)
    if result.is_closed:
        summary = await detector.summarize(result.topic_context)
        detector.decay(result.topic_id)
        await detector.inject_to_cortex(summary)
        detector.record_closure(result)
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class TopicClosureConfig:
    """Topic closure detection thresholds and settings.

    Attributes:
        closure_signal_words:  Words/phrases that indicate a user is
                               closing or wrapping up a topic.  Matched
                               case-insensitively against the user message.
        min_exchange_count:    Minimum number of exchanges before closure
                               detection activates (prevents false positives
                               in the first few turns).
        decay_cooldown:        Seconds before a closed topic can be
                               re-opened (avoids thrashing).
        max_closed_topics:     Maximum number of closed topics to retain
                               in history before eviction.
        require_ai_ack:        If ``True``, the AI reply must also contain
                               an acknowledgement-like pattern for closure
                               to be detected.
        token_window:          Number of recent tokens (from topic_context)
                               to include in the summary input.
    """

    closure_signal_words: list[str] = field(
        default_factory=lambda: [
            "好的",
            "谢谢",
            "thanks",
            "thank you",
            "OK",
            "ok",
            "bye",
            "goodbye",
            "再见",
            "拜拜",
            "明白了",
            "got it",
            "就这样",
            "that's all",
            "没问题",
            "no problem",
            "结束",
            "done",
            "完成",
            "搞定",
            "清楚了",
            "clear",
        ]
    )
    min_exchange_count: int = 3
    decay_cooldown: float = 300.0
    max_closed_topics: int = 50
    require_ai_ack: bool = False
    token_window: int = 1000


# ── Result dataclass ──────────────────────────────────────────────────


@dataclass
class TopicClosureResult:
    """Outcome of topic closure detection.

    Attributes:
        is_closed:       Whether a topic closure was detected.
        matched_word:    The specific signal word/phrase that triggered
                         the detection, or empty string if none.
        topic_context:   Relevant context lines (recent exchanges) for
                         summarisation.
        topic_id:        A stable identifier derived from the matched
                         word and timestamp, for decay tracking.
        confidence:      Detection confidence (0..1).  Based on matched
                         word weight + exchange count.
    """

    is_closed: bool = False
    matched_word: str = ""
    topic_context: list[str] = field(default_factory=list)
    topic_id: str = ""
    confidence: float = 0.0


# ── TopicClosureDetector ──────────────────────────────────────────────


class TopicClosureDetector:
    """Topic closure detection and lifecycle management base class.

    Detection pipeline::

        detect(user_msg, ai_reply)
          ├── exchange count check (min_exchange_count)
          ├── signal word match against user message
          ├── optional AI acknowledgement check
          └── → TopicClosureResult

    After detection, the app layer invokes the lifecycle hooks in order:
    ``summarize → decay → inject_to_cortex``.

    App layer can override any hook (``detect``, ``summarize``,
    ``decay``, ``inject_to_cortex``) for custom logic, e.g. LLM-based
    summarisation or semantic decay.
    """

    # ── Default signal words (class-level, safe to reference) ──────

    DEFAULT_SIGNAL_WORDS: list[str] = [
        "好的",
        "谢谢",
        "thanks",
        "thank you",
        "OK",
        "ok",
        "bye",
        "goodbye",
        "再见",
        "拜拜",
        "明白了",
        "got it",
        "就这样",
        "that's all",
        "没问题",
        "no problem",
        "结束",
        "done",
        "完成",
        "搞定",
        "清楚了",
        "clear",
    ]

    # ── Weight map: higher → stronger closure signal ────────────────

    DEFAULT_SIGNAL_WEIGHTS: dict[str, float] = {
        "好的": 0.6,
        "谢谢": 0.5,
        "thanks": 0.5,
        "thank you": 0.6,
        "OK": 0.3,
        "ok": 0.3,
        "bye": 0.9,
        "goodbye": 0.9,
        "再见": 0.9,
        "拜拜": 0.9,
        "明白了": 0.7,
        "got it": 0.7,
        "清楚了": 0.7,
        "clear": 0.5,
        "就这样": 0.8,
        "that's all": 0.8,
        "结束": 0.9,
        "done": 0.7,
        "完成": 0.7,
        "搞定": 0.7,
        "没问题": 0.4,
        "no problem": 0.4,
    }

    def __init__(
        self,
        closure_signal_words: Sequence[str] | None = None,
        min_exchange_count: int = 3,
        decay_cooldown: float = 300.0,
        max_closed_topics: int = 50,
        require_ai_ack: bool = False,
        token_window: int = 1000,
    ) -> None:
        self._config = TopicClosureConfig(
            closure_signal_words=(
                list(closure_signal_words)
                if closure_signal_words is not None
                else self.DEFAULT_SIGNAL_WORDS
            ),
            min_exchange_count=min_exchange_count,
            decay_cooldown=decay_cooldown,
            max_closed_topics=max_closed_topics,
            require_ai_ack=require_ai_ack,
            token_window=token_window,
        )
        # Pre-compile signal word patterns (case-insensitive)
        self._signal_re: list[tuple[str, re.Pattern[str]]] = [
            (w, re.compile(re.escape(w), re.IGNORECASE)) for w in self._config.closure_signal_words
        ]
        # Per-word weight overrides (merged with DEFAULT_SIGNAL_WEIGHTS)
        self._signal_weights: dict[str, float] = dict(
            self.DEFAULT_SIGNAL_WEIGHTS)
        # Internal tracking
        self._exchange_count: int = 0
        self._recent_context: list[str] = []  # sliding window of exchanges
        self._closed_topics: list[dict[str, Any]] = []  # closed topic history

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> TopicClosureConfig:
        """Current configuration (read-only copy)."""
        return TopicClosureConfig(
            closure_signal_words=list(self._config.closure_signal_words),
            min_exchange_count=self._config.min_exchange_count,
            decay_cooldown=self._config.decay_cooldown,
            max_closed_topics=self._config.max_closed_topics,
            require_ai_ack=self._config.require_ai_ack,
            token_window=self._config.token_window,
        )

    # ── Main entry: detect ─────────────────────────────────────────

    def detect(self, user_msg: str, ai_reply: str) -> TopicClosureResult:
        """Detect whether the current exchange signals topic closure.

        Checks in order:
        1. Exchange count ≥ min_exchange_count
        2. User message matches a registered signal word
        3. (Optional) AI reply contains an acknowledgement-like pattern

        Args:
            user_msg:  The user's message.
            ai_reply:  The AI's reply.

        Returns:
            ``TopicClosureResult`` with detection outcome, matched word,
            context, and confidence.
        """
        # Update exchange tracking
        self._exchange_count += 1
        exchange_text = f"User: {user_msg}\nAI: {ai_reply}"
        self._recent_context.append(exchange_text)
        # Trim context to token_window (characters as rough proxy)
        self._trim_context()

        # Minimum exchange count gate
        if self._exchange_count < self._config.min_exchange_count:
            return TopicClosureResult()

        return self._detect_impl(user_msg, ai_reply)

    def _detect_impl(
        self,
        user_msg: str,
        ai_reply: str,
    ) -> TopicClosureResult:
        """Core detection logic (overridable)."""
        # Match signal words in user message
        matched_word = self._match_signal(user_msg)
        if not matched_word:
            return TopicClosureResult()

        # Optional AI acknowledgement check
        if self._config.require_ai_ack and not self._check_ai_ack(ai_reply):
            return TopicClosureResult()

        # Build result
        confidence = self._compute_confidence(matched_word)
        topic_id = _make_topic_id(matched_word, time.monotonic())

        return TopicClosureResult(
            is_closed=True,
            matched_word=matched_word,
            topic_context=list(self._recent_context),
            topic_id=topic_id,
            confidence=confidence,
        )

    # ── Lifecycle hooks (overridable) ──────────────────────────────

    async def summarize(self, topic_context: list[str]) -> str:
        """Summarise the closing topic from context.

        Framework default returns a simple concatenation of recent
        context lines.  Override for LLM-based summarisation.

        Args:
            topic_context:  Recent exchange lines leading up to closure.

        Returns:
            A summary string describing the closed topic.
        """
        if not topic_context:
            return ""
        # Simple default: concatenate with truncation
        joined = "\n".join(topic_context)
        if len(joined) <= self._config.token_window:
            return joined
        return joined[: self._config.token_window] + "…"

    def decay(self, topic_id: str) -> None:
        """Decay or archive a closed topic.

        Framework default marks the topic as closed with a timestamp
        in the internal history.  Override for custom decay logic
        (e.g. semantic similarity merging with prior topics).

        Args:
            topic_id:  The topic identifier from detection result.
        """
        now = time.monotonic()

        # Check cooldown: if this topic was recently closed, skip
        for entry in self._closed_topics:
            if entry.get("topic_id") == topic_id:
                return  # already recorded

        self._closed_topics.append(
            {
                "topic_id": topic_id,
                "closed_at": now,
            }
        )

        # Evict oldest if over limit
        while len(self._closed_topics) > self._config.max_closed_topics:
            self._closed_topics.pop(0)

    async def inject_to_cortex(self, summary: str) -> None:
        """Inject topic summary into the cortex belief system.

        Framework default is a no-op.  Override to integrate with
        ``Cortex.synthesize()`` or other worldview update mechanisms.

        Args:
            summary:  The topic summary string from ``summarize()``.
        """
        # Default: no-op.  App layer hooks into cortex here.
        pass

    # ── Post-detection recording ───────────────────────────────────

    def record_closure(self, result: TopicClosureResult) -> None:
        """Record a detected closure and reset exchange tracking.

        Call this after the full lifecycle (summarize → decay →
        inject_to_cortex) to reset counters for the next topic.

        Args:
            result:  The detection result that was acted upon.
        """
        self._exchange_count = 0
        self._recent_context.clear()

    # ── Signal word management ─────────────────────────────────────

    def register_signal_word(self, word: str, weight: float = 0.5) -> None:
        """Register a new closure signal word at runtime.

        Args:
            word:   The word or phrase to register.
            weight: Closure signal weight (0..1).  Higher = stronger
                    closure signal.  Default 0.5.
        """
        if word not in self._config.closure_signal_words:
            self._config.closure_signal_words.append(word)
            self._signal_re.append(
                (word, re.compile(re.escape(word), re.IGNORECASE)))
        self._signal_weights[word] = weight

    def unregister_signal_word(self, word: str) -> None:
        """Remove a previously registered signal word.

        Args:
            word:  The word or phrase to remove.
        """
        if word in self._config.closure_signal_words:
            self._config.closure_signal_words.remove(word)
            self._signal_re = [(w, p) for w, p in self._signal_re if w != word]
        self._signal_weights.pop(word, None)

    # ── Internal helpers ───────────────────────────────────────────

    def _match_signal(self, user_msg: str) -> str:
        """Match the user message against registered signal words.

        Returns the first matched word, or empty string if no match.
        """
        for word, pat in self._signal_re:
            if pat.search(user_msg):
                return word
        return ""

    def _check_ai_ack(self, ai_reply: str) -> bool:
        """Check if AI reply contains an acknowledgement-like pattern.

        Framework default: returns ``True`` always (disabled).
        Override for custom acknowledgement detection.
        """
        return True

    def _compute_confidence(self, matched_word: str) -> float:
        """Compute detection confidence (0..1) based on matched word
        weight and exchange count.

        Args:
            matched_word:  The signal word that triggered detection.

        Returns:
            Confidence score (0..1).
        """
        base = self._score_signal_words(matched_word)
        # Boost confidence with more exchanges (logarithmic)
        exchange_bonus = min(0.3, self._exchange_count * 0.02)
        return min(1.0, base + exchange_bonus)

    def _score_signal_words(self, matched_word: str) -> float:
        """Score a matched signal word (0..1) from registered weights.

        Looks up the word in instance-level ``_signal_weights`` first,
        then falls back to ``DEFAULT_SIGNAL_WEIGHTS``, then to 0.5.

        Overridable for custom weighting logic.

        Args:
            matched_word:  The signal word to score.

        Returns:
            Weight score (0..1).  Higher = stronger closure signal.
        """
        return self._signal_weights.get(
            matched_word,
            self.DEFAULT_SIGNAL_WEIGHTS.get(matched_word, 0.5),
        )

    def _trim_context(self) -> None:
        """Trim recent context to stay within token_window (char-based)."""
        total = sum(len(line) for line in self._recent_context)
        while total > self._config.token_window and len(self._recent_context) > 1:
            removed = self._recent_context.pop(0)
            total -= len(removed)

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "closure_signal_words": list(self._config.closure_signal_words),
            "min_exchange_count": self._config.min_exchange_count,
            "decay_cooldown": self._config.decay_cooldown,
            "max_closed_topics": self._config.max_closed_topics,
            "require_ai_ack": self._config.require_ai_ack,
            "token_window": self._config.token_window,
            "exchange_count": self._exchange_count,
            "context_size": len(self._recent_context),
            "closed_topics_count": len(self._closed_topics),
        }


# ── Internal helpers ─────────────────────────────────────────────────


def _make_topic_id(matched_word: str, timestamp: float) -> str:
    """Generate a stable topic identifier."""
    safe = re.sub(r"[^\w]", "_", matched_word)
    return f"topic_{safe}_{int(timestamp * 1000)}"
