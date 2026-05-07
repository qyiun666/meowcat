# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — RememberPolicy 全覆盖测试
===================================

验证:
    1. TestRememberConfig           — RememberConfig dataclass 字段
    2. TestRememberPolicyInit       — 构造 + 阈值默认值
    3. TestRememberPreFilter        — 预过滤: 太短 / 噪声模式
    4. TestRememberLevel1           — Level 1: 新内容 → 总是记住
    5. TestRememberLevel2           — Level 2: 相似内容 → 冷却检查
    6. TestRememberLevel3           — Level 3: 太多相似 → 跳过
    7. TestRememberRecord           — record() 历史追踪
    8. TestRememberEdge             — 边界: 空字符串 / 纯空白 / 极长文本
    9. TestRememberDiagnose         — diagnose() 快照
   10. TestRememberSimilarity       — _is_similar 边界情况
   11. TestRememberCustomTiers      — 自定义 tier 方法覆盖
"""

from __future__ import annotations

import time

import pytest

from meowcat.remember import RememberPolicy, RememberConfig


# ── Helpers ────────────────────────────────────────────────────────────

def _make_exchange(
    user_msg: str = "What is the weather today?",
    ai_reply: str = "The weather is sunny with a high of 25°C.",
) -> tuple[str, str]:
    return user_msg, ai_reply


async def _record_and_check(
    policy: RememberPolicy,
    user_msg: str,
    ai_reply: str,
) -> bool:
    """Convenience: check then record."""
    ok = await policy.should_remember(user_msg, ai_reply)
    if ok:
        policy.record(user_msg, ai_reply)
    return ok


# ── 1. RememberConfig ──────────────────────────────────────────────────

class TestRememberConfig:
    """RememberConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = RememberConfig()
        assert cfg.cooldown_seconds == 60.0
        assert cfg.similarity_threshold == 0.6
        assert cfg.min_content_length == 10
        assert cfg.max_recent_duplicates == 3
        assert cfg.recent_window_size == 20
        assert cfg.noise_patterns == []

    def test_custom_fields(self) -> None:
        cfg = RememberConfig(
            cooldown_seconds=30.0,
            similarity_threshold=0.8,
            min_content_length=20,
            max_recent_duplicates=5,
            recent_window_size=50,
            noise_patterns=[r"^OK$", r"^Got it"],
        )
        assert cfg.cooldown_seconds == 30.0
        assert cfg.similarity_threshold == 0.8
        assert cfg.min_content_length == 20
        assert cfg.max_recent_duplicates == 5
        assert cfg.recent_window_size == 50
        assert cfg.noise_patterns == [r"^OK$", r"^Got it"]


# ── 2. Init ────────────────────────────────────────────────────────────

class TestRememberPolicyInit:
    """构造 + 阈值默认值。"""

    def test_default_construction(self) -> None:
        policy = RememberPolicy()
        assert policy.config.cooldown_seconds == 60.0
        assert policy.config.similarity_threshold == 0.6
        assert policy.config.min_content_length == 10
        assert policy.config.max_recent_duplicates == 3
        assert policy.config.recent_window_size == 20
        assert policy.config.noise_patterns == []

    def test_custom_thresholds(self) -> None:
        policy = RememberPolicy(
            cooldown_seconds=30.0,
            similarity_threshold=0.8,
            min_content_length=20,
            max_recent_duplicates=5,
            recent_window_size=50,
        )
        assert policy.config.cooldown_seconds == 30.0
        assert policy.config.similarity_threshold == 0.8
        assert policy.config.min_content_length == 20
        assert policy.config.max_recent_duplicates == 5
        assert policy.config.recent_window_size == 50

    def test_config_is_readonly_copy(self) -> None:
        policy = RememberPolicy()
        cfg = policy.config
        cfg.cooldown_seconds = 999.0  # type: ignore[misc]
        # Original should be unchanged
        assert policy.config.cooldown_seconds == 60.0

    def test_noise_patterns_accepted(self) -> None:
        policy = RememberPolicy(noise_patterns=[r"^OK$", r"noise\d+"])
        assert policy.config.noise_patterns == [r"^OK$", r"noise\d+"]


# ── 3. Pre-filter ──────────────────────────────────────────────────────

class TestRememberPreFilter:
    """预过滤: 太短 / 噪声模式。"""

    async def test_too_short_rejected(self) -> None:
        policy = RememberPolicy(min_content_length=10)
        ok = await policy.should_remember("Hi", "Hey")
        assert ok is False

    async def test_just_enough_length_passes(self) -> None:
        policy = RememberPolicy(min_content_length=5)
        ok = await policy.should_remember("Hello", "Hi there")
        assert ok is True

    async def test_noise_pattern_rejected(self) -> None:
        policy = RememberPolicy(
            noise_patterns=[r"^OK$", r"nothing"],
            min_content_length=0,
        )
        ok = await policy.should_remember("nothing special here", "OK")
        assert ok is False

    async def test_no_noise_match_passes(self) -> None:
        policy = RememberPolicy(
            noise_patterns=[r"^OK$"],
            min_content_length=0,
        )
        # "OK then" should not match ^OK$ pattern
        ok = await policy.should_remember(
            "What is the weather?", "It is sunny today."
        )
        assert ok is True

    async def test_custom_pre_filter(self) -> None:
        """Override _pre_filter for custom logic."""

        class CustomPolicy(RememberPolicy):
            def _pre_filter(self, user_msg: str, ai_reply: str) -> bool:
                return "important" in user_msg.lower()

        policy = CustomPolicy(min_content_length=0)
        ok = await policy.should_remember(
            "This is an important question", "Reply"
        )
        assert ok is True

        ok = await policy.should_remember(
            "Just a casual chat", "Reply"
        )
        assert ok is False


# ── 4. Level 1 — Always remember ───────────────────────────────────────

class TestRememberLevel1:
    """Level 1: 新内容 → 总是记住。"""

    async def test_first_exchange_always_remembered(self) -> None:
        policy = RememberPolicy()
        ok = await policy.should_remember(
            "Tell me about Python", "Python is a programming language."
        )
        assert ok is True

    async def test_distinct_content_always_remembered(self) -> None:
        policy = RememberPolicy()

        # Record first exchange
        await _record_and_check(
            policy, "What is Python?", "Python is a language."
        )

        # Second exchange is completely different
        ok = await policy.should_remember(
            "How to cook pasta?",
            "Boil water, add salt, cook for 8 minutes.",
        )
        assert ok is True

    async def test_multiple_distinct_exchanges(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.5)

        exchanges = [
            ("What is Python?", "Python is a language."),
            ("How to cook pasta?", "Boil water and cook."),
            ("Tell me about Mars", "Mars is the fourth planet."),
            ("What is quantum physics?", "Study of subatomic particles."),
        ]

        for u, a in exchanges:
            ok = await _record_and_check(policy, u, a)
            assert ok is True


# ── 5. Level 2 — Throttle / cooldown ───────────────────────────────────

class TestRememberLevel2:
    """Level 2: 相似内容 → 冷却检查。"""

    async def test_similar_within_cooldown_blocked(self) -> None:
        policy = RememberPolicy(
            cooldown_seconds=999.0,  # Very long cooldown
            similarity_threshold=0.3,  # Easy to match
        )

        # Record first
        await _record_and_check(
            policy,
            "What is the weather today?",
            "The weather is sunny.",
        )

        # Similar — should be blocked (cooldown)
        ok = await policy.should_remember(
            "What is the weather like today?",
            "It is sunny and warm today.",
        )
        assert ok is False

    async def test_similar_after_cooldown_passes(self) -> None:
        policy = RememberPolicy(
            cooldown_seconds=0.0,  # Zero cooldown
            similarity_threshold=0.3,
        )

        await _record_and_check(
            policy,
            "What is the weather today?",
            "The weather is sunny.",
        )

        # Zero cooldown → passes despite similarity
        ok = await policy.should_remember(
            "What is the weather today?",
            "Still sunny.",
        )
        assert ok is True

    async def test_custom_level2(self) -> None:
        """Override _level2_throttle for custom logic."""

        class CustomPolicy(RememberPolicy):
            def _level2_throttle(
                self, user_msg: str, ai_reply: str, last_similar_ts: float,
            ) -> bool:
                # Always allow on Tuesdays (simulated)
                return True

        policy = CustomPolicy(
            cooldown_seconds=999.0,
            similarity_threshold=0.3,
        )

        await _record_and_check(
            policy, "Weather today?", "Sunny."
        )

        ok = await policy.should_remember(
            "Weather today again?", "Still sunny."
        )
        assert ok is True


# ── 6. Level 3 — Skip ──────────────────────────────────────────────────

class TestRememberLevel3:
    """Level 3: 太多相似 → 跳过。"""

    async def test_too_many_similar_skipped(self) -> None:
        policy = RememberPolicy(
            max_recent_duplicates=2,
            similarity_threshold=0.3,
            cooldown_seconds=0.0,  # Remove cooldown to test Level 3
        )

        # Record 2 similar exchanges (reaches cap)
        await _record_and_check(
            policy,
            "What is the weather today?",
            "The weather is sunny today.",
        )
        await _record_and_check(
            policy,
            "What is the weather?",
            "It is sunny.",
        )

        # Third similar → Level 3 skip
        ok = await policy.should_remember(
            "Weather report please",
            "Today is sunny.",
        )
        assert ok is False

    async def test_dissimilar_after_cap_still_passes(self) -> None:
        policy = RememberPolicy(
            max_recent_duplicates=1,
            similarity_threshold=0.5,
            cooldown_seconds=0.0,
        )

        # Fill with weather exchanges
        await _record_and_check(
            policy, "Weather today?", "It is sunny."
        )

        # Completely different topic → Level 1
        ok = await policy.should_remember(
            "Explain quantum entanglement",
            "Quantum entanglement is a physical phenomenon...",
        )
        assert ok is True

    async def test_custom_level3(self) -> None:
        """Override _level3_skip for custom logic."""

        class CustomPolicy(RememberPolicy):
            def _level3_skip(
                self, user_msg: str, ai_reply: str, similar_count: int,
            ) -> bool:
                # Allow up to 10 regardless of config
                if similar_count <= 10:
                    return True
                return False

        policy = CustomPolicy(
            max_recent_duplicates=1,
            similarity_threshold=0.3,
            cooldown_seconds=0.0,
        )

        await _record_and_check(policy, "Weather?", "Sunny.")

        # Even though cap is 1, custom Level 3 allows it
        ok = await policy.should_remember("Weather again?", "Still sunny.")
        assert ok is True


# ── 7. Record ──────────────────────────────────────────────────────────

class TestRememberRecord:
    """record() 历史追踪。"""

    async def test_record_increments_history(self) -> None:
        policy = RememberPolicy()
        assert policy.diagnose()["history_size"] == 0

        policy.record("msg1", "reply1")
        assert policy.diagnose()["history_size"] == 1

        policy.record("msg2", "reply2")
        assert policy.diagnose()["history_size"] == 2

    async def test_history_trimmed_to_window(self) -> None:
        policy = RememberPolicy(recent_window_size=3)

        for i in range(10):
            policy.record(f"message {i}", f"reply {i}")

        assert policy.diagnose()["history_size"] == 3

    async def test_record_sequence_affects_tiers(self) -> None:
        policy = RememberPolicy(
            max_recent_duplicates=2,
            similarity_threshold=0.3,
            cooldown_seconds=0.0,
            recent_window_size=10,
        )

        # First: Level 1
        ok1 = await _record_and_check(
            policy, "What is the weather today", "It is sunny outside."
        )
        assert ok1 is True

        # Second similar: Level 2 (cooldown 0 → passes)
        ok2 = await _record_and_check(
            policy, "What is the weather like", "It is sunny today."
        )
        assert ok2 is True

        # Third similar: Level 3 (cap=2 reached)
        ok3 = await policy.should_remember(
            "Weather is what today", "Sunny it is outside today."
        )
        assert ok3 is False


# ── 8. Edge cases ──────────────────────────────────────────────────────

class TestRememberEdge:
    """边界: 空字符串 / 纯空白 / 极长文本。"""

    async def test_empty_messages_rejected(self) -> None:
        policy = RememberPolicy(min_content_length=1)
        ok = await policy.should_remember("", "")
        assert ok is False

    async def test_whitespace_only_rejected(self) -> None:
        policy = RememberPolicy(min_content_length=1)
        ok = await policy.should_remember("   ", "\t\n")
        assert ok is False

    async def test_very_long_content_accepted(self) -> None:
        policy = RememberPolicy(min_content_length=10)
        long_msg = "x" * 10000
        ok = await policy.should_remember(long_msg, "y" * 5000)
        assert ok is True

    async def test_min_content_length_zero(self) -> None:
        """min_content_length=0 means no length check."""
        policy = RememberPolicy(min_content_length=0)
        ok = await policy.should_remember("x", "y")
        assert ok is True

    async def test_punctuation_only_similarity(self) -> None:
        """Pure punctuation should normalize to empty for similarity."""
        policy = RememberPolicy(
            similarity_threshold=0.5,
            min_content_length=0,
            cooldown_seconds=0.0,
            max_recent_duplicates=10,
        )

        await _record_and_check(policy, "Hello world", "Hi there")

        # "!!!" and "..." both normalize to empty → not similar to "hello world"
        ok = await policy.should_remember("!!!", "...")
        assert ok is True


# ── 9. Diagnose ────────────────────────────────────────────────────────

class TestRememberDiagnose:
    """diagnose() 快照。"""

    async def test_initial_diagnose(self) -> None:
        policy = RememberPolicy(
            cooldown_seconds=30.0,
            similarity_threshold=0.7,
            min_content_length=15,
            max_recent_duplicates=4,
            recent_window_size=25,
            noise_patterns=[r"^test"],
        )
        d = policy.diagnose()
        assert d["cooldown_seconds"] == 30.0
        assert d["similarity_threshold"] == 0.7
        assert d["min_content_length"] == 15
        assert d["max_recent_duplicates"] == 4
        assert d["recent_window_size"] == 25
        assert d["noise_patterns"] == [r"^test"]
        assert d["history_size"] == 0

    async def test_diagnose_after_records(self) -> None:
        policy = RememberPolicy()
        policy.record("a", "b")
        policy.record("c", "d")
        assert policy.diagnose()["history_size"] == 2


# ── 10. Similarity ─────────────────────────────────────────────────────

class TestRememberSimilarity:
    """_is_similar 边界情况。"""

    def test_identical_text_is_similar(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.5)
        assert policy._is_similar("hello world", "ok", "hello world", "ok")

    def test_completely_different_is_not_similar(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.5)
        assert not policy._is_similar(
            "weather forecast", "sunny",
            "quantum physics", "entanglement",
        )

    def test_partial_overlap_below_threshold(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.9)
        # "hello world" vs "hello there" → ~50% overlap
        assert not policy._is_similar(
            "hello world", "ok",
            "hello there", "ok",
        )

    def test_partial_overlap_above_threshold(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.3)
        # Low threshold → partial overlap qualifies
        assert policy._is_similar(
            "hello world", "ok",
            "hello there", "ok",
        )

    def test_empty_text_not_similar(self) -> None:
        policy = RememberPolicy()
        assert not policy._is_similar("!!!", "...", "???", "---")

    def test_high_threshold_exact_match(self) -> None:
        policy = RememberPolicy(similarity_threshold=0.99)
        assert policy._is_similar(
            "the weather is nice today",
            "yes indeed",
            "the weather is nice today",
            "yes indeed",
        )


# ── 11. Custom tiers ───────────────────────────────────────────────────

class TestRememberCustomTiers:
    """自定义 tier 方法覆盖。"""

    async def test_override_evaluate_tier(self) -> None:
        """Override _evaluate_tier to always allow."""

        class AlwaysRemember(RememberPolicy):
            def _evaluate_tier(
                self, user_msg: str, ai_reply: str,
            ) -> bool:
                return True

        policy = AlwaysRemember(
            max_recent_duplicates=1,
            similarity_threshold=0.1,
            cooldown_seconds=999.0,
        )

        # Record first
        await _record_and_check(policy, "weather", "sunny")

        # Same topic → should normally be blocked, but custom tier allows
        ok = await policy.should_remember("weather again", "still sunny")
        assert ok is True

    async def test_override_is_similar(self) -> None:
        """Override _is_similar to use custom logic."""

        class LengthSimilarity(RememberPolicy):
            def _is_similar(
                self,
                msg1: str, reply1: str,
                msg2: str, reply2: str,
            ) -> bool:
                # Similar if lengths are close
                len1 = len(msg1) + len(reply1)
                len2 = len(msg2) + len(reply2)
                if len1 == 0 or len2 == 0:
                    return False
                return abs(len1 - len2) / max(len1, len2) < 0.2

        policy = LengthSimilarity(
            max_recent_duplicates=2,
            cooldown_seconds=0.0,
            min_content_length=0,
        )

        await _record_and_check(
            policy, "a" * 100, "b" * 100,
        )

        # Similar length → Level 2 (cooldown 0 → passes)
        ok = await policy.should_remember("c" * 105, "d" * 95)
        assert ok is True
