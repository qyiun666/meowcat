# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.3.0 — Gateway end-to-end integration tests.

Coverage:
  * Full chain: Gateway._on_message → FrontDesk → Colony → Cat → response
  * Security plugin on FrontDesk
  * Dynamic cat creation after Gateway setup
  * SignalContext preservation in full chain
  * Gateway construction, adapter management, lifecycle
  * FrontDesk plugin chain routing and cat target dispatch
  * Gateway _on_message / _on_stream delegation
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from meowcat.defaults.factory import create_cat
from meowcat.defaults.stages import BaseStage
from meowcat.gateway import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.gateway.protocol import (
    FrontDeskProtocol,
    IoAdapterProtocol,
    SignalContext,
)
from meowcat.models import StageEvent
from meowcat.reflex import BUILTIN_REFLEX_PATHS, Reflex
from meowcat.testing import make_test_colony
from tests.conftest import DummyOrgan, SimpleCerebrum


# ═══════════════════════════════════════════════════════════════════════
# Local helpers (not shared)
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
        self._serve_event.set()
        if self.should_fail:
            raise RuntimeError("adapter failure")
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


class _CerebrumOutputStage(BaseStage):
    """Custom stage that calls the cerebrum and yields output events."""

    async def run(self, ctx: Any) -> AsyncIterator[StageEvent]:
        cat = ctx.cat
        if cat is not None and hasattr(cat, "cerebrum"):
            response = await cat.cerebrum.generate(str(ctx.input))
            yield StageEvent.output(response)


# ═══════════════════════════════════════════════════════════════════════
# TestV230GatewayE2E — Full chain
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestV230GatewayE2E:
    """完整链路: Gateway._on_message → FrontDesk → Colony → Cat → 响应."""

    @pytest.mark.asyncio
    async def test_full_chain_gateway_to_colony_to_cat(self) -> None:
        """完整链路: Gateway → FrontDesk → Colony.get_cat → cat 器官调用."""
        col = make_test_colony()
        cat = col.create_cat(name="assistant")
        cat.mount("input", "ears", DummyOrgan())
        cat.wiring.connect(("input", "ears"), ("input", "ears"))

        class _CatRoutingFrontDesk(FrontDeskProtocol):
            """FrontDesk that routes to cat's ears.echo."""

            async def route(self, text, ctx, colony):
                if ctx.target_cat:
                    cat_obj = colony.get_cat(ctx.target_cat)
                    result = await cat_obj.signal(
                        ("input", "ears"), ("input", "ears"), "echo", text,
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
        fd.plug("on_route", lambda text, ctx,
                colony: "已拦截" if "hack" in text.lower() else None)

        gw = Gateway(col, front_desk=fd)
        ctx = SignalContext(session_id="s1", platform="test")

        blocked = await gw._on_message("try to hack server", ctx)
        assert blocked == "已拦截"

        passthrough = await gw._on_message("hello", ctx)
        assert passthrough != "已拦截"
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

        cat = col.create_cat(name="dynamic-cat")
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
            session_id="sess-123", platform="slack", user_id="U001", target_cat="cat-01",
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
# TestV230GatewayConstruction
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestV230GatewayConstruction:
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


# ═══════════════════════════════════════════════════════════════════════
# TestV230GatewayLifecycle
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestV230GatewayLifecycle:
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


# ═══════════════════════════════════════════════════════════════════════
# TestV230FrontDeskRouting
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestV230FrontDeskRouting:
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
        cerebrum = SimpleCerebrum()
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
        assert result == "passed through"

    @pytest.mark.asyncio
    async def test_route_to_target_cat(self) -> None:
        col = make_test_colony()
        cerebrum = SimpleCerebrum()
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
        cerebrum = SimpleCerebrum()
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
        assert result == "ok"


# ═══════════════════════════════════════════════════════════════════════
# TestV230GatewayOnMessage
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestV230GatewayOnMessage:
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
