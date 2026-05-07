# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus/gateway — WebhookAdapter (callback skeleton adapter).

Receives HTTP POST callbacks, supports signature verification interface (subclass implements).
The framework layer only provides the protocol pipe; platform-specific logic
(Feishu, WeChat, etc.) is implemented in application-layer subclasses.

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


class WebhookAdapter:
    """Webhook callback skeleton — HTTP POST receiver + overridable verify/parse methods.

    Subclass example (meowagent application layer)::

        class FeishuAdapter(WebhookAdapter):
            name = "feishu"

            def verify_signature(self, headers, body):
                # Feishu signature verification logic
                ...

            def parse_message(self, body):
                # Feishu message format parsing
                ...
    """

    name = "webhook"

    def __init__(
        self, host: str = "0.0.0.0", port: int = 8002, path: str = "/webhook",
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self._server: asyncio.AbstractServer | None = None

    # -- Hooks overridable by subclasses ----------------------------------------

    def verify_signature(self, headers: dict[str, str], body: bytes) -> bool:
        """Verify callback signature. Subclass overrides to add platform-specific
        verification (Feishu/WeChat). Default: always pass."""
        return True

    def parse_message(self, body: dict[str, Any]) -> tuple[str, str]:
        """Extract (message text, user id) from callback body. Subclass overrides."""
        return body.get("message", ""), body.get("user_id", "unknown")

    # -- Adapter protocol implementation --------------------------------------

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Start HTTP server, listen on POST {path}."""
        self._on_message = on_message
        self._on_stream = on_stream

        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await self._handle_webhook(reader, writer)

        self._server = await asyncio.start_server(
            handler, host=self.host, port=self.port,
        )

        async with self._server:
            await self._server.serve_forever()

    async def _handle_webhook(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single webhook POST request."""
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=GATEWAY_DEFAULT_TIMEOUT)
            if not request_line:
                writer.close()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await self._respond(writer, 400)
                return
            method, path = parts[0], parts[1]

            # Read headers
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                line_str = line.decode().strip()
                if not line_str:
                    break
                if ":" in line_str:
                    key, val = line_str.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            # Read body
            content_length = int(headers.get("content-length", "0"))
            body_raw = await asyncio.wait_for(
                reader.readexactly(content_length), timeout=10,
            ) if content_length > 0 else b""

            if method != "POST" or path != self.path:
                await self._respond(writer, 404)
                return

            # Signature verification
            if not self.verify_signature(headers, body_raw):
                await self._respond(writer, 403)
                return

            body = json.loads(body_raw.decode()) if body_raw else {}
            text, user_id = self.parse_message(body)

            ctx = SignalContext(
                session_id=f"{self.name}-{user_id}",
                platform=self.name,
                user_id=user_id,
            )

            reply = await self._on_message(text, ctx)
            await self._respond(writer, 200)

        except (json.JSONDecodeError, asyncio.TimeoutError):
            await self._respond(writer, 400)
        except (ConnectionError, OSError):
            await self._respond(writer, 500)
        finally:
            try:
                writer.close()
            except OSError:
                pass

    @staticmethod
    async def _respond(writer: asyncio.StreamWriter, status: int) -> None:
        """Send simple HTTP response."""
        body = b"OK" if status == 200 else b""
        reason = HTTP_REASONS.get(status, "OK")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
            .encode() + body,
        )
        await writer.drain()

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """send is a no-op in Webhook mode (response handled by callback return value)."""
        _logger.debug(
            "WebhookAdapter.send() no-op: webhook response handled by _on_message return value")

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Streaming not supported in Webhook mode."""
        _logger.debug(
            "WebhookAdapter.stream_chunk() no-op: webhook does not support streaming")

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Streaming not supported in Webhook mode."""
        _logger.debug(
            "WebhookAdapter.stream_end() no-op: webhook does not support streaming")

    async def stop(self) -> None:
        """Shut down webhook server."""
        if self._server:
            self._server.close()
            self._server = None


__all__ = ["WebhookAdapter"]

