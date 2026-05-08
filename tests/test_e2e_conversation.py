# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat end-to-end integration tests — full conversation loop.

Validates the complete chain from ``perceive()`` through reflex matching,
pipeline stage execution, and lifecycle events — without real LLM dependency.

Coverage:
- Default Noop pipeline: reflex → stages → lifecycle events
- Custom stage pipeline: verify Stage.run() is called in order
- Short-circuit: verify pipeline stops early
- PERCEIVE_START / PERCEIVE_END lifecycle events
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from meowcat.colony import Colony
from meowcat.defaults import InMemorySharedStore
from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import NoopCerebrum
from meowcat.defaults.stages import BaseStage
from meowcat.events import Lifecycle
from meowcat.models import PipelineContext, StageEvent
from meowcat.reflex import Reflex, BUILTIN_REFLEX_PATHS


# ── Helpers ────────────────────────────────────────────────────────────


def _make_colony() -> Colony:
    return Colony("e2e", storage=InMemorySharedStore())


def _create_test_cat(colony: Colony, **kw: Any) -> Any:
    return create_cat(container=colony, cerebrum=NoopCerebrum(), **kw)


# ── Custom Stages for pipeline verification ─────────────────────────────


class _RecordStage(BaseStage):
    """Stage that records it was called and yields a thinking event."""

    def __init__(self, label: str, calls: list[str]) -> None:
        super().__init__()
        self.label = label
        self.calls = calls

    async def run(self, ctx: PipelineContext) -> AsyncIterator[StageEvent]:
        self.calls.append(self.label)
        yield StageEvent.thinking(f"{self.label}: thinking")


class _ShortCircuitStage(BaseStage):
    """Stage that immediately short-circuits the pipeline."""

    def __init__(self, reply: str = "blocked") -> None:
        super().__init__()
        self.reply = reply

    async def run(self, ctx: PipelineContext) -> AsyncIterator[StageEvent]:
        yield StageEvent.short_circuit(self.reply)


# ── Tests ──────────────────────────────────────────────────────────────


class TestE2EConversationLoop:
    """Full perceive() → reflex → pipeline → lifecycle events."""

    @pytest.mark.asyncio
    async def test_default_noop_pipeline_completes(self):
        """Default Noop pipeline: perceive() runs without error and emits
        lifecycle events."""
        colony = _make_colony()
        cat = _create_test_cat(colony)

        events = []
        cat.on(Lifecycle.PERCEIVE_START, lambda p: events.append(("start", p)))
        cat.on(Lifecycle.PERCEIVE_END, lambda p: events.append(("end", p)))

        outputs = []
        async for ev in cat.perceive("你好"):
            outputs.append(ev)

        # Default Noop stages yield nothing → outputs empty
        assert outputs == []
        # Lifecycle events must fire
        assert len(events) == 2
        assert events[0][0] == "start"
        assert events[1][0] == "end"
        assert events[0][1]["input"] == "你好"
        assert events[0][1]["reflex_name"] == "text_dialogue"

    @pytest.mark.asyncio
    async def test_custom_stages_run_in_order(self):
        """Custom stages: verify run() is called in registration order."""
        colony = _make_colony()
        calls: list[str] = []

        # Build custom stages that record themselves
        stages = [
            _RecordStage("ingest", calls),
            _RecordStage("locate", calls),
            _RecordStage("execute", calls),
        ]

        cat = create_cat(
            container=colony,
            cerebrum=NoopCerebrum(),
            reflexes=[
                Reflex(
                    name="text_dialogue",
                    trigger=lambda x: isinstance(x, str),
                    path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                    stages=stages,
                ),
            ],
        )

        outputs = []
        async for ev in cat.perceive("测试消息"):
            outputs.append(ev)

        # All 3 stages must have been called in order
        assert calls == ["ingest", "locate", "execute"]
        # Each stage yielded one thinking event
        assert len(outputs) == 3
        assert all(ev.kind == "thinking" for ev in outputs)

    @pytest.mark.asyncio
    async def test_pipeline_short_circuit(self):
        """Short-circuit stage: later stages should NOT run."""
        colony = _make_colony()
        calls: list[str] = []

        stages = [
            _RecordStage("first", calls),
            _ShortCircuitStage("breached"),
            _RecordStage("never_runs", calls),
        ]

        cat = create_cat(
            container=colony,
            cerebrum=NoopCerebrum(),
            reflexes=[
                Reflex(
                    name="text_dialogue",
                    trigger=lambda x: isinstance(x, str),
                    path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                    stages=stages,
                ),
            ],
        )

        outputs = []
        async for ev in cat.perceive("触发短路"):
            outputs.append(ev)

        # Only first stage + short_circuit should have run
        assert calls == ["first"]
        assert len(outputs) == 2  # thinking + short_circuit
        assert outputs[-1].kind == "short_circuit"
        assert outputs[-1].reply == "breached"

    @pytest.mark.asyncio
    async def test_perceive_events_include_final_reply(self):
        """PERCEIVE_END event carries ctx.final_reply when set."""
        colony = _make_colony()
        stages = [_ShortCircuitStage("hello back")]

        cat = create_cat(
            container=colony,
            cerebrum=NoopCerebrum(),
            reflexes=[
                Reflex(
                    name="text_dialogue",
                    trigger=lambda x: isinstance(x, str),
                    path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                    stages=stages,
                ),
            ],
        )

        end_payload: dict[str, Any] = {}

        def capture_end(payload: Any) -> None:
            nonlocal end_payload
            end_payload = payload

        cat.on(Lifecycle.PERCEIVE_END, capture_end)

        outputs = []
        async for ev in cat.perceive("hi"):
            outputs.append(ev)

        assert end_payload["reflex_name"] == "text_dialogue"
        assert end_payload["reply"] == "hello back"

    @pytest.mark.asyncio
    async def test_multiple_perceive_calls(self):
        """Multiple perceive() calls: each invocation is independent."""
        colony = _make_colony()
        calls: list[str] = []
        stages = [_RecordStage("step", calls)]

        cat = create_cat(
            container=colony,
            cerebrum=NoopCerebrum(),
            reflexes=[
                Reflex(
                    name="text_dialogue",
                    trigger=lambda x: isinstance(x, str),
                    path=BUILTIN_REFLEX_PATHS["text_dialogue"],
                    stages=stages,
                ),
            ],
        )

        # First call
        async for _ in cat.perceive("消息1"):
            pass
        assert calls == ["step"]

        # Second call — stage runs again
        async for _ in cat.perceive("消息2"):
            pass
        assert calls == ["step", "step"]

    @pytest.mark.asyncio
    async def test_conversation_loop_with_colony_events(self):
        """Verify colony-level perceive doesn't break cat-level pipeline."""
        colony = _make_colony()
        cat = _create_test_cat(colony)

        results: list[str] = []

        async def on_start(payload: Any) -> None:
            results.append(payload["input"])

        async def on_end(payload: Any) -> None:
            results.append(payload["reflex_name"])

        cat.on(Lifecycle.PERCEIVE_START, on_start)
        cat.on(Lifecycle.PERCEIVE_END, on_end)

        async for _ in cat.perceive("测试"):
            pass

        assert results == ["测试", "text_dialogue"]

    @pytest.mark.asyncio
    async def test_empty_input_still_triggers_reflex(self):
        """Empty string input still matches text_dialogue trigger."""
        colony = _make_colony()
        cat = _create_test_cat(colony)

        fired = False

        def on_event(_: Any) -> None:
            nonlocal fired
            fired = True

        cat.on(Lifecycle.PERCEIVE_START, on_event)

        async for _ in cat.perceive(""):
            pass

        assert fired
