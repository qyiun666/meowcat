"""
v0.5.0 T3 meowcat 核心骨架契约测试
=====================================

职责：
    锁死 meowcat/assembly.py / events.py / pipeline.py / loop.py 的对外契约。

契约类别：
    1. TestEventBus       — 同步/异步 handler、注册/注销、顺序触发、装饰器
    2. TestCatBaseOrgans  — mount/organ/unmount/has_organ/organs
    3. TestCatBaseEvents  — on/off/emit、生命周期 start/shutdown 事件
    4. TestPipeline       — 顺序执行、短路中止、短路后续 Stage 不再调用
    5. TestLoopEvents     — 三大闭环事件名常量完整性

参考：docs/v0.5.0/design.md §4~§6、docs/v0.5.0/tasks.md T3
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from meowcat import (
    CatBase,
    EventBus,
    GrowthEvent,
    KittenEvent,
    Lifecycle,
    LocateEvent,
    OrchestrateEvent,
    OrganNotMountedError,
    Pipeline,
    RememberEvent,
    StageEvent,
)
from meowcat.loop import ALL_EVENTS


# -- 1. EventBus ----------------------------------------------------


class TestEventBus:
    """EventBus 同步/异步/顺序契约。"""

    async def test_sync_handler_receives_payload(self) -> None:
        bus = EventBus()
        seen: list[Any] = []
        bus.on("boot", lambda p: seen.append(p))
        await bus.emit("boot", {"hello": 1})
        assert seen == [{"hello": 1}]

    async def test_async_handler_is_awaited(self) -> None:
        bus = EventBus()
        seen: list[str] = []

        async def h(payload: str) -> None:
            seen.append(payload)

        bus.on("topic", h)
        await bus.emit("topic", "async-ok")
        assert seen == ["async-ok"]

    async def test_zero_arg_handler_supported(self) -> None:
        """无参 handler 不传 payload，不崩。"""
        bus = EventBus()
        hits: list[int] = []

        def h() -> None:
            hits.append(1)

        bus.on("ping", h)
        await bus.emit("ping", "ignored-payload")
        assert hits == [1]

    async def test_decorator_form_registers(self) -> None:
        bus = EventBus()
        seen: list[int] = []

        @bus.on("x")
        def h(p: int) -> None:
            seen.append(p)

        await bus.emit("x", 42)
        assert seen == [42]
        # 装饰器返回函数本身（可组合）
        assert callable(h)

    async def test_multiple_handlers_run_in_order(self) -> None:
        bus = EventBus()
        order: list[str] = []
        bus.on("e", lambda _p: order.append("a"))
        bus.on("e", lambda _p: order.append("b"))
        bus.on("e", lambda _p: order.append("c"))
        await bus.emit("e", None)
        assert order == ["a", "b", "c"]

    async def test_off_removes_handler(self) -> None:
        bus = EventBus()
        hits: list[int] = []

        def h(_: Any) -> None:
            hits.append(1)

        bus.on("e", h)
        assert bus.off("e", h) is True
        await bus.emit("e", None)
        assert hits == []
        # 重复注销返回 False，不抛
        assert bus.off("e", h) is False

    async def test_emit_to_unknown_event_is_noop(self) -> None:
        bus = EventBus()
        await bus.emit("nobody-listens", {"x": 1})  # 不抛即通过


# -- 2. CatBase 器官 ------------------------------------------------


class TestCatBaseOrgans:
    """CatBase.mount / organ / unmount / has_organ / organs."""

    def test_mount_and_organ_roundtrip(self) -> None:
        cat = CatBase("felix")
        sentinel = object()
        cat.mount("brain", "hippocampus", sentinel)
        assert cat.organ("brain", "hippocampus") is sentinel

    def test_organ_not_mounted_raises(self) -> None:
        cat = CatBase("felix")
        with pytest.raises(OrganNotMountedError) as exc:
            cat.organ("brain", "hippocampus")
        assert exc.value.category == "brain"
        assert exc.value.name == "hippocampus"

    def test_has_organ_and_unmount(self) -> None:
        cat = CatBase("felix")
        cat.mount("sense", "ears", object())
        assert cat.has_organ("sense", "ears") is True
        assert cat.unmount("sense", "ears") is True
        assert cat.has_organ("sense", "ears") is False
        # 再次 unmount 返回 False，不抛
        assert cat.unmount("sense", "ears") is False

    def test_organs_snapshot_is_copy(self) -> None:
        cat = CatBase("felix")
        a, b = object(), object()
        cat.mount("brain", "hippocampus", a)
        cat.mount("brain", "thalamus", b)
        snap = cat.organs("brain")
        assert snap == {"hippocampus": a, "thalamus": b}
        # 修改快照不影响内部状态
        snap["evil"] = object()
        assert cat.has_organ("brain", "evil") is False


# -- 3. CatBase 事件 ------------------------------------------------


class TestCatBaseEvents:
    """CatBase 事件转发 + 生命周期。"""

    async def test_cat_on_emit_roundtrip(self) -> None:
        cat = CatBase("felix")
        seen: list[Any] = []
        cat.on("wake", lambda p: seen.append(p))
        await cat.emit("wake", {"mood": "ok"})
        assert seen == [{"mood": "ok"}]

    async def test_start_triggers_lifecycle_event(self) -> None:
        cat = CatBase("felix")
        seen: list[Any] = []
        cat.on(Lifecycle.START, lambda p: seen.append(p))
        await cat.start()
        assert len(seen) == 1
        assert seen[0]["cat"] is cat

    async def test_shutdown_triggers_lifecycle_event(self) -> None:
        cat = CatBase("felix")
        seen: list[str] = []
        cat.on(Lifecycle.SHUTDOWN, lambda _p: seen.append("bye"))
        await cat.shutdown()
        assert seen == ["bye"]


# -- 4. Pipeline ----------------------------------------------------


class _Ctx:
    """Pipeline 测试用的最小上下文（dataclass 不是必须，duck-typed 即可）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.short_circuited: bool = False
        self.final_reply: str | None = None


class _RecordingStage:
    """记录自己被执行，产出一个 token 事件。"""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, ctx: _Ctx) -> AsyncIterator[StageEvent]:
        ctx.calls.append(self.name)
        yield StageEvent.output(f"{self.name}-token")


class _ShortCircuitStage:
    """直接短路，附带 reply。"""

    name = "halt"

    async def run(self, ctx: _Ctx) -> AsyncIterator[StageEvent]:
        yield StageEvent.short_circuit("done-early")


class TestPipeline:
    """Pipeline 顺序执行 + 短路 + 空清单。"""

    async def test_empty_pipeline_yields_nothing(self) -> None:
        pipe = Pipeline([])
        ctx = _Ctx()
        events = [ev async for ev in pipe.execute(ctx)]
        assert events == []
        assert ctx.short_circuited is False

    async def test_runs_stages_in_order(self) -> None:
        ctx = _Ctx()
        pipe = Pipeline(
            [_RecordingStage("a"), _RecordingStage("b"), _RecordingStage("c")])
        events = [ev async for ev in pipe.execute(ctx)]
        assert ctx.calls == ["a", "b", "c"]
        assert [ev.content for ev in events] == [
            "a-token", "b-token", "c-token"]
        assert all(ev.kind == "output" for ev in events)

    async def test_short_circuit_halts_and_marks_ctx(self) -> None:
        ctx = _Ctx()
        later = _RecordingStage("after-halt")
        pipe = Pipeline([_RecordingStage("before"),
                        _ShortCircuitStage(), later])
        events = [ev async for ev in pipe.execute(ctx)]

        # 短路后 later 不应被执行
        assert ctx.calls == ["before"]
        assert ctx.short_circuited is True
        assert ctx.final_reply == "done-early"
        # 最后一个事件是 short_circuit
        assert events[-1].kind == "short_circuit"
        assert events[-1].reply == "done-early"


# -- 5. 闭环事件名常量 ---------------------------------------------


class TestLoopEvents:
    """三大闭环 + 生命周期的事件名常量锁死。"""

    def test_closure_a_events_present(self) -> None:
        """闭环 A：locate / remember / compress。"""
        assert LocateEvent.PRE == "locate.pre"
        assert LocateEvent.POST == "locate.post"
        assert LocateEvent.ROUTE_DECIDED == "route.decided"
        assert RememberEvent.PRE == "remember.pre"
        assert RememberEvent.POST == "remember.post"
        assert RememberEvent.COMPRESS_PRE == "compress.pre"
        assert RememberEvent.COMPRESS_POST == "compress.post"

    def test_closure_b_events_present(self) -> None:
        """闭环 B：编排。"""
        assert OrchestrateEvent.START == "orchestrate.start"
        assert OrchestrateEvent.END == "orchestrate.end"

    def test_closure_c_events_present(self) -> None:
        """闭环 C：生长结晶。"""
        assert GrowthEvent.ANOMALY == "growth.anomaly"
        assert GrowthEvent.CORRECTION == "growth.correction"
        assert GrowthEvent.CRYSTALLIZE == "crystallize.emit"
        assert GrowthEvent.ROLE_EMERGE == "role.emerge"

    def test_lifecycle_events_present(self) -> None:
        assert Lifecycle.START == "lifecycle.start"
        assert Lifecycle.SHUTDOWN == "lifecycle.shutdown"

    def test_all_events_is_distinct_and_covers_each(self) -> None:
        """ALL_EVENTS 不重复，且包含每个常量。"""
        assert len(ALL_EVENTS) == len(set(ALL_EVENTS))
        expected = {
            LocateEvent.PRE, LocateEvent.POST, LocateEvent.ROUTE_DECIDED,
            RememberEvent.PRE, RememberEvent.POST,
            RememberEvent.COMPRESS_PRE, RememberEvent.COMPRESS_POST,
            OrchestrateEvent.START, OrchestrateEvent.END,
            GrowthEvent.ANOMALY, GrowthEvent.CORRECTION,
            GrowthEvent.CRYSTALLIZE, GrowthEvent.ROLE_EMERGE,
            Lifecycle.START, Lifecycle.SHUTDOWN,
            Lifecycle.PERCEIVE_START, Lifecycle.PERCEIVE_END,
            KittenEvent.SPAWNED, KittenEvent.EXECUTING, KittenEvent.COMPLETED,
            KittenEvent.STUCK, KittenEvent.DISMISSED,
            KittenEvent.MERGE_ABSORBED,
        }
        # ALL_EVENTS 至少包含以上所有事件（允许 v0.5.1+ 新增 nerve.signal 等）
        assert expected <= set(ALL_EVENTS)
