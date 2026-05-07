# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""CompressionManager — hierarchical context compression strategy with
configurable thresholds.

T-16 (v1.3.6): Framework-level base class providing three-tier compression
for conversation context.  App layer configures thresholds and optionally
plugs in an LLM summarizer for heavy compression.

Three tiers:

- **Light**  (≤ *light_threshold* messages): pass-through, no compression.
- **Medium** (≤ *medium_threshold* messages): algorithmic trim — keep first
  message + most recent messages within token budget.
- **Heavy**  (> *medium_threshold* messages): delegate to summarizer
  callback; falls back to medium if no summarizer is configured.

Usage::

    cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=4000)
    compressed = await cm.compress(messages)

    # With LLM summarizer
    cm = CompressionManager(
        summarizer=my_llm_summarize,  # async callable
    )
    compressed = await cm.compress(very_long_messages)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class CompressionConfig:
    """Hierarchical compression thresholds and budget.

    Attributes:
        light_threshold:  Messages ≤ this count → light (pass-through).
        medium_threshold: Messages ≤ this count → medium (algorithmic trim).
            Messages above this count trigger heavy (LLM summarization).
        max_tokens:       Target token budget for the compressed result.
        chars_per_token:  Rough character-to-token ratio for estimation.
    """

    light_threshold: int = 2
    medium_threshold: int = 5
    max_tokens: int = 4000
    chars_per_token: float = 4.0


# ── CompressionManager ─────────────────────────────────────────────────


class CompressionManager:
    """Hierarchical compression strategy base class.

    Three-tier strategy driven by message count:

    +--------------+-------------------+------------------------------+
    | Tier         | Condition         | Behaviour                    |
    +==============+===================+==============================+
    | **light**    | ≤ light_threshold | Pass-through, no compression |
    +--------------+-------------------+------------------------------+
    | **medium**   | ≤ medium_thresh.  | Algorithmic trim             |
    +--------------+-------------------+------------------------------+
    | **heavy**    | > medium_thresh.  | LLM summarizer (or fallback) |
    +--------------+-------------------+------------------------------+

    App layer can override any tier method for custom compression logic.
    """

    def __init__(
        self,
        light_threshold: int = 2,
        medium_threshold: int = 5,
        max_tokens: int = 4000,
        chars_per_token: float = 4.0,
        summarizer: (
            Callable[[list[dict[str, str]], int],
                     Awaitable[list[dict[str, str]]]]
            | None
        ) = None,
    ) -> None:
        self._config = CompressionConfig(
            light_threshold=light_threshold,
            medium_threshold=medium_threshold,
            max_tokens=max_tokens,
            chars_per_token=chars_per_token,
        )
        self._summarizer = summarizer

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> CompressionConfig:
        """Current compression configuration (read-only copy)."""
        return CompressionConfig(
            light_threshold=self._config.light_threshold,
            medium_threshold=self._config.medium_threshold,
            max_tokens=self._config.max_tokens,
            chars_per_token=self._config.chars_per_token,
        )

    # ── Main entry ─────────────────────────────────────────────────

    async def compress(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
    ) -> list[dict[str, str]]:
        """Compress messages to fit within token budget.

        Args:
            messages:  List of message dicts (``{role, content}``).
            max_tokens: Override the configured target token budget.

        Returns:
            Compressed message list (may be the same list if light tier).
        """
        if not messages:
            return messages

        budget = max_tokens if max_tokens is not None else self._config.max_tokens
        n = len(messages)

        if n <= self._config.light_threshold:
            return self._light_compress(messages, budget)
        if n <= self._config.medium_threshold:
            return self._medium_compress(messages, budget)
        return await self._heavy_compress(messages, budget)

    # ── Tier implementations (overridable) ──────────────────────────

    def _light_compress(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> list[dict[str, str]]:
        """Light tier: pass-through (no compression)."""
        return list(dict(m) for m in messages)

    def _medium_compress(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> list[dict[str, str]]:
        """Medium tier: keep first message + most recent within budget.

        Always preserves the first message (typically system/context),
        then fills the remaining budget with the most recent messages
        (working backwards).
        """
        if not messages:
            return messages

        budget_chars = int(max_tokens * self._config.chars_per_token)
        result: list[dict[str, str]] = [dict(messages[0])]
        used = len(str(messages[0]))

        for msg in reversed(messages[1:]):
            chars = len(str(msg))
            if used + chars <= budget_chars:
                result.insert(1, dict(msg))
                used += chars
            else:
                break

        return result

    async def _heavy_compress(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> list[dict[str, str]]:
        """Heavy tier: delegate to LLM summarizer, fallback to medium.

        If no summarizer is configured or summarizer fails,
        falls back to ``_medium_compress``.
        """
        if self._summarizer is not None:
            try:
                return await self._summarizer(messages, max_tokens)
            except Exception:
                pass  # graceful fallback
        return self._medium_compress(messages, max_tokens)

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current configuration."""
        return {
            "light_threshold": self._config.light_threshold,
            "medium_threshold": self._config.medium_threshold,
            "max_tokens": self._config.max_tokens,
            "chars_per_token": self._config.chars_per_token,
            "has_summarizer": self._summarizer is not None,
        }
