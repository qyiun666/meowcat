# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat v1.0.14 — Cat Lifecycle Hooks 测试。

覆盖:
- on_start hook 在 start() 时被调用
- on_shutdown hook 在 shutdown() 时被调用
- 多 on_start hooks 按注册顺序执行
- 多 on_shutdown hooks 按注册逆序执行
- start() 先发射 lifecycle.start 事件再调 hooks
- shutdown() 先调 hooks 再发射 lifecycle.shutdown 事件
- 无 hooks 时 start/shutdown 行为不变（向后兼容）
- hook 接收正确的 CatBase 实例
- on_start + on_shutdown 组合完整生命周期
"""

from __future__ import annotations

import anyio
import pytest

from meowcat.testing import make_cat
from meowcat import CatBase, CatHook, Lifecycle


# -- 1. on_start hook -------------------------------------------------

class TestOnStart:
    """on_start hook 在 start() 时被调用。"""

    def test_single_on_start_hook_called(self) -> None:
        cat = make_cat("test")
        hooks_called: list[str] = []

        def _my_hook(c: CatBase) -> None:
            hooks_called.append(c.name)

        cat.on_start(_my_hook)

        async def _run() -> None:
            await cat.start()

        anyio.run(_run)
        assert hooks_called == ["test"]

    def test_on_start_hook_receives_correct_cat(self) -> None:
        cat = make_cat("test")
        received: list[CatBase] = []

        def _my_hook(c: CatBase) -> None:
            received.append(c)

        cat.on_start(_my_hook)

        async def _run() -> None:
            await cat.start()

        anyio.run(_run)
        assert len(received) == 1
        assert received[0] is cat


# -- 2. on_shutdown hook ----------------------------------------------

class TestOnShutdown:
    """on_shutdown hook 在 shutdown() 时被调用。"""

    def test_single_on_shutdown_hook_called(self) -> None:
        cat = make_cat("test")
        hooks_called: list[str] = []

        def _my_hook(c: CatBase) -> None:
            hooks_called.append(c.name)

        cat.on_shutdown(_my_hook)

        async def _run() -> None:
            await cat.shutdown()

        anyio.run(_run)
        assert hooks_called == ["test"]

    def test_on_shutdown_hook_receives_correct_cat(self) -> None:
        cat = make_cat("test")
        received: list[CatBase] = []

        def _my_hook(c: CatBase) -> None:
            received.append(c)

        cat.on_shutdown(_my_hook)

        async def _run() -> None:
            await cat.shutdown()

        anyio.run(_run)
        assert len(received) == 1
        assert received[0] is cat


# -- 3. 多 hooks 执行顺序 ---------------------------------------------

class TestHookOrder:
    """多 hooks 按正确顺序执行。"""

    def test_multiple_start_hooks_ordered(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        def _h1(c: CatBase) -> None:
            log.append("h1")

        def _h2(c: CatBase) -> None:
            log.append("h2")

        def _h3(c: CatBase) -> None:
            log.append("h3")

        cat.on_start(_h1)
        cat.on_start(_h2)
        cat.on_start(_h3)

        async def _run() -> None:
            await cat.start()

        anyio.run(_run)
        assert log == ["h1", "h2", "h3"]

    def test_multiple_shutdown_hooks_reversed(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        def _h1(c: CatBase) -> None:
            log.append("h1")

        def _h2(c: CatBase) -> None:
            log.append("h2")

        def _h3(c: CatBase) -> None:
            log.append("h3")

        cat.on_shutdown(_h1)
        cat.on_shutdown(_h2)
        cat.on_shutdown(_h3)

        async def _run() -> None:
            await cat.shutdown()

        anyio.run(_run)
        assert log == ["h3", "h2", "h1"]


# -- 4. 事件发射顺序 -------------------------------------------------

class TestEventEmitOrder:
    """start/shutdown 与 hook 的事件发射顺序。"""

    def test_start_emits_event_before_hooks(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        async def _listener(payload: dict) -> None:
            log.append("lifecycle.start")

        cat.on(Lifecycle.START, _listener)

        def _hook(c: CatBase) -> None:
            log.append("hook")

        cat.on_start(_hook)

        async def _run() -> None:
            await cat.start()

        anyio.run(_run)
        # 事件先于 hooks
        assert log == ["lifecycle.start", "hook"]

    def test_shutdown_emits_event_after_hooks(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        async def _listener(payload: dict) -> None:
            log.append("lifecycle.shutdown")

        cat.on(Lifecycle.SHUTDOWN, _listener)

        def _hook(c: CatBase) -> None:
            log.append("hook")

        cat.on_shutdown(_hook)

        async def _run() -> None:
            await cat.shutdown()

        anyio.run(_run)
        # hooks 先于事件
        assert log == ["hook", "lifecycle.shutdown"]


# -- 5. 向后兼容 — 无 hooks 时行为不变 --------------------------------

class TestBackwardCompat:
    """无 hooks 时 start/shutdown 行为完全不变。"""

    def test_start_without_hooks_still_emits_event(self) -> None:
        cat = make_cat("test")
        events: list[str] = []

        async def _listener(payload: dict) -> None:
            events.append("lifecycle.start")

        cat.on(Lifecycle.START, _listener)

        async def _run() -> None:
            await cat.start()

        anyio.run(_run)
        assert events == ["lifecycle.start"]

    def test_shutdown_without_hooks_still_emits_event(self) -> None:
        cat = make_cat("test")
        events: list[str] = []

        async def _listener(payload: dict) -> None:
            events.append("lifecycle.shutdown")

        cat.on(Lifecycle.SHUTDOWN, _listener)

        async def _run() -> None:
            await cat.shutdown()

        anyio.run(_run)
        assert events == ["lifecycle.shutdown"]


# -- 6. 完整生命周期组合测试 ------------------------------------------

class TestFullLifecycle:
    """on_start + on_shutdown 组合完整生命周期。"""

    def test_full_lifecycle_with_hooks(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        async def _start_listener(payload: dict) -> None:
            log.append("event:start")

        async def _shutdown_listener(payload: dict) -> None:
            log.append("event:shutdown")

        def _start_hook(c: CatBase) -> None:
            log.append("hook:start")

        def _shutdown_hook(c: CatBase) -> None:
            log.append("hook:shutdown")

        cat.on(Lifecycle.START, _start_listener)
        cat.on(Lifecycle.SHUTDOWN, _shutdown_listener)
        cat.on_start(_start_hook)
        cat.on_shutdown(_shutdown_hook)

        async def _run() -> None:
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)
        assert log == [
            "event:start",   # start: 事件先
            "hook:start",    # start: 钩子后
            "hook:shutdown",  # shutdown: 钩子先
            "event:shutdown",  # shutdown: 事件后
        ]

    def test_multiple_start_and_shutdown_hooks(self) -> None:
        cat = make_cat("test")
        log: list[str] = []

        def _s1(c): log.append("s1")  # type: ignore[no-untyped-def]
        def _s2(c): log.append("s2")  # type: ignore[no-untyped-def]
        def _d1(c): log.append("d1")  # type: ignore[no-untyped-def]
        def _d2(c): log.append("d2")  # type: ignore[no-untyped-def]

        cat.on_start(_s1)
        cat.on_start(_s2)
        cat.on_shutdown(_d1)
        cat.on_shutdown(_d2)

        async def _run() -> None:
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)
        assert log == ["s1", "s2", "d2", "d1"]  # start 顺序, shutdown 逆序

