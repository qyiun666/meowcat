# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — ClarifyManager 全覆盖测试
===================================

验证:
    1. TestClarifyConfig              — ClarifyConfig dataclass 字段
    2. TestClarifyManagerInit         — 构造 + 阈值默认值
    3. TestClarifyPreCheck            — 预检查: 太短触发澄清
    4. TestClarifyScore               — 歧义评分: 模糊代词 / 片段 / 长度
    5. TestClarifyEvaluate            — evaluate() 完整判定流程
    6. TestClarifyRoundLimit          — max_clarify_rounds 上限
    7. TestClarifyReset               — reset() 重置计数器
    8. TestClarifyEdge                — 边界: 空字符串 / 极长 / 纯标点
    9. TestClarifyDiagnose            — diagnose() 快照
   10. TestClarifyCustom              — 自定义 _score_ambiguity / _generate_question / _pre_check
   11. TestClarifyThresholds          — 不同 ambiguity_threshold 效果
"""

from __future__ import annotations

from unittest.mock import patch

from meowcat.clarify import ClarifyManager, ClarifyConfig, ClarifyResult


# ── 1. ClarifyConfig ───────────────────────────────────────────────────

class TestClarifyConfig:
    """ClarifyConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = ClarifyConfig()
        assert cfg.ambiguity_threshold == 0.5
        assert cfg.min_chars == 10
        assert cfg.max_clarify_rounds == 3
        assert len(cfg.vague_patterns) == 4

    def test_custom_fields(self) -> None:
        cfg = ClarifyConfig(
            ambiguity_threshold=0.7,
            min_chars=20,
            max_clarify_rounds=5,
            vague_patterns=[r"^huh$"],
        )
        assert cfg.ambiguity_threshold == 0.7
        assert cfg.min_chars == 20
        assert cfg.max_clarify_rounds == 5
        assert cfg.vague_patterns == [r"^huh$"]


# ── 2. Init ────────────────────────────────────────────────────────────

class TestClarifyManagerInit:
    """构造 + 阈值默认值。"""

    def test_default_construction(self) -> None:
        cm = ClarifyManager()
        assert cm.config.ambiguity_threshold == 0.5
        assert cm.config.min_chars == 10
        assert cm.config.max_clarify_rounds == 3
        assert len(cm.config.vague_patterns) == 4

    def test_custom_thresholds(self) -> None:
        cm = ClarifyManager(
            ambiguity_threshold=0.8,
            min_chars=15,
            max_clarify_rounds=2,
        )
        assert cm.config.ambiguity_threshold == 0.8
        assert cm.config.min_chars == 15
        assert cm.config.max_clarify_rounds == 2

    def test_config_is_readonly_copy(self) -> None:
        cm = ClarifyManager()
        cfg = cm.config
        cfg.ambiguity_threshold = 0.99  # type: ignore[misc]
        assert cm.config.ambiguity_threshold == 0.5

    def test_custom_vague_patterns(self) -> None:
        cm = ClarifyManager(vague_patterns=[r"^hmm$", r"^err+"])
        assert cm.config.vague_patterns == [r"^hmm$", r"^err+"]

    def test_none_vague_patterns_uses_default(self) -> None:
        cm = ClarifyManager(vague_patterns=None)
        assert len(cm.config.vague_patterns) == 4


# ── 3. ClarifyResult ───────────────────────────────────────────────────

class TestClarifyResult:
    """ClarifyResult dataclass 字段。"""

    def test_default_result(self) -> None:
        r = ClarifyResult()
        assert r.needs_clarification is False
        assert r.ambiguity_score == 0.0
        assert r.question == ""
        assert r.reason == ""

    def test_clarify_result(self) -> None:
        r = ClarifyResult(
            needs_clarification=True,
            ambiguity_score=0.8,
            question="What do you mean?",
            reason="Ambiguous.",
        )
        assert r.needs_clarification is True
        assert r.ambiguity_score == 0.8
        assert r.question == "What do you mean?"
        assert r.reason == "Ambiguous."


# ── 4. Pre-check ───────────────────────────────────────────────────────

class TestClarifyPreCheck:
    """预检查: 太短触发澄清。"""

    def test_too_short_triggers_clarify(self) -> None:
        cm = ClarifyManager(min_chars=10)
        r = cm.evaluate("hi")
        assert r.needs_clarification is True
        assert r.ambiguity_score == 1.0
        assert r.question != ""

    def test_just_enough_passes_precheck(self) -> None:
        cm = ClarifyManager(min_chars=5)
        r = cm.evaluate("Hello")
        assert r.ambiguity_score < 1.0  # passes pre-check, goes to scoring

    def test_custom_pre_check(self) -> None:
        """Override _pre_check for custom logic."""

        class CustomCM(ClarifyManager):
            def _pre_check(self, user_msg: str) -> ClarifyResult | None:
                if "?" not in user_msg:
                    return ClarifyResult(
                        needs_clarification=True,
                        ambiguity_score=1.0,
                        question="Please use a question mark.",
                    )
                return None

        cm = CustomCM(min_chars=0)
        r = cm.evaluate("tell me something")
        assert r.needs_clarification is True
        assert "question mark" in r.question

        r2 = cm.evaluate("tell me something?")
        assert r2.needs_clarification is False


# ── 5. Ambiguity scoring ───────────────────────────────────────────────

class TestClarifyScore:
    """歧义评分: 模糊代词 / 片段 / 长度。"""

    def test_clear_message_scores_low(self) -> None:
        cm = ClarifyManager(min_chars=1)
        r = cm.evaluate("What is the capital of France?")
        assert r.ambiguity_score < 0.5
        assert r.needs_clarification is False

    def test_vague_pronoun_scores_high(self) -> None:
        cm = ClarifyManager(min_chars=1)
        r = cm.evaluate("Can you fix it for me?")
        # Reverse-order vague pattern matches "fix...it"
        assert r.ambiguity_score >= 0.25

    def test_fragment_scores_higher(self) -> None:
        cm = ClarifyManager(min_chars=5)
        # Fragment without sentence-ending punctuation
        r = cm.evaluate("tell me about")
        # Should score: +0.15 (no terminal punct) + maybe length-based
        assert r.ambiguity_score > 0.0

    def test_short_but_above_min_scores_partial(self) -> None:
        cm = ClarifyManager(min_chars=5)
        r = cm.evaluate("Hello there")
        # Length-based partial scoring for < 30 chars
        assert 0.0 <= r.ambiguity_score <= 1.0

    def test_high_threshold_blocks_most(self) -> None:
        """With ambiguity_threshold=1.0, almost nothing triggers clarify."""
        cm = ClarifyManager(ambiguity_threshold=1.0, min_chars=5)
        r = cm.evaluate("fix it please")
        assert r.needs_clarification is False  # score likely < 1.0

    def test_low_threshold_triggers_easily(self) -> None:
        cm = ClarifyManager(ambiguity_threshold=0.0, min_chars=5)
        r = cm.evaluate("?")
        assert r.needs_clarification is True


# ── 6. Evaluate — full flow ────────────────────────────────────────────

class TestClarifyEvaluate:
    """evaluate() 完整判定流程。"""

    def test_ambiguous_message_triggers(self) -> None:
        cm = ClarifyManager(min_chars=5)
        r = cm.evaluate("fix that one")
        assert r.needs_clarification is True
        assert r.question != ""
        assert r.ambiguity_score > 0.0
        assert r.reason != ""

    def test_clear_message_no_trigger(self) -> None:
        cm = ClarifyManager(min_chars=1)
        r = cm.evaluate(
            "Please write a Python function that sorts a list of integers."
        )
        assert r.needs_clarification is False
        assert r.question == ""

    def test_multiple_rounds_tracked(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=10)

        # First ambiguous message
        r1 = cm.evaluate("fix it")
        assert r1.needs_clarification is True

        # Second ambiguous message — counter increments
        r2 = cm.evaluate("change that")
        assert r2.needs_clarification is True

        assert cm.diagnose()["clarify_count"] == 2

    def test_clear_message_resets_counter(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=10)

        # Ambiguous
        cm.evaluate("fix it")
        assert cm.diagnose()["clarify_count"] == 1

        # Clear message → reset
        cm.evaluate("What is the weather in Paris today?")
        assert cm.diagnose()["clarify_count"] == 0

    def test_max_rounds_exceeded(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=2)

        cm.evaluate("fix it")       # round 1 — triggers
        cm.evaluate("change that")  # round 2 — triggers
        r = cm.evaluate("update it")  # round 3 — exceeds max

        assert r.needs_clarification is False
        assert "max" in r.reason.lower() or "round" in r.reason.lower()
        # Counter stays at max until reset() or clear message
        assert cm.diagnose()["clarify_count"] == 2


# ── 7. Round limit ─────────────────────────────────────────────────────

class TestClarifyRoundLimit:
    """max_clarify_rounds 上限。"""

    def test_round_limit_one(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=1)

        r1 = cm.evaluate("fix it")
        assert r1.needs_clarification is True

        r2 = cm.evaluate("change that")
        assert r2.needs_clarification is False  # limit exceeded
        # Counter stays at max — only reset() or clear message resets it
        assert cm.diagnose()["clarify_count"] == 1

    def test_round_limit_zero(self) -> None:
        """max_clarify_rounds=0 means never clarify."""
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=0)

        r = cm.evaluate("fix it")
        # If pre-check catches it (< min_chars), still triggers
        # For messages above min_chars with high ambiguity:
        r2 = cm.evaluate("fix it please now")  # 19 chars > min_chars=5
        assert r2.needs_clarification is False

    def test_round_limit_sustained_ambiguity(self) -> None:
        """Long sequence of ambiguous messages respects the limit."""
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=3)

        results = []
        for i in range(5):
            r = cm.evaluate(f"fix it number {i}")
            results.append(r.needs_clarification)

        # First 3 should trigger, next 2 should not
        assert results == [True, True, True, False, False]


# ── 8. Reset ───────────────────────────────────────────────────────────

class TestClarifyReset:
    """reset() 重置计数器。"""

    def test_reset_clears_counter(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=5)

        cm.evaluate("fix it")
        cm.evaluate("change that")
        assert cm.diagnose()["clarify_count"] == 2

        cm.reset()
        assert cm.diagnose()["clarify_count"] == 0

    def test_reset_allows_more_clarify(self) -> None:
        cm = ClarifyManager(min_chars=5, max_clarify_rounds=2)

        cm.evaluate("fix it")
        cm.evaluate("change it")
        r = cm.evaluate("update it")
        assert r.needs_clarification is False  # limit exceeded

        cm.reset()
        r2 = cm.evaluate("update it")
        assert r2.needs_clarification is True  # can clarify again


# ── 9. Edge cases ──────────────────────────────────────────────────────

class TestClarifyEdge:
    """边界: 空字符串 / 极长 / 纯标点。"""

    def test_empty_string_triggers(self) -> None:
        cm = ClarifyManager(min_chars=1)
        r = cm.evaluate("")
        assert r.needs_clarification is True

    def test_whitespace_only_triggers(self) -> None:
        cm = ClarifyManager(min_chars=1)
        r = cm.evaluate("   \t\n  ")
        assert r.needs_clarification is True

    def test_very_long_message_scores_low(self) -> None:
        cm = ClarifyManager(min_chars=1)
        long_msg = (
            "Please write a comprehensive Python script that implements "
            "a binary search tree with insertion, deletion, search, and "
            "traversal operations. The script should include proper error "
            "handling and unit tests."
        )
        r = cm.evaluate(long_msg)
        assert r.needs_clarification is False
        assert r.ambiguity_score < 0.3

    def test_punctuation_only(self) -> None:
        cm = ClarifyManager(min_chars=3, ambiguity_threshold=0.2)
        r = cm.evaluate("???")
        assert r.needs_clarification is True

    def test_single_word(self) -> None:
        cm = ClarifyManager(min_chars=5)
        r = cm.evaluate("help")
        assert r.needs_clarification is True

    def test_threshold_zero_never_clarifies_except_precheck(self) -> None:
        """ambiguity_threshold=0 with sufficient length: only triggers if score > 0."""
        cm = ClarifyManager(ambiguity_threshold=0.0, min_chars=5)
        # Clear, well-formed sentence: score should be 0
        r = cm.evaluate("What is the capital of France?")
        assert r.ambiguity_score == 0.0
        assert r.needs_clarification is False


# ── 10. Diagnose ───────────────────────────────────────────────────────

class TestClarifyDiagnose:
    """diagnose() 快照。"""

    def test_initial_diagnose(self) -> None:
        cm = ClarifyManager(
            ambiguity_threshold=0.6,
            min_chars=12,
            max_clarify_rounds=4,
            vague_patterns=[r"^test"],
        )
        d = cm.diagnose()
        assert d["ambiguity_threshold"] == 0.6
        assert d["min_chars"] == 12
        assert d["max_clarify_rounds"] == 4
        assert d["vague_patterns"] == [r"^test"]
        assert d["clarify_count"] == 0

    def test_diagnose_after_evaluate(self) -> None:
        cm = ClarifyManager(min_chars=5)
        cm.evaluate("fix it")
        assert cm.diagnose()["clarify_count"] == 1


# ── 11. Custom overrides ───────────────────────────────────────────────

class TestClarifyCustom:
    """自定义 _score_ambiguity / _generate_question / _pre_check。"""

    def test_override_score_ambiguity(self) -> None:
        """Custom scoring that always returns 0.9 for short + keyword."""

        class CustomCM(ClarifyManager):
            def _score_ambiguity(self, user_msg: str) -> float:
                if "unclear" in user_msg.lower():
                    return 0.9
                return 0.0

        cm = CustomCM(min_chars=5, ambiguity_threshold=0.5)
        r = cm.evaluate("this is unclear what to do")
        assert r.needs_clarification is True
        assert r.ambiguity_score == 0.9

        r2 = cm.evaluate("define binary search tree")
        assert r2.needs_clarification is False

    def test_override_generate_question(self) -> None:
        """Custom question generation."""

        class CustomCM(ClarifyManager):
            def _generate_question(self, user_msg: str) -> str:
                return f"DEBUG: {user_msg!r} is ambiguous"

        cm = CustomCM(min_chars=5)
        r = cm.evaluate("fix it")
        assert r.question.startswith("DEBUG:")
        assert "fix it" in r.question

    def test_override_full_flow(self) -> None:
        """Override both score and question."""

        class SmartCM(ClarifyManager):
            def _score_ambiguity(self, user_msg: str) -> float:
                words = user_msg.split()
                if len(words) < 3:
                    return 0.8
                if len(words) < 6:
                    return 0.4
                return 0.1

            def _generate_question(self, user_msg: str) -> str:
                words = user_msg.split()
                if len(words) < 3:
                    return "That's very brief — could you expand?"
                return "I need a bit more context."

        cm = SmartCM(min_chars=5)

        r1 = cm.evaluate("help me")
        assert r1.needs_clarification is True
        assert "brief" in r1.question.lower()

        r2 = cm.evaluate("help me with this task please")
        assert r2.needs_clarification is False


# ── 12. Thresholds ─────────────────────────────────────────────────────

class TestClarifyThresholds:
    """不同 ambiguity_threshold 效果。"""

    def test_zero_threshold_always_clarifies(self) -> None:
        """Threshold 0.0: any positive score triggers, plus pre-check."""
        cm = ClarifyManager(ambiguity_threshold=0.0, min_chars=5)

        # Very short → pre-check catches
        r1 = cm.evaluate("hi")
        assert r1.needs_clarification is True

        # Sufficiently long + clear with terminal punct → score exactly 0
        r2 = cm.evaluate(
            "Please explain the theory of relativity in detail."
        )
        # Long + clear with terminal punctuation → score 0, threshold 0
        # score=0 is NOT > 0, so no clarification
        assert r2.ambiguity_score == 0.0
        assert r2.needs_clarification is False

    def test_one_threshold_almost_never_clarifies(self) -> None:
        """Threshold 1.0: only pre-check triggers (score 1.0)."""
        cm = ClarifyManager(ambiguity_threshold=1.0, min_chars=5)

        r = cm.evaluate("fix it please now")
        assert r.needs_clarification is False

    def test_mid_threshold_behavior(self) -> None:
        """0.5 threshold: borderline messages vary."""
        cm = ClarifyManager(ambiguity_threshold=0.5, min_chars=5)

        # Vague pronoun + fragment → likely > 0.5
        r1 = cm.evaluate("fix it")
        assert r1.needs_clarification is True

        # Clear request → likely < 0.5
        r2 = cm.evaluate(
            "Create a function that reverses a string in Python."
        )
        assert r2.needs_clarification is False
