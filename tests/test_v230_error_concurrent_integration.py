# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.3.0 T-11 / H-11 — 错误路径 / 并发 / 集成测试.

Coverage:
  * Signal error propagation (IllegalNeuralPathError, CircuitOpenError, organ exception)
  * EventBus concurrency (concurrent emit, registration during emit, emit_nowait)
  * Gateway integration (start/stop, FrontDesk plugin chain, route → cat)
  * do_task e2e (safety rejection, tool not found, multi-round, max_rounds cutoff)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import anyio
import pytest

from meowcat import CatBase as _CatBase
from meowcat.assembly import CatBase
from meowcat.colony import Colony
from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import DefaultCerebrum
from meowcat.defaults.stages import BaseStage
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.errors import (
    CircuitOpenError,
    IllegalNeuralPathError,
    MeowCatError,
    OrganNotMountedError,
    StageTimeoutError,
)
from meowcat.events import EventBus
from meowcat.gateway import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.gateway.protocol import (
    FrontDeskProtocol,
    IoAdapterProtocol,
    SignalContext,
)
from meowcat.models import StageEvent
from meowcat.nervous import Nervous
from meowcat.reflex import BUILTIN_REFLEX_PATHS, Reflex
from meowcat.testing import make_cat, make_test_colony
from meowcat.tools.tool import Tool, ToolSpec
from meowcat.tools.tool_call import DoTaskResult, XmlToolCallParser
from meowcat.wiring import Organ

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


class _DummyOrgan:
    """Minimal signal-test organ with call tracking."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}

    async def async_echo(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("async_echo", args, kwargs))
        return {"args": args, "kwargs": kwargs}

    def fail(self) -> None:
        raise ValueError("intentional organ failure")

    async def async_fail(self) -> None:
        raise RuntimeError("intentional async organ failure")


class _FragileOrgan:
    """Organ that fails N times before succeeding."""

    def __init__(self, fail_count: int = 0) -> None:
        self._fail_remaining = fail_count
        self.call_count = 0

    async def act(self, msg: str = "") -> str:
        self.call_count += 1
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise RuntimeError(
                f"fragile organ failed (call {self.call_count})")
        return f"success:{msg}"


def _wired_cat(*connections: tuple[Organ, Organ]) -> CatBase:
    """Create a cat with organs a→b wired (plus any extra connections)."""
    cat = make_cat("test")
    cat.mount("brain", "a", _DummyOrgan())
    cat.mount("brain", "b", _DummyOrgan())
    for frm, to in connections:
        cat.wiring.connect(frm, to)
    return cat


def _make_colony(*cats: tuple[str, str], allow_all: bool = False) -> Colony:
    """Create a Colony with registered cats.

    ``cats``: ``(name, uid_hint)`` tuples.
    ``allow_all``: if True, allow all cross-wiring edges.
    """
    colony = Colony("test", storage=InMemorySharedStore())
    cat_objs = []
    for name, _ in cats:
        c = colony.create_cat(name=name)
        c.mount("brain", "hippocampus", _DummyOrgan())
        cat_objs.append(c)
    if allow_all:
        for a in cat_objs:
            for b in cat_objs:
                if a is not b:
                    colony.allow_cross(a.cat_uid, b.cat_uid)
    return colony


# ═══════════════════════════════════════════════════════════════════════
# Section 1 — Signal error propagation
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestSignalErrorPropagation:
    """Error paths through Nervous.signal() and cat.signal()."""

    # -- Forbidden / unwired paths ------------------------------------

    @pytest.mark.asyncio
    async def test_forbidden_method_raises_illegal_path(self) -> None:
        cat = _wired_cat((("brain", "a"), ("brain", "b")))
        cat._nervous.forbidden_methods = frozenset({"echo"})
        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            await cat.signal(("brain", "a"), ("brain", "b"), "echo")

    @pytest.mark.asyncio
    async def test_unwired_path_raises_illegal_path(self) -> None:
        cat = _wired_cat()
        cat.mount("brain", "c", _DummyOrgan())
        cat.mount("brain", "d", _DummyOrgan())
        with pytest.raises(IllegalNeuralPathError, match="not connected"):
            await cat.signal(("brain", "c"), ("brain", "d"), "echo")

    @pytest.mark.asyncio
    async def test_organ_not_mounted_raises_organ_not_mounted(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", _DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "nonexistent"))
        with pytest.raises(OrganNotMountedError):
            await cat.signal(("brain", "a"), ("brain", "nonexistent"), "echo")

    @pytest.mark.asyncio
    async def test_disabled_wiring_raises_runtime_error(self) -> None:
        cat = make_cat(name="test", enable_wiring=False)
        with pytest.raises(RuntimeError):
            await cat.signal(("brain", "a"), ("brain", "b"), "echo")

    # -- Organ exception propagation --------------------------------

    @pytest.mark.asyncio
    async def test_organ_exception_propagates_through_signal(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", _DummyOrgan())
        cat.mount("brain", "b", _DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        with pytest.raises(ValueError, match="intentional organ failure"):
            await cat.signal(("brain", "a"), ("brain", "b"), "fail")

    @pytest.mark.asyncio
    async def test_async_organ_exception_propagates(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", _DummyOrgan())
        cat.mount("brain", "b", _DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        with pytest.raises(RuntimeError, match="intentional async organ failure"):
            await cat.signal(("brain", "a"), ("brain", "b"), "async_fail")

    # -- Middleware error handling ---------------------------------

    @pytest.mark.asyncio
    async def test_before_middleware_short_circuit_returns_none(self) -> None:
        cat = _wired_cat((("brain", "a"), ("brain", "b")))

        class _BlockMW:
            async def before(self, ctx):
                return None

        cat._nervous.use_middleware(_BlockMW())
        result = await cat.signal(("brain", "a"), ("brain", "b"), "echo")
        assert result is None

    @pytest.mark.asyncio
    async def test_on_error_middleware_fires_on_exception(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", _DummyOrgan())
        cat.mount("brain", "b", _DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))

        errors: list[Exception] = []

        class _ErrorCatcher:
            async def on_error(self, ctx, exc):
                errors.append(exc)

        cat._nervous.use_middleware(_ErrorCatcher())
        with pytest.raises(ValueError):
            await cat.signal(("brain", "a"), ("brain", "b"), "fail")
        assert len(errors) == 1
        assert "intentional organ failure" in str(errors[0])

    @pytest.mark.asyncio
    async def test_after_middleware_can_modify_result(self) -> None:
        cat = _wired_cat((("brain", "a"), ("brain", "b")))

        class _WrapperMW:
            async def after(self, ctx, result):
                return {"wrapped": result}

        cat._nervous.use_middleware(_WrapperMW())
        result = await cat.signal(("brain", "a"), ("brain", "b"), "echo", key="val")
        assert result == {"wrapped": {"args": (), "kwargs": {"key": "val"}}}

    @pytest.mark.asyncio
    async def test_multiple_middleware_chain_in_order(self) -> None:
        cat = _wired_cat((("brain", "a"), ("brain", "b")))
        calls: list[str] = []

        class _MW1:
            async def before(self, ctx):
                calls.append("mw1.before")
                return True

            async def after(self, ctx, result):
                calls.append("mw1.after")
                return result

        class _MW2:
            async def before(self, ctx):
                calls.append("mw2.before")
                return True

            async def after(self, ctx, result):
                calls.append("mw2.after")
                return result

        cat._nervous.use_middleware(_MW1())
        cat._nervous.use_middleware(_MW2())
        await cat.signal(("brain", "a"), ("brain", "b"), "echo")
        assert calls == ["mw1.before", "mw2.before", "mw1.after", "mw2.after"]

    # -- Circuit breaker (integration-level smoke) -------------------

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self) -> None:
        """Smoke: circuit-breaker-enabled signal opens after threshold failures."""
        host = cat = make_cat("cb-test")
        events = cat._events

        from meowcat.nervous import Nervous
        nervous = Nervous(host, events, circuit_breaker=True,
                          cb_threshold=2, cb_timeout=10.0)

        host.mount("brain", "a", _DummyOrgan())
        host.mount("brain", "b", _FragileOrgan(fail_count=99))
        from meowcat import biology
        biology.apply_default_wiring(nervous.wiring)
        nervous.wiring.connect(("brain", "a"), ("brain", "b"))

        # 2 failures → circuit should open
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await nervous.signal(("brain", "a"), ("brain", "b"), "act", "hi")
        # 3rd call → CircuitOpenError
        with pytest.raises(CircuitOpenError, match="Circuit open"):
            await nervous.signal(("brain", "a"), ("brain", "b"), "act", "hi")

    # -- signal_between error paths -------------------------------------------

    @pytest.mark.asyncio
    async def test_signal_between_target_organ_not_mounted(self) -> None:
        col = _make_colony(("a", "a"), ("b", "b"), allow_all=True)
        with pytest.raises(OrganNotMountedError):
            await col.signal_between("01", "02", "brain", "nonexistent", "locate")

    @pytest.mark.asyncio
    async def test_signal_between_cross_wiring_rejected_with_detail(self) -> None:
        col = _make_colony(("a", "a"), ("b", "b"))
        col.forbid_cross("01", "02")
        with pytest.raises(IllegalNeuralPathError, match="forbidden.*01.*02"):
            await col.signal_between("01", "02", "brain", "hippocampus", "echo")

    @pytest.mark.asyncio
    async def test_signal_between_default_deny_unconfigured(self) -> None:
        col = _make_colony(("a", "a"), ("b", "b"))
        with pytest.raises(IllegalNeuralPathError, match="not allowed"):
            await col.signal_between("01", "02", "brain", "hippocampus", "echo")

    @pytest.mark.asyncio
    async def test_signal_between_unknown_cat_raises_keyerror(self) -> None:
        col = _make_colony(("a", "a"))
        col.allow_cross("01", "nonexistent")
        with pytest.raises(KeyError):
            await col.signal_between("01", "nonexistent", "brain", "hippocampus", "echo")

    # -- MeowCatError hierarchy ----------------------------------------------

    def test_meowcat_error_base_class(self) -> None:
        err = MeowCatError("base")
        assert isinstance(err, Exception)
        assert str(err) == "base"

    def test_illegal_path_error_carries_organs(self) -> None:
        err = IllegalNeuralPathError(
            ("brain", "a"), ("brain", "b"), reason="test reason")
        assert err.from_organ == ("brain", "a")
        assert err.to_organ == ("brain", "b")
        assert "test reason" in str(err)

    def test_circuit_open_error_carries_diagnostics(self) -> None:
        err = CircuitOpenError(
            ("brain", "x"), "act", failures=3, retry_after=5.0)
        assert err.to_organ == ("brain", "x")
        assert err.method == "act"
        assert err.failures == 3
        assert err.retry_after == 5.0
        assert "Circuit open" in str(err)

    # -- StageTimeoutError ----------------------------------------------

    def test_stage_timeout_error_construction(self) -> None:
        """StageTimeoutError carries stage_name and timeout values."""
        err = StageTimeoutError("reasoning_stage", 5.0)
        assert isinstance(err, MeowCatError)
        assert err.stage_name == "reasoning_stage"
        assert err.timeout == 5.0
        assert "reasoning_stage" in str(err)
        assert "5.0" in str(err)

    # -- signal_between timeout -------------------------------------------

    @pytest.mark.asyncio
    async def test_signal_between_with_timeout_none_completes(self) -> None:
        """signal_between with timeout=None completes normally."""
        col = _make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", _DummyOrgan())
        result = await col.signal_between(
            "01", "02", "brain", "hippocampus", "async_echo",
            "hello",
            timeout=None,
        )
        assert result == {"args": ("hello",), "kwargs": {}}

    @pytest.mark.asyncio
    async def test_signal_between_timeout_expires(self) -> None:
        """signal_between with short timeout raises asyncio.TimeoutError."""

        class _SlowOrgan:
            async def slow(self) -> str:
                await asyncio.sleep(1.0)
                return "done"

        col = _make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", _SlowOrgan())
        with pytest.raises(asyncio.TimeoutError):
            await col.signal_between(
                "01", "02", "brain", "hippocampus", "slow",
                timeout=0.05,
            )

    @pytest.mark.asyncio
    async def test_signal_between_sync_method_completes_fast(self) -> None:
        """signal_between with sync method returns immediately regardless of timeout."""
        col = _make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", _DummyOrgan())
        # Sync echo with short timeout should still work fine
        result = await col.signal_between(
            "01", "02", "brain", "hippocampus", "echo",
            "quick",
            timeout=5.0,
        )
        assert result == {"args": ("quick",), "kwargs": {}}
        err = MeowCatError("base")
        assert isinstance(err, Exception)
        assert str(err) == "base"

    def test_illegal_path_error_carries_organs(self) -> None:
        err = IllegalNeuralPathError(
            ("brain", "a"), ("brain", "b"), reason="test reason")
        assert err.from_organ == ("brain", "a")
        assert err.to_organ == ("brain", "b")
        assert "test reason" in str(err)

    def test_circuit_open_error_carries_diagnostics(self) -> None:
        err = CircuitOpenError(
            ("brain", "x"), "act", failures=3, retry_after=5.0)
        assert err.to_organ == ("brain", "x")
        assert err.method == "act"
        assert err.failures == 3
        assert err.retry_after == 5.0
        assert "Circuit open" in str(err)


# ═══════════════════════════════════════════════════════════════════════
# Section 2 — EventBus concurrency
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

        # Two concurrent emits — lock only protects handler list copy, not execution.
        # Both ha() calls may append "a" before either finishes sleeping.
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
        # evt_b fires while evt_a is mid-flight (different event, no lock contention)
        assert "evt_b" in started


# ═══════════════════════════════════════════════════════════════════════
# Section 2a — Colony broadcast and signal concurrency
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestColonyBroadcastConcurrency:
    """并发 broadcast 和猫间通信竞态测试."""

    @pytest.mark.asyncio
    async def test_concurrent_broadcast_to_multiple_cats(self) -> None:
        """多 cat 并发接收 broadcast，不丢消息."""
        col = _make_colony(("a", "a"), ("b", "b"), ("c", "c"))
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
        col = _make_colony(("a", "a"), ("b", "b"), ("c", "c"), allow_all=True)
        target = col.get_cat("03")
        target.mount("brain", "hippocampus", _DummyOrgan())

        results: list[Any] = []

        async def _signal(from_id: str) -> None:
            r = await col.signal_between(
                from_id, "03", "brain", "hippocampus", "echo", from_id,
            )
            results.append(r)

        await asyncio.gather(
            _signal("01"),
            _signal("02"),
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_broadcast_and_signal_between_concurrent(self) -> None:
        """broadcast 和 signal_between 同时进行不崩溃."""
        col = _make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", _DummyOrgan())

        received: list[str] = []
        cat_a = col.get_cat("01")
        cat_a.on("evt", lambda p: received.append(p.get("msg", "")))

        async def _broadcast() -> None:
            await col.broadcast("evt", msg="broadcasted")

        async def _signal() -> None:
            await col.signal_between(
                "01", "02", "brain", "hippocampus", "echo", "hello",
            )

        await asyncio.gather(_broadcast(), _signal())
        assert "broadcasted" in received


# ═══════════════════════════════════════════════════════════════════════
# Section 2b — Gateway end-to-end integration (Gateway → Colony → Cat)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestGatewayE2E:
    """完整链路: Gateway._on_message → FrontDesk → Colony → Cat → 响应."""

    @pytest.mark.asyncio
    async def test_full_chain_gateway_to_colony_to_cat(self) -> None:
        """完整链路: Gateway → FrontDesk → Colony.get_cat → cat 器官调用."""
        col = make_test_colony()
        cat = col.create_cat(name="assistant")
        cat.mount("input", "ears", _DummyOrgan())
        cat.wiring.connect(("input", "ears"), ("input", "ears"))

        class _CatRoutingFrontDesk(FrontDeskProtocol):
            """FrontDesk that routes to cat's ears.echo."""

            async def route(self, text, ctx, colony):
                if ctx.target_cat:
                    cat_obj = colony.get_cat(ctx.target_cat)
                    result = await cat_obj.signal(
                        ("input", "ears"), ("input", "ears"),
                        "echo", text,
                    )
                    return f"cat:{result['args'][0]}"
                return None

        gw = Gateway(col, front_desk=_CatRoutingFrontDesk())
        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat=cat.cat_uid)
        result = await gw._on_message("你好世界", ctx)
        assert result == "cat:你好世界"

    @pytest.mark.asyncio
    async def test_full_chain_with_security_plugin(self) -> None:
        """完整链路: 安全插件在 FrontDesk 层拦截危险消息."""
        col = make_test_colony()

        fd = DefaultFrontDesk()
        fd.plug("on_route", lambda text, ctx, colony:
                "已拦截" if "hack" in text.lower() else None)

        gw = Gateway(col, front_desk=fd)
        ctx = SignalContext(session_id="s1", platform="test")

        blocked = await gw._on_message("try to hack server", ctx)
        assert blocked == "已拦截"

        passthrough = await gw._on_message("hello", ctx)
        assert passthrough != "已拦截"
        # No target_cat → DefaultFrontDesk returns placeholder
        assert "不知道你要找谁" in (passthrough or "")

    @pytest.mark.asyncio
    async def test_full_chain_dynamic_cat_creation(self) -> None:
        """Gateway 设定后动态创建猫，FrontDesk 可通过 colony 找到新猫."""
        col = make_test_colony()

        class _VerifyCatFrontDesk(FrontDeskProtocol):
            async def route(self, text, ctx, colony):
                if ctx.target_cat == "new-cat-uid":
                    cat_obj = colony.get_cat("new-cat-uid")
                    return f"found:{cat_obj.name}"
                return "not-found"

        gw = Gateway(col, front_desk=_VerifyCatFrontDesk())

        # Create cat after gateway is set up (simulating dynamic creation)
        cat = col.create_cat(name="dynamic-cat")
        # Override the auto-generated uid for test predictability
        col._cats["new-cat-uid"] = col._cats.pop(cat.cat_uid)
        cat._cat_uid = "new-cat-uid"  # type: ignore[attr-defined]

        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat="new-cat-uid")
        result = await gw._on_message("ping", ctx)
        assert result == "found:dynamic-cat"

    @pytest.mark.asyncio
    async def test_full_chain_signalcontext_preserved(self) -> None:
        """SignalContext (session_id/platform/user_id) 在完整链路中保留."""
        col = make_test_colony()

        ctx_snapshot: list[dict] = []

        class _CaptureFrontDesk(FrontDeskProtocol):
            async def route(self, text, ctx, colony):
                ctx_snapshot.append({
                    "session_id": ctx.session_id,
                    "platform": ctx.platform,
                    "user_id": ctx.user_id,
                    "target_cat": ctx.target_cat,
                    "text": text,
                })
                return "ok"

        gw = Gateway(col, front_desk=_CaptureFrontDesk())
        ctx = SignalContext(
            session_id="sess-123", platform="slack",
            user_id="U001", target_cat="cat-01",
        )
        result = await gw._on_message("test message", ctx)
        assert result == "ok"
        assert len(ctx_snapshot) == 1
        assert ctx_snapshot[0]["session_id"] == "sess-123"
        assert ctx_snapshot[0]["platform"] == "slack"
        assert ctx_snapshot[0]["user_id"] == "U001"
        assert ctx_snapshot[0]["target_cat"] == "cat-01"
        assert ctx_snapshot[0]["text"] == "test message"


# ═══════════════════════════════════════════════════════════════════════
# Section 3 — Gateway integration
# ═══════════════════════════════════════════════════════════════════════


class _MockAdapter(IoAdapterProtocol):
    """Mock adapter that records serve/stop calls."""

    def __init__(self, name: str = "mock", should_fail: bool = False, serve_sleep: float = 0.1) -> None:
        self.name = name
        self.should_fail = should_fail
        self.serve_sleep = serve_sleep
        self.serve_calls: list[tuple] = []
        self.stop_called = False
        self._serve_event = asyncio.Event()

    async def serve(self, on_message, on_stream) -> None:
        self.serve_calls.append(
            ("serve", on_message is not None, on_stream is not None))
        # Signal ready, then wait until stop is called
        self._serve_event.set()
        if self.should_fail:
            raise RuntimeError("adapter failure")
        # keep alive until stopped externally
        await asyncio.sleep(self.serve_sleep)

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        pass

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        pass

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        pass

    async def stop(self) -> None:
        self.stop_called = True


class _CustomFrontDesk(FrontDeskProtocol):
    """Custom FrontDesk for testing."""

    async def route(self, text: str, ctx: SignalContext, colony: Any) -> str | None:
        return f"custom:{text}"


# -- Gateway construction / adapter management --------------------------


@pytest.mark.anyio
class TestGatewayConstruction:
    """Gateway construction and adapter management."""

    def test_default_construction(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        assert gw.colony is col
        assert isinstance(gw.front_desk, DefaultFrontDesk)

    def test_custom_front_desk(self) -> None:
        col = make_test_colony()
        fd = _CustomFrontDesk()
        gw = Gateway(col, front_desk=fd)
        assert gw.front_desk is fd

    def test_mount_unmount_adapter(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        adapter = _MockAdapter("test")
        gw.mount_adapter(adapter)
        assert gw.adapter_names == ["test"]
        gw.mount_adapter(_MockAdapter("test"))  # overwrite
        assert gw.adapter_names == ["test"]
        gw.unmount_adapter("test")
        assert gw.adapter_names == []

    def test_unmount_nonexistent_adapter(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        gw.unmount_adapter("nonexistent")  # no-op, no error

    def test_adapter_names(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        assert gw.adapter_names == []
        gw.mount_adapter(_MockAdapter("a"))
        gw.mount_adapter(_MockAdapter("b"))
        assert sorted(gw.adapter_names) == ["a", "b"]


@pytest.mark.anyio
class TestGatewayLifecycle:
    """Gateway start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_no_adapters_returns_immediately(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        await gw.start()  # No error, instant return

    @pytest.mark.asyncio
    async def test_start_with_one_adapter(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        adapter = _MockAdapter("mock", serve_sleep=2.0)
        gw.mount_adapter(adapter)

        # Start with timeout via gather → serve() will be called
        async def _start_with_timeout():
            await asyncio.wait_for(gw.start(), timeout=0.3)
        with pytest.raises(asyncio.TimeoutError):
            await _start_with_timeout()
        assert len(adapter.serve_calls) == 1  # serve() was called

    @pytest.mark.asyncio
    async def test_stop_calls_all_adapters(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        a1 = _MockAdapter("a1")
        a2 = _MockAdapter("a2")
        gw.mount_adapter(a1)
        gw.mount_adapter(a2)
        await gw.stop()
        assert a1.stop_called
        assert a2.stop_called

    @pytest.mark.asyncio
    async def test_adapter_failure_propagates(self) -> None:
        col = make_test_colony()
        gw = Gateway(col)
        gw.mount_adapter(_MockAdapter("failing", should_fail=True))
        with pytest.raises(RuntimeError, match="adapter failure"):
            await gw.start()


class _CerebrumOutputStage(BaseStage):
    """Custom stage that calls the cerebrum and yields output events."""

    async def run(self, ctx: Any) -> AsyncIterator[StageEvent]:
        cat = ctx.cat
        if cat is not None and hasattr(cat, "cerebrum"):
            response = await cat.cerebrum.generate(str(ctx.input))
            yield StageEvent.output(response)


@pytest.mark.anyio
class TestFrontDeskRouting:
    """FrontDesk plugin chain and routing."""

    @pytest.mark.asyncio
    async def test_plugin_chain_first_hit(self) -> None:
        fd = DefaultFrontDesk()
        fd.plug("on_route", lambda text, ctx, colony: "first_hit")
        fd.plug("on_route", lambda text, ctx, colony: "never_returned")
        col = make_test_colony()
        ctx = SignalContext(session_id="s1", platform="test")
        result = await fd.route("hello", ctx, col)
        assert result == "first_hit"

    @pytest.mark.asyncio
    async def test_plugin_returns_none_passes_through(self) -> None:
        fd = DefaultFrontDesk()
        fd.plug("on_route", lambda text, ctx, colony: None)
        col = make_test_colony()
        cerebrum = _SimpleCerebrum()
        cerebrum._response = "passed through"  # type: ignore[attr-defined]
        reflex = Reflex(
            name="text_dialogue",
            trigger=lambda x: isinstance(x, str),
            path=BUILTIN_REFLEX_PATHS["text_dialogue"],
            stages=[_CerebrumOutputStage()],
        )
        cat = create_cat(name="test-cat", container=col,
                         cerebrum=cerebrum, reflexes=[reflex])
        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat=cat.cat_uid)
        result = await fd.route("hi", ctx, col)
        assert result == "passed through"  # passed through to cat

    @pytest.mark.asyncio
    async def test_route_to_target_cat(self) -> None:
        col = make_test_colony()
        cerebrum = _SimpleCerebrum()
        cerebrum._response = "hello from cat"  # type: ignore[attr-defined]
        reflex = Reflex(
            name="text_dialogue",
            trigger=lambda x: isinstance(x, str),
            path=BUILTIN_REFLEX_PATHS["text_dialogue"],
            stages=[_CerebrumOutputStage()],
        )
        cat = create_cat(name="test-cat", container=col,
                         cerebrum=cerebrum, reflexes=[reflex])
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat=cat.cat_uid)
        result = await fd.route("hello", ctx, col)
        assert result == "hello from cat"

    @pytest.mark.asyncio
    async def test_route_unknown_cat(self) -> None:
        col = make_test_colony()
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat="nonexistent")
        result = await fd.route("hello", ctx, col)
        assert "找不到猫" in (result or "")

    @pytest.mark.asyncio
    async def test_route_no_target_cat(self) -> None:
        col = make_test_colony()
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s1", platform="test")  # no target_cat
        result = await fd.route("hello", ctx, col)
        assert "不知道你要找谁" in (result or "")

    @pytest.mark.asyncio
    async def test_route_plugin_blocks_message(self) -> None:
        col = make_test_colony()
        fd = DefaultFrontDesk()

        def security(text, ctx, colony):
            if "DROP" in text.upper():
                return "已拦截危险操作"
            return None

        fd.plug("on_route", security)
        ctx = SignalContext(session_id="s1", platform="test", target_cat="01")
        result = await fd.route("DROP TABLE users", ctx, col)
        assert result == "已拦截危险操作"

    @pytest.mark.asyncio
    async def test_route_empty_text(self) -> None:
        col = make_test_colony()
        cerebrum = _SimpleCerebrum()
        cerebrum._response = "ok"  # type: ignore[attr-defined]
        reflex = Reflex(
            name="text_dialogue",
            trigger=lambda x: isinstance(x, str),
            path=BUILTIN_REFLEX_PATHS["text_dialogue"],
            stages=[_CerebrumOutputStage()],
        )
        cat = create_cat(name="test-cat", container=col,
                         cerebrum=cerebrum, reflexes=[reflex])
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s1", platform="test",
                            target_cat=cat.cat_uid)
        result = await fd.route("", ctx, col)
        # Empty text should still be handled (not crash)
        assert result == "ok"


@pytest.mark.anyio
class TestGatewayOnMessage:
    """Gateway._on_message / _on_stream delegation."""

    @pytest.mark.asyncio
    async def test_on_message_delegates_to_front_desk(self) -> None:
        col = make_test_colony()
        fd = _CustomFrontDesk()
        gw = Gateway(col, front_desk=fd)
        ctx = SignalContext(session_id="s1", platform="test")
        result = await gw._on_message("test message", ctx)
        assert result == "custom:test message"

    @pytest.mark.asyncio
    async def test_on_stream_wraps_reply(self) -> None:
        col = make_test_colony()
        fd = _CustomFrontDesk()
        gw = Gateway(col, front_desk=fd)
        ctx = SignalContext(session_id="s1", platform="test")
        result = await gw._on_stream("stream test", ctx)
        assert result is not None
        chunks = [chunk async for chunk in result]
        assert chunks == ["custom:stream test"]

    @pytest.mark.asyncio
    async def test_on_stream_returns_none_for_null_reply(self) -> None:
        col = make_test_colony()

        class _NullFrontDesk(FrontDeskProtocol):
            async def route(self, text, ctx, colony):
                return None

        gw = Gateway(col, front_desk=_NullFrontDesk())
        ctx = SignalContext(session_id="s1", platform="test")
        result = await gw._on_stream("hello", ctx)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# Section 4 — do_task e2e
# ═══════════════════════════════════════════════════════════════════════


class _SimpleCerebrum:
    """Minimal cerebrum that returns a fixed response."""

    name = "simple"

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        # Store the prompt for assertions (ignored)
        self.last_prompt = prompt  # type: ignore[attr-defined]
        return self._response  # type: ignore[attr-defined]

    async def stream_generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        yield self._response  # type: ignore[attr-defined]

    def reload_config(self):
        pass


class _MultiStepCerebrum:
    """Cerebrum that returns different responses per round."""

    name = "multi"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_idx = 0

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        idx = self.call_idx
        self.call_idx += 1
        if idx < len(self.responses):
            return self.responses[idx]
        return "default response"

    async def stream_generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=None):
        idx = self.call_idx
        self.call_idx += 1
        if idx < len(self.responses):
            yield self.responses[idx]
        else:
            yield "default response"

    def reload_config(self):
        pass


class _SafeAmygdala:
    """Amygdala that returns risk assessment."""

    def __init__(self, risk_level: str = "none") -> None:
        self.risk_level = risk_level

    async def assess_safety(self, user_input):
        return {"safe": self.risk_level != "high", "risk": self.risk_level}


class _FakeToolHandler:
    """Call-counting tool handler."""

    def __init__(self, result: dict | None = None) -> None:
        self.result = result or {"output": "done"}
        self.calls: list[dict] = []

    def __call__(self, **kw: Any) -> dict:
        self.calls.append(kw)
        return self.result


@pytest.mark.anyio
class TestDoTaskE2E:
    """End-to-end do_task tests — safety, tool errors, multi-round."""

    def _cat_with_cerebrum(self, cerebrum, name: str = "test-cat",
                           risk_level: str = "none"):
        col = make_test_colony(f"dotask_{name}")
        cat = create_cat(name=name, container=col, cerebrum=cerebrum)
        # Replace amygdala for controlled safety checks
        cat.mount("brain", "amygdala", _SafeAmygdala(risk_level))
        return cat

    @pytest.mark.asyncio
    async def test_safety_high_risk_tool_rejected(self) -> None:
        """工具被安全策略拒绝后，继续尝试其他方法。"""
        cerebrum = _MultiStepCerebrum([
            '<tool name="dangerous"><param name="cmd">rm -rf /</param></tool>',
            '<tool name="safe_echo"><param name="msg">hello</param></tool>',
            "任务完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "safety", risk_level="high")

        handler = _FakeToolHandler({"output": "echo: hello"})
        cat.tool_registry.register(
            Tool(ToolSpec(name="dangerous", description="危险工具"), handler=handler))
        cat.tool_registry.register(
            Tool(ToolSpec(name="safe_echo", description="安全工具"), handler=handler))

        result = await cat.do_task("做点危险的事", max_rounds=5)
        assert isinstance(result, DoTaskResult)
        assert result.rounds >= 2  # dangerous rejected, safe_echo executed, then done
        # dangerous should not have been called
        for tc in result.tool_calls:
            assert tc.name != "dangerous"

    @pytest.mark.asyncio
    async def test_tool_not_found_returns_error_response(self) -> None:
        """工具未注册时，do_task 将错误信息反馈给 cerebrum 重新推理。"""
        cerebrum = _MultiStepCerebrum([
            '<tool name="unknown_tool"><param name="x">1</param></tool>',
            "无法使用工具，任务回退到手动完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "missing_tool")
        # No tools registered
        result = await cat.do_task("做某事", max_rounds=5)
        assert isinstance(result, DoTaskResult)
        # Tool not found → error output fed back → cerebrum retries
        assert result.rounds >= 2

    @pytest.mark.asyncio
    async def test_multi_round_multiple_different_tools(self) -> None:
        """多轮调用不同工具链。"""
        cerebrum = _MultiStepCerebrum([
            '<tool name="step1"><param name="a">1</param></tool>',
            '<tool name="step2"><param name="b">2</param></tool>',
            '<tool name="step3"><param name="c">3</param></tool>',
            "全部完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "chain")
        for name in ["step1", "step2", "step3"]:
            cat.tool_registry.register(Tool(
                ToolSpec(name=name, description=f"step {name}"),
                handler=_FakeToolHandler({"output": f"{name}_output"}),
            ))
        result = await cat.do_task("多步操作", max_rounds=10)
        assert result.rounds == 4
        assert len(result.tool_calls) == 3
        assert [tc.name for tc in result.tool_calls] == [
            "step1", "step2", "step3"]

    @pytest.mark.asyncio
    async def test_max_rounds_exhaustion_returns_last_output(self) -> None:
        """max_rounds 耗尽时返回最后一轮的 cerebrum 输出。"""
        cerebrum = _MultiStepCerebrum(
            ['<tool name="loop"><param name="n">1</param></tool>'] * 20
        )
        cat = self._cat_with_cerebrum(cerebrum, "exhaust")
        cat.tool_registry.register(Tool(
            ToolSpec(name="loop", description="looping tool"),
            handler=_FakeToolHandler({"output": "looped"}),
        ))
        result = await cat.do_task("无限循环任务", max_rounds=3)
        assert result.rounds == 3
        assert len(result.tool_calls) == 3
        assert result.final_text != ""  # last cerebrum output used

    @pytest.mark.asyncio
    async def test_do_task_result_shape(self) -> None:
        """DoTaskResult 结构验证。"""
        cerebrum = _SimpleCerebrum()
        cerebrum._response = "没有工具调用，直接完成"  # type: ignore[attr-defined]
        cat = self._cat_with_cerebrum(cerebrum, "shape")
        result = await cat.do_task("简单任务")
        assert isinstance(result, DoTaskResult)
        assert result.final_text == "没有工具调用，直接完成"
        assert result.rounds == 1
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_tool_params_passed_correctly(self) -> None:
        """验证工具参数正确传递给 handler。"""
        cerebrum = _MultiStepCerebrum([
            '<tool name="calculator"><param name="expr">2+3</param><param name="precision">2</param></tool>',
            "结果是 5",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "params")
        handler = _FakeToolHandler({"output": "5.00"})
        cat.tool_registry.register(Tool(
            ToolSpec(name="calculator", description="计算器"), handler=handler,
        ))
        result = await cat.do_task("计算 2+3", max_rounds=5)
        assert result.rounds == 2
        tc = result.tool_calls[0]
        assert tc.name == "calculator"
        assert tc.params["expr"] == "2+3"
        assert tc.params["precision"] == "2"  # XML parser stores strings

    @pytest.mark.asyncio
    async def test_custom_parser(self) -> None:
        """自定义解析器的 do_task 测试。"""

        class _SimpleParser:
            def extract(self, text: str):
                if "TOOL:" in text:
                    parts = text.split("\n", 1)
                    name_line = parts[0].replace("TOOL:", "").strip()
                    params_str = parts[1] if len(parts) > 1 else ""
                    params = {}
                    for line in params_str.split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            params[k.strip()] = v.strip()
                    from meowcat.tools.tool_call import ToolCall
                    return ToolCall(name=name_line, params=params)
                return None

        cerebrum = _MultiStepCerebrum([
            "TOOL:echo\nmsg: hello\nuser: test",
            "任务完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "custom_parser")
        cat.tool_registry.register(Tool(
            ToolSpec(name="echo", description="echo"),
            handler=_FakeToolHandler({"output": "echo: hello"}),
        ))
        result = await cat.do_task("解析测试", max_rounds=5, parser=_SimpleParser())
        assert result.rounds == 2
        assert result.tool_calls[0].name == "echo"
        assert result.tool_calls[0].params["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_safe_tool_allowed_when_risk_none(self) -> None:
        """低风险工具正常执行。"""
        cerebrum = _MultiStepCerebrum([
            '<tool name="read"><param name="file">test.txt</param></tool>',
            "文件内容: hello world",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "safe", risk_level="none")
        cat.tool_registry.register(Tool(
            ToolSpec(name="read", description="read file"),
            handler=_FakeToolHandler({"output": "hello world"}),
        ))
        result = await cat.do_task("读取文件", max_rounds=5)
        assert result.rounds == 2
        assert result.tool_calls[0].name == "read"

    @pytest.mark.asyncio
    async def test_do_task_accepts_timeout_parameter(self) -> None:
        """do_task 接受 timeout 参数且不影响正常执行."""
        cerebrum = _SimpleCerebrum()
        cerebrum._response = "直接完成，无需工具"  # type: ignore[attr-defined]
        cat = self._cat_with_cerebrum(cerebrum, "timeout_param")
        # timeout parameter should be accepted without error
        result = await cat.do_task("简单任务", timeout=1.0)
        assert isinstance(result, DoTaskResult)
        assert result.final_text == "直接完成，无需工具"
        # Also test with timeout=None
        result2 = await cat.do_task("简单任务", timeout=None)
        assert isinstance(result2, DoTaskResult)
        assert result2.final_text == "直接完成，无需工具"
