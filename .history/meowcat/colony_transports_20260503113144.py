"""meowcat Colony 联邦传输层内置实现（v1.0.12）。

提供两种内置传输：
- TCPSocketTransport: 标准库 asyncio TCP，同网络内两台主机
- RedisPubSubTransport: Redis pub/sub，生产部署（可选依赖 redis）

全部实现 FederationTransport 协议。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncIterator

from meowcat.protocols_storage import FederationTransport

logger = logging.getLogger("meowcat.colony.federation")

# ---------------------------------------------------------------------------
# 线协议常量
# ---------------------------------------------------------------------------

_MSG_DELIMITER = b"\n"
_REQUEST_TIMEOUT = 30.0  # 秒


# ---------------------------------------------------------------------------
# TCPSocketTransport
# ---------------------------------------------------------------------------

class TCPSocketTransport:
    """基于 TCP socket 的 Colony 联邦传输。

    每端启动一个 TCP server 接收消息，publish 时作为 TCP client 连接远端发送。

    线程安全：单事件循环内使用。

    典型用法::

        # Colony A (host-a, port 9000)
        t_a = TCPSocketTransport(host="0.0.0.0", port=9000)
        t_a.register_peer("colony-b", "host-b", 9001)
        await t_a.start()

        # Colony B (host-b, port 9001)
        t_b = TCPSocketTransport(host="0.0.0.0", port=9001)
        t_b.register_peer("colony-a", "host-a", 9000)
        await t_b.start()
    """

    def __init__(self, *, host: str = "0.0.0.0", port: int = 9000) -> None:
        self._host = host
        self._port = port
        # colony_id → (host, port)
        self._peers: dict[str, tuple[str, int]] = {}
        self._server: asyncio.AbstractServer | None = None
        self._incoming: asyncio.Queue[dict] = asyncio.Queue()
        self._pending_requests: dict[str, asyncio.Future] = {}

    # -- 对端注册 -------------------------------------------------------

    def register_peer(self, colony_id: str, host: str, port: int) -> None:
        """注册远端 colony 的地址。publish 时根据 colony_id 查找连接目标。

        Args:
            colony_id: 远端 colony 标识。
            host: 远端主机地址。
            port: 远端 TCP 端口。
        """
        self._peers[colony_id] = (host, port)

    def unregister_peer(self, colony_id: str) -> None:
        """移除远端 colony 地址。"""
        self._peers.pop(colony_id, None)

    # -- 生命周期 -------------------------------------------------------

    async def start(self) -> None:
        """启动 TCP server 监听。"""
        self._server = await asyncio.start_server(
            self._handle_connection, self._host, self._port,
        )
        logger.info("TCPSocketTransport listening on %s:%d",
                    self._host, self._port)

    async def stop(self) -> None:
        """停止 TCP server。"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # 取消所有未完成的请求
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.cancel()
        self._pending_requests.clear()

    # -- publish --------------------------------------------------------

    async def publish(self, topic: str, payload: dict) -> None:
        """向指定 colony 发送消息（fire-and-forget）。

        连接远端 TCP server，发送 JSON 行后关闭连接。

        Args:
            topic: 目标 colony_id。
            payload: 消息负载。

        Raises:
            ValueError: colony_id 未注册。
            ConnectionError: 无法连接远端。
        """
        if topic not in self._peers:
            raise ValueError(f"Unknown peer colony: {topic}")

        host, port = self._peers[topic]
        line = (json.dumps(payload, ensure_ascii=False) + "\n").encode()

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=_REQUEST_TIMEOUT,
            )
            writer.write(line)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception:
            logger.exception(
                "Failed to publish to %s (%s:%d)", topic, host, port)
            raise ConnectionError(f"Failed to publish to {topic}") from None

    async def request(self, topic: str, payload: dict) -> dict:
        """向指定 colony 发送请求并等待响应。

        在 payload 中自动注入 request_id，等待远端回传同 request_id 的响应。

        Args:
            topic: 目标 colony_id。
            payload: 请求负载（不含 request_id）。

        Returns:
            远端回传的响应 dict。

        Raises:
            ValueError: colony_id 未注册。
            ConnectionError: 无法连接远端。
            TimeoutError: 等待响应超时。
        """
        request_id = uuid.uuid4().hex
        payload["request_id"] = request_id

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = fut

        try:
            await self.publish(topic, payload)
            return await asyncio.wait_for(fut, timeout=_REQUEST_TIMEOUT)
        finally:
            self._pending_requests.pop(request_id, None)

    # -- subscribe ------------------------------------------------------

    async def subscribe(self, topic: str) -> AsyncIterator[dict]:
        """订阅本 colony 的入站消息流。

        持续从 TCP 入站队列中读取消息并 yield。
        不按 topic 过滤（TCP 是无连接的，所有入站消息由 subscribe 消费）。

        Args:
            topic: 本 colony_id（用于日志）。

        Yields:
            每条入站消息的 payload dict。
        """
        while True:
            msg = await self._incoming.get()
            yield msg

    # -- 内部 -----------------------------------------------------------

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """处理一条 TCP 入站连接。"""
        try:
            data = await asyncio.wait_for(
                reader.readline(), timeout=_REQUEST_TIMEOUT,
            )
            if not data:
                return

            payload = json.loads(data.decode())

            # 如果是响应（含 request_id），唤醒等待方
            req_id = payload.get("request_id")
            if req_id and req_id in self._pending_requests:
                fut = self._pending_requests[req_id]
                if not fut.done():
                    fut.set_result(payload)
            else:
                # 否则是入站请求，放入队列
                await self._incoming.put(payload)

                # 如果是请求（带 reply_to），不需要在此处理
                # 由 Colony 层的联邦调度器处理后再 publish 响应
        except asyncio.TimeoutError:
            pass
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from peer")
        except Exception:
            logger.exception("Error handling TCP connection")
        finally:
            writer.close()
            await writer.wait_closed()


# ---------------------------------------------------------------------------
# RedisPubSubTransport
# ---------------------------------------------------------------------------

class RedisPubSubTransport:
    """基于 Redis pub/sub 的 Colony 联邦传输。

    依赖 ``redis`` 包（``pip install redis``）。框架层不强制依赖。

    典型用法::

        import redis.asyncio as redis

        r = redis.Redis(host="localhost", port=6379)
        t = RedisPubSubTransport(r, colony_id="colony-a")
        await t.start()
    """

    def __init__(self, client: Any, *, colony_id: str) -> None:
        """构造 Redis 传输。

        Args:
            client: ``redis.asyncio.Redis`` 实例。
            colony_id: 本 colony 标识（用作 channel 前缀）。
        """
        self._client = client
        self._colony_id = colony_id
        self._pubsub: Any = None
        self._listener_task: asyncio.Task | None = None
        self._incoming: asyncio.Queue[dict] = asyncio.Queue()

    @property
    def _channel(self) -> str:
        """本 colony 的入站 channel 名。"""
        return f"meowcat:federation:{self._colony_id}"

    async def start(self) -> None:
        """启动 Redis pub/sub 监听。"""
        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(self._channel)
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        """停止 Redis pub/sub 监听。"""
        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
        if self._pubsub:
            await self._pubsub.unsubscribe(self._channel)
            self._pubsub = None

    async def publish(self, topic: str, payload: dict) -> None:
        """向指定 colony 发布消息。

        Args:
            topic: 目标 colony_id。
            payload: 消息负载。
        """
        channel = f"meowcat:federation:{topic}"
        line = json.dumps(payload, ensure_ascii=False)
        await self._client.publish(channel, line)

    async def subscribe(self, topic: str) -> AsyncIterator[dict]:
        """订阅本 colony 的入站消息流。

        Args:
            topic: 本 colony_id（用于日志）。

        Yields:
            每条入站消息的 payload dict。
        """
        while True:
            msg = await self._incoming.get()
            yield msg

    async def _listen(self) -> None:
        """后台监听 Redis pub/sub 消息。"""
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from Redis pub/sub")
                    continue
                await self._incoming.put(payload)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Redis pub/sub listener error")


__all__ = ["TCPSocketTransport", "RedisPubSubTransport"]
