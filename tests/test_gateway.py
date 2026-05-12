# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Gateway + FrontDesk 单元测试 — C-02 修复。

覆盖：
- SignalContext 数据类（构造、默认值、冷冻）
- Gateway 构造、适配器管理、生命周期、消息回调
- DefaultFrontDesk 路由（插件 first-hit、target_cat 转发、缺失处理）
- 协议类 @runtime_checkable
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from meowcat.gateway import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.gateway.protocol import (
    FrontDeskProtocol,
    GatewayProtocol,
    IoAdapterProtocol,
    SignalContext,
)
from meowcat.testing import make_test_colony

# =============================================================================
# SignalContext
# =============================================================================


class TestSignalContext:
    """SignalContext 数据类测试。"""

    def test_construction(self) -> None:
        ctx = SignalContext(session_id="cli-test", platform="cli")
        assert ctx.session_id == "cli-test"
        assert ctx.platform == "cli"
        assert ctx.user_id == "unknown"
        assert ctx.target_cat is None
        assert ctx.timestamp  # auto-generated ISO string

    def test_custom_user_id_and_target(self) -> None:
        ctx = SignalContext(
            session_id="ws-x", platform="ws", user_id="alice", target_cat="cat-1"
        )
        assert ctx.user_id == "alice"
        assert ctx.target_cat == "cat-1"

    def test_frozen(self) -> None:
        ctx = SignalContext(session_id="s", platform="p")
        with pytest.raises(FrozenInstanceError):
            ctx.user_id = "hack"  # type: ignore[misc]

    def test_timestamp_is_utc_iso(self) -> None:
        ctx = SignalContext(session_id="s", platform="p")
        # Basic ISO format check — should contain 'T' and end with timezone offset or Z
        assert "T" in ctx.timestamp
        # Should parse without error
        datetime.fromisoformat(ctx.timestamp)


# =============================================================================
# Protocols — @runtime_checkable
# =============================================================================


class TestProtocols:
    """协议类的 @runtime_checkable 验证。"""

    def test_front_desk_protocol_checkable(self) -> None:
        class CustomFD:
            async def route(self, text, ctx, colony):
                return "ok"

        assert isinstance(CustomFD(), FrontDeskProtocol)

    def test_io_adapter_protocol_checkable(self) -> None:
        class CustomAdapter:
            name = "test-adapter"

            async def serve(self, on_message, on_stream):
                pass

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                pass

        assert isinstance(CustomAdapter(), IoAdapterProtocol)

    def test_gateway_protocol_checkable(self) -> None:
        class CustomGW:
            async def start(self):
                pass

            async def stop(self):
                pass

            def mount_adapter(self, adapter):
                pass

            def unmount_adapter(self, name):
                pass

        assert isinstance(CustomGW(), GatewayProtocol)


# =============================================================================
# Gateway — 构造 & 适配器管理
# =============================================================================


class TestGatewayConstruction:
    """Gateway 构造和相关属性。"""

    def test_default_front_desk(self) -> None:
        colony = make_test_colony("gw-c1")
        gw = Gateway(colony)
        assert isinstance(gw.front_desk, DefaultFrontDesk)

    def test_custom_front_desk(self) -> None:
        colony = make_test_colony("gw-c2")

        class MyFD(DefaultFrontDesk):
            pass

        fd = MyFD()
        gw = Gateway(colony, front_desk=fd)
        assert gw.front_desk is fd

    def test_colony_reference(self) -> None:
        colony = make_test_colony("gw-c3")
        gw = Gateway(colony)
        assert gw.colony is colony


class TestGatewayAdapterManagement:
    """Gateway 适配器挂载/卸载。"""

    def test_mount_adds_adapter(self) -> None:
        colony = make_test_colony("gw-a1")
        gw = Gateway(colony)

        class MockAdapter:
            name = "mock"

            async def serve(self, on_msg, on_stream):
                pass

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                pass

        gw.mount_adapter(MockAdapter())
        assert gw.adapter_names == ["mock"]

    def test_mount_same_name_overwrites(self) -> None:
        colony = make_test_colony("gw-a2")
        gw = Gateway(colony)

        class MockA:
            name = "mock"

            async def serve(self, on_msg, on_stream):
                pass

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                pass

        gw.mount_adapter(MockA())
        gw.mount_adapter(MockA())
        assert len(gw.adapter_names) == 1

    def test_unmount_removes_adapter(self) -> None:
        colony = make_test_colony("gw-a3")
        gw = Gateway(colony)

        class MockAdapter:
            name = "mock"

            async def serve(self, on_msg, on_stream):
                pass

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                pass

        gw.mount_adapter(MockAdapter())
        gw.unmount_adapter("mock")
        assert gw.adapter_names == []

    def test_unmount_unknown_noop(self) -> None:
        colony = make_test_colony("gw-a4")
        gw = Gateway(colony)
        gw.unmount_adapter("no-such-adapter")  # should not raise


# =============================================================================
# Gateway — 生命周期
# =============================================================================


@pytest.mark.anyio
class TestGatewayLifecycle:
    """Gateway start/stop 生命周期。"""

    @pytest.mark.asyncio
    async def test_start_with_no_adapters_returns_immediately(self) -> None:
        colony = make_test_colony("gw-l1")
        gw = Gateway(colony)
        await gw.start()  # should return immediately without error

    @pytest.mark.asyncio
    async def test_start_with_mock_adapter(self) -> None:
        colony = make_test_colony("gw-l2")
        gw = Gateway(colony)

        served = False

        class MockAdapter:
            name = "mock"

            async def serve(self, on_msg, on_stream):
                nonlocal served
                served = True
                # immediately return so start() doesn't block forever
                return

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                pass

        gw.mount_adapter(MockAdapter())
        await gw.start()
        assert served

    @pytest.mark.asyncio
    async def test_stop_calls_adapter_stop(self) -> None:
        colony = make_test_colony("gw-l3")
        gw = Gateway(colony)
        stopped = False

        class MockAdapter:
            name = "mock"

            async def serve(self, on_msg, on_stream):
                return

            async def send(self, output, session_id, **meta):
                pass

            async def stream_chunk(self, chunk, session_id, **meta):
                pass

            async def stream_end(self, session_id, **meta):
                pass

            async def stop(self):
                nonlocal stopped
                stopped = True

        gw.mount_adapter(MockAdapter())
        await gw.stop()
        assert stopped


# =============================================================================
# Gateway — 消息回调
# =============================================================================


@pytest.mark.anyio
class TestGatewayMessageCallback:
    """Gateway _on_message → FrontDesk.route() 委托。"""

    @pytest.mark.asyncio
    async def test_on_message_delegates_to_front_desk(self) -> None:
        colony = make_test_colony("gw-m1")
        ctx = SignalContext(session_id="s", platform="cli")

        class SpyFD:
            async def route(self, text, ctx_in, colony_in):
                assert text == "hello"
                assert ctx_in is ctx
                return "world"

        gw = Gateway(colony, front_desk=SpyFD())
        reply = await gw._on_message("hello", ctx)
        assert reply == "world"

    @pytest.mark.asyncio
    async def test_on_message_target_cat_forward(self) -> None:
        """Verify _on_message delegates to FrontDesk with target_cat set.

        Uses a spy FrontDesk to avoid CatBase/perceive() assembly (which
        depends on loops.py Chain import — a pre-existing T-05 issue).
        """
        colony = make_test_colony("gw-m2")
        ctx = SignalContext(
            session_id="s", platform="cli", target_cat="cat-1"
        )

        class SpyFD:
            async def route(self, text, ctx_in, colony_in):
                assert ctx_in.target_cat == "cat-1"
                return "routed"

        gw = Gateway(colony, front_desk=SpyFD())
        reply = await gw._on_message("ping", ctx)
        assert reply == "routed"

    @pytest.mark.asyncio
    async def test_on_message_missing_target_cat(self) -> None:
        colony = make_test_colony("gw-m3")
        ctx = SignalContext(session_id="s", platform="cli",
                            target_cat="no-such-cat")
        gw = Gateway(colony)
        reply = await gw._on_message("ping", ctx)
        assert reply is not None
        assert "找不到猫" in reply

    @pytest.mark.asyncio
    async def test_on_message_no_target_placeholder(self) -> None:
        colony = make_test_colony("gw-m4")
        ctx = SignalContext(session_id="s", platform="cli")
        gw = Gateway(colony)
        reply = await gw._on_message("ping", ctx)
        assert reply is not None
        assert "不知道你要找谁" in reply


# =============================================================================
# DefaultFrontDesk — 插件 & 路由
# =============================================================================


class TestFrontDeskHooks:
    """DefaultFrontDesk 插件 hook 注册和 first-hit 逻辑。"""

    def test_plug_and_unplug(self) -> None:
        fd = DefaultFrontDesk()
        counter = 0

        def my_hook(text, ctx, colony):
            nonlocal counter
            counter += 1
            return None  # pass-through

        fd.plug("on_route", my_hook)
        assert fd.list_plugs().get("on_route", 0) == 1

        fd.unplug("on_route", my_hook)
        assert fd.list_plugs().get("on_route", 0) == 0

    def test_unplug_all_removes_all(self) -> None:
        fd = DefaultFrontDesk()

        def h1(text, ctx, colony):
            return None

        def h2(text, ctx, colony):
            return None

        fd.plug("on_route", h1)
        fd.plug("on_route", h2)
        assert fd.list_plugs().get("on_route", 0) == 2

        fd.unplug("on_route")  # remove all
        assert fd.list_plugs().get("on_route", 0) == 0


@pytest.mark.anyio
class TestFrontDeskRoute:
    """DefaultFrontDesk.route() 路由逻辑。"""

    @pytest.mark.asyncio
    async def test_plugin_first_hit_short_circuits(self) -> None:
        colony = make_test_colony("fd-r1")
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s", platform="cli")

        fd.plug("on_route", lambda t, c, col: "blocked")
        fd.plug("on_route", lambda t, c, col: "never-called")

        result = await fd.route("hello", ctx, colony)
        assert result == "blocked"

    @pytest.mark.asyncio
    async def test_plugin_pass_through_falls_to_default(self) -> None:
        colony = make_test_colony("fd-r2")
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s", platform="cli")

        fd.plug("on_route", lambda t, c, col: None)  # pass-through
        result = await fd.route("hello", ctx, colony)
        # No target_cat → placeholder
        assert "不知道你要找谁" in result

    @pytest.mark.asyncio
    async def test_route_missing_cat(self) -> None:
        colony = make_test_colony("fd-r3")
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s", platform="cli", target_cat="nope")

        result = await fd.route("hello", ctx, colony)
        assert "找不到猫" in result

    @pytest.mark.asyncio
    async def test_route_no_target(self) -> None:
        colony = make_test_colony("fd-r4")
        fd = DefaultFrontDesk()
        ctx = SignalContext(session_id="s", platform="cli")

        result = await fd.route("hello", ctx, colony)
        assert "不知道你要找谁" in result
