# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.3.0 — Signal error propagation and error type tests.

Coverage:
  * Signal error propagation (IllegalNeuralPathError, CircuitOpenError, organ exception)
  * Middleware error handling (before/after/on_error chain)
  * signal_between error paths and timeout
  * Error class construction (MeowCatError, IllegalNeuralPathError, CircuitOpenError, StageTimeoutError)
"""

from __future__ import annotations

import asyncio

import pytest

from meowcat.assembly import CatBase
from meowcat.errors import (
    CircuitOpenError,
    IllegalNeuralPathError,
    MeowCatError,
    OrganNotMountedError,
    StageTimeoutError,
)
from meowcat.nervous import Nervous
from meowcat.testing import make_cat
from meowcat.wiring import Organ
from tests.conftest import DummyOrgan, make_colony


# ═══════════════════════════════════════════════════════════════════════
# Local helpers (not shared)
# ═══════════════════════════════════════════════════════════════════════


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
    cat.mount("brain", "a", DummyOrgan())
    cat.mount("brain", "b", DummyOrgan())
    for frm, to in connections:
        cat.wiring.connect(frm, to)
    return cat


# ═══════════════════════════════════════════════════════════════════════
# TestSignalErrorPropagation
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
        cat.mount("brain", "c", DummyOrgan())
        cat.mount("brain", "d", DummyOrgan())
        with pytest.raises(IllegalNeuralPathError, match="not connected"):
            await cat.signal(("brain", "c"), ("brain", "d"), "echo")

    @pytest.mark.asyncio
    async def test_organ_not_mounted_raises_organ_not_mounted(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", DummyOrgan())
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
        cat.mount("brain", "a", DummyOrgan())
        cat.mount("brain", "b", DummyOrgan())
        cat.wiring.connect(("brain", "a"), ("brain", "b"))
        with pytest.raises(ValueError, match="intentional organ failure"):
            await cat.signal(("brain", "a"), ("brain", "b"), "fail")

    @pytest.mark.asyncio
    async def test_async_organ_exception_propagates(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "a", DummyOrgan())
        cat.mount("brain", "b", DummyOrgan())
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
        cat.mount("brain", "a", DummyOrgan())
        cat.mount("brain", "b", DummyOrgan())
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

        nervous = Nervous(host, events, circuit_breaker=True,
                          cb_threshold=2, cb_timeout=10.0)

        host.mount("brain", "a", DummyOrgan())
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
        col = make_colony(("a", "a"), ("b", "b"), allow_all=True)
        with pytest.raises(OrganNotMountedError):
            await col.signal_between("01", "02", "brain", "nonexistent", "locate")

    @pytest.mark.asyncio
    async def test_signal_between_cross_wiring_rejected_with_detail(self) -> None:
        col = make_colony(("a", "a"), ("b", "b"))
        col.forbid_cross("01", "02")
        with pytest.raises(IllegalNeuralPathError, match="forbidden.*01.*02"):
            await col.signal_between("01", "02", "brain", "hippocampus", "echo")

    @pytest.mark.asyncio
    async def test_signal_between_default_deny_unconfigured(self) -> None:
        col = make_colony(("a", "a"), ("b", "b"))
        with pytest.raises(IllegalNeuralPathError, match="not allowed"):
            await col.signal_between("01", "02", "brain", "hippocampus", "echo")

    @pytest.mark.asyncio
    async def test_signal_between_unknown_cat_raises_keyerror(self) -> None:
        col = make_colony(("a", "a"))
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
        err = CircuitOpenError(("brain", "x"), "act",
                               failures=3, retry_after=5.0)
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
        col = make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", DummyOrgan())
        result = await col.signal_between(
            "01", "02", "brain", "hippocampus", "async_echo", "hello", timeout=None,
        )
        assert result == {"args": ("hello",), "kwargs": {}}

    @pytest.mark.asyncio
    async def test_signal_between_timeout_expires(self) -> None:
        """signal_between with short timeout raises asyncio.TimeoutError."""

        class _SlowOrgan:
            async def slow(self) -> str:
                await asyncio.sleep(1.0)
                return "done"

        col = make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", _SlowOrgan())
        with pytest.raises(asyncio.TimeoutError):
            await col.signal_between(
                "01", "02", "brain", "hippocampus", "slow", timeout=0.05,
            )

    @pytest.mark.asyncio
    async def test_signal_between_sync_method_completes_fast(self) -> None:
        """signal_between with sync method returns immediately regardless of timeout."""
        col = make_colony(("a", "a"), ("b", "b"), allow_all=True)
        cat_b = col.get_cat("02")
        cat_b.mount("brain", "hippocampus", DummyOrgan())
        result = await col.signal_between(
            "01", "02", "brain", "hippocampus", "echo", "quick", timeout=5.0,
        )
        assert result == {"args": ("quick",), "kwargs": {}}
