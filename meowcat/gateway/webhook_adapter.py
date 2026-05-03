"""meowcat Gateway — WebhookAdapter（回调骨架适配器）。

接收 HTTP POST 回调，支持签名验证接口（子类实现）。
框架层只提供协议管道，飞书/微信等平台特定逻辑在应用层子类实现。
"""
# (c) 2025-2026 Axonant. MIT License.


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
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
}

_logger = logging.getLogger(__name__)


class WebhookAdapter:
    """Webhook 回调骨架 — HTTP POST 接收 + 可重写的验证/解析方法。

    子类化示例（meowagent 应用层）::

        class FeishuAdapter(WebhookAdapter):
            name = "feishu"

            def verify_signature(self, headers, body):
                # 飞书签名验证逻辑
                ...

            def parse_message(self, body):
                # 飞书消息格式解析
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

    # -- 可被子类重写的钩子 ------------------------------------------

    def verify_signature(self, headers: dict[str, str], body: bytes) -> bool:
        """验证回调签名。子类重写以添加平台特定验证（飞书/微信）。默认放行。"""
        return True

    def parse_message(self, body: dict[str, Any]) -> tuple[str, str]:
        """从回调 body 提取 (消息文本, 用户ID)。子类重写。"""
        return body.get("message", ""), body.get("user_id", "unknown")

    # -- Adapter 协议实现 --------------------------------------------

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动 HTTP server，监听 POST {path}。"""
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
        """处理单个 webhook POST 请求。"""
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=30)
            if not request_line:
                writer.close()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await self._respond(writer, 400)
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

            if method != "POST" or path != self.path:
                await self._respond(writer, 404)
                return

            # 签名验证
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
        except (ConnectionError, OSError, asyncio.TimeoutError):
            await self._respond(writer, 500)
        finally:
            try:
                writer.close()
            except OSError:
                pass

    @staticmethod
    async def _respond(writer: asyncio.StreamWriter, status: int) -> None:
        """发送简单 HTTP 响应。"""
        body = b"OK" if status == 200 else b""
        reason = _HTTP_REASONS.get(status, "OK")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
            .encode() + body,
        )
        await writer.drain()

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """Webhook 模式下 send 为 no-op（响应由回调返回值处理）。"""
        _logger.debug(
            "WebhookAdapter.send() no-op: webhook 模式响应由 _on_message 返回值处理")

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Webhook 模式下不支持流式。"""
        _logger.debug("WebhookAdapter.stream_chunk() no-op: webhook 不支持流式")

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Webhook 模式下不支持流式。"""
        _logger.debug("WebhookAdapter.stream_end() no-op: webhook 不支持流式")

    async def stop(self) -> None:
        """关闭 webhook server。"""
        if self._server:
            self._server.close()
            self._server = None


__all__ = ["WebhookAdapter"]
