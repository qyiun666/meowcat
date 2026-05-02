"""
v0.5.1 Task 1.9c — CatBase signal / perceive 契约测试
=======================================================

契约类别：
    1. TestSignal           — signal 调用链路、wiring 校验、nerve.signal 事件、异常
    2. TestPerceive         — perceive 反射匹配、stages 驱动、path 事件广播、无匹配抛异常
    3. TestNervousSystem    — wire_default / freeze / register_reflex

每个需要 CatBase 的测试都先 mount 必要器官并接通 wiring。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from meowcat import (
    CatBase,
    IllegalNeuralPathError,
    NerveEvent,
    NoReflexMatchedError,
    ReflexPathInvalidError,
)
from meowcat.loop import Lifecycle
from meowcat.models import StageEvent
from meowcat.reflex import Reflex


class _DummyOrgan:
    """用于 signal 测试的最小器官。"""

    def __init__(self, name: str = "dummy") -> None:
        self.name = name
        self.calls: list[tuple[str, tuple, dict]] = []

    def echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}

    async def async_echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("async_echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}


class _EchoStage:
    """产出单个 token 事件的最简 Stage。"""

    name = "echo_stage"

    async def run(self, ctx: Any) -> AsyncIterator[StageEvent]:
        yield StageEvent.output(f"echo:{ctx.reflex_name}")


def _new_cat_with_wiring() -> CatBase:
    """准备好 wiring 的猫：a→b→c 连通。"""
    cat = CatBase("test")
    cat.wiring.connect(("brain", "a"), ("brain", "b"))
    cat.wiring.connect(("brain", "b"), ("brain", "c"))
    cat.wiring.connect(("brain", "a"), ("brain", "c"))
    return cat


# -- 1. signal -----------------------------------------------------

class TestSignal:
    """cat.signal(from, to, method, *args) 调用链路测试。"""

    async def test_signal_calls_method(self) -> None:
        cat = _new_cat_with_wiring()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)
        result = await cat.signal(
            ("brain", "a"), ("brain", "b"), "echo", "hello", key="val",
        )
        assert result == {"args": ("hello",), "kwargs": {"key": "val"}}
        assert organ.calls == [("echo", ("hello",), {"key": "val"})]

    async def test_signal_awaits_async_method(self) -> None:
        cat = _new_cat_with_wiring()
        organ = _DummyOrgan()
        cat.mount("brain", "c", organ)
        result = await cat.signal(
            ("brain", "b"), ("brain", "c"), "async_echo", 42,
        )
        assert result == {"args": (42,), "kwargs": {}}
        assert ("async_echo", (42,), {}) in organ.calls

    async def test_signal_emits_nerve_event(self) -> None:
        cat = _new_cat_with_wiring()
        cat.mount("brain", "b", _DummyOrgan())
        seen: list[dict] = []

        @cat.on(NerveEvent.SIGNAL)
        def _trap(payload: dict) -> None:
            seen.append(payload)

        await cat.signal(("brain", "a"), ("brain", "b"), "echo")
        assert len(seen) == 1
        assert seen[0]["from"] == ("brain", "a")
        assert seen[0]["to"] == ("brain", "b")
        assert seen[0]["method"] == "echo"

    async def test_signal_raises_on_forbidden(self) -> None:
        cat = _new_cat_with_wiring()
        cat.wiring.forbid(("brain", "a"), ("brain", "b"))
        cat.mount("brain", "b", _DummyOrgan())
        with pytest.raises(IllegalNeuralPathError):
            await cat.signal(("brain", "a"), ("brain", "b"), "echo")

    async def test_signal_raises_on_unconnected(self) -> None:
        cat = CatBase("test")
        cat.mount("brain", "b", _DummyOrgan())
        # wiring 空 → 任何边都不允许
        with pytest.raises(IllegalNeuralPathError):
            await cat.signal(("brain", "a"), ("brain", "b"), "echo")


# -- 2. perceive ---------------------------------------------------

class TestPerceive:
    """cat.perceive(input) 反射入口测试。"""

    async def test_perceive_no_match_raises(self) -> None:
        cat = CatBase("test")
        with pytest.raises(NoReflexMatchedError):
            async for _ in cat.perceive("hello"):
                pass

    async def test_perceive_with_stages(self) -> None:
        cat = _new_cat_with_wiring()
        cat.mount("brain", "b", _DummyOrgan())
        cat.mount("brain", "c", _DummyOrgan())

        reflex = Reflex(
            name="test_staged",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b"), ("brain", "c")),
            stages=[_EchoStage()],
        )
        cat.register_reflex(reflex)

        events: list[StageEvent] = []
        async for ev in cat.perceive("hello"):
            events.append(ev)
        assert len(events) >= 1
        assert events[0].content == "echo:test_staged"

    async def test_perceive_without_stages_emits_signal_events(self) -> None:
        cat = _new_cat_with_wiring()
        cat.mount("brain", "b", _DummyOrgan())
        cat.mount("brain", "c", _DummyOrgan())

        reflex = Reflex(
            name="bare_path",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b"), ("brain", "c")),
            stages=[],
        )
        cat.register_reflex(reflex)

        signals: list[dict] = []

        @cat.on(NerveEvent.SIGNAL)
        def _trap(payload: dict) -> None:
            signals.append(payload)

        events: list[Any] = []
        async for ev in cat.perceive("hello"):
            events.append(ev)

        # 没有 yield 回来的 event（Pipeline 没跑），但 nerve.signal 事件触发了
        assert len(events) == 0
        # 两个 hop：(a,b) (b,c) 各一次事件
        assert len(signals) == 2
        assert signals[0]["from"] == ("brain", "a")
        assert signals[0]["to"] == ("brain", "b")
        assert signals[1]["from"] == ("brain", "b")
        assert signals[1]["to"] == ("brain", "c")

    async def test_perceive_emits_lifecycle_events(self) -> None:
        cat = _new_cat_with_wiring()
        cat.mount("brain", "b", _DummyOrgan())
        cat.mount("brain", "c", _DummyOrgan())

        reflex = Reflex(
            name="lc_test",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b"), ("brain", "c")),
        )
        cat.register_reflex(reflex)

        lc_events: list[str] = []

        @cat.on(Lifecycle.PERCEIVE_START)
        def _start(payload: dict) -> None:
            lc_events.append("start")

        @cat.on(Lifecycle.PERCEIVE_END)
        def _end(payload: dict) -> None:
            lc_events.append("end")

        async for _ in cat.perceive("test"):
            pass

        assert lc_events == ["start", "end"]


# -- 3. 神经系统装配 -----------------------------------------------

class TestNervousSystem:
    """wire_default_nervous_system / freeze / register_reflex。"""

    def test_wire_default_nervous_system(self) -> None:
        cat = CatBase("test")
        cat.wire_default_nervous_system()
        # 默认 wiring 必然不是空的
        assert len(cat.wiring.edges()) > 0
        # 大脑不直连四肢
        assert not cat.wiring.is_allowed(
            ("brain", "cerebrum"), ("sense", "paws"),
        )

    def test_freeze_nervous_system(self) -> None:
        cat = CatBase("test")
        cat.wire_default_nervous_system()

        reflex = Reflex(
            name="ok",
            trigger=lambda x: True,
            path=(("sense", "ears"), ("brain", "thalamus"),
                  ("brain", "brainstem")),
        )
        cat.register_reflex(reflex)
        cat.freeze_nervous_system()
        assert cat.wiring.frozen

    def test_freeze_rejects_invalid_reflex_path(self) -> None:
        cat = CatBase("test")
        cat.wire_default_nervous_system()

        reflex = Reflex(
            name="bad",
            trigger=lambda x: True,
            path=(("brain", "cerebrum"), ("sense", "paws")),  # 禁止通路
        )
        cat.register_reflex(reflex)
        with pytest.raises(ReflexPathInvalidError):
            cat.freeze_nervous_system()

    async def test_signal_after_freeze_still_works(self) -> None:
        """freeze 只锁写，不锁读——signal 仍然可用。"""
        cat = CatBase("test")
        a = _DummyOrgan()
        cat.mount("brain", "a", a)
        cat.mount("brain", "b", _DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        cat.wiring.freeze()

        # signal 仍能走（只读 wiring）
        result = await cat.signal(("brain", "a"), ("brain", "b"), "echo", "x")
        assert result == {"args": ("x",), "kwargs": {}}
