# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""NoiseFilter — pre-filter for determining what is worth remembering.

T-20 (v1.3.6): Framework-level noise detection base class.  Plugs into
the remember pipeline to filter out low-value exchanges before they
reach the hippocampus.

Detection heuristics (framework defaults — app layer can override):

- **Noise patterns**:  Regex-based matching for pure acknowledgements,
  filler, greetings, etc.
- **Minimum length**:  Exchanges shorter than *min_chars* are noise.
- **Repetition ratio**:  Exchanges with high character repetition
  (e.g. ``aaaaaa``) are flagged as noise.
- **Custom filter**:  Override ``_custom_filter`` for domain-specific
  logic (e.g. LLM-based quality scoring).

Usage::

    nf = NoiseFilter(
        noise_patterns=[r"^OK$", r"^Got it"],
        min_chars=8,
        max_rep_ratio=0.5,
    )

    if nf.worth_remembering(user_msg, ai_reply):
        await hippocampus.remember(user_msg, ai_reply, cat_uid, model)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


# ── Shared defaults ────────────────────────────────────────────────

_DEFAULT_NOISE_PATTERNS: list[str] = [
    r"^(ok|okay|k|kk|okie|got it|gotcha|thanks|thx|ty|np|no problem|yw|you're welcome|sure|yep|yeah|nope|nah|hi|hello|hey|bye|goodbye|see ya|later)$",
    r"^(cool|nice|great|awesome|perfect|fine|good|alright|all right)$",
    r"^(yes|no|maybe|idk|i don't know|dunno|not sure)$",
    r"^([\s,;.!?\-]+)$",  # pure punctuation/whitespace/dash
    r"^(ha){2,}$",       # laughing: haha, hahaha...
    r"^(lo+l+)+$",       # lol, lolol...
]


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class NoiseFilterConfig:
    """Noise filter thresholds and patterns.

    Attributes:
        noise_patterns:     Regex patterns that identify noise
                            (pure acknowledgements, filler, etc.).
        min_chars:           Combined user+reply shorter than this is
                            considered noise.
        max_rep_ratio:       Maximum ratio of the most frequent character
                            to total length.  Above this, the text is
                            considered repetitive noise (0..1).
        check_repetition:    Whether to perform repetition checking.
    """

    noise_patterns: list[str] = field(
        default_factory=lambda: list(_DEFAULT_NOISE_PATTERNS))
    min_chars: int = 8
    max_rep_ratio: float = 0.5
    check_repetition: bool = True


# ── NoiseFilter ───────────────────────────────────────────────────────


class NoiseFilter:
    """Noise pre-filter for the remember pipeline.

    Decision flow::

        worth_remembering(user_msg, ai_reply)
          ├── _check_noise_patterns(text)     → True if noise regex match
          ├── _check_min_length(text)         → True if too short
          ├── _check_repetition(text)         → True if too repetitive
          └── _custom_filter(user_msg, reply) → True if domain-specific noise

    Returns ``False`` if ANY check flags the exchange as noise.
    """

    # ── Default noise patterns (class-level, safe to reference) ──

    DEFAULT_NOISE_PATTERNS: list[str] = _DEFAULT_NOISE_PATTERNS

    def __init__(
        self,
        noise_patterns: Sequence[str] | None = None,
        min_chars: int = 8,
        max_rep_ratio: float = 0.5,
        check_repetition: bool = True,
    ) -> None:
        self._config = NoiseFilterConfig(
            noise_patterns=(
                list(noise_patterns)
                if noise_patterns is not None
                else self.DEFAULT_NOISE_PATTERNS
            ),
            min_chars=min_chars,
            max_rep_ratio=max_rep_ratio,
            check_repetition=check_repetition,
        )
        self._noise_re: list[re.Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in self._config.noise_patterns
        ]
        # Counter for diagnostics
        self._noise_count: int = 0
        self._passed_count: int = 0

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> NoiseFilterConfig:
        """Current filter configuration (read-only copy)."""
        return NoiseFilterConfig(
            noise_patterns=list(self._config.noise_patterns),
            min_chars=self._config.min_chars,
            max_rep_ratio=self._config.max_rep_ratio,
            check_repetition=self._config.check_repetition,
        )

    # ── Main API ───────────────────────────────────────────────────

    def is_noise(self, text: str) -> bool:
        """Check whether a single text string is noise.

        This is a convenience wrapper that runs all checks on a
        standalone string (useful for filtering individual messages).

        Args:
            text:  The text to check.

        Returns:
            ``True`` if the text is classified as noise.
        """
        stripped = text.strip()
        if not stripped:
            return True
        if self._check_noise_patterns(stripped):
            return True
        if self._check_min_length(stripped):
            return True
        if self._check_repetition(stripped):
            return True
        return self._custom_filter(text, "")

    def worth_remembering(self, user_msg: str, ai_reply: str) -> bool:
        """Full exchange filter — should this be written to memory?

        Checks the combined user + reply text against all noise filters.

        Args:
            user_msg:  The user's message.
            ai_reply:  The AI's reply.

        Returns:
            ``True`` if the exchange passes all noise checks.
        """
        combined = f"{user_msg} {ai_reply}".strip()

        # Quick reject: empty
        if not combined:
            self._noise_count += 1
            return False

        # Noise pattern check — check combined first, then individually
        if self._check_noise_patterns(combined):
            self._noise_count += 1
            return False

        # If both individual messages are noise (pure ack + ack), reject
        if (
            self._check_noise_patterns(user_msg.strip())
            and self._check_noise_patterns(ai_reply.strip())
        ):
            self._noise_count += 1
            return False

        # Minimum length
        if self._check_min_length(combined):
            self._noise_count += 1
            return False

        # Repetition check
        if self._check_repetition(combined):
            self._noise_count += 1
            return False

        # Custom filter (overridable)
        if self._custom_filter(user_msg, ai_reply):
            self._noise_count += 1
            return False

        self._passed_count += 1
        return True

    # ── Individual checks (overridable) ────────────────────────────

    def _check_noise_patterns(self, text: str) -> bool:
        """Check text against registered noise patterns.

        Returns ``True`` if any pattern matches (text is noise).
        """
        for pat in self._noise_re:
            if pat.search(text):
                return True
        return False

    def _check_min_length(self, text: str) -> bool:
        """Check if text is below minimum content length.

        Returns ``True`` if too short (text is noise).
        """
        return len(text.strip()) < self._config.min_chars

    def _check_repetition(self, text: str) -> bool:
        """Check if text has excessive character repetition.

        Returns ``True`` if too repetitive (text is noise).
        """
        if not self._config.check_repetition:
            return False

        stripped = text.strip()
        if len(stripped) < 3:
            return False  # too short to meaningfully check

        # Count most frequent character
        char_counts: dict[str, int] = {}
        for ch in stripped.lower():
            if ch.isalpha():
                char_counts[ch] = char_counts.get(ch, 0) + 1

        if not char_counts:
            return False

        max_count = max(char_counts.values())
        alpha_len = sum(char_counts.values())

        if alpha_len < 3:
            return False  # too few alpha chars for meaningful check

        return (max_count / alpha_len) > self._config.max_rep_ratio

    def _custom_filter(self, user_msg: str, ai_reply: str) -> bool:
        """Custom noise check — override for domain-specific logic.

        Returns ``True`` if the exchange should be treated as noise.
        Default is always ``False`` (pass-through).
        """
        return False

    # ── Diagnostics ────────────────────────────────────────────────

    def reset_counts(self) -> None:
        """Reset noise/pass counters."""
        self._noise_count = 0
        self._passed_count = 0

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "noise_patterns": list(self._config.noise_patterns),
            "min_chars": self._config.min_chars,
            "max_rep_ratio": self._config.max_rep_ratio,
            "check_repetition": self._config.check_repetition,
            "noise_count": self._noise_count,
            "passed_count": self._passed_count,
        }
