# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ClarifyManager — ambiguity detection and clarification question generation.

T-18 (v1.3.6): Framework-level base class providing ambiguity scoring with
configurable thresholds.  When user input is too ambiguous to act on safely,
the manager triggers a clarification question instead of proceeding with
potentially incorrect reasoning.

Detection heuristics (framework defaults — app layer can override):

- **Length**:  Very short messages (< *min_chars*) are inherently ambiguous.
- **Vague referents**: Messages containing pronouns without clear antecedents
  (e.g. "that one", "fix it") score higher ambiguity.
- **Fragment**:  Messages that look like sentence fragments rather than
  complete requests.
- **Multiple intents**: Messages that could be interpreted multiple ways.

The app layer typically plugs in an LLM-based detector via
``_score_ambiguity()`` override.  The framework provides simple rule-based
fallback.

Usage::

    cm = ClarifyManager(ambiguity_threshold=0.6, min_chars=10)

    result = cm.evaluate("fix it")
    if result.needs_clarification:
        # Ask user: result.question
        await speak(result.question)
    else:
        # Proceed with reasoning
        ...
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class ClarifyConfig:
    """Ambiguity detection thresholds.

    Attributes:
        ambiguity_threshold: Score (0..1) above which clarification is
                             triggered.  0 = never clarify, 1 = always
                             clarify unless perfectly clear.
        min_chars:           Messages shorter than this are considered
                             too short to disambiguate.
        max_clarify_rounds:  Max consecutive clarification rounds before
                             giving up and making a best-effort guess.
        vague_patterns:      Regex patterns that indicate vague referents
                             (e.g. pronouns without clear antecedent).
    """

    ambiguity_threshold: float = 0.5
    min_chars: int = 10
    max_clarify_rounds: int = 3
    vague_patterns: list[str] = field(
        default_factory=lambda: [
            r"\b(it|that|this|those|these|them|they)\b.*\b(fix|change|update|do|make|set|get)\b",
            r"\b(fix|change|update|do|make|set|get)\b.*\b(it|that|this|those|these|them|they)\b",
            r"\b(the (one|same|other|first|last|previous|next))\b",
            r"^(what about|and|or|but|so|then)\b",
        ]
    )


# ── Result dataclass ──────────────────────────────────────────────────


@dataclass
class ClarifyResult:
    """Outcome of ambiguity evaluation.

    Attributes:
        needs_clarification: Whether the manager recommends asking for
                             clarification before proceeding.
        ambiguity_score:     Raw ambiguity score (0..1).
        question:            A generated clarification question, or empty
                             string if no clarification is needed.
        reason:              Human-readable reason for the decision.
    """

    needs_clarification: bool = False
    ambiguity_score: float = 0.0
    question: str = ""
    reason: str = ""


# ── ClarifyManager ────────────────────────────────────────────────────


class ClarifyManager:
    """Ambiguity detection and clarification base class.

    Decision flow::

        evaluate(user_msg)
          ├── score = _score_ambiguity(user_msg)
          ├── if score >= threshold:
          │     question = _generate_question(user_msg)
          │     return ClarifyResult(needs=True, score, question)
          └── else:
                return ClarifyResult(needs=False, score)

    App layer can override ``_score_ambiguity`` (LLM-based scoring),
    ``_generate_question`` (LLM question generation), or ``_pre_check``
    (quick rejection before scoring).
    """

    # ── Default question templates ─────────────────────────────────

    DEFAULT_VAGUE_PATTERNS: list[str] = [
        r"\b(it|that|this|those|these|them|they)\b.*\b(fix|change|update|do|make|set|get)\b",
        r"\b(fix|change|update|do|make|set|get)\b.*\b(it|that|this|those|these|them|they)\b",
        r"\b(the (one|same|other|first|last|previous|next))\b",
        r"^(what about|and|or|but|so|then)\b",
    ]

    DEFAULT_QUESTIONS: list[str] = [
        "Could you clarify what you mean by that?",
        "I'm not sure I understand — could you elaborate?",
        "What specifically would you like me to do?",
        "Could you provide more details?",
    ]

    def __init__(
        self,
        ambiguity_threshold: float = 0.5,
        min_chars: int = 10,
        max_clarify_rounds: int = 3,
        vague_patterns: Sequence[str] | None = None,
    ) -> None:
        self._config = ClarifyConfig(
            ambiguity_threshold=ambiguity_threshold,
            min_chars=min_chars,
            max_clarify_rounds=max_clarify_rounds,
            vague_patterns=(
                list(
                    vague_patterns) if vague_patterns is not None else self.DEFAULT_VAGUE_PATTERNS
            ),
        )
        self._vague_re: list[re.Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in self._config.vague_patterns
        ]
        self._clarify_count: int = 0

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> ClarifyConfig:
        """Current configuration (read-only copy)."""
        return ClarifyConfig(
            ambiguity_threshold=self._config.ambiguity_threshold,
            min_chars=self._config.min_chars,
            max_clarify_rounds=self._config.max_clarify_rounds,
            vague_patterns=list(self._config.vague_patterns),
        )

    # ── Main entry ─────────────────────────────────────────────────

    def evaluate(self, user_msg: str) -> ClarifyResult:
        """Evaluate whether user input needs clarification.

        Args:
            user_msg:  The raw user message.

        Returns:
            ``ClarifyResult`` with decision, score, and optional question.
        """
        # Pre-check: quick rejection
        pre = self._pre_check(user_msg)
        if pre is not None:
            return pre

        # Score ambiguity
        score = self._score_ambiguity(user_msg)

        if score >= self._config.ambiguity_threshold and self._config.ambiguity_threshold > 0.0:
            # Check round limit
            if self._clarify_count >= self._config.max_clarify_rounds:
                return ClarifyResult(
                    needs_clarification=False,
                    ambiguity_score=score,
                    reason=f"Max clarify rounds ({self._config.max_clarify_rounds}) reached; proceeding with best-effort.",  # noqa: E501
                )

            self._clarify_count += 1
            question = self._generate_question(user_msg)
            return ClarifyResult(
                needs_clarification=True,
                ambiguity_score=score,
                question=question,
                reason=f"Ambiguity score {score:.2f} >= threshold {self._config.ambiguity_threshold}.",
            )

        # Clear enough → reset clarify counter
        self._clarify_count = 0
        return ClarifyResult(
            needs_clarification=False,
            ambiguity_score=score,
            reason=f"Ambiguity score {score:.2f} < threshold {self._config.ambiguity_threshold}.",
        )

    def reset(self) -> None:
        """Reset the internal clarify round counter."""
        self._clarify_count = 0

    # ── Pre-check (overridable) ────────────────────────────────────

    def _pre_check(self, user_msg: str) -> ClarifyResult | None:
        """Quick pre-check before scoring.  Return a ``ClarifyResult`` to
        short-circuit, or ``None`` to continue to scoring.

        Default: messages shorter than *min_chars* are too ambiguous to
        proceed without clarification.
        """
        stripped = user_msg.strip()
        if len(stripped) < self._config.min_chars:
            return ClarifyResult(
                needs_clarification=True,
                ambiguity_score=1.0,
                question=self._generate_question(stripped),
                reason=f"Message too short ({len(stripped)} < {self._config.min_chars} chars).",
            )
        return None

    # ── Ambiguity scoring (overridable) ────────────────────────────

    def _score_ambiguity(self, user_msg: str) -> float:
        """Score the ambiguity of user input (0 = clear, 1 = totally ambiguous).

        Framework default uses rule-based heuristics:

        1. Vague pronoun patterns → +0.4
        2. Fragment-like (no sentence terminator) → +0.2
        3. Very short but above *min_chars* → partial scoring

        Override for LLM-based scoring in app layer.
        """
        score = 0.0
        msg = user_msg.strip()

        # Vague referent patterns
        vague_hits = sum(1 for pat in self._vague_re if pat.search(msg))
        if vague_hits > 0:
            # Cap vague contribution at 0.5
            score += min(0.5, vague_hits * 0.25)

        # Fragment detection: no sentence-ending punctuation
        if not re.search(r"[.!?。！？]$", msg):
            score += 0.15

        # Length-based: short but above min_chars
        char_len = len(msg)
        if char_len < 30:
            # Linear scale: 30 chars → 0.0, min_chars → 0.3
            t = max(0.0, (30 - char_len) / max(1, 30 - self._config.min_chars))
            score += t * 0.3

        return min(1.0, score)

    # ── Question generation (overridable) ──────────────────────────

    def _generate_question(self, user_msg: str) -> str:
        """Generate a clarification question.

        Framework default returns a generic question.  Override for
        context-aware LLM-based question generation.
        """
        import random

        return random.choice(self.DEFAULT_QUESTIONS)

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "ambiguity_threshold": self._config.ambiguity_threshold,
            "min_chars": self._config.min_chars,
            "max_clarify_rounds": self._config.max_clarify_rounds,
            "vague_patterns": list(self._config.vague_patterns),
            "clarify_count": self._clarify_count,
        }
