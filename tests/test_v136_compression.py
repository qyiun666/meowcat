# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — CompressionManager 全覆盖测试
========================================

验证:
    1. TestCompressionConfig        — CompressionConfig dataclass 字段
    2. TestCompressionManagerInit   — 构造 + 阈值默认值
    3. TestCompressionLight         — light tier: pass-through (≤2 messages)
    4. TestCompressionMedium        — medium tier: algorithmic trim (≤5 messages)
    5. TestCompressionHeavy         — heavy tier (>5) without summarizer → fallback
    6. TestCompressionHeavySummarizer — heavy tier with LLM summarizer
    7. TestCompressionEdge          — 边界: 空列表, 单条, max_tokens override
    8. TestCompressionDiagnose      — diagnose() 快照
"""

from __future__ import annotations

import pytest

from meowcat.compression import CompressionManager, CompressionConfig


# ── Helpers ────────────────────────────────────────────────────────────

def _make_msgs(n: int) -> list[dict[str, str]]:
    """Create *n* message dicts with realistic-sized content."""
    return [
        {"role": "system", "content": "You are a helpful AI assistant."},
    ] + [
        {"role": "user" if i % 2 == 0 else "assistant",
         "content": f"This is message number {i}. " * 15}
        for i in range(1, n + 1)
    ]


# ── 1. CompressionConfig ───────────────────────────────────────────────

class TestCompressionConfig:
    """CompressionConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = CompressionConfig()
        assert cfg.light_threshold == 2
        assert cfg.medium_threshold == 5
        assert cfg.max_tokens == 4000
        assert cfg.chars_per_token == 4.0

    def test_custom_fields(self) -> None:
        cfg = CompressionConfig(
            light_threshold=1,
            medium_threshold=3,
            max_tokens=2000,
            chars_per_token=3.5,
        )
        assert cfg.light_threshold == 1
        assert cfg.medium_threshold == 3
        assert cfg.max_tokens == 2000
        assert cfg.chars_per_token == 3.5


# ── 2. Init ────────────────────────────────────────────────────────────

class TestCompressionManagerInit:
    """构造 + 阈值默认值。"""

    def test_default_construction(self) -> None:
        cm = CompressionManager()
        assert cm.config.light_threshold == 2
        assert cm.config.medium_threshold == 5
        assert cm.config.max_tokens == 4000

    def test_custom_thresholds(self) -> None:
        cm = CompressionManager(
            light_threshold=1,
            medium_threshold=3,
            max_tokens=1000,
            chars_per_token=3.0,
        )
        assert cm.config.light_threshold == 1
        assert cm.config.medium_threshold == 3
        assert cm.config.max_tokens == 1000
        assert cm.config.chars_per_token == 3.0

    def test_config_is_readonly_copy(self) -> None:
        cm = CompressionManager()
        cfg = cm.config
        cfg.light_threshold = 99  # type: ignore[misc]
        # Original should be unchanged
        assert cm.config.light_threshold == 2


# ── 3. Light tier ──────────────────────────────────────────────────────

class TestCompressionLight:
    """Light tier: pass-through for ≤ light_threshold messages."""

    @pytest.mark.anyio
    async def test_single_message_passthrough(self) -> None:
        cm = CompressionManager(light_threshold=2)
        msgs = _make_msgs(1)
        result = await cm.compress(msgs)
        assert result == msgs

    @pytest.mark.anyio
    async def test_two_messages_passthrough(self) -> None:
        cm = CompressionManager(light_threshold=2)
        msgs = _make_msgs(2)
        result = await cm.compress(msgs)
        assert result == msgs

    @pytest.mark.anyio
    async def test_light_copies_not_mutates(self) -> None:
        cm = CompressionManager(light_threshold=2)
        msgs = _make_msgs(2)
        result = await cm.compress(msgs)
        assert result is not msgs  # shallow copy
        assert result == msgs

    @pytest.mark.anyio
    async def test_custom_light_threshold(self) -> None:
        cm = CompressionManager(light_threshold=4, medium_threshold=10)
        msgs = _make_msgs(3)  # 4 total: 1 system + 3 messages
        result = await cm.compress(msgs)
        assert len(result) == 4


# ── 4. Medium tier ─────────────────────────────────────────────────────

class TestCompressionMedium:
    """Medium tier: algorithmic trim (≤ medium_threshold)."""

    @pytest.mark.anyio
    async def test_three_messages_trim_if_over_budget(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=10)
        msgs = _make_msgs(3)
        result = await cm.compress(msgs)
        # First message always kept
        assert result[0] == msgs[0]
        # May or may not include all messages depending on budget
        assert 1 <= len(result) <= 3

    @pytest.mark.anyio
    async def test_keeps_first_message_always(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=10)
        msgs = _make_msgs(3)
        result = await cm.compress(msgs)
        assert result[0] == msgs[0]

    @pytest.mark.anyio
    async def test_five_messages_budget_sufficient(self) -> None:
        cm = CompressionManager(
            light_threshold=2, medium_threshold=6, max_tokens=20000,
        )
        msgs = _make_msgs(5)  # 6 total
        result = await cm.compress(msgs)
        # All 6 fit because budget is large
        assert len(result) == 6

    @pytest.mark.anyio
    async def test_five_messages_tight_budget(self) -> None:
        cm = CompressionManager(
            light_threshold=2, medium_threshold=5, max_tokens=50,
        )
        msgs = _make_msgs(5)
        result = await cm.compress(msgs)
        # At least first message kept
        assert len(result) >= 1
        assert result[0] == msgs[0]


# ── 5. Heavy tier (fallback) ───────────────────────────────────────────

class TestCompressionHeavy:
    """Heavy tier (> medium_threshold) without summarizer → fallback."""

    @pytest.mark.anyio
    async def test_heavy_falls_back_to_medium(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=500)
        msgs = _make_msgs(6)
        result = await cm.compress(msgs)
        # Falls back to medium; first message always kept
        assert len(result) >= 1
        assert result[0] == msgs[0]
        # Should be trimmed (fewer than 6 messages)
        assert len(result) < 6

    @pytest.mark.anyio
    async def test_heavy_many_messages(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=500)
        msgs = _make_msgs(20)
        result = await cm.compress(msgs)
        assert len(result) >= 1
        assert result[0] == msgs[0]
        assert len(result) < 20

    @pytest.mark.anyio
    async def test_heavy_messages_order_preserved(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5, max_tokens=500)
        msgs = _make_msgs(6)
        result = await cm.compress(msgs)
        # First message is msgs[0]
        assert result[0] == msgs[0]
        # Remaining messages appear in msgs order (reversed insert ⇒ original order)
        if len(result) > 1:
            # Check that remaining msgs preserve original relative order
            remaining = result[1:]
            original_tail = msgs[1:]
            # Should be a suffix of original_tail
            idx = 0
            for r in remaining:
                while idx < len(original_tail) and original_tail[idx] != r:
                    idx += 1
                assert idx < len(original_tail)
                idx += 1


# ── 6. Heavy tier with summarizer ──────────────────────────────────────

class TestCompressionHeavySummarizer:
    """Heavy tier with LLM summarizer callback."""

    @pytest.mark.anyio
    async def test_summarizer_called(self) -> None:
        calls: list[tuple] = []

        async def fake_summarizer(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            calls.append((len(msgs), budget))
            return [
                {"role": "system", "content": "Summarized context."},
                {"role": "user", "content": "Latest user message."},
            ]

        cm = CompressionManager(
            light_threshold=2, medium_threshold=6,
            summarizer=fake_summarizer,
        )
        msgs = _make_msgs(6)  # 7 total
        result = await cm.compress(msgs)
        assert len(calls) == 1
        assert calls[0] == (7, 4000)
        assert len(result) == 2
        assert result[0]["content"] == "Summarized context."

    @pytest.mark.anyio
    async def test_summarizer_not_called_for_light(self) -> None:
        calls: list[tuple] = []

        async def fake_summarizer(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            calls.append(1)
            return msgs

        cm = CompressionManager(summarizer=fake_summarizer)
        msgs = _make_msgs(1)
        await cm.compress(msgs)
        assert len(calls) == 0  # light tier, no summarizer call

    @pytest.mark.anyio
    async def test_summarizer_not_called_for_medium(self) -> None:
        calls: list[tuple] = []

        async def fake_summarizer(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            calls.append(1)
            return msgs

        cm = CompressionManager(summarizer=fake_summarizer, medium_threshold=10)
        msgs = _make_msgs(5)  # 6 total, ≤ medium_threshold(10)
        await cm.compress(msgs)
        assert len(calls) == 0  # medium tier, no summarizer call

    @pytest.mark.anyio
    async def test_summarizer_failure_fallback(self) -> None:
        async def failing_summarizer(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            raise RuntimeError("LLM unavailable")

        cm = CompressionManager(
            light_threshold=2, medium_threshold=5,
            summarizer=failing_summarizer,
        )
        msgs = _make_msgs(6)
        result = await cm.compress(msgs)
        # Should not crash; falls back to medium trim
        assert len(result) >= 1
        assert result[0] == msgs[0]

    @pytest.mark.anyio
    async def test_summarizer_max_tokens_override(self) -> None:
        calls: list[tuple] = []

        async def fake_summarizer(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            calls.append(budget)
            return msgs[:3]

        cm = CompressionManager(
            light_threshold=2, medium_threshold=5,
            summarizer=fake_summarizer,
        )
        msgs = _make_msgs(6)
        await cm.compress(msgs, max_tokens=1000)
        assert calls[0] == 1000  # override applied


# ── 7. Edge cases ──────────────────────────────────────────────────────

class TestCompressionEdge:
    """边界用例。"""

    @pytest.mark.anyio
    async def test_empty_list(self) -> None:
        cm = CompressionManager()
        result = await cm.compress([])
        assert result == []

    @pytest.mark.anyio
    async def test_max_tokens_override(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=5)
        msgs = _make_msgs(3)
        # Tiny budget — only first message survives
        result = await cm.compress(msgs, max_tokens=1)
        assert len(result) >= 1

    @pytest.mark.anyio
    async def test_huge_budget_passthrough(self) -> None:
        cm = CompressionManager(light_threshold=2, medium_threshold=10)
        msgs = _make_msgs(5)  # 6 total
        result = await cm.compress(msgs, max_tokens=999999)
        assert len(result) == 6


# ── 8. Diagnose ────────────────────────────────────────────────────────

class TestCompressionDiagnose:
    """diagnose() 快照。"""

    def test_diagnose_defaults(self) -> None:
        cm = CompressionManager()
        diag = cm.diagnose()
        assert diag["light_threshold"] == 2
        assert diag["medium_threshold"] == 5
        assert diag["max_tokens"] == 4000
        assert diag["chars_per_token"] == 4.0
        assert diag["has_summarizer"] is False

    def test_diagnose_with_summarizer(self) -> None:
        async def dummy(
            msgs: list[dict[str, str]], budget: int,
        ) -> list[dict[str, str]]:
            return msgs

        cm = CompressionManager(summarizer=dummy)
        diag = cm.diagnose()
        assert diag["has_summarizer"] is True
