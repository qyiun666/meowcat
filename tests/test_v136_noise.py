# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — NoiseFilter 全覆盖测试
================================

验证:
    1. TestNoiseFilterConfig         — NoiseFilterConfig dataclass 字段
    2. TestNoiseFilterInit           — 构造 + 默认值
    3. TestNoiseWorthRemembering     — worth_remembering() 核心判定
    4. TestNoiseIsNoise              — is_noise() 单文本检查
    5. TestNoisePatterns             — 噪声正则: 确认词 / 问候 / 标点
    6. TestNoiseMinLength            — 最小长度过滤
    7. TestNoiseRepetition           — 字符重复检测
    8. TestNoiseCustomFilter         — _custom_filter 自定义
    9. TestNoiseEdge                 — 边界: 空 / 纯空白 / 极长
   10. TestNoiseDiagnose             — diagnose() 快照 + 计数
   11. TestNoiseResetCounts          — reset_counts()
   12. TestNoiseOneSidedNoise        — 仅一侧噪声不拦截
"""

from __future__ import annotations

from meowcat.noise import NoiseFilter, NoiseFilterConfig


# ── 1. NoiseFilterConfig ────────────────────────────────────────────────

class TestNoiseFilterConfig:
    """NoiseFilterConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = NoiseFilterConfig()
        assert len(cfg.noise_patterns) == 6
        assert cfg.min_chars == 8
        assert cfg.max_rep_ratio == 0.5
        assert cfg.check_repetition is True

    def test_custom_fields(self) -> None:
        cfg = NoiseFilterConfig(
            noise_patterns=[r"^test$"],
            min_chars=20,
            max_rep_ratio=0.3,
            check_repetition=False,
        )
        assert cfg.noise_patterns == [r"^test$"]
        assert cfg.min_chars == 20
        assert cfg.max_rep_ratio == 0.3
        assert cfg.check_repetition is False


# ── 2. Init ─────────────────────────────────────────────────────────────

class TestNoiseFilterInit:
    """构造 + 默认值。"""

    def test_default_construction(self) -> None:
        nf = NoiseFilter()
        assert len(nf.config.noise_patterns) == 6
        assert nf.config.min_chars == 8
        assert nf.config.max_rep_ratio == 0.5
        assert nf.config.check_repetition is True

    def test_custom_construction(self) -> None:
        nf = NoiseFilter(
            noise_patterns=[r"^noise$"],
            min_chars=15,
            max_rep_ratio=0.4,
            check_repetition=False,
        )
        assert nf.config.noise_patterns == [r"^noise$"]
        assert nf.config.min_chars == 15
        assert nf.config.max_rep_ratio == 0.4
        assert nf.config.check_repetition is False

    def test_config_is_readonly_copy(self) -> None:
        nf = NoiseFilter()
        cfg = nf.config
        cfg.min_chars = 999  # type: ignore[misc]
        assert nf.config.min_chars == 8

    def test_none_patterns_uses_default(self) -> None:
        nf = NoiseFilter(noise_patterns=None)
        assert len(nf.config.noise_patterns) == 6


# ── 3. worth_remembering ────────────────────────────────────────────────

class TestNoiseWorthRemembering:
    """worth_remembering() 核心判定。"""

    def test_real_content_passes(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering(
            "What is the capital of France?",
            "The capital of France is Paris.",
        )
        assert ok is True

    def test_pure_ack_noise_rejected(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering("ok", "got it")
        assert ok is False

    def test_greeting_pair_rejected(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering("hi", "hello")
        assert ok is False

    def test_empty_exchange_rejected(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering("", "")
        assert ok is False

    def test_whitespace_only_rejected(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering("   ", "\t\n")
        assert ok is False

    def test_too_short_rejected(self) -> None:
        nf = NoiseFilter(min_chars=10)
        ok = nf.worth_remembering("abc", "def")
        assert ok is False

    def test_repetitive_text_rejected(self) -> None:
        nf = NoiseFilter(max_rep_ratio=0.3, min_chars=0)
        ok = nf.worth_remembering("aaaaa bbbbb", "cccccc")
        assert ok is False  # a,b,c each > 30%

    def test_counts_updated(self) -> None:
        nf = NoiseFilter()
        nf.worth_remembering("ok", "got it")   # noise
        nf.worth_remembering("hi", "hey")       # noise
        nf.worth_remembering("Real question?", "Real answer here.")  # pass
        assert nf.diagnose()["noise_count"] == 2
        assert nf.diagnose()["passed_count"] == 1


# ── 4. is_noise ─────────────────────────────────────────────────────────

class TestNoiseIsNoise:
    """is_noise() 单文本检查。"""

    def test_ack_is_noise(self) -> None:
        nf = NoiseFilter()
        assert nf.is_noise("ok") is True

    def test_greeting_is_noise(self) -> None:
        nf = NoiseFilter()
        assert nf.is_noise("hello") is True

    def test_real_content_not_noise(self) -> None:
        nf = NoiseFilter()
        assert nf.is_noise("What is the weather today?") is False

    def test_empty_is_noise(self) -> None:
        nf = NoiseFilter()
        assert nf.is_noise("") is True

    def test_whitespace_is_noise(self) -> None:
        nf = NoiseFilter()
        assert nf.is_noise("   ") is True

    def test_repetitive_is_noise(self) -> None:
        nf = NoiseFilter(max_rep_ratio=0.3, min_chars=0)
        assert nf.is_noise("aaaaa") is True

    def test_too_short_is_noise(self) -> None:
        nf = NoiseFilter(min_chars=10)
        assert nf.is_noise("short") is True


# ── 5. Noise patterns ───────────────────────────────────────────────────

class TestNoisePatterns:
    """噪声正则: 确认词 / 问候 / 标点。"""

    def test_ok_variants(self) -> None:
        nf = NoiseFilter(min_chars=0)
        for word in ["ok", "okay", "k", "kk", "okie", "got it", "gotcha"]:
            assert nf.worth_remembering(word, "xyz"), (
                f"Single '{word}' not noise because reply 'xyz' is not noise"
            )
            # Both sides noise → rejected
            assert nf.worth_remembering(word, word) is False

    def test_gratitude_variants(self) -> None:
        nf = NoiseFilter(min_chars=0)
        for word in ["thanks", "thx", "ty", "np", "no problem", "yw"]:
            assert nf.worth_remembering(word, word) is False

    def test_greeting_variants(self) -> None:
        nf = NoiseFilter(min_chars=0)
        for word in ["hi", "hello", "hey", "bye", "goodbye"]:
            assert nf.worth_remembering(word, word) is False

    def test_punctuation_is_noise(self) -> None:
        nf = NoiseFilter(min_chars=0)
        assert nf.worth_remembering("!!!", "???") is False
        assert nf.worth_remembering("...", "---") is False

    def test_laughter_is_noise(self) -> None:
        nf = NoiseFilter(min_chars=0)
        assert nf.worth_remembering("haha", "hahaha") is False
        assert nf.worth_remembering("lol", "lolol") is False


# ── 6. Min length ───────────────────────────────────────────────────────

class TestNoiseMinLength:
    """最小长度过滤。"""

    def test_below_min_rejected(self) -> None:
        nf = NoiseFilter(min_chars=20, noise_patterns=[])
        ok = nf.worth_remembering("short", "msg")
        assert ok is False  # "short msg" = 9 chars < 20

    def test_at_min_accepted(self) -> None:
        nf = NoiseFilter(min_chars=5, noise_patterns=[])
        ok = nf.worth_remembering("abcde", "fghij")
        assert ok is True  # "abcde fghij" = 11 chars >= 5

    def test_min_length_zero(self) -> None:
        nf = NoiseFilter(min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("x", "y")
        assert ok is True


# ── 7. Repetition ───────────────────────────────────────────────────────

class TestNoiseRepetition:
    """字符重复检测。"""

    def test_high_repetition_rejected(self) -> None:
        nf = NoiseFilter(max_rep_ratio=0.3, min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("aaaaa", "bbbbb")
        assert ok is False  # 'a' is 5/5 = 1.0 > 0.3

    def test_normal_repetition_accepted(self) -> None:
        nf = NoiseFilter(max_rep_ratio=0.5, min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("hello", "world")
        assert ok is True  # 'l' is 3/10 = 0.3 ≤ 0.5

    def test_repetition_disabled(self) -> None:
        nf = NoiseFilter(
            check_repetition=False, min_chars=0, noise_patterns=[],
        )
        ok = nf.worth_remembering("aaaaa", "bbbbb")
        assert ok is True

    def test_short_text_no_repetition_check(self) -> None:
        # Text < 3 alpha chars → skip repetition check
        nf = NoiseFilter(max_rep_ratio=0.01, min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("a", "b")
        assert ok is True  # too short for repetition check


# ── 8. Custom filter ────────────────────────────────────────────────────

class TestNoiseCustomFilter:
    """_custom_filter 自定义。"""

    def test_custom_block_keyword(self) -> None:
        class CustomNF(NoiseFilter):
            def _custom_filter(self, user_msg: str, ai_reply: str) -> bool:
                return "spam" in user_msg.lower()

        nf = CustomNF(min_chars=0, noise_patterns=[])
        assert nf.worth_remembering("this is spam content", "reply") is False
        assert nf.worth_remembering("this is fine", "reply") is True

    def test_custom_allow_all(self) -> None:
        class CustomNF(NoiseFilter):
            def _custom_filter(self, user_msg: str, ai_reply: str) -> bool:
                return "block" in (user_msg + ai_reply).lower()

        nf = CustomNF(min_chars=0, noise_patterns=[])
        assert nf.worth_remembering("please block this", "ok") is False
        assert nf.worth_remembering("real question?", "real answer.") is True


# ── 9. Edge cases ───────────────────────────────────────────────────────

class TestNoiseEdge:
    """边界: 空 / 纯空白 / 极长。"""

    def test_very_long_content_is_noise(self) -> None:
        nf = NoiseFilter()
        long_msg = "x" * 1000
        ok = nf.worth_remembering(long_msg, "y" * 500)
        # "x"*1000 → repetition 1000/1000 = 1.0 > 0.5 → noise
        assert ok is False

    def test_single_char_each_side(self) -> None:
        nf = NoiseFilter(min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("x", "y")
        assert ok is True  # passes all checks

    def test_numbers_only(self) -> None:
        nf = NoiseFilter(min_chars=0, noise_patterns=[])
        ok = nf.worth_remembering("123", "456")
        assert ok is True  # no alpha chars → no repetition flag


# ── 10. Diagnose ────────────────────────────────────────────────────────

class TestNoiseDiagnose:
    """diagnose() 快照 + 计数。"""

    def test_initial_diagnose(self) -> None:
        nf = NoiseFilter(
            noise_patterns=[r"^test$"],
            min_chars=12,
            max_rep_ratio=0.3,
            check_repetition=False,
        )
        d = nf.diagnose()
        assert d["noise_patterns"] == [r"^test$"]
        assert d["min_chars"] == 12
        assert d["max_rep_ratio"] == 0.3
        assert d["check_repetition"] is False
        assert d["noise_count"] == 0
        assert d["passed_count"] == 0

    def test_diagnose_after_operations(self) -> None:
        nf = NoiseFilter()
        nf.worth_remembering("ok", "got it")
        nf.worth_remembering("real?", "real answer here.")
        d = nf.diagnose()
        assert d["noise_count"] == 1
        assert d["passed_count"] == 1


# ── 11. Reset counts ────────────────────────────────────────────────────

class TestNoiseResetCounts:
    """reset_counts()。"""

    def test_reset_zeroes_counters(self) -> None:
        nf = NoiseFilter()
        nf.worth_remembering("ok", "got it")
        nf.worth_remembering("real?", "real answer.")
        assert nf.diagnose()["noise_count"] == 1
        assert nf.diagnose()["passed_count"] == 1

        nf.reset_counts()
        assert nf.diagnose()["noise_count"] == 0
        assert nf.diagnose()["passed_count"] == 0


# ── 12. One-sided noise ─────────────────────────────────────────────────

class TestNoiseOneSidedNoise:
    """仅一侧噪声不拦截（需要两侧都是噪声才拦截）。"""

    def test_user_noise_but_real_reply_passes(self) -> None:
        nf = NoiseFilter(min_chars=0)
        # User says "ok" but AI gives real answer → should pass
        ok = nf.worth_remembering(
            "ok",
            "The capital of France is Paris, a city known for its culture.",
        )
        assert ok is True

    def test_real_question_but_noise_reply_passes(self) -> None:
        nf = NoiseFilter(min_chars=0)
        # User asks real question, AI says "sure" → should pass
        ok = nf.worth_remembering(
            "What is the population of Tokyo?",
            "sure",
        )
        assert ok is True

    def test_real_question_and_real_reply_passes(self) -> None:
        nf = NoiseFilter()
        ok = nf.worth_remembering(
            "Explain quantum computing.",
            "Quantum computing uses qubits instead of bits...",
        )
        assert ok is True
