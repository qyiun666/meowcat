# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.1.23 ScribblePad — cat's private scratchpad for fragment accumulation."""

from __future__ import annotations

import pytest

from meowcat.biology.scribble_pad import (
    DefaultScribbleFilter,
    DefaultScribbleLogger,
    ScribblePad,
)


# -- 1. Core API — scribble / peek / drain / count / is_full --------------

class TestScribblePadCore:
    """ScribblePad basic read/write/drain operations."""

    def test_scribble_and_count(self):
        """scribble appends entries, count reflects it."""
        pad = ScribblePad(capacity=10)
        assert pad.count() == 0
        pad.scribble("hello")
        pad.scribble({"key": "value"})
        assert pad.count() == 2

    def test_peek(self):
        """peek returns recent entries without removing."""
        pad = ScribblePad()
        pad.scribble("a")
        pad.scribble("b")
        pad.scribble("c")
        assert pad.peek(2) == ["b", "c"]
        assert pad.count() == 3  # still there

    def test_peek_all(self):
        """peek(-1) returns all."""
        pad = ScribblePad()
        pad.scribble(1)
        pad.scribble(2)
        assert pad.peek(-1) == [1, 2]

    def test_drain(self):
        """drain returns all entries and clears the pad."""
        pad = ScribblePad()
        pad.scribble("x")
        pad.scribble("y")
        result = pad.drain()
        assert result == ["x", "y"]
        assert pad.count() == 0

    def test_is_full(self):
        """is_full returns True when count >= capacity."""
        pad = ScribblePad(capacity=3)
        assert not pad.is_full()
        pad.scribble(1)
        pad.scribble(2)
        assert not pad.is_full()
        pad.scribble(3)
        assert pad.is_full()

    def test_capacity_property(self):
        """capacity property returns max."""
        pad = ScribblePad(capacity=42)
        assert pad.capacity == 42

    def test_capacity_invalid(self):
        """capacity < 1 raises ValueError."""
        with pytest.raises(ValueError, match="capacity"):
            ScribblePad(capacity=0)


# -- 2. Plugin slots — on_scribble / on_drain / post_filter ---------------

class TestScribblePadPlug:
    """ScribblePad plug/unplug and plugin execution."""

    def test_on_scribble_plugin(self):
        """on_scribble fires on every write."""
        pad = ScribblePad()
        calls: list = []

        def log_it(payload):
            calls.append(payload)

        pad.plug("on_scribble", log_it)
        pad.scribble("first")
        pad.scribble("second")
        assert calls == ["first", "second"]

    def test_post_filter_veto(self):
        """post_filter returning False drops the payload."""
        pad = ScribblePad()

        def block_x(payload, _entries):
            if payload == "x":
                return False
            return None

        pad.plug("post_filter", block_x)
        pad.scribble("a")
        pad.scribble("x")
        pad.scribble("b")
        assert pad.peek(-1) == ["a", "b"]

    def test_on_drain_transform(self):
        """on_drain can transform entries before drain returns."""
        pad = ScribblePad()

        def add_tag(entries):
            return [f"tagged:{e}" for e in entries]

        pad.plug("on_drain", add_tag)
        pad.scribble("hello")
        pad.scribble("world")
        result = pad.drain()
        assert result == ["tagged:hello", "tagged:world"]

    def test_on_drain_last_wins(self):
        """Multiple on_drain plugins — last one wins."""
        pad = ScribblePad()

        def first(entries):
            return [f"1:{e}" for e in entries]

        def second(entries):
            return [f"2:{e}" for e in entries]

        pad.plug("on_drain", first)
        pad.plug("on_drain", second)
        pad.scribble("x")
        result = pad.drain()
        assert result == ["2:x"]

    def test_multiple_post_filters(self):
        """Multiple post_filters — first False stops the chain."""
        pad = ScribblePad()

        def block_a(payload, _entries):
            if payload == "a":
                return False
            return None

        # This filter should never see "a" because it's blocked upstream
        log2: list = []

        def log_b(payload, _entries):
            log2.append(payload)
            return None

        pad.plug("post_filter", block_a)
        pad.plug("post_filter", log_b)
        pad.scribble("a")
        pad.scribble("b")
        assert pad.peek(-1) == ["b"]
        assert log2 == ["b"]  # "a" was blocked before reaching log_b

    def test_unplug(self):
        """unplug removes a plugin."""
        pad = ScribblePad()
        calls: list = []

        def tracker(payload):
            calls.append(payload)

        pad.plug("on_scribble", tracker)
        pad.scribble("keep")
        pad.unplug("on_scribble", tracker)
        pad.scribble("drop")
        assert calls == ["keep"]


# -- 3. Prefabs — DefaultScribbleFilter / DefaultScribbleLogger -----------

class TestScribblePadPrefabs:
    """Default prefabs — filter and logger."""

    def test_default_filter_dedup(self):
        """DefaultScribbleFilter drops exact duplicates."""
        pad = ScribblePad()
        pad.plug("post_filter", DefaultScribbleFilter())
        pad.scribble("hello")
        pad.scribble("hello")  # duplicate
        pad.scribble("world")
        assert pad.peek(-1) == ["hello", "world"]

    def test_default_filter_allow_near_dupes(self):
        """DefaultScribbleFilter allows non-exact matches."""
        pad = ScribblePad()
        pad.plug("post_filter", DefaultScribbleFilter())
        pad.scribble({"a": 1})
        pad.scribble({"a": 2})  # different value → allowed
        assert pad.count() == 2

    def test_default_logger(self):
        """DefaultScribbleLogger logs without crashing."""
        pad = ScribblePad()
        pad.plug("on_scribble", DefaultScribbleLogger())
        # Should not raise
        pad.scribble("test log entry")
        pad.scribble({"complex": [1, 2, 3]})
        assert pad.count() == 2


# -- 4. Diagnose ---------------------------------------------------------

class TestScribblePadDiagnose:
    """diagnose returns snapshot."""

    def test_diagnose(self):
        pad = ScribblePad(capacity=50)
        pad.scribble("a")
        d = pad.diagnose()
        assert d["count"] == 1
        assert d["capacity"] == 50
        assert d["is_full"] is False
        assert isinstance(d["plugs"], dict)

    def test_diagnose_full(self):
        pad = ScribblePad(capacity=2)
        pad.scribble(1)
        pad.scribble(2)
        d = pad.diagnose()
        assert d["is_full"] is True


# -- 5. Integration — ScribblePad with Colony ----------------------------

class TestScribblePadIntegration:
    """ScribblePad usable standalone and within a cat context."""

    def test_standalone_usage(self):
        """ScribblePad works without colony — no external deps."""
        pad = ScribblePad(capacity=5)
        for i in range(3):
            pad.scribble(f"msg_{i}")
        assert pad.count() == 3
        drained = pad.drain()
        assert len(drained) == 3
        assert pad.count() == 0

    def test_pluggable_inheritance(self):
        """ScribblePad is a Pluggable."""
        from meowcat.pluggable import Pluggable
        pad = ScribblePad()
        assert isinstance(pad, Pluggable)
        assert pad.list_plugs() == {}
        pad.plug("on_scribble", lambda x: None)
        assert "on_scribble" in pad.list_plugs()

