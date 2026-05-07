# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — BudgetTracker 全覆盖测试
==================================

验证:
    1. TestBudgetConfig              — BudgetConfig dataclass 字段
    2. TestBudgetTrackerInit         — 构造 + 默认值
    3. TestBudgetAllocate            — allocate() 基本用法 + token 估算
    4. TestBudgetRelease             — release() 释放
    5. TestBudgetTouch               — touch() LRU 时间戳更新
    6. TestBudgetGet                 — get() 查询
    7. TestBudgetLRUEviction         — total budget 超限 LRU 驱逐
    8. TestBudgetCategoryEviction    — 分类 budget 超限驱逐
    9. TestBudgetMinFreeRatio        — min_free_ratio 预留空间
   10. TestBudgetCategoryTracking    — 分类追踪 + 查询
   11. TestBudgetReallocate          — 同一 key 重新分配
   12. TestBudgetEdge                — 边界: 零预算 / 超大 / 空操作
   13. TestBudgetDiagnose            — diagnose() 快照
   14. TestBudgetOnEvict             — _on_evict hook
   15. TestBudgetUtilization         — utilization + remaining
"""

from __future__ import annotations

from meowcat.budget import BudgetTracker, BudgetConfig


# ── 1. BudgetConfig ─────────────────────────────────────────────────────

class TestBudgetConfig:
    """BudgetConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = BudgetConfig()
        assert cfg.total_budget == 8000
        assert cfg.category_budgets == {}
        assert cfg.chars_per_token == 4.0
        assert cfg.min_free_ratio == 0.05

    def test_custom_fields(self) -> None:
        cfg = BudgetConfig(
            total_budget=4000,
            category_budgets={"system": 1000, "tools": 2000},
            chars_per_token=3.5,
            min_free_ratio=0.1,
        )
        assert cfg.total_budget == 4000
        assert cfg.category_budgets == {"system": 1000, "tools": 2000}
        assert cfg.chars_per_token == 3.5
        assert cfg.min_free_ratio == 0.1


# ── 2. Init ─────────────────────────────────────────────────────────────

class TestBudgetTrackerInit:
    """构造 + 默认值。"""

    def test_default_construction(self) -> None:
        bt = BudgetTracker()
        assert bt.config.total_budget == 8000
        assert bt.config.category_budgets == {}
        assert bt.config.chars_per_token == 4.0
        assert bt.remaining == 8000
        assert bt.total_used == 0
        assert bt.utilization == 0.0

    def test_custom_construction(self) -> None:
        bt = BudgetTracker(
            total_budget=2000,
            category_budgets={"chat": 500},
            chars_per_token=2.0,
            min_free_ratio=0.2,
        )
        assert bt.config.total_budget == 2000
        assert bt.config.category_budgets == {"chat": 500}
        assert bt.remaining == 2000

    def test_config_is_readonly_copy(self) -> None:
        bt = BudgetTracker(total_budget=5000)
        cfg = bt.config
        cfg.total_budget = 9999  # type: ignore[misc]
        assert bt.config.total_budget == 5000


# ── 3. Allocate ─────────────────────────────────────────────────────────

class TestBudgetAllocate:
    """allocate() 基本用法 + token 估算。"""

    def test_allocate_tokens(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        freed = bt.allocate("a", tokens=300)
        assert freed == 0
        assert bt.total_used == 300
        assert bt.remaining == 700

    def test_allocate_chars_estimation(self) -> None:
        bt = BudgetTracker(total_budget=1000, chars_per_token=4.0)
        freed = bt.allocate("a", chars=400)
        assert freed == 0
        assert bt.total_used == 100  # 400 / 4.0

    def test_allocate_zero_tokens(self) -> None:
        bt = BudgetTracker(total_budget=100)
        freed = bt.allocate("a", tokens=0)
        assert freed == 0
        assert bt.total_used == 0

    def test_allocate_multiple(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=200)
        bt.allocate("b", tokens=300)
        bt.allocate("c", tokens=100)
        assert bt.total_used == 600
        assert bt.remaining == 400

    def test_allocate_returns_freed_on_eviction(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("old", tokens=80)
        # Next allocation forces eviction
        freed = bt.allocate("new", tokens=50)
        assert freed > 0
        # "old" should be evicted
        assert bt.get("old") is None
        assert bt.get("new") == 50


# ── 4. Release ──────────────────────────────────────────────────────────

class TestBudgetRelease:
    """release() 释放。"""

    def test_release_existing(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=300)
        freed = bt.release("a")
        assert freed == 300
        assert bt.total_used == 0
        assert bt.get("a") is None

    def test_release_non_existent(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        freed = bt.release("nonexistent")
        assert freed == 0

    def test_release_partial_recovery(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=200)
        bt.allocate("b", tokens=300)
        bt.release("a")
        assert bt.total_used == 300
        assert bt.remaining == 700


# ── 5. Touch ────────────────────────────────────────────────────────────

class TestBudgetTouch:
    """touch() LRU 时间戳更新。"""

    def test_touch_existing(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("a", tokens=30)
        bt.allocate("b", tokens=30)
        # Touch "a" to make it most recent
        assert bt.touch("a") is True
        # "b" is now oldest → allocating more should evict "b"
        bt.allocate("c", tokens=50)
        assert bt.get("b") is None
        assert bt.get("a") == 30

    def test_touch_non_existent(self) -> None:
        bt = BudgetTracker(total_budget=100)
        assert bt.touch("nonexistent") is False


# ── 6. Get ──────────────────────────────────────────────────────────────

class TestBudgetGet:
    """get() 查询。"""

    def test_get_existing(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=250)
        assert bt.get("a") == 250

    def test_get_non_existent(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        assert bt.get("x") is None

    def test_get_after_release(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=100)
        bt.release("a")
        assert bt.get("a") is None


# ── 7. LRU Eviction ─────────────────────────────────────────────────────

class TestBudgetLRUEviction:
    """Total budget 超限 LRU 驱逐。"""

    def test_lru_evicts_oldest(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("first", tokens=40)
        bt.allocate("second", tokens=40)
        # Budget: 80/100 used
        bt.allocate("third", tokens=40)
        # Over budget → "first" evicted
        assert bt.get("first") is None
        assert bt.get("second") == 40
        assert bt.get("third") == 40

    def test_lru_eviction_respects_touch(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("a", tokens=40)
        bt.allocate("b", tokens=40)
        bt.touch("a")  # "a" now most recent
        bt.allocate("c", tokens=40)
        # "b" should be evicted (oldest)
        assert bt.get("b") is None
        assert bt.get("a") == 40

    def test_eviction_frees_enough(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("a", tokens=30)
        bt.allocate("b", tokens=30)
        bt.allocate("c", tokens=30)
        # 90 used, need 50 more → evict a (30) + b (30), then 90-60+50=80
        bt.allocate("d", tokens=50)
        assert bt.get("a") is None
        assert bt.get("b") is None
        assert bt.get("c") == 30
        assert bt.get("d") == 50
        assert bt.total_used <= 100

    def test_no_eviction_when_within_budget(self) -> None:
        bt = BudgetTracker(total_budget=200, min_free_ratio=0.0)
        bt.allocate("a", tokens=50)
        bt.allocate("b", tokens=50)
        bt.allocate("c", tokens=50)
        assert bt.get("a") == 50
        assert bt.get("b") == 50
        assert bt.get("c") == 50
        assert bt.total_used == 150


# ── 8. Category Eviction ────────────────────────────────────────────────

class TestBudgetCategoryEviction:
    """分类 budget 超限驱逐。"""

    def test_category_limit_enforced(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"tools": 200},
        )
        bt.allocate("t1", tokens=120, category="tools")
        assert bt.category_used("tools") == 120

        # Allocate more in "tools" → within budget still
        bt.allocate("t2", tokens=80, category="tools")
        assert bt.category_used("tools") == 200

        # Overflow: should evict oldest "tools" item
        bt.allocate("t3", tokens=100, category="tools")
        assert bt.get("t1") is None  # oldest tools item evicted
        # t2 (80) + t3 (100) = 180 ≤ 200
        assert bt.category_used("tools") <= 200

    def test_category_limit_uses_lru(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"chat": 300},
        )
        bt.allocate("c1", tokens=150, category="chat")
        bt.allocate("c2", tokens=150, category="chat")
        bt.touch("c1")  # c1 most recent
        bt.allocate("c3", tokens=150, category="chat")
        assert bt.get("c2") is None  # c2 was oldest
        assert bt.get("c1") == 150
        assert bt.get("c3") == 150

    def test_no_category_limit(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=500, category="uncapped")
        bt.allocate("b", tokens=400, category="uncapped")
        assert bt.category_used("uncapped") == 900
        assert bt.category_remaining("uncapped") is None


# ── 9. Min Free Ratio ───────────────────────────────────────────────────

class TestBudgetMinFreeRatio:
    """min_free_ratio 预留空间。"""

    def test_default_keeps_headroom(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.1)
        # Allocate enough to trigger eviction
        bt.allocate("a", tokens=90)
        freed = bt.allocate("b", tokens=20)
        # Should evict enough to have 10% free after
        assert freed >= 10  # at least 10 tokens freed
        headroom = bt.remaining
        assert headroom >= 5  # roughly 10% of 100 = 10, minus any rounding

    def test_zero_min_free_ratio(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("a", tokens=80)
        bt.allocate("b", tokens=20)  # exactly 100
        assert bt.total_used == 100
        assert bt.remaining == 0

    def test_high_min_free_ratio(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.5)
        bt.allocate("a", tokens=30)
        freed = bt.allocate("b", tokens=80)
        # Needs massive eviction to keep 50% free
        assert freed >= 30  # a is evicted


# ── 10. Category Tracking ───────────────────────────────────────────────

class TestBudgetCategoryTracking:
    """分类追踪 + 查询。"""

    def test_category_used(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"system": 500, "tools": 300},
        )
        bt.allocate("s1", tokens=200, category="system")
        bt.allocate("t1", tokens=100, category="tools")
        assert bt.category_used("system") == 200
        assert bt.category_used("tools") == 100
        assert bt.category_used("unknown") == 0

    def test_category_remaining(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"system": 500},
        )
        bt.allocate("s1", tokens=200, category="system")
        assert bt.category_remaining("system") == 300
        assert bt.category_remaining("nonexistent") is None

    def test_category_released(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"system": 500},
        )
        bt.allocate("s1", tokens=200, category="system")
        bt.release("s1")
        assert bt.category_used("system") == 0

    def test_reallocate_changes_category(self) -> None:
        bt = BudgetTracker(
            total_budget=1000,
            category_budgets={"a": 500, "b": 500},
        )
        bt.allocate("x", tokens=200, category="a")
        # Re-allocate same key with different category
        bt.allocate("x", tokens=200, category="b")
        assert bt.category_used("a") == 0
        assert bt.category_used("b") == 200


# ── 11. Re-allocate ─────────────────────────────────────────────────────

class TestBudgetReallocate:
    """同一 key 重新分配。"""

    def test_reallocate_updates_tokens(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("x", tokens=100)
        bt.allocate("x", tokens=300)
        assert bt.get("x") == 300
        assert bt.total_used == 300

    def test_reallocate_smaller_frees_space(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("x", tokens=500)
        bt.allocate("x", tokens=100)
        assert bt.total_used == 100
        assert bt.remaining == 900


# ── 12. Edge cases ──────────────────────────────────────────────────────

class TestBudgetEdge:
    """边界: 零预算 / 超大 / 空操作。"""

    def test_zero_total_budget(self) -> None:
        bt = BudgetTracker(total_budget=0, min_free_ratio=0.0)
        assert bt.remaining == 0
        assert bt.utilization == 0.0  # 0/0 → 0.0
        # With zero budget, nothing to evict — allocation still proceeds
        freed = bt.allocate("a", tokens=10)
        assert freed == 0  # nothing to evict
        assert bt.get("a") == 10
        assert bt.remaining == 0  # 0 - 10 → clamped to 0

    def test_allocate_none_tokens_zero_chars(self) -> None:
        bt = BudgetTracker(total_budget=100)
        freed = bt.allocate("a")
        assert freed == 0
        assert bt.total_used == 0  # tokens=None, chars=0 → 0 tokens

    def test_very_large_allocation(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("small", tokens=10)
        bt.allocate("huge", tokens=1000)
        # "small" evicted, "huge" allocated
        assert bt.get("small") is None
        assert bt.get("huge") == 1000

    def test_eviction_count_tracked(self) -> None:
        bt = BudgetTracker(total_budget=50, min_free_ratio=0.0)
        bt.allocate("a", tokens=30)
        bt.allocate("b", tokens=30)  # evicts a
        assert bt.diagnose()["eviction_count"] == 1
        bt.allocate("c", tokens=30)  # evicts b
        assert bt.diagnose()["eviction_count"] == 2


# ── 13. Diagnose ────────────────────────────────────────────────────────

class TestBudgetDiagnose:
    """diagnose() 快照。"""

    def test_initial_diagnose(self) -> None:
        bt = BudgetTracker(
            total_budget=5000,
            category_budgets={"sys": 1000},
            chars_per_token=3.0,
            min_free_ratio=0.15,
        )
        d = bt.diagnose()
        assert d["total_budget"] == 5000
        assert d["total_used"] == 0
        assert d["remaining"] == 5000
        assert d["utilization"] == 0.0
        assert d["item_count"] == 0
        assert d["category_budgets"] == {"sys": 1000}
        assert d["category_used"] == {}
        assert d["eviction_count"] == 0
        assert d["min_free_ratio"] == 0.15

    def test_diagnose_after_operations(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=200, category="chat")
        bt.allocate("b", tokens=300)
        d = bt.diagnose()
        assert d["total_used"] == 500
        assert d["remaining"] == 500
        assert d["item_count"] == 2
        assert d["category_used"]["chat"] == 200
        assert round(d["utilization"], 2) == 0.5


# ── 14. On Evict Hook ───────────────────────────────────────────────────

class TestBudgetOnEvict:
    """_on_evict hook。"""

    def test_on_evict_called(self) -> None:
        evicted_keys: list[str] = []

        class HookedTracker(BudgetTracker):
            def _on_evict(self, key: str) -> None:
                evicted_keys.append(key)

        bt = HookedTracker(total_budget=50, min_free_ratio=0.0)
        bt.allocate("a", tokens=30)
        bt.allocate("b", tokens=30)
        assert "a" in evicted_keys
        assert len(evicted_keys) == 1

    def test_on_evict_multiple(self) -> None:
        evicted: list[str] = []

        class HookedTracker(BudgetTracker):
            def _on_evict(self, key: str) -> None:
                evicted.append(key)

        bt = HookedTracker(total_budget=40, min_free_ratio=0.0)
        bt.allocate("a", tokens=15)
        bt.allocate("b", tokens=15)
        bt.allocate("c", tokens=15)
        bt.allocate("d", tokens=30)  # needs to evict a+b+c
        assert "a" in evicted
        assert "b" in evicted
        assert "c" in evicted


# ── 15. Utilization ─────────────────────────────────────────────────────

class TestBudgetUtilization:
    """utilization + remaining。"""

    def test_utilization_half(self) -> None:
        bt = BudgetTracker(total_budget=1000)
        bt.allocate("a", tokens=500)
        assert bt.utilization == 0.5

    def test_utilization_full(self) -> None:
        bt = BudgetTracker(total_budget=100, min_free_ratio=0.0)
        bt.allocate("a", tokens=100)
        assert bt.utilization == 1.0

    def test_remaining_never_negative(self) -> None:
        bt = BudgetTracker(total_budget=50, min_free_ratio=0.0)
        bt.allocate("a", tokens=100)
        assert bt.remaining == 0

    def test_utilization_zero_budget(self) -> None:
        bt = BudgetTracker(total_budget=0)
        assert bt.utilization == 0.0
