# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""BudgetTracker — token budget enforcement with LRU eviction.

T-19 (v1.3.6): Framework-level base class for tracking token consumption
against a configurable budget.  When the budget is exceeded, the least
recently used items are evicted to free space.

Key features:

- **Total budget**:  Hard cap on total tokens across all categories.
- **Category allocation**: Optional per-category sub-budgets (e.g.
  ``system_prompt``, ``conversation``, ``tools``).
- **LRU eviction**:  When budget is full, evict least-recently-used
  entries to make room.
- **Usage tracking**:  Record per-item token counts with timestamps
  for LRU ordering.

Usage::

    tracker = BudgetTracker(total_budget=8000)

    # Allocate tokens to items
    tracker.allocate("msg_1", 500)   # 500 tokens
    tracker.allocate("msg_2", 1200)  # 1200 tokens

    remaining = tracker.remaining  # 6300

    # When budget is exceeded, LRU eviction kicks in:
    freed = tracker.allocate("msg_3", 7500)  # forces eviction of oldest
    # freed > 0 means some items were evicted
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class BudgetConfig:
    """Token budget configuration.

    Attributes:
        total_budget:      Hard cap on total tokens across all items.
        category_budgets:  Optional per-category token limits.  Categories
                           not listed have no individual cap (only the
                           total budget applies).
        chars_per_token:   Rough character-to-token ratio for estimation
                           when token count is not provided.
        min_free_ratio:    Minimum fraction of budget to keep free after
                           eviction (0.0 = evict exactly to fit, 0.1 =
                           keep 10% free).
    """

    total_budget: int = 8000
    category_budgets: dict[str, int] = field(default_factory=dict)
    chars_per_token: float = 4.0
    min_free_ratio: float = 0.05


# ── BudgetTracker ─────────────────────────────────────────────────────


class BudgetTracker:
    """Token budget tracker with LRU eviction.

    Tracks per-item token consumption with monotonic access timestamps.
    When ``allocate()`` would exceed the total budget, the least-recently-
    used items are evicted until enough room is available (respecting
    ``min_free_ratio``).

    Items are identified by arbitrary string keys (e.g. ``"msg_1"``,
    ``"system_prompt"``, ``"tool_result_3"``).

    App layer can override ``_on_evict`` to handle side effects of
    eviction (e.g. summarizing evicted content).
    """

    def __init__(
        self,
        total_budget: int = 8000,
        category_budgets: dict[str, int] | None = None,
        chars_per_token: float = 4.0,
        min_free_ratio: float = 0.05,
    ) -> None:
        self._config = BudgetConfig(
            total_budget=total_budget,
            category_budgets=dict(category_budgets or {}),
            chars_per_token=chars_per_token,
            min_free_ratio=min_free_ratio,
        )
        # OrderedDict maintains insertion order; we update on access for LRU
        self._items: OrderedDict[str, tuple[int, str | None, float]] = (
            OrderedDict()
        )
        # item_key → (tokens, category, last_access_ts)
        self._total_used: int = 0
        self._category_used: dict[str, int] = {}
        self._eviction_count: int = 0

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> BudgetConfig:
        """Current budget configuration (read-only copy)."""
        return BudgetConfig(
            total_budget=self._config.total_budget,
            category_budgets=dict(self._config.category_budgets),
            chars_per_token=self._config.chars_per_token,
            min_free_ratio=self._config.min_free_ratio,
        )

    @property
    def remaining(self) -> int:
        """Tokens remaining in the total budget."""
        return max(0, self._config.total_budget - self._total_used)

    @property
    def total_used(self) -> int:
        """Total tokens currently allocated."""
        return self._total_used

    @property
    def utilization(self) -> float:
        """Budget utilization ratio (0..1)."""
        if self._config.total_budget == 0:
            return 0.0
        return self._total_used / self._config.total_budget

    # ── Main API ───────────────────────────────────────────────────

    def allocate(
        self,
        key: str,
        tokens: int | None = None,
        chars: int = 0,
        category: str | None = None,
    ) -> int:
        """Allocate token budget for an item.

        If the allocation would exceed the budget, LRU eviction is
        triggered to free space.

        Args:
            key:      Unique identifier for this item (e.g. ``"msg_3"``).
            tokens:   Token count.  If ``None``, estimated from *chars*.
            chars:    Character count (used only when *tokens* is None).
            category: Optional category name for per-category tracking.

        Returns:
            Number of tokens freed by eviction (0 if no eviction needed).
        """
        if tokens is None:
            tokens = self._estimate_tokens(chars)

        freed = 0

        # Check category budget
        if category is not None and category in self._config.category_budgets:
            cat_limit = self._config.category_budgets[category]
            cat_used = self._category_used.get(category, 0)
            if cat_used + tokens > cat_limit:
                freed += self._evict_for_category(category,
                                                  cat_used + tokens - cat_limit)

        # Check total budget
        needed = self._total_used + tokens - self._config.total_budget
        if needed > 0:
            # Add min_free_ratio headroom
            headroom = int(self._config.total_budget *
                           self._config.min_free_ratio)
            freed += self._evict_for_total(needed + headroom)

        # Update tracking
        now = time.monotonic()
        if key in self._items:
            old_tokens, old_cat, _ = self._items[key]
            self._total_used -= old_tokens
            if old_cat is not None:
                self._category_used[old_cat] = (
                    self._category_used.get(old_cat, 0) - old_tokens
                )
            # Move to end (LRU: most recent at end)
            del self._items[key]
        else:
            old_tokens = 0

        self._items[key] = (tokens, category, now)
        self._total_used += tokens
        if category is not None:
            self._category_used[category] = (
                self._category_used.get(category, 0) + tokens
            )

        return freed

    def touch(self, key: str) -> bool:
        """Mark an item as recently used (update its LRU timestamp).

        Returns ``True`` if the item exists, ``False`` otherwise.
        """
        if key not in self._items:
            return False
        tokens, category, _ = self._items[key]
        self._items[key] = (tokens, category, time.monotonic())
        # Move to end (LRU)
        self._items.move_to_end(key)
        return True

    def release(self, key: str) -> int:
        """Release an item's budget back to the pool.

        Returns the number of tokens freed, or 0 if the key was
        not found.
        """
        if key not in self._items:
            return 0
        tokens, category, _ = self._items.pop(key)
        self._total_used -= tokens
        if category is not None:
            self._category_used[category] = (
                self._category_used.get(category, 0) - tokens
            )
        return tokens

    def get(self, key: str) -> int | None:
        """Get the token count for an item, or ``None`` if not found."""
        entry = self._items.get(key)
        if entry is None:
            return None
        return entry[0]

    # ── Category queries ───────────────────────────────────────────

    def category_used(self, category: str) -> int:
        """Get token usage for a specific category."""
        return self._category_used.get(category, 0)

    def category_remaining(self, category: str) -> int | None:
        """Get remaining budget for a category, or ``None`` if no cap."""
        limit = self._config.category_budgets.get(category)
        if limit is None:
            return None
        return max(0, limit - self._category_used.get(category, 0))

    # ── Eviction (overridable) ─────────────────────────────────────

    def _evict_for_total(self, needed: int) -> int:
        """Evict LRU items until *needed* tokens are freed.

        Returns total tokens freed.
        """
        freed = 0
        # Sort by last_access_ts ascending (oldest first) for explicit LRU order
        sorted_items = sorted(
            self._items.items(),
            key=lambda kv: kv[1][2],  # last_access_ts
        )
        keys_to_evict: list[str] = []
        for key, (tokens, category, _ts) in sorted_items:
            if freed >= needed:
                break
            keys_to_evict.append(key)
            freed += tokens

        for key in keys_to_evict:
            self._on_evict(key)
            self.release(key)

        self._eviction_count += len(keys_to_evict)
        return freed

    def _evict_for_category(self, category: str, needed: int) -> int:
        """Evict LRU items of a specific *category* to free *needed* tokens.

        Returns total tokens freed.
        """
        freed = 0
        # Sort matching items by last_access_ts ascending (oldest first)
        matching = [
            (key, tokens, ts)
            for key, (tokens, cat, ts) in self._items.items()
            if cat == category
        ]
        matching.sort(key=lambda x: x[2])  # last_access_ts
        keys_to_evict: list[str] = []
        for key, tokens, _ts in matching:
            if freed >= needed:
                break
            keys_to_evict.append(key)
            freed += tokens

        for key in keys_to_evict:
            self._on_evict(key)
            self.release(key)

        self._eviction_count += len(keys_to_evict)
        return freed

    def _on_evict(self, key: str) -> None:
        """Hook called before an item is evicted.

        Override to handle side effects (summarization, logging, etc.).
        Default is a no-op.
        """
        pass

    # ── Helpers ────────────────────────────────────────────────────

    def _estimate_tokens(self, chars: int) -> int:
        """Estimate token count from character count."""
        if chars <= 0:
            return 0
        return max(1, int(chars / self._config.chars_per_token))

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "total_budget": self._config.total_budget,
            "total_used": self._total_used,
            "remaining": self.remaining,
            "utilization": round(self.utilization, 4),
            "item_count": len(self._items),
            "category_budgets": dict(self._config.category_budgets),
            "category_used": dict(self._category_used),
            "eviction_count": self._eviction_count,
            "min_free_ratio": self._config.min_free_ratio,
        }
