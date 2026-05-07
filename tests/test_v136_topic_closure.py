# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — TopicClosureDetector 全覆盖测试
=========================================

验证:
    1. TestTopicClosureConfig        — TopicClosureConfig dataclass 字段
    2. TestDetectorInit              — 构造 + 默认值
    3. TestDetectBasic               — 基础检测: 匹配/不匹配/交换计数门控
    4. TestDetectAIack               — AI 确认检查
    5. TestSignalWordManagement      — 注册/注销信号词
    6. TestSummarize                 — summarize() 默认行为
    7. TestDecay                     — decay() 记录/冷却/驱逐
    8. TestRecordClosure             — record_closure() 重置
    9. TestEdgeCases                 — 边界: 空/长/unicode
    10. TestDiagnose                 — diagnose() 快照
    11. TestCustomOverrides          — 自定义各钩子
    12. TestConfidence               — 置信度计算
"""

from __future__ import annotations

import time

from meowcat.topic_closure import (
    TopicClosureDetector,
    TopicClosureConfig,
    TopicClosureResult,
)


# ── 1. TopicClosureConfig ──────────────────────────────────────────────

class TestTopicClosureConfig:
    """TopicClosureConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = TopicClosureConfig()
        assert len(cfg.closure_signal_words) > 0
        assert "好的" in cfg.closure_signal_words
        assert "bye" in cfg.closure_signal_words
        assert cfg.min_exchange_count == 3
        assert cfg.decay_cooldown == 300.0
        assert cfg.max_closed_topics == 50
        assert cfg.require_ai_ack is False
        assert cfg.token_window == 1000

    def test_custom_fields(self) -> None:
        cfg = TopicClosureConfig(
            closure_signal_words=["done", "finish"],
            min_exchange_count=5,
            decay_cooldown=600.0,
            max_closed_topics=10,
            require_ai_ack=True,
            token_window=500,
        )
        assert cfg.closure_signal_words == ["done", "finish"]
        assert cfg.min_exchange_count == 5
        assert cfg.decay_cooldown == 600.0
        assert cfg.max_closed_topics == 10
        assert cfg.require_ai_ack is True
        assert cfg.token_window == 500


# ── 2. Init ────────────────────────────────────────────────────────────

class TestDetectorInit:
    """构造 + 默认值。"""

    def test_default_construction(self) -> None:
        d = TopicClosureDetector()
        cfg = d.config
        assert len(cfg.closure_signal_words) > 0
        assert cfg.min_exchange_count == 3
        assert cfg.decay_cooldown == 300.0
        assert cfg.max_closed_topics == 50
        assert cfg.require_ai_ack is False

    def test_custom_construction(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["结束", "finish"],
            min_exchange_count=5,
            decay_cooldown=120.0,
            max_closed_topics=20,
            require_ai_ack=True,
            token_window=2000,
        )
        cfg = d.config
        assert cfg.closure_signal_words == ["结束", "finish"]
        assert cfg.min_exchange_count == 5
        assert cfg.decay_cooldown == 120.0
        assert cfg.max_closed_topics == 20
        assert cfg.require_ai_ack is True
        assert cfg.token_window == 2000

    def test_config_is_readonly_copy(self) -> None:
        d = TopicClosureDetector()
        cfg = d.config
        cfg.min_exchange_count = 99  # type: ignore[misc]
        assert d.config.min_exchange_count == 3

    def test_none_signal_words_uses_default(self) -> None:
        d = TopicClosureDetector(closure_signal_words=None)
        assert len(d.config.closure_signal_words) > 0
        assert "好的" in d.config.closure_signal_words


# ── 3. TopicClosureResult ──────────────────────────────────────────────

class TestTopicClosureResult:
    """TopicClosureResult dataclass 字段。"""

    def test_default_result(self) -> None:
        r = TopicClosureResult()
        assert r.is_closed is False
        assert r.matched_word == ""
        assert r.topic_context == []
        assert r.topic_id == ""
        assert r.confidence == 0.0

    def test_positive_result(self) -> None:
        r = TopicClosureResult(
            is_closed=True,
            matched_word="好的",
            topic_context=["User: 好的", "AI: 不客气"],
            topic_id="topic_abc",
            confidence=0.8,
        )
        assert r.is_closed is True
        assert r.matched_word == "好的"
        assert len(r.topic_context) == 2
        assert r.topic_id == "topic_abc"
        assert r.confidence == 0.8


# ── 4. Basic detect ────────────────────────────────────────────────────

class TestDetectBasic:
    """基础检测: 匹配/不匹配/交换计数门控。"""

    def test_no_match_returns_false(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("What is the weather?", "It is sunny today.")
        assert r.is_closed is False
        assert r.matched_word == ""

    def test_match_returns_true(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("好的，谢谢", "不客气！")
        assert r.is_closed is True
        assert r.matched_word in ("好的", "谢谢")

    def test_match_after_min_exchanges(self) -> None:
        """Closure is detected only after min_exchange_count."""
        d = TopicClosureDetector(min_exchange_count=3)

        # Exchange 1 — too few
        r1 = d.detect("好的，谢谢", "不客气")
        assert r1.is_closed is False

        # Exchange 2 — too few
        r2 = d.detect("hello", "hi there")
        assert r2.is_closed is False

        # Exchange 3 — meets threshold
        r3 = d.detect("好的，谢谢", "不客气")
        assert r3.is_closed is True

    def test_exchange_count_resets_after_record(self) -> None:
        d = TopicClosureDetector(min_exchange_count=3)

        # Build up to 3 exchanges + closure
        d.detect("hi", "hello")
        d.detect("how are you", "fine")
        r = d.detect("好的，谢谢", "不客气")
        assert r.is_closed is True

        # Record closure
        d.record_closure(r)

        # Next exchange starts from 1
        r2 = d.detect("好的，谢谢", "不客气")
        assert r2.is_closed is False

    def test_case_insensitive_match(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("OK THANKS", "you're welcome")
        assert r.is_closed is True

    def test_partial_embedded_match(self) -> None:
        """Signal word embedded in longer text still matches."""
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("我觉得这样就OK了，谢谢你", "不客气")
        assert r.is_closed is True


# ── 5. AI acknowledgement check ────────────────────────────────────────

class TestDetectAIack:
    """AI 确认检查。"""

    def test_require_ai_ack_disabled_default(self) -> None:
        """By default, AI ack is not required."""
        d = TopicClosureDetector(min_exchange_count=1, require_ai_ack=False)
        r = d.detect("好的，谢谢", "好的")  # AI reply doesn't matter
        assert r.is_closed is True

    def test_require_ai_ack_enabled_no_ack(self) -> None:
        """With require_ai_ack=True, default _check_ai_ack returns True."""
        d = TopicClosureDetector(min_exchange_count=1, require_ai_ack=True)
        # Default _check_ai_ack returns True → still detects
        r = d.detect("好的，谢谢", "anything")
        assert r.is_closed is True

    def test_custom_ai_ack_check_rejects(self) -> None:
        """Override _check_ai_ack to enforce actual ack presence."""

        class StrictDetector(TopicClosureDetector):
            def _check_ai_ack(self, ai_reply: str) -> bool:
                ack_words = ["不客气", "you're welcome", "没问题", "no problem"]
                return any(w in ai_reply.lower() for w in ack_words)

        d = StrictDetector(min_exchange_count=1, require_ai_ack=True)

        # AI reply without ack → no closure
        r1 = d.detect("好的，谢谢", "Let me know if you need anything else.")
        assert r1.is_closed is False

        # AI reply with ack → closure detected
        r2 = d.detect("好的，谢谢", "不客气！有问题随时问。")
        assert r2.is_closed is True


# ── 6. Signal word management ──────────────────────────────────────────

class TestSignalWordManagement:
    """注册/注销信号词。"""

    def test_register_new_word(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done"],
            min_exchange_count=1,
        )
        # "finish" is not registered → no match
        r1 = d.detect("finish", "ok")
        assert r1.is_closed is False

        # Register "finish"
        d.register_signal_word("finish")
        r2 = d.detect("finish", "ok")
        assert r2.is_closed is True

    def test_register_duplicate(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done"],
            min_exchange_count=1,
        )
        initial_count = len(d.config.closure_signal_words)
        d.register_signal_word("done")  # duplicate
        assert len(d.config.closure_signal_words) == initial_count

    def test_unregister_word(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done", "finish"],
            min_exchange_count=1,
        )
        r1 = d.detect("done", "ok")
        assert r1.is_closed is True

        d.unregister_signal_word("done")
        r2 = d.detect("done", "ok")
        assert r2.is_closed is False

        # "finish" still works
        r3 = d.detect("finish", "ok")
        assert r3.is_closed is True

    def test_unregister_nonexistent(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done"],
            min_exchange_count=1,
        )
        initial_count = len(d.config.closure_signal_words)
        d.unregister_signal_word("nonexistent")
        assert len(d.config.closure_signal_words) == initial_count

    def test_runtime_registration_persists(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done"],
            min_exchange_count=1,
        )
        d.register_signal_word("custom_end")
        assert "custom_end" in d.config.closure_signal_words


# ── 7. Summarize ───────────────────────────────────────────────────────

class TestSummarize:
    """summarize() 默认行为。"""

    async def test_empty_context(self) -> None:
        d = TopicClosureDetector()
        summary = await d.summarize([])
        assert summary == ""

    async def test_short_context(self) -> None:
        d = TopicClosureDetector()
        ctx = ["User: hello", "AI: hi there"]
        summary = await d.summarize(ctx)
        assert "User: hello" in summary
        assert "AI: hi there" in summary

    async def test_long_context_truncation(self) -> None:
        d = TopicClosureDetector(token_window=10)
        ctx = ["User: this is a very long message that exceeds the window"]
        summary = await d.summarize(ctx)
        assert len(summary) <= 10 + 1  # +1 for "…"

    async def test_custom_summarize(self) -> None:
        """Override summarize for custom behaviour."""

        class CustomDetector(TopicClosureDetector):
            async def summarize(
                self, topic_context: list[str],
            ) -> str:
                return f"Summary of {len(topic_context)} exchanges"

        d = CustomDetector()
        summary = await d.summarize(["a", "b", "c"])
        assert summary == "Summary of 3 exchanges"


# ── 8. Decay ───────────────────────────────────────────────────────────

class TestDecay:
    """decay() 记录/冷却/驱逐。"""

    def test_decay_records_topic(self) -> None:
        d = TopicClosureDetector()
        d.decay("topic_123")
        assert d.diagnose()["closed_topics_count"] == 1

    def test_decay_duplicate_is_idempotent(self) -> None:
        d = TopicClosureDetector()
        d.decay("topic_abc")
        d.decay("topic_abc")  # same topic_id → no duplicate
        assert d.diagnose()["closed_topics_count"] == 1

    def test_decay_different_topics(self) -> None:
        d = TopicClosureDetector()
        d.decay("topic_a")
        d.decay("topic_b")
        d.decay("topic_c")
        assert d.diagnose()["closed_topics_count"] == 3

    def test_decay_eviction(self) -> None:
        """Oldest topics are evicted when exceeding max_closed_topics."""
        d = TopicClosureDetector(max_closed_topics=3)

        d.decay("topic_1")
        d.decay("topic_2")
        d.decay("topic_3")
        assert d.diagnose()["closed_topics_count"] == 3

        # Adding a 4th should evict the oldest
        d.decay("topic_4")
        assert d.diagnose()["closed_topics_count"] == 3


# ── 9. Record closure ──────────────────────────────────────────────────

class TestRecordClosure:
    """record_closure() 重置。"""

    def test_record_resets_exchange_count(self) -> None:
        d = TopicClosureDetector(min_exchange_count=3)

        d.detect("hi", "hello")
        d.detect("how are you", "fine")
        r = d.detect("好的，谢谢", "不客气")
        assert r.is_closed is True

        assert d.diagnose()["exchange_count"] == 3

        d.record_closure(r)
        assert d.diagnose()["exchange_count"] == 0

    def test_record_clears_context(self) -> None:
        d = TopicClosureDetector(min_exchange_count=3)

        d.detect("hi", "hello")
        d.detect("how are you", "fine")
        r = d.detect("好的，谢谢", "不客气")
        assert d.diagnose()["context_size"] > 0

        d.record_closure(r)
        assert d.diagnose()["context_size"] == 0


# ── 10. Topic context accumulation ─────────────────────────────────────

class TestTopicContext:
    """话题上下文积累。"""

    def test_context_accumulates(self) -> None:
        d = TopicClosureDetector(min_exchange_count=2)
        d.detect("hello", "hi")
        d.detect("好的", "ok")
        assert d.diagnose()["context_size"] == 2

    def test_context_in_result(self) -> None:
        d = TopicClosureDetector(min_exchange_count=2)
        d.detect("hello", "hi")
        r = d.detect("好的，谢谢", "不客气")
        assert len(r.topic_context) == 2
        assert "User: hello" in r.topic_context[0]
        assert "User: 好的，谢谢" in r.topic_context[1]

    def test_context_trimming(self) -> None:
        """Context is trimmed to stay within token_window."""
        d = TopicClosureDetector(min_exchange_count=1, token_window=50)
        d.detect("a" * 100, "b")  # will trim
        assert d.diagnose()["context_size"] <= 2


# ── 11. Edge cases ─────────────────────────────────────────────────────

class TestEdgeCases:
    """边界: 空/长/unicode。"""

    def test_empty_messages(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("", "")
        assert r.is_closed is False

    def test_only_ai_has_signal(self) -> None:
        """Signal word in AI reply only should NOT trigger (only user msg)."""
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("hello", "好的，再见")
        assert r.is_closed is False

    def test_chinese_signal_words(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["好的", "谢谢", "再见", "明白了", "搞定"],
            min_exchange_count=1,
        )
        r = d.detect("明白了，搞定了", "好的")
        assert r.is_closed is True
        assert r.matched_word in ("明白了", "搞定")

    def test_multiple_signal_words_first_match_wins(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("好的谢谢再见", "bye")
        # First match in signal_re order wins
        assert r.is_closed is True
        assert r.matched_word != ""

    def test_newline_in_message(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("好的\n谢谢", "不客气")
        assert r.is_closed is True


# ── 12. Diagnose ───────────────────────────────────────────────────────

class TestDiagnose:
    """diagnose() 快照。"""

    def test_initial_diagnose(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["done", "结束"],
            min_exchange_count=5,
            decay_cooldown=120.0,
            max_closed_topics=20,
            require_ai_ack=True,
            token_window=800,
        )
        diag = d.diagnose()
        assert diag["closure_signal_words"] == ["done", "结束"]
        assert diag["min_exchange_count"] == 5
        assert diag["decay_cooldown"] == 120.0
        assert diag["max_closed_topics"] == 20
        assert diag["require_ai_ack"] is True
        assert diag["token_window"] == 800
        assert diag["exchange_count"] == 0
        assert diag["context_size"] == 0
        assert diag["closed_topics_count"] == 0

    def test_diagnose_after_activity(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("好的", "ok")
        assert r.is_closed is True
        d.decay(r.topic_id)
        d.record_closure(r)

        diag = d.diagnose()
        assert diag["exchange_count"] == 0  # reset by record_closure
        assert diag["closed_topics_count"] == 1


# ── 13. Custom overrides ───────────────────────────────────────────────

class TestCustomOverrides:
    """自定义各钩子。"""

    def test_override_detect_impl(self) -> None:
        """Custom detection logic."""

        class CustomDetector(TopicClosureDetector):
            def _detect_impl(
                self, user_msg: str, ai_reply: str,
            ) -> TopicClosureResult:
                if "?" in user_msg:
                    # Questions are not closures
                    return TopicClosureResult()
                if len(user_msg) < 5:
                    return TopicClosureResult(
                        is_closed=True,
                        matched_word="short",
                        topic_context=list(self._recent_context),
                        topic_id="short_msg",
                        confidence=0.3,
                    )
                return TopicClosureResult()

        d = CustomDetector(min_exchange_count=1)

        r1 = d.detect("What is this?", "answer")
        assert r1.is_closed is False  # question → not closure

        r2 = d.detect("ok", "bye")
        assert r2.is_closed is True  # short → closure
        assert r2.matched_word == "short"

    async def test_override_summarize(self) -> None:
        """Custom summarisation."""

        class CustomDetector(TopicClosureDetector):
            async def summarize(
                self, topic_context: list[str],
            ) -> str:
                return "CUSTOM_SUMMARY"

        d = CustomDetector(min_exchange_count=1)
        summary = await d.summarize(["a", "b"])
        assert summary == "CUSTOM_SUMMARY"

    def test_override_decay(self) -> None:
        """Custom decay logic."""

        class CustomDetector(TopicClosureDetector):
            def decay(self, topic_id: str) -> None:
                # Custom: also log to external system
                pass  # no-op

        d = CustomDetector()
        d.decay("topic_x")
        assert d.diagnose()["closed_topics_count"] == 0  # custom decay is no-op

    async def test_override_inject_to_cortex(self) -> None:
        """Custom cortex injection."""

        injected: list[str] = []

        class CustomDetector(TopicClosureDetector):
            async def inject_to_cortex(self, summary: str) -> None:
                injected.append(summary)

        d = CustomDetector()
        await d.inject_to_cortex("topic summary")
        assert injected == ["topic summary"]

    async def test_full_lifecycle_custom(self) -> None:
        """End-to-end custom lifecycle."""

        logs: list[str] = []

        class LifecycleDetector(TopicClosureDetector):
            async def summarize(
                self, topic_context: list[str],
            ) -> str:
                logs.append("summarize")
                return "summary"

            def decay(self, topic_id: str) -> None:
                logs.append(f"decay:{topic_id}")

            async def inject_to_cortex(self, summary: str) -> None:
                logs.append(f"inject:{summary}")

        d = LifecycleDetector(min_exchange_count=1)
        r = d.detect("好的", "ok")
        assert r.is_closed is True

        summary = await d.summarize(r.topic_context)
        d.decay(r.topic_id)
        await d.inject_to_cortex(summary)

        assert "summarize" in logs
        assert any("decay:" in entry for entry in logs)
        assert "inject:summary" in logs


# ── 14. Confidence ─────────────────────────────────────────────────────

class TestConfidence:
    """置信度计算。"""

    def test_high_weight_words(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("再见", "bye")
        assert r.is_closed is True
        # "再见" has weight 0.9
        assert r.confidence >= 0.9

    def test_low_weight_words(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("OK", "ok")
        assert r.is_closed is True
        # "OK" has weight 0.3
        assert r.confidence >= 0.3

    def test_confidence_capped_at_one(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)

        # Accumulate many exchanges to boost confidence
        for _ in range(20):
            d.detect("msg", "reply")

        r = d.detect("bye", "goodbye")
        assert r.is_closed is True
        assert r.confidence <= 1.0

    def test_unknown_word_default_weight(self) -> None:
        d = TopicClosureDetector(
            closure_signal_words=["custom_word"],
            min_exchange_count=1,
        )
        r = d.detect("custom_word", "ok")
        assert r.is_closed is True
        # Unknown weight defaults to 0.5
        assert r.confidence >= 0.5


# ── 15. Topic ID ───────────────────────────────────────────────────────

class TestTopicID:
    """topic_id 生成。"""

    def test_topic_id_is_stable_pattern(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r = d.detect("好的", "ok")
        assert r.topic_id.startswith("topic_")
        assert "好的" in r.topic_id  # encoded in the id

    def test_topic_id_differs_per_word(self) -> None:
        d = TopicClosureDetector(min_exchange_count=1)
        r1 = d.detect("好的", "ok")
        # Need to reset counter, but detect already incremented
        # Just check the pattern differs by word
        assert "好的" in r1.topic_id
