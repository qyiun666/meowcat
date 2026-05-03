"""meowcat Gateway — CliAdapter（stdin/stdout 对话适配器）。

替代应用层内嵌的 CLI 循环。纯标准库，零外部依赖。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext


class CliAdapter:
    """CLI 协议适配器 — stdin/stdout 对话。

    纯标准库 stdin.readline() + print()。
    """

    name = "cli"

    def __init__(self) -> None:
        self._running = False

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动 stdin.readline 循环。"""
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
                session_id=f"cli-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                platform="cli",
                user_id="cli-user",
            )

            reply = await self._on_message(text, ctx)
            if reply:
                await self.send(reply, ctx.session_id)

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """输出到 stdout。"""
        print(output, flush=True)

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """流式块输出到 stdout（不换行）。"""
        print(chunk, end="", flush=True)

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """流式结束，补一个换行。"""
        print(flush=True)

    async def stop(self) -> None:
        """停止 stdin 读取循环。"""
        self._running = False


__all__ = ["CliAdapter"]
