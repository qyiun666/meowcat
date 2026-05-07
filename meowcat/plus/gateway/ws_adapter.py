# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus/gateway — WsAdapter (WebSocket bidirectional streaming dialogue adapter).

Pure asyncio WebSocket protocol implementation (RFC 6455 minimal subset), zero external dependencies.
Supports text frame send/receive + streaming push.

Moved from ``meowcat.gateway`` to ``meowcat.plus.gateway`` in v1.2.22 as an optional battery.
"""


from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import struct
from typing import Any, AsyncIterator, Awaitable, Callable

from meowcat.gateway.protocol import IoAdapterProtocol, SignalContext

# WebSocket frame opcodes
_OP_TEXT = 0x1
_OP_CLOSE = 0x8

# WebSocket GUID (RFC 6455 §4.2.2)
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _compute_accept(key: str) -> str:
    """Compute Sec-WebSocket-Accept value."""
    digest = hashlib.sha1((key + _WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def _encode_frame(payload: bytes, opcode: int = _OP_TEXT) -> bytes:
    """Encode WebSocket text frame (server→client, no mask)."""
    frame = bytearray()
    frame.append(0x80 | opcode)  # FIN + opcode

    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))

    frame.extend(payload)
    return bytes(frame)


def _decode_frame(data: bytes) -> tuple[int, bytes, bool]:
    """Decode WebSocket frame. Returns (opcode, payload, fin).

    Client→server frames MUST be masked.
    """
    if len(data) < 2:
        raise ValueError("frame too short")

    byte1, byte2 = data[0], data[1]
    fin = bool(byte1 & 0x80)
    opcode = byte1 & 0x0F
    masked = bool(byte2 & 0x80)
    length = byte2 & 0x7F

    offset = 2
    if length == 126:
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
    elif length == 127:
        length = struct.unpack(">Q", data[offset:offset + 8])[0]
        offset += 8

    if masked:
        mask_key = data[offset:offset + 4]
        offset += 4
        payload = bytearray(data[offset:offset + length])
        for i in range(len(payload)):
            payload[i] ^= mask_key[i % 4]
        return opcode, bytes(payload), fin
    else:
        return opcode, data[offset:offset + length], fin


class WsAdapter:
    """WebSocket protocol adapter — bidirectional streaming dialogue.

    Pure asyncio, zero external dependencies.
    """

    name = "ws"

    def __init__(self, host: str = "0.0.0.0", port: int = 8001) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self._connections: dict[str, asyncio.StreamWriter] = {}

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Start asyncio WebSocket server."""
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
        """Handle WebSocket connection: handshake → message loop."""
        session_id = f"ws-{id(writer)}"

        try:
            # HTTP Upgrade handshake
            request_data = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
            request_text = request_data.decode(errors="replace")
            headers = self._parse_http_headers(request_text)

            ws_key = headers.get("sec-websocket-key", "")
            if not ws_key:
                writer.close()
                return

            accept = _compute_accept(ws_key)
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            )
            writer.write(response.encode())
            await writer.drain()

            self._connections[session_id] = writer

            ctx = SignalContext(
                session_id=session_id,
                platform="ws",
                user_id=headers.get("x-user-id", "unknown"),
            )

            # Message loop
            buf = bytearray()
            while True:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=300)
                if not chunk:
                    break
                buf.extend(chunk)

                while len(buf) >= 2:
                    try:
                        opcode, payload, fin = _decode_frame(bytes(buf))
                    except (ValueError, struct.error):
                        # Frame incomplete, wait for more data
                        break

                    frame_size = self._frame_size(bytes(buf))
                    if len(buf) < frame_size:
                        break

                    buf = buf[frame_size:]

                    if opcode == _OP_CLOSE:
                        writer.write(_encode_frame(b"", _OP_CLOSE))
                        await writer.drain()
                        return

                    if opcode == _OP_TEXT:
                        text = payload.decode("utf-8")
                        # Streaming processing — message ↔ stream bidirectional fallback
                        result = await self._on_stream(text, ctx)
                        if result is not None:
                            async for chunk_text in result:
                                writer.write(_encode_frame(
                                    chunk_text.encode("utf-8")))
                                await writer.drain()
                        else:
                            reply = await self._on_message(text, ctx)
                            if reply:
                                writer.write(_encode_frame(
                                    reply.encode("utf-8")))
                                await writer.drain()
                        writer.write(_encode_frame(b"[DONE]"))
                        await writer.drain()

        except (asyncio.TimeoutError, ConnectionError, UnicodeDecodeError):
            pass
        finally:
            self._connections.pop(session_id, None)
            try:
                writer.close()
            except OSError:
                pass

    @staticmethod
    def _parse_http_headers(request_text: str) -> dict[str, str]:
        """Parse HTTP request headers into lowercase-keyed dict."""
        headers: dict[str, str] = {}
        for line in request_text.split("\r\n")[1:]:
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()
        return headers

    @staticmethod
    def _frame_size(data: bytes) -> int:
        """Calculate total byte size of a complete frame."""
        if len(data) < 2:
            return 0
        masked = bool(data[1] & 0x80)
        length = data[1] & 0x7F
        offset = 2
        if length == 126:
            if len(data) < 4:
                return 0
            length = struct.unpack(">H", data[2:4])[0]
            offset = 4
        elif length == 127:
            if len(data) < 10:
                return 0
            length = struct.unpack(">Q", data[2:10])[0]
            offset = 10
        # Check mask bit rather than assume
        if masked:
            offset += 4
        return offset + length

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """Send complete message frame."""
        writer = self._connections.get(session_id)
        if writer:
            writer.write(_encode_frame(
                json.dumps({"reply": output}).encode("utf-8"),
            ))
            await writer.drain()

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Send streaming text frame."""
        writer = self._connections.get(session_id)
        if writer:
            writer.write(_encode_frame(chunk.encode("utf-8")))
            await writer.drain()

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Send stream end marker."""
        writer = self._connections.get(session_id)
        if writer:
            writer.write(_encode_frame(b"[DONE]"))
            await writer.drain()

    async def stop(self) -> None:
        """Shut down WebSocket server and all connections."""
        for writer in list(self._connections.values()):
            try:
                writer.write(_encode_frame(b"", _OP_CLOSE))
                await writer.drain()
                writer.close()
            except (OSError, ConnectionError):
                pass
        self._connections.clear()
        if self._server:
            self._server.close()
            self._server = None


__all__ = ["WsAdapter"]

