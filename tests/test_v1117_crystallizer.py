# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.1.17 Crystallizer L1 — tool-usage frequency detector tests."""

from meowcat.plus.crystallizer import Crystallizer, DefaultDetector


class TestDefaultDetector:
    """DefaultDetector frequency heuristic."""

    def test_empty(self) -> None:
        d = DefaultDetector()
        assert d({}, 0, 0.6) == []

    def test_no_above_threshold(self) -> None:
        d = DefaultDetector()
        hits = {"a": 1, "b": 1, "c": 2}
        # max ratio = 2/4 = 0.5 < 0.6
        assert d(hits, 4, 0.6) == []

    def test_above_threshold(self) -> None:
        d = DefaultDetector()
        hits = {"a": 3, "b": 1}
        # a = 3/4 = 0.75 >= 0.6
        assert d(hits, 4, 0.6) == ["a"]

    def test_custom_threshold(self) -> None:
        d = DefaultDetector()
        hits = {"a": 1, "b": 1, "c": 1}
        # 1/3 = 0.33, all below 0.5
        assert d(hits, 3, 0.5) == []


class TestCrystallizer:
    """Crystallizer tool."""

    def test_record_and_hotspots(self) -> None:
        c = Crystallizer(min_samples=2)
        c.record("read_file")
        c.record("read_file")
        c.record("write_file")
        c.record("read_file")

        assert c.total == 4
        assert c.unique_tools == 2

        hotspots = c.hotspots()
        assert len(hotspots) == 1
        assert hotspots[0] == ("read_file", 3)

    def test_hotspots_custom_threshold(self) -> None:
        c = Crystallizer(min_samples=2)
        c.record("a")
        c.record("b")
        c.record("b")
        c.record("b")

        assert c.hotspots(threshold=3) == [("b", 3)]

    def test_detect_empty(self) -> None:
        c = Crystallizer()
        assert c.detect() == []

    def test_detect_crystallizes(self) -> None:
        c = Crystallizer(threshold=0.5, min_samples=2)
        c.record("read_file")
        c.record("read_file")  # 2/2 = 1.0 > 0.5
        c.record("write_file")

        result = c.detect()
        assert "read_file" in result

    def test_detect_below_threshold(self) -> None:
        c = Crystallizer(threshold=0.8, min_samples=2)
        c.record("a")
        c.record("b")
        c.record("c")
        # max ratio = 1/3 = 0.33 < 0.8
        assert c.detect() == []

    def test_reset(self) -> None:
        c = Crystallizer()
        c.record("a")
        c.record("a")
        c.reset()
        assert c.total == 0
        assert c.unique_tools == 0
        assert c.detect() == []

    def test_plug_detector(self) -> None:
        c = Crystallizer()
        c.record("x")
        c.record("x")
        c.record("y")

        # custom detector: always returns ["x"]
        c.plug("detector", lambda hits, total, thresh: ["x"])
        assert c.detect() == ["x"]

    def test_plug_threshold(self) -> None:
        c = Crystallizer(threshold=0.6)
        c.record("a")
        c.record("a")
        c.record("b")
        # a = 2/3 = 0.67 >= 0.6 → would detect
        # plug threshold 0.9 → not detect
        c.plug("threshold", 0.9)
        assert c.detect() == []
        assert c.threshold == 0.9

    def test_plug_threshold_callable(self) -> None:
        c = Crystallizer()
        c.record("a")
        c.record("a")
        c.record("b")
        c.record("b")
        # a: 2/4 = 0.5 < 1.0 → not detected
        c.plug("threshold", lambda: 1.0)
        assert c.detect() == []
        assert c.threshold == 1.0

    def test_unplug(self) -> None:
        c = Crystallizer()
        c.record("a")
        c.record("a")
        c.plug("detector", lambda hits, total, thresh: ["fake"])
        assert c.detect() == ["fake"]
        c.unplug("detector")
        # back to DefaultDetector: 2/2=1.0 >= 0.6
        assert c.detect() == ["a"]

    def test_default_threshold(self) -> None:
        c = Crystallizer()
        assert c.threshold == 0.6

    def test_hotspots_empty_when_no_records(self) -> None:
        c = Crystallizer()
        assert c.hotspots() == []

    def test_hotspots_sorts_descending(self) -> None:
        c = Crystallizer(min_samples=1)
        c.record("b")
        c.record("a")
        c.record("a")
        assert c.hotspots() == [("a", 2), ("b", 1)]

