"""meowcat Gateway — CliAdapter (stdin/stdout dialogue adapter).

Replaces app-layer embedded CLI loop. Pure stdlib, zero external dependencies.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext


class CliAdapter:
    """CLI protocol adapter — stdin/stdout dialogue.

    Pure stdlib stdin.readline() + print().
    """

    name = "cli"

    def __init__(self) -> None:
        self._running = False

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Start stdin.readline loop."""
        self._on_message = on_message
        self._on_stream = on_stream
        self._running = True

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

            reply = await self._on_message(text, ctx)
            if reply:
                await self.send(reply, ctx.session_id)

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
