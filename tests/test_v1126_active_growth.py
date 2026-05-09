# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.1.26 Active Growth — curiosity, tool evolution, reflex evolution tests."""

from __future__ import annotations

import pytest

from meowcat.biology.active_growth import (
    BlindSpotDetector,
    HotPathObserver,
    ToolFailureLearner,
)
from meowcat.defaults.organs import NoopPaws, NoopWhiskers
from meowcat.reflex import ReflexRegistry

# ════════════════════════════════════════════════════════════════════
# BlindSpotDetector — curiosity-driven knowledge gap detection
# ════════════════════════════════════════════════════════════════════

class TestBlindSpotDetector:
    """Curiosity: detect knowledge blind spots from queries."""

    @pytest.mark.anyio
    async def test_detect_empty_queries(self):
        bsd = BlindSpotDetector()
        assert await bsd.detect([]) == []

    @pytest.mark.anyio
    async def test_detect_all_novel(self):
        bsd = BlindSpotDetector(novelty_threshold=0.3)
        queries = [
            "What is Kubernetes and how does it work?",
            "Can you explain Redis caching?",
        ]
        spots = await bsd.detect(queries, known_topics=["Python"])
        # Kubernetes and Redis should be detected as novel
        assert len(spots) >= 1

    @pytest.mark.anyio
    async def test_detect_nothing_when_known(self):
        bsd = BlindSpotDetector()
        queries = ["Tell me about Python"]
        spots = await bsd.detect(queries, known_topics=["Python", "Redis"])
        # Python is known, no blind spot
        assert all(s["topic"] != "Python" for s in spots)

    @pytest.mark.anyio
    async def test_detect_camelcase_terms(self):
        bsd = BlindSpotDetector(novelty_threshold=0.3)
        queries = ["How do I use ReactQuery with TypeScript?"]
        spots = await bsd.detect(queries, known_topics=[])
        topics = {s["topic"] for s in spots}
        assert "ReactQuery" in topics or "TypeScript" in topics

    @pytest.mark.anyio
    async def test_detect_snake_case_terms(self):
        bsd = BlindSpotDetector(novelty_threshold=0.3)
        queries = ["The fast_api endpoint returns 404"]
        spots = await bsd.detect(queries, known_topics=[])
        topics = {s["topic"] for s in spots}
        assert "fast_api" in topics

    @pytest.mark.anyio
    async def test_detect_acronyms(self):
        bsd = BlindSpotDetector(novelty_threshold=0.3)
        queries = ["How to set up CI/CD with AWS ECS?"]
        spots = await bsd.detect(queries, known_topics=[])
        topics = {s["topic"] for s in spots}
        assert "AWS" in topics

    @pytest.mark.anyio
    async def test_novelty_threshold_filters(self):
        bsd = BlindSpotDetector(novelty_threshold=1.0)  # impossibly high
        queries = ["What is Docker?", "What is Docker?"]
        spots = await bsd.detect(queries, known_topics=[])
        # novelty = 2/2 = 1.0, but threshold is 1.0 strict — should pass
        # Actually with 2 queries, novelty=1.0, threshold=1.0, should be >=
        assert len(spots) >= 1

        bsd2 = BlindSpotDetector(novelty_threshold=1.1)  # above max
        spots2 = await bsd2.detect(queries, known_topics=[])
        assert spots2 == []

    @pytest.mark.anyio
    async def test_evidence_included(self):
        bsd = BlindSpotDetector()
        queries = ["Tell me about Docker containers"]
        spots = await bsd.detect(queries, known_topics=[])
        for s in spots:
            assert "evidence" in s
            assert "novelty" in s
            assert "count" in s

    @pytest.mark.anyio
    async def test_sorted_by_novelty(self):
        bsd = BlindSpotDetector(novelty_threshold=0.1)
        queries = [
            "Docker Docker Docker",
            "Kubernetes",
        ]
        spots = await bsd.detect(queries, known_topics=[])
        if len(spots) >= 2:
            assert spots[0]["novelty"] >= spots[1]["novelty"]

    @pytest.mark.anyio
    async def test_plug_detector(self):
        bsd = BlindSpotDetector()

        def custom_detector(queries, known):
            return [{"topic": "custom", "novelty": 0.99, "count": 1, "evidence": []}]

        bsd.plug("detector", custom_detector)
        spots = await bsd.detect(["anything"], [])
        assert len(spots) == 1
        assert spots[0]["topic"] == "custom"

    @pytest.mark.anyio
    async def test_unplug_detector(self):
        bsd = BlindSpotDetector(novelty_threshold=0.3)

        def fake(queries, known):
            return []

        bsd.plug("detector", fake)
        assert await bsd.detect(["Docker Docker"], []) == []

        bsd.unplug("detector", fake)
        spots = await bsd.detect(["Docker Docker"], [])
        assert len(spots) >= 1

    def test_pluggable_inheritance(self):
        from meowcat.pluggable import Pluggable
        bsd = BlindSpotDetector()
        assert isinstance(bsd, Pluggable)


# ════════════════════════════════════════════════════════════════════
# ToolFailureLearner — tool evolution from failures
# ════════════════════════════════════════════════════════════════════

class TestToolFailureLearner:
    """Tool evolution: learn from execution failures."""

    @pytest.mark.anyio
    async def test_record_and_count(self):
        tfl = ToolFailureLearner()
        await tfl.record("read_file", {"path": "/x"}, "FileNotFound", 120)
        assert tfl.fail_count() == 1
        assert tfl.fail_count("read_file") == 1
        assert tfl.fail_count("write_file") == 0

    @pytest.mark.anyio
    async def test_hotspots_min_failures(self):
        tfl = ToolFailureLearner()
        await tfl.record("tool_a", {}, "err", 0)
        await tfl.record("tool_b", {}, "err", 0)
        await tfl.record("tool_b", {}, "err", 0)
        await tfl.record("tool_b", {}, "err", 0)

        # min_failures=2 → tool_b only
        hotspots = tfl.hotspots(min_failures=2)
        assert len(hotspots) == 1
        assert hotspots[0][0] == "tool_b"
        assert hotspots[0][1] == 3

    @pytest.mark.anyio
    async def test_hotspots_sorted_by_count(self):
        tfl = ToolFailureLearner()
        for _ in range(5):
            await tfl.record("tool_a", {}, "e", 0)
        for _ in range(3):
            await tfl.record("tool_b", {}, "e", 0)

        hotspots = tfl.hotspots(min_failures=1)
        assert hotspots[0][0] == "tool_a"
        assert hotspots[0][1] == 5

    @pytest.mark.anyio
    async def test_record_stores_error_info(self):
        tfl = ToolFailureLearner()
        await tfl.record("tool_x", {"key": "val"}, "TimeoutError", 5000)
        hotspots = tfl.hotspots(min_failures=1)
        assert len(hotspots) == 1
        _, _, info = hotspots[0]
        assert info["tool"] == "tool_x"
        assert info["error"] == "TimeoutError"
        assert info["elapsed_ms"] == 5000

    @pytest.mark.anyio
    async def test_fifo_eviction(self):
        tfl = ToolFailureLearner(max_records=3)
        for i in range(5):
            await tfl.record(f"tool_{i}", {}, "err", 0)
        assert tfl.fail_count() == 3
        # oldest two evicted: tool_0, tool_1 → latest three kept
        tools = {r["tool"] for r in tfl._records}
        assert tools == {"tool_2", "tool_3", "tool_4"}

    @pytest.mark.anyio
    async def test_reset(self):
        tfl = ToolFailureLearner()
        await tfl.record("t", {}, "e", 0)
        await tfl.record("t", {}, "e", 0)
        assert tfl.fail_count() == 2
        tfl.reset()
        assert tfl.fail_count() == 0

    @pytest.mark.anyio
    async def test_plug_on_failure(self):
        tfl = ToolFailureLearner()
        side_effect: list[dict] = []

        def hook(tool, params, error, elapsed):
            side_effect.append({"tool": tool, "error": error})

        tfl.plug("on_failure", hook)
        await tfl.record("tool_a", {}, "ERR", 10)
        assert len(side_effect) == 1
        assert side_effect[0]["tool"] == "tool_a"

    def test_pluggable_inheritance(self):
        from meowcat.pluggable import Pluggable
        tfl = ToolFailureLearner()
        assert isinstance(tfl, Pluggable)


# ════════════════════════════════════════════════════════════════════
# HotPathObserver — reflex arc evolution
# ════════════════════════════════════════════════════════════════════

class TestHotPathObserver:
    """Reflex evolution: promote frequently used paths."""

    @pytest.mark.anyio
    async def test_detect_empty(self):
        hpo = HotPathObserver()
        assert await hpo.detect() == []

    @pytest.mark.anyio
    async def test_detect_below_threshold(self):
        hpo = HotPathObserver(min_triggers=5)
        hpo.record("text_dialogue")
        hpo.record("text_dialogue")
        hpo.record("text_dialogue")
        hpo.record("text_dialogue")  # 4 < 5
        assert await hpo.detect() == []

    @pytest.mark.anyio
    async def test_detect_above_threshold(self):
        hpo = HotPathObserver(min_triggers=3)
        for _ in range(3):
            hpo.record("text_dialogue")
        assert await hpo.detect() == ["text_dialogue"]

    @pytest.mark.anyio
    async def test_detect_custom_threshold(self):
        hpo = HotPathObserver(min_triggers=5)
        for _ in range(3):
            hpo.record("danger")
        # default min_triggers=5 → empty
        assert await hpo.detect() == []
        # override to 2 → detected
        assert await hpo.detect(min_triggers=2) == ["danger"]

    @pytest.mark.anyio
    async def test_detect_sorted_by_count(self):
        hpo = HotPathObserver(min_triggers=1)
        for _ in range(5):
            hpo.record("text_dialogue")
        for _ in range(3):
            hpo.record("danger")
        result = await hpo.detect()
        assert result[0] == "text_dialogue"
        assert result[1] == "danger"

    def test_stats(self):
        hpo = HotPathObserver()
        hpo.record("a")
        hpo.record("a")
        hpo.record("b")
        stats = hpo.stats()
        assert stats == {"a": 2, "b": 1}

    def test_total(self):
        hpo = HotPathObserver()
        hpo.record("x")
        hpo.record("y")
        hpo.record("z")
        assert hpo.total == 3

    @pytest.mark.anyio
    async def test_reset(self):
        hpo = HotPathObserver()
        hpo.record("x")
        hpo.record("x")
        hpo.record("x")
        assert hpo.total == 3
        hpo.reset()
        assert hpo.total == 0
        assert await hpo.detect() == []
        assert hpo.stats() == {}

    @pytest.mark.anyio
    async def test_plug_observer(self):
        hpo = HotPathObserver()
        for _ in range(5):
            hpo.record("x")

        def custom_observer(counts, total):
            return ["custom_path"]

        hpo.plug("observer", custom_observer)
        assert await hpo.detect() == ["custom_path"]

    def test_pluggable_inheritance(self):
        from meowcat.pluggable import Pluggable
        hpo = HotPathObserver()
        assert isinstance(hpo, Pluggable)


# ════════════════════════════════════════════════════════════════════
# ReflexRegistry.observe_hot_paths
# ════════════════════════════════════════════════════════════════════

class TestReflexRegistryHotPaths:
    """ReflexRegistry integration: trigger tracking + hot path observation."""

    def test_empty_registry(self):
        rr = ReflexRegistry()
        assert rr.observe_hot_paths() == []
        assert rr.trigger_stats() == {}

    def test_record_and_observe(self):
        rr = ReflexRegistry()
        rr._record_trigger("text_dialogue")
        rr._record_trigger("text_dialogue")
        rr._record_trigger("text_dialogue")
        rr._record_trigger("text_dialogue")
        rr._record_trigger("text_dialogue")
        rr._record_trigger("danger")

        hot = rr.observe_hot_paths(min_triggers=3)
        assert len(hot) == 1
        assert hot[0] == ("text_dialogue", 5)

    def test_trigger_stats(self):
        rr = ReflexRegistry()
        rr._record_trigger("a")
        rr._record_trigger("b")
        rr._record_trigger("a")
        assert rr.trigger_stats() == {"a": 2, "b": 1}

    def test_observe_hot_paths_empty_below_threshold(self):
        rr = ReflexRegistry()
        rr._record_trigger("x")
        rr._record_trigger("x")
        assert rr.observe_hot_paths(min_triggers=5) == []


# ════════════════════════════════════════════════════════════════════
# NoopWhiskers detect_blind_spot
# ════════════════════════════════════════════════════════════════════

class TestNoopWhiskersBlindSpot:
    """NoopWhiskers detect_blind_spot — default and pluggable."""

    @pytest.mark.anyio
    async def test_default_returns_empty(self):
        nw = NoopWhiskers()
        assert await nw.detect_blind_spot(["What is Redis?"]) == []

    @pytest.mark.anyio
    async def test_plug_returns_list(self):
        nw = NoopWhiskers()

        def my_detector(queries, known):
            return [{"topic": "Redis", "novelty": 0.8}]

        nw.plug("detect_blind_spot", my_detector)
        spots = await nw.detect_blind_spot(["What is Redis?"], ["Python"])
        assert len(spots) == 1
        assert spots[0]["topic"] == "Redis"


# ════════════════════════════════════════════════════════════════════
# NoopPaws on_tool_failure
# ════════════════════════════════════════════════════════════════════

class TestNoopPawsToolFailure:
    """NoopPaws on_tool_failure — default and pluggable."""

    @pytest.mark.anyio
    async def test_default_returns_recorded_false(self):
        np = NoopPaws()
        result = await np.on_tool_failure("read_file", {}, "Error")
        assert result == {"recorded": False}

    @pytest.mark.anyio
    async def test_plug_returns_dict(self):
        np = NoopPaws()

        def my_handler(tool, params, error, elapsed):
            return {"recorded": True, "tool": tool}

        np.plug("on_tool_failure", my_handler)
        result = await np.on_tool_failure(
            "read_file", {"path": "/x"}, "NotFound", 100)
        assert result["recorded"] is True
        assert result["tool"] == "read_file"


# ════════════════════════════════════════════════════════════════════
# Diagnosis (diagnose method)
# ════════════════════════════════════════════════════════════════════

class TestDiagnose:
    """All three components support diagnose()."""

    def test_blind_spot_diagnose(self):
        bsd = BlindSpotDetector()
        info = bsd.diagnose()
        assert "plugs" in info

    @pytest.mark.anyio
    async def test_tool_failure_diagnose(self):
        tfl = ToolFailureLearner()
        await tfl.record("t", {}, "e", 0)
        info = tfl.diagnose()
        assert info["total_failures"] == 1
        assert "hotspots" in info

    @pytest.mark.anyio
    async def test_hot_path_diagnose(self):
        hpo = HotPathObserver()
        hpo.record("x")
        info = await hpo.diagnose()
        assert info["total_triggers"] == 1
        assert "hot_paths" in info
