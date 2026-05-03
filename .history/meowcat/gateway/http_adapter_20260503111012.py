"""meowcat Gateway — HttpAdapter（HTTP POST /chat JSON 协议适配器）。

非流式请求/响应模式: JSON body ``{"message": "..."}`` → JSON response ``{"reply": "..."}``。
可选 SSE 支持流式（``Accept: text/event-stream`` → stream_chunk 逐块推送）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext

# HTTP 状态码 → RFC 7230 理由短语
_HTTP_REASONS: dict[int, str] = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    500: "Internal Server Error",
}

_logger = logging.getLogger(__name__)


class HttpAdapter:
    """HTTP 协议适配器 — 接受 HTTP POST /chat 请求。

    纯 asyncio，零外部依赖。
    """

    name = "http"

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动 asyncio HTTP server，监听 POST /chat。"""
        self._on_message = on_message
        self._on_stream = on_stream

        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await self._handle_connection(reader, writer)

        self._server = await asyncio.start_server(
            handler, host=self.host, port=self.port,
        )

        async with self._server:
            await self._server.serve_forever()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """处理单个 HTTP 连接。"""
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=30)
            if not request_line:
                writer.close()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await self._write_response(writer, 400, {"error": "bad request"})
                return
            method, path = parts[0], parts[1]

            # 读 headers
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                line_str = line.decode().strip()
                if not line_str:
                    break
                if ":" in line_str:
                    key, val = line_str.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            # 读 body
            content_length = int(headers.get("content-length", "0"))
            body_raw = await asyncio.wait_for(
                reader.readexactly(content_length), timeout=10,
            ) if content_length > 0 else b""

            if method != "POST" or path != "/chat":
                await self._write_response(writer, 404, {"error": "not found"})
                return

            body = json.loads(body_raw.decode()) if body_raw else {}
            text = body.get("message", "")

            if not text:
                await self._write_response(writer, 400, {"error": "missing message"})
                return

            ctx = SignalContext(
                session_id=f"http-{id(writer)}",
                platform="http",
                user_id=headers.get("x-user-id", "unknown"),
            )

            accept = headers.get("accept", "")

            if "text/event-stream" in accept:
                # SSE 流式响应
                await self._handle_sse(writer, text, ctx)
            else:
                # 标准 JSON 响应
                reply = await self._on_message(text, ctx)
                await self._write_response(writer, 200, {"reply": reply or ""})

        except (json.JSONDecodeError, asyncio.TimeoutError):
            await self._write_response(writer, 400, {"error": "invalid json"})
        except (ConnectionError, OSError, asyncio.TimeoutError):
            await self._write_response(writer, 500, {"error": "internal error"})
        finally:
            try:
                writer.close()
            except OSError:
                pass

    async def _handle_sse(
        self, writer: asyncio.StreamWriter, text: str, ctx: SignalContext,
    ) -> None:
        """SSE 流式响应。"""
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/event-stream\r\n"
            b"Cache-Control: no-cache\r\n"
            b"Connection: keep-alive\r\n\r\n"
        )
        await writer.drain()

        result = await self._on_stream(text, ctx)
        if result is not None:
            async for chunk in result:
                data = f"data: {json.dumps({'chunk': chunk})}\n\n"
                writer.write(data.encode())
                await writer.drain()
            writer.write(b"data: [DONE]\n\n")
            await writer.drain()

    async def _write_response(
        self, writer: asyncio.StreamWriter, status: int, body: dict[str, Any],
    ) -> None:
        """写 HTTP JSON 响应。"""
        payload = json.dumps(body).encode()
        reason = _HTTP_REASONS.get(status, "OK")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n\r\n"
            .encode() + payload,
        )
        await writer.drain()

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """HTTP 无状态 — 存到内部 buffer 等下次请求返回。"""
        _logger.debug("HttpAdapter.send() no-op: HTTP req/resp模式下响应由 _on_message 返回值处理")

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """SSE 推送块（由 _handle_sse 内部处理）。"""
        _logger.debug("HttpAdapter.stream_chunk() no-op: SSE 由 _handle_sse 内部处理")

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """SSE 结束标记（由 _handle_sse 内部处理）。"""
        _logger.debug("HttpAdapter.stream_end() no-op: SSE 由 _handle_sse 内部处理")

    async def stop(self) -> None:
        """关闭 HTTP server。"""
        if self._server:
            self._server.close()
            self._server = None


__all__ = ["HttpAdapter"]
