# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.3.0 — EventBus concurrency and Colony broadcast/signal concurrency tests.

Coverage:
  * EventBus concurrency (concurrent emit, registration during emit, emit_nowait)
  * Colony broadcast concurrency (multiple cats, empty colony, signal_between)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.events import EventBus

from tests.conftest import DummyOrgan, make_colony


# ═══════════════════════════════════════════════════════════════════════
# TestEventBusConcurrency
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestEventBusConcurrency:
    """Concurrent emit, registration during emit, emit_nowait behaviour."""

    @pytest.mark.asyncio
    async def test_concurrent_emit_with_multiple_handlers(self) -> None:
        bus = EventBus()
        results_a: list[str] = []
        results_b: list[str] = []

        async def ha(payload: Any = None) -> None:
            results_a.append("a")
            await asyncio.sleep(0.01)
            results_a.append("a_done")

        async def hb(payload: Any = None) -> None:
            results_b.append("b")

        bus.on("evt", ha)
        bus.on("evt", hb)

        await asyncio.gather(
            bus.emit("evt"),
            bus.emit("evt"),
        )
        assert results_a.count("a") == 2
        assert results_a.count("a_done") == 2
        assert results_b == ["b", "b"]

    @pytest.mark.asyncio
    async def test_concurrent_registration_during_emit(self) -> None:
        """Register handler while another emit is in flight — no crash."""
        bus = EventBus()
        fired: list[str] = []

        async def h1(payload: Any = None) -> None:
            fired.append("h1")
            await asyncio.sleep(0.02)

        bus.on("evt", h1)

        async def _register_late() -> None:
            await asyncio.sleep(0.005)
            bus.on("evt", lambda p=None: fired.append("h2"))

        await asyncio.gather(
            bus.emit("evt"),
            _register_late(),
        )
        assert "h1" in fired

    @pytest.mark.asyncio
    async def test_concurrent_multiple_events(self) -> None:
        bus = EventBus()
        results: list[tuple[str, int]] = []

        async def handler_a(payload: Any = None) -> None:
            results.append(("a", 1))
            await asyncio.sleep(0.01)
            results.append(("a", 2))

        async def handler_b(payload: Any = None) -> None:
            results.append(("b", 1))

        bus.on("evt_a", handler_a)
        bus.on("evt_b", handler_b)

        await asyncio.gather(
            bus.emit("evt_a"),
            bus.emit("evt_b"),
        )
        assert ("b", 1) in results

    @pytest.mark.asyncio
    async def test_emit_nowait_sync_handler_executes(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        def handler(payload: Any = None) -> None:
            calls.append(payload["x"])

        bus.on("evt", handler)
        bus.emit_nowait("evt", {"x": "hello"})
        assert calls == ["hello"]

    @pytest.mark.asyncio
    async def test_emit_nowait_async_handler_not_awaited(self) -> None:
        bus = EventBus()
        completed = False

        async def handler(payload: Any = None) -> None:
            nonlocal completed
            await asyncio.sleep(0.1)
            completed = True

        bus.on("evt", handler)
        bus.emit_nowait("evt")
        # emit_nowait is sync; async handler coroutine is discarded
        assert not completed  # Not awaited, so not completed

    @pytest.mark.asyncio
    async def test_emit_nowait_exception_does_not_propagate(self) -> None:
        bus = EventBus()

        def bad_handler(payload: Any = None) -> None:
            raise ValueError("boom")

        bus.on("evt", bad_handler)
        # Must not raise
        bus.emit_nowait("evt")

    @pytest.mark.asyncio
    async def test_off_during_emit_does_not_crash(self) -> None:
        bus = EventBus()
        fired: list[str] = []

        async def h1(payload: Any = None) -> None:
            fired.append("h1")
            await asyncio.sleep(0.02)

        def h2(payload: Any = None) -> None:
            fired.append("h2")

        bus.on("evt", h1)
        bus.on("evt", h2)

        async def _unregister():
            await asyncio.sleep(0.005)
            bus.off("evt", h2)

        await asyncio.gather(
            bus.emit("evt"),
            _unregister(),
        )
        # h1 must still fire; h2 might or might not depending on timing
        assert "h1" in fired

    @pytest.mark.asyncio
    async def test_clear_all_handlers(self) -> None:
        bus = EventBus()
        bus.on("evt_a", lambda: None)
        bus.on("evt_b", lambda: None)
        assert len(bus.events()) == 2
        bus.clear()
        assert bus.events() == []

    @pytest.mark.asyncio
    async def test_clear_specific_event(self) -> None:
        bus = EventBus()
        bus.on("evt_a", lambda: None)
        bus.on("evt_b", lambda: None)
        bus.clear("evt_a")
        assert bus.events() == ["evt_b"]

    @pytest.mark.asyncio
    async def test_handler_hangs_does_not_block_other_events(self) -> None:
        """一个 handler 挂起不会阻塞其他事件的 emit 调用."""
        bus = EventBus()
        started: list[str] = []

        async def slow(payload: Any = None) -> None:
            started.append("slow_start")
            await asyncio.sleep(0.1)
            started.append("slow_done")

        async def fast(payload: Any = None) -> None:
            started.append("fast")

        bus.on("evt_a", slow)
        bus.on("evt_a", fast)
        bus.on("evt_b", lambda p=None: started.append("evt_b"))

        async def _emit_b_late() -> None:
            await asyncio.sleep(0.02)
            await bus.emit("evt_b")

        await asyncio.gather(
            bus.emit("evt_a"),
            _emit_b_late(),
        )
        assert "evt_b" in started


# ═══════════════════════════════════════════════════════════════════════
# TestColonyBroadcastConcurrency
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestColonyBroadcastConcurrency:
    """并发 broadcast 和猫间通信竞态测试."""

    @pytest.mark.asyncio
    async def test_concurrent_broadcast_to_multiple_cats(self) -> None:
        """多 cat 并发接收 broadcast，不丢消息."""
        col = make_colony(("a", "a"), ("b", "b"), ("c", "c"))
        received: list[str] = []

        for uid in ["01", "02", "03"]:
            cat = col.get_cat(uid)

            def handler(payload: Any = None, _uid: str = uid) -> None:
                received.append(_uid)

            cat.on("ping", handler)

        await asyncio.gather(
            col.broadcast("ping", msg="1"),
            col.broadcast("ping", msg="2"),
        )
        # 3 cats × 2 broadcasts = 6 receptions
        assert len(received) == 6

    @pytest.mark.asyncio
    async def test_broadcast_no_cats_no_error(self) -> None:
        """空 Colony broadcast 不报错."""
        col = Colony("empty", storage=InMemorySharedStore())
        await col.broadcast("ping", msg="hi")  # No error

    @pytest.mark.asyncio
    async def test_concurrent_signal_between_same_target(self) -> None:
        """多 cat 同时向同一 cat 发信号不崩溃."""
        col = make_colony(("a", "a"), ("b", "b"), ("c", "c"), allow_all=True)
        target = col.get_cat("03")
        target.mount("brain", "hippocampus", DummyOrgan())

        results: list[Any] = []

        async def _signal(from_id: str) -> None:
            r = await col.signal_between(from_id, "03", "brain", "hippocampus", "echo", from_id)
            results.append(r)

        await asyncio.gather(_signal("01"), _signal("02"))
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_broadcast_and_signal_between_concurrent(self) -> None:
        """broadcast 和 signal_between 同时进行不崩溃."""
        col = make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", DummyOrgan())

        received: list[str] = []
        cat_a = col.get_cat("01")
        cat_a.on("evt", lambda p: received.append(p.get("msg", "")))

        async def _broadcast() -> None:
            await col.broadcast("evt", msg="broadcasted")

        async def _signal() -> None:
            await col.signal_between("01", "02", "brain", "hippocampus", "echo", "hello")

        await asyncio.gather(_broadcast(), _signal())
        assert "broadcasted" in received
