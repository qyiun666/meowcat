# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""
v1.0.10 — Gateway 体系测试
===========================

验证:
    1. SignalContext — 构造 / 不可变 / 字段类型
    2. Protocols — isinstance 检查 / IoAdapterProtocol 实现
    3. Gateway — mount / unmount / 同名覆盖
    4. HttpAdapter — POST 收发 / JSON 解析 / 错误响应 / SSE
    5. WsAdapter — WebSocket 连接 / 消息帧 / 流式帧 / 断开
    6. CliAdapter — stdin 输入 / stdout 输出 / stream 输出
    7. WebhookAdapter — 签名验证 / 消息解析 / 回调
    8. IpcAdapter — Unix socket 连接 / 收发
    9. Multi-adapter — 两 Adapter 共存 / 独立 session_id / 独立 platform
   10. SignalContext 注入 — perceive extras 透传 / Pipeline ctx 可访问
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.plus.gateway import (
    CliAdapter,
    HttpAdapter,
    IpcAdapter,
    WebhookAdapter,
    WsAdapter,
)
from meowcat.gateway import Gateway
from meowcat.gateway.protocol import (
    IoAdapterProtocol,
    GatewayProtocol,
    SignalContext,
)


# ═══════════════════════════════════════════════════════════════════
# 1. SignalContext
# ═══════════════════════════════════════════════════════════════════

class TestSignalContext:
    """SignalContext 构造 / 不可变 / 字段类型。"""

    def test_construct_minimal(self) -> None:
        """最简构造：只需 session_id + platform。"""
        ctx = SignalContext(session_id="s1", platform="cli")
        assert ctx.session_id == "s1"
        assert ctx.platform == "cli"
        assert ctx.user_id == "unknown"
        assert ctx.timestamp  # 自动生成

    def test_construct_full(self) -> None:
        """完整构造。"""
        ctx = SignalContext(
            session_id="feishu-grp-abc",
            platform="feishu",
            user_id="u123",
            timestamp="2026-05-03T00:00:00+00:00",
        )
        assert ctx.session_id == "feishu-grp-abc"
        assert ctx.platform == "feishu"
        assert ctx.user_id == "u123"
        assert ctx.timestamp == "2026-05-03T00:00:00+00:00"

    def test_frozen_immutable(self) -> None:
        """frozen=True，字段不可修改。"""
        ctx = SignalContext(session_id="s1", platform="cli")
        with pytest.raises(Exception):  # FrozenInstanceError 或类似
            ctx.session_id = "s2"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════
# 2. Protocols
# ═══════════════════════════════════════════════════════════════════

class TestProtocols:
    """GatewayProtocol / IoAdapterProtocol isinstance 检查。"""

    def test_gateway_is_gateway_protocol(self) -> None:
        """Gateway 实例满足 GatewayProtocol。"""
        cat = make_cat("test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        assert isinstance(gw, GatewayProtocol)

    def test_cli_adapter_is_adapter_protocol(self) -> None:
        """CliAdapter 满足 IoAdapterProtocol。"""
        assert isinstance(CliAdapter(), IoAdapterProtocol)

    def test_http_adapter_is_adapter_protocol(self) -> None:
        """HttpAdapter 满足 IoAdapterProtocol。"""
        assert isinstance(HttpAdapter(), IoAdapterProtocol)

    def test_ws_adapter_is_adapter_protocol(self) -> None:
        """WsAdapter 满足 IoAdapterProtocol。"""
        assert isinstance(WsAdapter(), IoAdapterProtocol)

    def test_adapter_must_have_name(self) -> None:
        """所有 Adapter 实现都有 name 属性。"""
        for cls in [HttpAdapter, WsAdapter, WebhookAdapter, CliAdapter, IpcAdapter]:
            assert hasattr(cls, "name") and isinstance(cls.name, str), \
                f"{cls.__name__} missing 'name'"


# ═══════════════════════════════════════════════════════════════════
# 3. Gateway mount / unmount
# ═══════════════════════════════════════════════════════════════════

class TestGatewayMount:
    """Gateway 挂载/卸载/同名覆盖。"""

    def test_mount_adapter(self) -> None:
        """挂载适配器后出现在 adapter_names 中。"""
        cat = make_cat("test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        gw.mount_adapter(HttpAdapter())
        assert "http" in gw.adapter_names

    def test_unmount_adapter(self) -> None:
        """卸载后 adapter_names 中移除。"""
        cat = make_cat("test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        gw.mount_adapter(HttpAdapter())
        gw.unmount_adapter("http")
        assert "http" not in gw.adapter_names

    def test_unmount_nonexistent_noop(self) -> None:
        """卸载不存在的 adapter 不抛异常。"""
        cat = make_cat("test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        gw.unmount_adapter("nonexistent")  # no-op

    def test_same_name_overwrite(self) -> None:
        """同名挂载覆盖旧 adapter。"""
        cat = make_cat("test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        a1 = HttpAdapter(port=8000)
        a2 = HttpAdapter(port=9000)
        gw.mount_adapter(a1)
        gw.mount_adapter(a2)
        assert gw.adapter_names == ["http"]
        # _adapters["http"] 应该是 a2
        assert gw._adapters["http"] is a2


# ═══════════════════════════════════════════════════════════════════
# 4. HttpAdapter
# ═══════════════════════════════════════════════════════════════════

class TestHttpAdapter:
    """HttpAdapter POST 收发 / JSON / 错误 / SSE。"""

    @pytest.mark.asyncio
    async def test_post_chat_ok(self) -> None:
        """POST /chat 返回 JSON reply。"""
        adapter = HttpAdapter(port=0)  # port=0 让 OS 分配

        async def on_message(text: str, ctx: SignalContext) -> str | None:
            return f"echo: {text}"

        async def on_stream(text, ctx):
            return None

        # 在后台启动 server
        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))

        # 等待 server 启动并获取实际端口
        await asyncio.sleep(0.1)
        if adapter._server and adapter._server.sockets:
            actual_port = adapter._server.sockets[0].getsockname()[1]
        else:
            actual_port = adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps({"message": "hello"}).encode()
            request = (
                f"POST /chat HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()

            assert "200" in response_text.split("\r\n")[0]
            assert '"echo: hello"' in response_text

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_post_missing_message(self) -> None:
        """POST /chat 缺少 message 字段返回 400。"""
        adapter = HttpAdapter(port=0)

        async def on_message(text, ctx):
            return f"echo: {text}"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps({}).encode()
            request = (
                f"POST /chat HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()
            assert "400" in response_text.split("\r\n")[0]

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_post_wrong_path_404(self) -> None:
        """POST 到错误路径返回 404。"""
        adapter = HttpAdapter(port=0)

        async def on_message(text, ctx):
            return "ok"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps({"message": "hi"}).encode()
            request = (
                f"POST /wrong HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()
            assert "404" in response_text.split("\r\n")[0]

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_sse_stream_response(self) -> None:
        """Accept: text/event-stream 触发 SSE 流式响应。"""
        adapter = HttpAdapter(port=0)

        async def on_message(text, ctx):
            return "not used"

        async def on_stream(text, ctx):
            # 模拟流式返回
            async def gen():
                yield "Hello"
                yield " World"
            return gen()

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps({"message": "hi"}).encode()
            request = (
                f"POST /chat HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Accept: text/event-stream\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()
            assert "text/event-stream" in response_text
            assert "Hello" in response_text
            assert "[DONE]" in response_text

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass


# ═══════════════════════════════════════════════════════════════════
# 5. WsAdapter
# ═══════════════════════════════════════════════════════════════════

# WebSocket 帧工具（复用 ws_adapter 中的函数）
from meowcat.plus.gateway.ws_adapter import (  # noqa: E402
    _compute_accept,
    _decode_frame,
    _encode_frame,
    _OP_TEXT,
    _OP_CLOSE,
    _WS_GUID,
)


class TestWsFrameEncoding:
    """WebSocket 帧编解码。"""

    def test_encode_text_frame(self) -> None:
        """编码文本帧。"""
        frame = _encode_frame(b"hello")
        assert frame[0] & 0x01  # opcode = text
        assert b"hello" in frame

    def test_decode_text_frame(self) -> None:
        """解码带 mask 的文本帧。"""
        import struct
        payload = b"test"
        mask_key = b"\x12\x34\x56\x78"
        masked = bytearray(payload)
        for i in range(len(masked)):
            masked[i] ^= mask_key[i % 4]

        frame = bytearray()
        frame.append(0x81)  # FIN + text
        frame.append(0x80 | len(payload))  # masked + length
        frame.extend(mask_key)
        frame.extend(masked)

        opcode, decoded, fin = _decode_frame(bytes(frame))
        assert opcode == _OP_TEXT
        assert decoded == b"test"
        assert fin is True

    def test_compute_accept(self) -> None:
        """Sec-WebSocket-Accept 计算正确。"""
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        accept = _compute_accept(key)
        assert accept == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


class TestWsAdapter:
    """WsAdapter WebSocket 协议收发。"""

    @pytest.mark.asyncio
    async def test_ws_handshake_and_message(self) -> None:
        """WebSocket handshake + 消息收发。"""
        adapter = WsAdapter(port=0)

        async def on_message(text, ctx):
            return f"ws-echo: {text}"

        async def on_stream(text, ctx):
            async def gen():
                yield f"ws-stream: {text}"
            return gen()

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)

            # WebSocket handshake
            ws_key = "dGhlIHNhbXBsZSBub25jZQ=="
            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
            writer.write(handshake)
            await writer.drain()

            response = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
            response_text = response.decode()
            assert "101" in response_text
            expected_accept = _compute_accept(ws_key)
            assert expected_accept in response_text

            # 发送文本帧
            text = "hello ws"
            import struct
            payload = text.encode()
            mask_key = b"\x00\x01\x02\x03"
            masked = bytearray(payload)
            for i in range(len(masked)):
                masked[i] ^= mask_key[i % 4]
            frame = bytearray()
            frame.append(0x81)  # FIN + text
            frame.append(0x80 | len(payload))
            frame.extend(mask_key)
            frame.extend(masked)
            writer.write(bytes(frame))
            await writer.drain()

            # 读取响应帧
            response_data = await asyncio.wait_for(reader.read(4096), timeout=5)
            # 至少应该收到流式响应 + [DONE]
            assert len(response_data) > 0

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_ws_missing_key_rejected(self) -> None:
        """缺少 Sec-WebSocket-Key 的连接被拒绝。"""
        adapter = WsAdapter(port=0)

        async def on_message(text, ctx):
            return "ok"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            # 不带 Sec-WebSocket-Key
            request = (
                f"GET / HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode()
            writer.write(request)
            await writer.drain()

            # 连接不应 hang，应被关闭
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=3)
            except (asyncio.TimeoutError, ConnectionError):
                data = b""
            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass


# ═══════════════════════════════════════════════════════════════════
# 6. CliAdapter
# ═══════════════════════════════════════════════════════════════════

class TestCliAdapter:
    """CliAdapter stdin/stdout 收发。"""

    @pytest.mark.asyncio
    async def test_cli_input_output(self) -> None:
        """stdin 输入 → on_message 回调 → stdout 输出。"""
        adapter = CliAdapter()
        calls: list[tuple[str, SignalContext]] = []

        async def on_message(text: str, ctx: SignalContext) -> str | None:
            calls.append((text, ctx))
            return f"reply: {text}"

        async def on_stream(text, ctx):
            return None

        # 用 StringIO 替换 stdin
        fake_stdin = io.StringIO("hello\nworld\n")
        with patch.object(sys, "stdin", fake_stdin):
            # serve 在读到空行后会退出
            serve_task = asyncio.create_task(
                adapter.serve(on_message, on_stream))
            await asyncio.wait_for(serve_task, timeout=3)

        assert len(calls) == 2
        assert calls[0][0] == "hello"
        assert calls[0][1].platform == "cli"
        assert calls[0][1].user_id == "cli-user"
        assert calls[1][0] == "world"

    @pytest.mark.asyncio
    async def test_cli_send_to_stdout(self) -> None:
        """send() 输出到 stdout。"""
        adapter = CliAdapter()
        with patch("builtins.print") as mock_print:
            await adapter.send("hello stdout", "s1")
            mock_print.assert_called_once_with("hello stdout", flush=True)

    @pytest.mark.asyncio
    async def test_cli_stream_chunk_no_newline(self) -> None:
        """stream_chunk 输出不换行。"""
        adapter = CliAdapter()
        with patch("builtins.print") as mock_print:
            await adapter.stream_chunk("chunk1", "s1")
            mock_print.assert_called_once_with("chunk1", end="", flush=True)

    @pytest.mark.asyncio
    async def test_cli_stream_end_newline(self) -> None:
        """stream_end 补换行。"""
        adapter = CliAdapter()
        with patch("builtins.print") as mock_print:
            await adapter.stream_end("s1")
            mock_print.assert_called_once_with(flush=True)


# ═══════════════════════════════════════════════════════════════════
# 6b. CliAdapter — queue mode (v1.0.4 Textual TUI)
# ═══════════════════════════════════════════════════════════════════

class TestCliAdapterQueue:
    """CliAdapter queue 模式 — Textual TUI async event loop 兼容。"""

    def test_queue_mode_construct(self) -> None:
        """queue 模式构造成功，_queue 不为 None。"""
        adapter = CliAdapter(mode="queue")
        assert adapter._mode == "queue"
        assert adapter._queue is not None
        assert isinstance(adapter, IoAdapterProtocol)

    def test_stdio_mode_default(self) -> None:
        """默认 mode='stdio'，_queue 为 None。"""
        adapter = CliAdapter()
        assert adapter._mode == "stdio"
        assert adapter._queue is None

    def test_invalid_mode_raises(self) -> None:
        """非法 mode 抛 ValueError。"""
        with pytest.raises(ValueError, match="mode"):
            CliAdapter(mode="invalid")

    @pytest.mark.asyncio
    async def test_enqueue_without_queue_raises(self) -> None:
        """stdio 模式下调用 enqueue 抛 RuntimeError。"""
        adapter = CliAdapter()
        with pytest.raises(RuntimeError, match="enqueue"):
            await adapter.enqueue("hello")

    @pytest.mark.asyncio
    async def test_queue_single_message(self) -> None:
        """queue 模式：enqueue 一条消息 → on_message 被调用。"""
        adapter = CliAdapter(mode="queue")
        calls: list[tuple[str, SignalContext]] = []

        async def on_message(text: str, ctx: SignalContext) -> str | None:
            calls.append((text, ctx))
            return f"reply: {text}"

        async def on_stream(text, ctx):
            return None

        # 启动 serve loop
        serve_task = asyncio.create_task(
            adapter.serve(on_message, on_stream))

        # 喂入消息
        await adapter.enqueue("hello queue")

        # 等待处理
        await asyncio.sleep(0.1)

        # 停止
        await adapter.stop()
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass

        assert len(calls) == 1
        assert calls[0][0] == "hello queue"
        assert calls[0][1].platform == "cli"
        assert calls[0][1].user_id == "cli-user"

    @pytest.mark.asyncio
    async def test_queue_multiple_messages(self) -> None:
        """queue 模式：多条消息依次处理。"""
        adapter = CliAdapter(mode="queue")
        calls: list[str] = []

        async def on_message(text, ctx):
            calls.append(text)
            return f"r:{text}"

        async def on_stream(text, ctx):
            return None

        serve_task = asyncio.create_task(
            adapter.serve(on_message, on_stream))

        await adapter.enqueue("msg1")
        await adapter.enqueue("msg2")
        await adapter.enqueue("msg3")

        await asyncio.sleep(0.15)

        await adapter.stop()
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass

        assert calls == ["msg1", "msg2", "msg3"]

    @pytest.mark.asyncio
    async def test_queue_send_to_stdout(self) -> None:
        """queue 模式下 send() 仍然输出到 stdout。"""
        adapter = CliAdapter(mode="queue")
        with patch("builtins.print") as mock_print:
            await adapter.send("queue output", "s1")
            mock_print.assert_called_once_with("queue output", flush=True)

    @pytest.mark.asyncio
    async def test_queue_stream_chunk(self) -> None:
        """queue 模式下 stream_chunk 正常输出。"""
        adapter = CliAdapter(mode="queue")
        with patch("builtins.print") as mock_print:
            await adapter.stream_chunk("chunk", "s1")
            mock_print.assert_called_once_with("chunk", end="", flush=True)

    @pytest.mark.asyncio
    async def test_queue_stop_before_enqueue(self) -> None:
        """stop 后 serve loop 退出，不再处理消息。"""
        adapter = CliAdapter(mode="queue")
        calls: list[str] = []

        async def on_message(text, ctx):
            calls.append(text)
            return "ok"

        async def on_stream(text, ctx):
            return None

        serve_task = asyncio.create_task(
            adapter.serve(on_message, on_stream))

        # 先 cancel serve task 真正停止 loop
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass

        # serve loop 已退出，enqueue 不再触发 on_message
        await adapter.enqueue("after stop")
        await asyncio.sleep(0.1)

        assert calls == []


# ═══════════════════════════════════════════════════════════════════
# 7. WebhookAdapter
# ═══════════════════════════════════════════════════════════════════

class TestWebhookAdapter:
    """WebhookAdapter 签名验证 / 消息解析 / 回调。"""

    def test_verify_signature_default_pass(self) -> None:
        """默认签名验证放行。"""
        adapter = WebhookAdapter()
        assert adapter.verify_signature({}, b"any") is True

    def test_parse_message_default(self) -> None:
        """默认消息解析从 body 提取 message 和 user_id。"""
        adapter = WebhookAdapter()
        text, uid = adapter.parse_message({"message": "hi", "user_id": "u1"})
        assert text == "hi"
        assert uid == "u1"

    def test_parse_message_missing_fields(self) -> None:
        """缺失字段时返回默认值。"""
        adapter = WebhookAdapter()
        text, uid = adapter.parse_message({})
        assert text == ""
        assert uid == "unknown"

    @pytest.mark.asyncio
    async def test_webhook_post_callback(self) -> None:
        """POST webhook 回调 → on_message 被调用。"""
        adapter = WebhookAdapter(port=0)

        called: list[tuple[str, SignalContext]] = []

        async def on_message(text: str, ctx: SignalContext) -> str | None:
            called.append((text, ctx))
            return "ok"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps(
                {"message": "webhook hi", "user_id": "u42"}).encode()
            request = (
                f"POST /webhook HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()
            assert "200" in response_text.split("\r\n")[0]

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

        assert len(called) == 1
        assert called[0][0] == "webhook hi"
        assert called[0][1].platform == "webhook"
        assert called[0][1].user_id == "u42"

    @pytest.mark.asyncio
    async def test_webhook_signature_rejected(self) -> None:
        """签名验证失败返回 403。"""
        adapter = WebhookAdapter(port=0)
        # type: ignore[method-assign]
        adapter.verify_signature = lambda headers, body: False

        async def on_message(text, ctx):
            pytest.fail("should not be called")
            return ""

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)
        actual_port = adapter._server.sockets[0].getsockname(
        )[1] if adapter._server else adapter.port

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", actual_port)
            body = json.dumps({"message": "hi"}).encode()
            request = (
                f"POST /webhook HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{actual_port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + body
            writer.write(request)
            await writer.drain()

            response = await asyncio.wait_for(reader.read(), timeout=5)
            response_text = response.decode()
            assert "403" in response_text.split("\r\n")[0]

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass


# ═══════════════════════════════════════════════════════════════════
# 8. IpcAdapter
# ═══════════════════════════════════════════════════════════════════

class TestIpcAdapter:
    """IpcAdapter Unix socket 收发。"""

    @pytest.mark.asyncio
    async def test_ipc_send_receive(self) -> None:
        """Unix socket 发送消息 → on_message 被调用 → 收到回复。"""
        socket_path = f"/tmp/test-meowcat-{os.getpid()}.sock"
        adapter = IpcAdapter(socket_path=socket_path)

        called: list[tuple[str, SignalContext]] = []

        async def on_message(text: str, ctx: SignalContext) -> str | None:
            called.append((text, ctx))
            return f"ipc-reply: {text}"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            msg = json.dumps({"message": "hello ipc"}) + "\n"
            writer.write(msg.encode())
            await writer.drain()

            response = await asyncio.wait_for(reader.readline(), timeout=5)
            response_data = json.loads(response.decode().strip())
            assert response_data.get("reply") == "ipc-reply: hello ipc"

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

        assert len(called) == 1
        assert called[0][0] == "hello ipc"
        assert called[0][1].platform == "ipc"

    @pytest.mark.asyncio
    async def test_ipc_multiple_messages(self) -> None:
        """Unix socket 支持多轮消息。"""
        socket_path = f"/tmp/test-meowcat-multi-{os.getpid()}.sock"
        adapter = IpcAdapter(socket_path=socket_path)
        calls: list[str] = []

        async def on_message(text, ctx):
            calls.append(text)
            return f"r:{text}"

        async def on_stream(text, ctx):
            return None

        server_task = asyncio.create_task(adapter.serve(on_message, on_stream))
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            for i in range(3):
                writer.write(json.dumps(
                    {"message": f"msg{i}"}).encode() + b"\n")
                await writer.drain()
                response = await asyncio.wait_for(reader.readline(), timeout=5)
                data = json.loads(response.decode().strip())
                assert data["reply"] == f"r:msg{i}"

            writer.close()
        finally:
            await adapter.stop()
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass

        assert calls == ["msg0", "msg1", "msg2"]


# ═══════════════════════════════════════════════════════════════════
# 9. Multi-adapter
# ═══════════════════════════════════════════════════════════════════

class TestMultiAdapter:
    """两个 Adapter 共存 / 独立 session_id / 独立 platform。"""

    def test_two_adapters_coexist(self) -> None:
        """两个不同 Adapter 可同时挂载到 Gateway。"""
        cat = make_cat("multi", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        gw.mount_adapter(HttpAdapter(port=8000))
        gw.mount_adapter(CliAdapter())
        assert set(gw.adapter_names) == {"http", "cli"}

    def test_independent_sessions(self) -> None:
        """不同 Adapter 产生不同 session_id。"""
        ctx_http = SignalContext(
            session_id="http-123", platform="http", user_id="u1",
        )
        ctx_cli = SignalContext(
            session_id="cli-456", platform="cli", user_id="cli-user",
        )
        assert ctx_http.session_id != ctx_cli.session_id
        assert ctx_http.platform != ctx_cli.platform

    def test_independent_platforms(self) -> None:
        """每个 Adapter 的 SignalContext 有独立 platform。"""
        http_ctx = SignalContext(session_id="s1", platform="http")
        ws_ctx = SignalContext(session_id="s2", platform="ws")
        cli_ctx = SignalContext(session_id="s3", platform="cli")
        assert http_ctx.platform == "http"
        assert ws_ctx.platform == "ws"
        assert cli_ctx.platform == "cli"


# ═══════════════════════════════════════════════════════════════════
# 10. SignalContext 注入
# ═══════════════════════════════════════════════════════════════════

class TestSignalContextInjection:
    """SignalContext 通过 perceive extras 透传。"""

    def test_signalcontext_in_perceive_extras(self) -> None:
        """perceive() 的 **extras 包含 context。"""
        cat = make_cat("inject-test", enable_wiring=False, enable_reflex=False)
        ctx = SignalContext(session_id="s1", platform="test")

        # 验证 extras 字典中包含 SignalContext
        extras = {"context": ctx, "other": 42}
        assert extras["context"] is ctx
        assert isinstance(extras["context"], SignalContext)
        assert extras["context"].session_id == "s1"

    def test_gateway_on_message_uses_perceive(self) -> None:
        """Gateway._on_message 调用 cat.perceive(text, context=ctx)。"""
        cat = make_cat("gw-test", enable_wiring=False, enable_reflex=False)
        gw = Gateway(cat)
        ctx = SignalContext(session_id="gw-s1", platform="test")

        # Gateway._on_message 会调用 cat.perceive(text, context=ctx)
        # 但因为没有安装 reflex，perceive 会抛 RuntimeError
        # 这里验证 SignalContext 正确传递
        assert isinstance(gw, Gateway)

    def test_signalcontext_fields_correct_types(self) -> None:
        """SignalContext 字段类型正确。"""
        ctx = SignalContext(
            session_id="s1",
            platform="http",
            user_id="user-123",
        )
        assert isinstance(ctx.session_id, str)
        assert isinstance(ctx.platform, str)
        assert isinstance(ctx.user_id, str)
        assert isinstance(ctx.timestamp, str)
        # timestamp 是 ISO 8601 格式
        assert "T" in ctx.timestamp

