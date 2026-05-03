"""meowcat v1.0.13 — Signal Middleware 测试。

覆盖:
- SignalCall 数据形状
- 零中间件时 signal 行为不变
- before 短路机制
- before → after 正常链式调用
- on_error 通知 + 异常传播
- after 修改返回值
- 多中间件按注册顺序执行
- 4 个内置中间件 (SignalLogger / RateLimiter / TimeoutGuard / ContextInjector)
- enable_wiring=False 时 use_middleware 报错
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pytest

from meowcat import (
    CatBase,
    ContextInjector,
    IllegalNeuralPathError,
    RateLimiter,
    SignalCall,
    SignalLogger,
    TimeoutGuard,
)
from meowcat.nervous import SignalMiddleware


# -- 测试辅助 --------------------------------------------------------

class _DummyOrgan:
    """用于 signal 测试的最小器官。"""

    def echo(self, *args: Any, **kwargs: Any) -> Any:
        return {"args": args, "kwargs": kwargs}

    async def async_echo(self, *args: Any, **kwargs: Any) -> Any:
        return {"args": args, "kwargs": kwargs}

    def fail(self) -> None:
        raise ValueError("intentional failure")


def _new_cat() -> CatBase:
    """准备好 wiring 的猫：a→b 连通。"""
    cat = CatBase("test")
    cat.wiring.connect(("brain", "a"), ("brain", "b"))
    return cat


# -- 1. SignalCall 数据形状 -----------------------------------------

class TestSignalCall:
    """SignalCall 不可变上下文。"""

    def test_signal_call_attributes(self) -> None:
        ctx = SignalCall(
            from_organ=("brain", "a"),
            to_organ=("brain", "b"),
            method="echo",
            args=("hello",),
            kwargs={"key": "val"},
            timestamp=100.0,
        )
        assert ctx.from_organ == ("brain", "a")
        assert ctx.to_organ == ("brain", "b")
        assert ctx.method == "echo"
        assert ctx.args == ("hello",)
        assert ctx.kwargs == {"key": "val"}
        assert ctx.timestamp == 100.0

    def test_signal_call_defaults(self) -> None:
        ctx = SignalCall(
            from_organ=("brain", "a"),
            to_organ=("brain", "b"),
            method="ping",
            args=(),
        )
        assert ctx.kwargs == {}
        assert ctx.timestamp > 0  # 自动填充时间戳

    def test_signal_call_is_frozen(self) -> None:
        ctx = SignalCall(
            from_organ=("brain", "a"),
            to_organ=("brain", "b"),
            method="ping",
            args=(),
        )
        with pytest.raises(Exception):  # dataclass frozen
            ctx.method = "other"  # type: ignore[misc]


# -- 2. 零中间件 — 行为不变 -----------------------------------------


class TestZeroMiddleware:
    """无中间件时 signal 行为不变。"""

    def test_signal_no_middleware(self) -> None:
        import anyio

        cat = _new_cat()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result == {"args": ("hello",), "kwargs": {}}

        anyio.run(_run)

    def test_signal_no_middleware_async(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "async_echo", 42,
            )
            assert result == {"args": (42,), "kwargs": {}}

        anyio.run(_run)


# -- 3. before 短路 -------------------------------------------------


class TestBeforeShortCircuit:
    """before 返回 None 则短路。"""

    def test_before_short_circuit(self) -> None:
        import anyio

        cat = _new_cat()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)

        class _ShortCircuitMW:
            async def before(self, ctx: SignalCall) -> SignalCall | None:
                return None

        cat.use_middleware(_ShortCircuitMW())

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result is None
            # 目标方法未被调用
            assert organ.calls == []

        anyio.run(_run)

    def test_before_pass_through(self) -> None:
        import anyio

        cat = _new_cat()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)

        class _PassMW:
            async def before(self, ctx: SignalCall) -> SignalCall | None:
                return ctx

        cat.use_middleware(_PassMW())

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result == {"args": ("hello",), "kwargs": {}}

        anyio.run(_run)


# -- 4. after 修改返回值 ---------------------------------------------


class TestAfterModify:
    """after 可修改/包装返回值。"""

    def test_after_wraps_result(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())

        class _WrapMW:
            async def after(self, ctx: SignalCall, result: Any) -> Any:
                return {"wrapped": result}

        cat.use_middleware(_WrapMW())

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result == {"wrapped": {"args": ("hello",), "kwargs": {}}}

        anyio.run(_run)


# -- 5. on_error 通知 + 异常传播 ------------------------------------


class TestOnError:
    """on_error 通知后异常继续传播。"""

    def test_on_error_notified_and_exception_propagates(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())

        errors_seen: list[Exception] = []

        class _ErrMW:
            async def on_error(self, ctx: SignalCall, error: Exception) -> None:
                errors_seen.append(error)

        cat.use_middleware(_ErrMW())

        async def _run() -> None:
            with pytest.raises(ValueError, match="intentional"):
                await cat.signal(
                    ("brain", "a"), ("brain", "b"), "fail",
                )

        anyio.run(_run)
        assert len(errors_seen) == 1
        assert isinstance(errors_seen[0], ValueError)


# -- 6. 多个中间件按注册顺序执行 -------------------------------------


class TestMultiMiddleware:
    """多中间件按注册顺序执行。"""

    def test_multi_middleware_order(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())

        log: list[str] = []

        class _MW1:
            async def before(self, ctx: SignalCall) -> SignalCall | None:
                log.append("mw1_before")
                return ctx

            async def after(self, ctx: SignalCall, result: Any) -> Any:
                log.append("mw1_after")
                return result

        class _MW2:
            async def before(self, ctx: SignalCall) -> SignalCall | None:
                log.append("mw2_before")
                return ctx

            async def after(self, ctx: SignalCall, result: Any) -> Any:
                log.append("mw2_after")
                return result

        cat.use_middleware(_MW1())
        cat.use_middleware(_MW2())

        async def _run() -> None:
            await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )

        anyio.run(_run)
        assert log == [
            "mw1_before", "mw2_before",
            "mw1_after", "mw2_after",
        ]


# -- 7. 内置中间件: SignalLogger ------------------------------------


class TestSignalLogger:
    """SignalLogger 记录日志。"""

    def test_signal_logger_logs_after(self, caplog: pytest.LogCaptureFixture) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())
        cat.use_middleware(SignalLogger())

        async def _run() -> None:
            await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )

        with caplog.at_level(logging.DEBUG, logger="meowcat.signal"):
            anyio.run(_run)

        assert any("signal" in r.message for r in caplog.records)
        assert any("echo" in r.message for r in caplog.records)


# -- 8. 内置中间件: RateLimiter -------------------------------------


class TestRateLimiter:
    """RateLimiter 限流。"""

    def test_rate_limiter_allows_within_limit(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())
        cat.use_middleware(RateLimiter(max_calls=10, window_seconds=1.0))

        async def _run() -> None:
            for _ in range(5):
                result = await cat.signal(
                    ("brain", "a"), ("brain", "b"), "echo", "hello",
                )
                assert result is not None

        anyio.run(_run)

    def test_rate_limiter_blocks_after_limit(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())
        cat.use_middleware(RateLimiter(max_calls=2, window_seconds=1.0))

        results: list[Any] = []

        async def _run() -> None:
            for _ in range(5):
                r = await cat.signal(
                    ("brain", "a"), ("brain", "b"), "echo", "hello",
                )
                results.append(r)

        anyio.run(_run)
        # 前 2 个通过，后 3 个被限流返回 None
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 2
        assert results[2] is None
        assert results[3] is None
        assert results[4] is None


# -- 9. 内置中间件: TimeoutGuard ------------------------------------


class TestTimeoutGuard:
    """TimeoutGuard 超时 abort。"""

    def test_timeout_guard_passes_before_deadline(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())
        # 30 秒后超时 — 肯定在截止前
        cat.use_middleware(TimeoutGuard(deadline=time.monotonic() + 30))

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result is not None

        anyio.run(_run)

    def test_timeout_guard_blocks_after_deadline(self) -> None:
        import anyio

        cat = _new_cat()
        cat.mount("brain", "b", _DummyOrgan())
        # 已经过期的 deadline
        cat.use_middleware(TimeoutGuard(deadline=time.monotonic() - 1))

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result is None

        anyio.run(_run)


# -- 10. 内置中间件: ContextInjector --------------------------------


class TestContextInjector:
    """ContextInjector 注入上下文。"""

    def test_context_injector_adds_to_kwargs(self) -> None:
        import anyio

        cat = _new_cat()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)
        cat.use_middleware(ContextInjector(
            inject={"session_id": "test-001", "platform": "cli"},
        ))

        async def _run() -> None:
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
            )
            assert result["kwargs"]["session_id"] == "test-001"
            assert result["kwargs"]["platform"] == "cli"

        anyio.run(_run)

    def test_context_injector_does_not_overwrite_existing(self) -> None:
        import anyio

        cat = _new_cat()
        organ = _DummyOrgan()
        cat.mount("brain", "b", organ)
        cat.use_middleware(ContextInjector(
            inject={"session_id": "injected"},
        ))

        async def _run() -> None:
            # 调用方显式传了 session_id — 不应被覆盖
            result = await cat.signal(
                ("brain", "a"), ("brain", "b"), "echo", "hello",
                session_id="explicit",
            )
            assert result["kwargs"]["session_id"] == "explicit"

        anyio.run(_run)


# -- 11. 边界条件 ---------------------------------------------------


class TestEdgeCases:
    """边界条件测试。"""

    def test_use_middleware_with_wiring_disabled(self) -> None:
        cat = CatBase("test", enable_wiring=False)
        with pytest.raises(RuntimeError, match="middleware unavailable"):
            cat.use_middleware(SignalLogger())

    def test_signal_still_checks_wiring_before_middleware(self) -> None:
        """中间件不绕过 wiring 校验。"""
        import anyio

        cat = CatBase("test")
        cat.mount("brain", "b", _DummyOrgan())
        cat.use_middleware(SignalLogger())

        async def _run() -> None:
            with pytest.raises(IllegalNeuralPathError):
                await cat.signal(
                    ("brain", "a"), ("brain", "b"), "echo",
                )

        anyio.run(_run)
