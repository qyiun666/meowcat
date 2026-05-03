"""meowcat Gateway — IpcAdapter（Unix socket 进程间通信适配器）。

供桌面 App 进程间通信。框架层只提供 Unix socket 管道，
macOS 沙盒、Windows named pipe 等由桌面层实现。
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import AdapterProtocol, SignalContext


class IpcAdapter:
    """IPC 协议适配器 — Unix socket JSON 行协议。

    纯 asyncio，零外部依赖。
    """

    name = "ipc"

    def __init__(self, socket_path: str = "/tmp/meowcat.sock") -> None:
        self.socket_path = socket_path
        self._server: asyncio.AbstractServer | None = None
        self._connections: dict[str, asyncio.StreamWriter] = {}

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动 Unix socket server。"""
        self._on_message = on_message
        self._on_stream = on_stream

        # 清理旧的 socket 文件
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass

        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await self._handle_connection(reader, writer)

        self._server = await asyncio.start_unix_server(
            handler, path=self.socket_path,
        )

        async with self._server:
            await self._server.serve_forever()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """处理单个 IPC 连接 — JSON 行协议。"""
        session_id = f"ipc-{id(writer)}"
        self._connections[session_id] = writer

        ctx = SignalContext(
            session_id=session_id,
            platform="ipc",
            user_id="desktop-user",
        )

        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=300)
                if not line:
                    break

                try:
                    msg = json.loads(line.decode().strip())
                except json.JSONDecodeError:
                    continue

                text = msg.get("message", "") if isinstance(
                    msg, dict) else str(msg)
                if not text:
                    continue

                reply = await self._on_message(text, ctx)
                if reply:
                    payload = json.dumps({"reply": reply}) + "\n"
                    writer.write(payload.encode())
                    await writer.drain()

        except (asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            self._connections.pop(session_id, None)
            try:
                writer.close()
            except Exception:
                pass

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """发送 JSON 响应。"""
        writer = self._connections.get(session_id)
        if writer:
            payload = json.dumps({"reply": output}) + "\n"
            writer.write(payload.encode())
            await writer.drain()

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """发送流式文本行。"""
        writer = self._connections.get(session_id)
        if writer:
            payload = json.dumps({"chunk": chunk}) + "\n"
            writer.write(payload.encode())
            await writer.drain()

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """发送流式结束标记。"""
        writer = self._connections.get(session_id)
        if writer:
            writer.write(b'{"end": true}\n')
            await writer.drain()

    async def stop(self) -> None:
        """关闭 IPC server 及所有连接。"""
        for writer in list(self._connections.values()):
            try:
                writer.close()
            except Exception:
                pass
        self._connections.clear()
        if self._server:
            self._server.close()
            self._server = None
        # 清理 socket 文件
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass


__all__ = ["IpcAdapter"]
