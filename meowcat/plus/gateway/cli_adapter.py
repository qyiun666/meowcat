"""meowcat plus/gateway — CliAdapter (stdin/stdout dialogue adapter).

Replaces app-layer embedded CLI loop. Pure stdlib, zero external dependencies.

Moved from ``meowcat.gateway`` to ``meowcat.plus.gateway`` in v1.2.22 as an optional battery.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext


class CliAdapter:
    """CLI protocol adapter — stdin/stdout dialogue or async queue (Textual TUI).

    Mode ``"stdio"`` (default): reads from stdin via ``run_in_executor``.
    Mode ``"queue"``: reads from ``asyncio.Queue``, non-blocking for Textual TUI.
    """

    name = "cli"

    def __init__(self, mode: str = "stdio") -> None:
        if mode not in ("stdio", "queue"):
            raise ValueError(
                f"CliAdapter mode must be 'stdio' or 'queue', got {mode!r}"
            )
        self._mode = mode
        self._running = False
        self._queue: asyncio.Queue[str] | None = None
        if mode == "queue":
            self._queue = asyncio.Queue()

    async def enqueue(self, message: str) -> None:
        """Feed a message from Textual widget (queue mode only).

        Raises RuntimeError if mode is not ``"queue"``.
        """
        if self._queue is None:
            raise RuntimeError("enqueue() requires mode='queue'")
        await self._queue.put(message)

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Start listen loop — stdin.readline or asyncio.Queue.get."""
        self._on_message = on_message
        self._on_stream = on_stream
        self._running = True

        if self._mode == "queue":
            await self._serve_queue(on_message, on_stream)
        else:
            await self._serve_stdio(on_message, on_stream)

    async def _serve_stdio(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Stdio mode: blocking stdin.readline in executor."""
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except EOFError:
                break

            if not line:
                break

            text = line.strip()
            if not text:
                continue

            ctx = SignalContext(
                session_id=f"cli-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                platform="cli",
                user_id="cli-user",
            )

            reply = await on_message(text, ctx)
            if reply:
                await self.send(reply, ctx.session_id)
            else:
                stream = await on_stream(text, ctx)
                if stream is not None:
                    async for chunk in stream:
                        await self.stream_chunk(chunk, ctx.session_id)
                    await self.stream_end(ctx.session_id)

    async def _serve_queue(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Queue mode: async asyncio.Queue.get, non-blocking for Textual TUI."""
        assert self._queue is not None  # ensured by __init__

        while self._running:
            try:
                text = await self._queue.get()
            except asyncio.CancelledError:
                break

            ctx = SignalContext(
                session_id=f"cli-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                platform="cli",
                user_id="cli-user",
            )

            reply = await on_message(text, ctx)
            if reply:
                await self.send(reply, ctx.session_id)
            else:
                stream = await on_stream(text, ctx)
                if stream is not None:
                    async for chunk in stream:
                        await self.stream_chunk(chunk, ctx.session_id)
                    await self.stream_end(ctx.session_id)

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """Output to stdout."""
        print(output, flush=True)

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Stream chunk output to stdout (no newline)."""
        print(chunk, end="", flush=True)

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Stream end, append a newline."""
        print(flush=True)

    async def stop(self) -> None:
        """Stop stdin read loop."""
        self._running = False


__all__ = ["CliAdapter"]
