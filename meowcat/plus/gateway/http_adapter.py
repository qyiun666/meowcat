# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus/gateway — HttpAdapter (HTTP POST /chat JSON protocol adapter).

Non-streaming request/response: JSON body ``{"message": "..."}`` → JSON response ``{"reply": "..."}``.
Optional SSE for streaming (``Accept: text/event-stream`` → stream_chunk push chunk by chunk).

Moved from ``meowcat.gateway`` to ``meowcat.plus.gateway`` in v1.2.22 as an optional battery.
"""


from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.constants import GATEWAY_DEFAULT_TIMEOUT
from meowcat.gateway.protocol import HTTP_REASONS, IoAdapterProtocol, SignalContext

_logger = logging.getLogger(__name__)


class HttpAdapter:
    """HTTP protocol adapter — accepts HTTP POST /chat requests.

    Pure asyncio, zero external dependencies.
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
        """Start asyncio HTTP server, listening on POST /chat."""
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
        """Handle a single HTTP connection."""
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=GATEWAY_DEFAULT_TIMEOUT)
            if not request_line:
                writer.close()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await self._write_response(writer, 400, {"error": "bad request"})
                return
            method, path = parts[0], parts[1]

            # read headers
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                line_str = line.decode().strip()
                if not line_str:
                    break
                if ":" in line_str:
                    key, val = line_str.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            # read body
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
                # SSE streaming response
                await self._handle_sse(writer, text, ctx)
            else:
                # standard JSON response
                reply = await self._on_message(text, ctx)
                await self._write_response(writer, 200, {"reply": reply or ""})

        except (json.JSONDecodeError, asyncio.TimeoutError):
            await self._write_response(writer, 400, {"error": "invalid json"})
        except (ConnectionError, OSError):
            await self._write_response(writer, 500, {"error": "internal error"})
        finally:
            try:
                writer.close()
            except OSError:
                pass

    async def _handle_sse(
        self, writer: asyncio.StreamWriter, text: str, ctx: SignalContext,
    ) -> None:
        """SSE streaming response."""
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
        """Write HTTP JSON response."""
        payload = json.dumps(body).encode()
        reason = HTTP_REASONS.get(status, "OK")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n\r\n"
            .encode() + payload,
        )
        await writer.drain()

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """HTTP is stateless — store in internal buffer for next request to return."""
        _logger.debug(
            "HttpAdapter.send() no-op: in HTTP req/resp mode, response handled by _on_message return value")

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """SSE push chunk (handled internally by _handle_sse)."""
        _logger.debug(
            "HttpAdapter.stream_chunk() no-op: SSE handled internally by _handle_sse")

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """SSE end marker (handled internally by _handle_sse)."""
        _logger.debug(
            "HttpAdapter.stream_end() no-op: SSE handled internally by _handle_sse")

    async def stop(self) -> None:
        """Close HTTP server."""
        if self._server:
            self._server.close()
            self._server = None


__all__ = ["HttpAdapter"]

