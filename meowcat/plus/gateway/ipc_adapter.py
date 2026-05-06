# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus/gateway — IpcAdapter (Unix socket inter-process communication adapter).

For desktop app IPC. The framework layer only provides Unix socket pipes;
macOS sandbox, Windows named pipes, etc. are implemented by the desktop layer.

Moved from ``meowcat.gateway`` to ``meowcat.plus.gateway`` in v1.2.22 as an optional battery.
"""


from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext


class IpcAdapter:
    """IPC protocol adapter — Unix socket JSON-line protocol.

    Pure asyncio, zero external dependencies.
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
        """Start Unix socket server."""
        self._on_message = on_message
        self._on_stream = on_stream

        # Clean up old socket file
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
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single IPC connection — JSON-line protocol."""
        session_id = f"ipc-{id(writer)}"
        self._connections[session_id] = writer

        ctx = SignalContext(
            session_id=session_id,
            platform="ipc",
            user_id="desktop-user",
        )
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=300)
                if not line:
                    break

                try:
                    msg = json.loads(line.decode().strip())
                except json.JSONDecodeError:
                    continue
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


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
            except OSError:
                pass

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """Send JSON response."""
        writer = self._connections.get(session_id)
        if writer:
            payload = json.dumps({"reply": output}) + "\n"
            writer.write(payload.encode())
            await writer.drain()

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Send streaming text line."""
        writer = self._connections.get(session_id)
        if writer:
            payload = json.dumps({"chunk": chunk}) + "\n"
            writer.write(payload.encode())
            await writer.drain()

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Send stream end marker."""
        writer = self._connections.get(session_id)
        if writer:
            writer.write(b'{"end": true}\n')
            await writer.drain()

    async def stop(self) -> None:
        """Shut down IPC server and all connections."""
        for writer in list(self._connections.values()):
            try:
                writer.close()
            except OSError:
                pass
        self._connections.clear()
        if self._server:
            self._server.close()
            self._server = None
        # Clean up socket file
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass


__all__ = ["IpcAdapter"]

