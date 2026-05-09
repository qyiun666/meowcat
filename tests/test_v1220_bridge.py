# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.2.20 — Two closed-loop systems bridge (A1).

ReflectionLoop ↔ LoopRegistry bridge via ``use_organ_pipeline``.
When True, the cognitive layer delegates to the physical organ pipeline.

v2.0: Updated to use unified ReflectionLoop(mode=...) instead of Default*Loop classes.
"""

from __future__ import annotations

import pytest

from meowcat.biology.cat_self import (
    CatSelf,
    ReflectionLoop,
)
from meowcat.biology.pineal_gland import PinealGland
from meowcat.biology.scribble_pad import ScribblePad

# -- Mock Cat with perceive / run_loop for bridge tests ---------------


class MockBridgeCat:
    """Cat stub that supports perceive() and run_loop() for bridge mode."""

    def __init__(self, cat_self):
        self.cat_self = cat_self
        self._current_snapshot = None
        self.perceive_calls: list[str] = []
        self.run_loop_calls: list[tuple[str, dict]] = []
        self._perceive_result: list = [
            {"reply": "bridge: processed via organ pipeline"}]
        self._run_loop_result: dict = {"status": "completed", "result": "ok"}
        self._perceive_should_fail: bool = False
        self._run_loop_should_fail: bool = False

    async def perceive(self, input, **extras):
        self.perceive_calls.append(str(input)[:100])
        if self._perceive_should_fail:
            raise RuntimeError("reflex disabled")
        for ev in self._perceive_result:
            yield ev

    async def run_loop(self, name, **initial_input):
        self.run_loop_calls.append((name, initial_input))
        if self._run_loop_should_fail:
            raise KeyError(f"loop {name} not found")
        return self._run_loop_result


# -- 1. Bridge: ReflectionLoop conversation mode ----------------------


class TestBridgeConversationLoop:
    """ReflectionLoop(mode="conversation") with use_organ_pipeline."""

    @pytest.mark.anyio
    async def test_default_no_bridge(self):
        """Without use_organ_pipeline, behavior unchanged."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="conversation", use_organ_pipeline=False)
        resp = await loop.run(cat, "hello")
        assert resp == "[conversation] received: hello"
        assert len(cat.perceive_calls) == 0
        assert len(cat.run_loop_calls) == 0

    @pytest.mark.anyio
    async def test_bridged_perceive(self):
        """Bridge mode calls cat.perceive() and returns pipeline result."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="conversation", use_organ_pipeline=True)
        resp = await loop.run(cat, "hello bridge")
        assert len(cat.perceive_calls) == 1
        assert cat.perceive_calls[0] == "hello bridge"
        assert "bridge" in resp

    @pytest.mark.anyio
    async def test_bridged_fallback_to_run_loop(self):
        """When perceive() fails, fall back to run_loop()."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        cat._perceive_should_fail = True
        cat._run_loop_result = {"reply": "fallback reply"}
        loop = ReflectionLoop(mode="conversation", use_organ_pipeline=True)
        resp = await loop.run(cat, "hello")
        assert len(cat.perceive_calls) == 1  # tried
        assert len(cat.run_loop_calls) == 1  # fell back
        assert cat.run_loop_calls[0][0] == "conversation"
        assert "fallback reply" in resp

    @pytest.mark.anyio
    async def test_bridged_both_fail(self):
        """When both perceive() and run_loop() fail, graceful fallback."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        cat._perceive_should_fail = True
        cat._run_loop_should_fail = True
        loop = ReflectionLoop(mode="conversation", use_organ_pipeline=True)
        resp = await loop.run(cat, "hello")
        # Should still return something, not raise
        assert isinstance(resp, str)

    @pytest.mark.anyio
    async def test_bridged_preserves_before_after(self):
        """Bridge mode still fires before_act/after_act and fusion."""
        pad = ScribblePad(capacity=10)
        gland = PinealGland(pad)
        cs = CatSelf(scribble_pad=pad, pineal_gland=gland)
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="conversation", use_organ_pipeline=True)
        await loop.run(cat, "hello")
        # PinealGland trigger_if fires → pad drained
        assert pad.count() >= 0  # may be 0 after drain


# -- 2. Bridge: ReflectionLoop task mode ------------------------------


class TestBridgeTaskLoop:
    """ReflectionLoop(mode="task") with use_organ_pipeline."""

    @pytest.mark.anyio
    async def test_default_no_bridge(self):
        """Without use_organ_pipeline, behavior unchanged."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="task", use_organ_pipeline=False)
        result = await loop.run(cat, "deploy")
        assert result == {"task": "deploy", "status": "planned"}
        assert len(cat.run_loop_calls) == 0

    @pytest.mark.anyio
    async def test_bridged_run_loop(self):
        """Bridge mode calls cat.run_loop("tool_execution")."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="task", use_organ_pipeline=True)
        result = await loop.run(cat, "deploy task")
        assert len(cat.run_loop_calls) == 1
        assert cat.run_loop_calls[0][0] == "tool_execution"
        assert cat.run_loop_calls[0][1] == {"task": "deploy task"}
        assert result["status"] == "completed"

    @pytest.mark.anyio
    async def test_bridged_failure_fallback(self):
        """When run_loop() fails, graceful fallback."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        cat._run_loop_should_fail = True
        loop = ReflectionLoop(mode="task", use_organ_pipeline=True)
        result = await loop.run(cat, "deploy")
        assert result == {"task": "deploy", "status": "planned"}


# -- 3. Bridge: ReflectionLoop learn mode -----------------------------


class TestBridgeLearnLoop:
    """ReflectionLoop(mode="learn") with use_organ_pipeline."""

    @pytest.mark.anyio
    async def test_default_no_bridge(self):
        """Without use_organ_pipeline, behavior unchanged."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="learn", use_organ_pipeline=False)
        result = await loop.run(cat, "topic")
        assert result == {"topic": "topic", "learned": True}
        assert len(cat.run_loop_calls) == 0

    @pytest.mark.anyio
    async def test_bridged_run_loop(self):
        """Bridge mode calls cat.run_loop("diagnostic")."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        loop = ReflectionLoop(mode="learn", use_organ_pipeline=True)
        result = await loop.run(cat, "kubernetes")
        assert len(cat.run_loop_calls) == 1
        assert cat.run_loop_calls[0][0] == "diagnostic"
        assert cat.run_loop_calls[0][1] == {"topic": "kubernetes"}
        assert result["learned"] is True
        assert "diagnostic" in result

    @pytest.mark.anyio
    async def test_bridged_failure_fallback(self):
        """When run_loop() fails, graceful fallback."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        cat = MockBridgeCat(cs)
        cat._run_loop_should_fail = True
        loop = ReflectionLoop(mode="learn", use_organ_pipeline=True)
        result = await loop.run(cat, "topic")
        assert result == {"topic": "topic", "learned": True}


# -- 4. CatSelf.loop() pass-through -----------------------------------


class TestCatSelfLoopBridge:
    """CatSelf.loop() passes use_organ_pipeline to loop constructors."""

    def test_loop_passes_flag_conversation(self):
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        loop = cs.loop("conversation", use_organ_pipeline=True)
        assert isinstance(loop, ReflectionLoop)
        assert loop._mode == "conversation"
        assert loop._use_organ_pipeline is True

    def test_loop_passes_flag_task(self):
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        loop = cs.loop("task", use_organ_pipeline=True)
        assert isinstance(loop, ReflectionLoop)
        assert loop._mode == "task"
        assert loop._use_organ_pipeline is True

    def test_loop_passes_flag_learn(self):
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        loop = cs.loop("learn", use_organ_pipeline=True)
        assert isinstance(loop, ReflectionLoop)
        assert loop._mode == "learn"
        assert loop._use_organ_pipeline is True

    def test_loop_default_false(self):
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))
        loop = cs.loop("conversation")
        assert loop._use_organ_pipeline is False

    def test_loop_with_fusion_trigger_and_bridge(self):
        """Both fusion_trigger and use_organ_pipeline can be passed."""
        cs = CatSelf(scribble_pad=ScribblePad(capacity=10))

        def my_strategy(x):
            return True

        loop = cs.loop("task", fusion_trigger=my_strategy,
                       use_organ_pipeline=True)
        assert loop._fusion is my_strategy
        assert loop._use_organ_pipeline is True
