# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Colony federation transport layer built-in implementations (v1.0.12, moved to colony/ v1.2.37).

Provides two built-in transports:
- TCPSocketTransport: stdlib asyncio TCP, for two hosts on the same network
- RedisPubSubTransport: Redis pub/sub, for production deployment (optional redis dependency)

All implement the FederationTransport protocol.
"""


from __future__ import annotations

import asyncio
import json
import logging
import ssl
import uuid
from typing import Any, AsyncIterator

from meowcat.constants import TRANSPORT_REQUEST_TIMEOUT
from meowcat.protocols_storage import FederationTransport

logger = logging.getLogger("meowcat.colony.federation")

# ---------------------------------------------------------------------------
# Wire protocol constants
# ---------------------------------------------------------------------------

_MSG_DELIMITER = b"\n"


# ---------------------------------------------------------------------------
# TCPSocketTransport
# ---------------------------------------------------------------------------

class TCPSocketTransport:
    """TCP socket-based Colony federation transport.

    Each end starts a TCP server to receive messages; on publish it connects
    as a TCP client to the remote to send.

    Thread safety: use within a single event loop.

    .. warning::

        By default, traffic is **plaintext** — no encryption. For production
        deployments, pass an ``ssl_context`` to enable TLS::

            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain("cert.pem", "key.pem")
            t = TCPSocketTransport(host="0.0.0.0", port=9000, ssl_context=ctx)

    Typical usage::

        # Colony A (host-a, port 9000)
        t_a = TCPSocketTransport(host="0.0.0.0", port=9000)
        t_a.register_peer("colony-b", "host-b", 9001)
        await t_a.start()

        # Colony B (host-b, port 9001)
        t_b = TCPSocketTransport(host="0.0.0.0", port=9001)
        t_b.register_peer("colony-a", "host-a", 9000)
        await t_b.start()
    """

    def __init__(
        self, *,
        host: str = "0.0.0.0",
        port: int = 9000,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._ssl_context = ssl_context
        # colony_id → (host, port)
        self._peers: dict[str, tuple[str, int]] = {}
        self._server: asyncio.AbstractServer | None = None
        self._incoming: asyncio.Queue[dict] = asyncio.Queue()
        self._pending_requests: dict[str, asyncio.Future] = {}
        # peer_id → (reader, writer) connection pool
        self._connections: dict[str,
                                tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self._conn_locks: dict[str, asyncio.Lock] = {}

    # -- Peer registration ----------------------------------------------

    def register_peer(self, colony_id: str, host: str, port: int) -> None:
        """Register the address of a remote colony. Used during publish to
        look up the connection target by colony_id.

        Args:
            colony_id: Remote colony identifier.
            host: Remote host address.
            port: Remote TCP port.
        """
        self._peers[colony_id] = (host, port)

    def unregister_peer(self, colony_id: str) -> None:
        """Remove remote colony address."""
        self._peers.pop(colony_id, None)

    # -- Lifecycle ------------------------------------------------------

    async def start(self) -> None:
        """Start TCP server listening.

        If ``ssl_context`` was provided at construction, TLS is enabled.
        """
        self._server = await asyncio.start_server(
            self._handle_connection, self._host, self._port,
            ssl=self._ssl_context,
        )
        tls_status = "TLS " if self._ssl_context else ""
        logger.info("TCPSocketTransport %slistening on %s:%d",
                    tls_status, self._host, self._port)

    async def stop(self) -> None:
        """Stop TCP server and close all pooled connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close all pooled connections
        for peer_id, (_reader, writer) in list(self._connections.items()):
            try:
                writer.close()
            except Exception:
                pass
        self._connections.clear()
        self._conn_locks.clear()

        # Cancel all pending requests
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.cancel()
        self._pending_requests.clear()

    # -- Publish --------------------------------------------------------

    async def publish(self, topic: str, payload: dict) -> None:
        """Send a message to a specified colony (fire-and-forget).

        Uses pooled persistent TCP connections — reuses existing connections
        and reconnects on failure.

        Args:
            topic: Target colony_id.
            payload: Message payload.

        Raises:
            ValueError: colony_id not registered.
            ConnectionError: Cannot connect to remote.
        """
        if topic not in self._peers:
            raise ValueError(f"Unknown peer colony: {topic}")

        host, port = self._peers[topic]
        line = (json.dumps(payload, ensure_ascii=False) + "\n").encode()

        try:
            writer = await self._get_writer(topic, host, port)
            writer.write(line)
            await writer.drain()
        except Exception:
            # Connection stale — evict and retry once
            self._connections.pop(topic, None)
            try:
                writer = await self._get_writer(topic, host, port)
                writer.write(line)
                await writer.drain()
            except Exception:
                logger.exception(
                    "Failed to publish to %s (%s:%d)", topic, host, port)
                self._connections.pop(topic, None)
                raise ConnectionError(
                    f"Failed to publish to {topic}") from None

    async def request(self, topic: str, payload: dict) -> dict:
        """Send a request to a specified colony and wait for response.

        Automatically injects request_id into payload, waits for the remote
        to respond with the same request_id.

        Args:
            topic: Target colony_id.
            payload: Request payload (without request_id).

        Returns:
            Response dict from the remote.

        Raises:
            ValueError: colony_id not registered.
            ConnectionError: Cannot connect to remote.
            TimeoutError: Timed out waiting for response.
        """
        request_id = uuid.uuid4().hex
        payload["request_id"] = request_id

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = fut

        try:
            await self.publish(topic, payload)
            return await asyncio.wait_for(fut, timeout=TRANSPORT_REQUEST_TIMEOUT)
        finally:
            self._pending_requests.pop(request_id, None)

    # -- Subscribe ------------------------------------------------------

    async def subscribe(self, topic: str) -> AsyncIterator[dict]:
        """Subscribe to this colony's inbound message stream.

        Continuously reads from the TCP inbound queue and yields messages.
        Does not filter by topic (TCP is connectionless; all inbound messages
        are consumed by subscribe).

        Args:
            topic: This colony_id (for logging).

        Yields:
            Payload dict of each inbound message.
        """
        while True:
            msg = await self._incoming.get()
            yield msg

    # -- Internal -------------------------------------------------------

    async def _get_writer(
        self, peer_id: str, host: str, port: int,
    ) -> asyncio.StreamWriter:
        """Get or create a pooled TCP writer for peer.

        Reuses existing connection if alive; creates a new one otherwise.
        Uses per-peer lock to avoid concurrent connection creation.
        """
        conn = self._connections.get(peer_id)
        if conn is not None:
            _reader, writer = conn
            if not writer.is_closing():
                return writer
            # Stale — close and evict
            try:
                writer.close()
            except Exception:
                pass
            self._connections.pop(peer_id, None)

        # Serialise connection creation per peer
        lock = self._conn_locks.setdefault(peer_id, asyncio.Lock())
        async with lock:
            # Double-check after acquiring lock
            conn = self._connections.get(peer_id)
            if conn is not None and not conn[1].is_closing():
                return conn[1]

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=self._ssl_context),
                timeout=TRANSPORT_REQUEST_TIMEOUT,
            )
            self._connections[peer_id] = (reader, writer)
            return writer

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """Handle an inbound TCP connection."""
        try:
            data = await asyncio.wait_for(
                reader.readline(), timeout=TRANSPORT_REQUEST_TIMEOUT,
            )
            if not data:
                return

            payload = json.loads(data.decode())

            # If it's a response (has request_id), wake the waiter
            req_id = payload.get("request_id")
            if req_id and req_id in self._pending_requests:
                fut = self._pending_requests[req_id]
                if not fut.done():
                    fut.set_result(payload)
            else:
                # Otherwise it's an inbound request, put in queue
                await self._incoming.put(payload)

                # If it's a request (with reply_to), no need to handle here
                # Colony layer federation dispatcher handles it and publishes response
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
    """Redis pub/sub-based Colony federation transport.

    Depends on the ``redis`` package (``pip install redis``). Not a hard
    dependency at the framework level.

    Typical usage::

        import redis.asyncio as redis

        r = redis.Redis(host="localhost", port=6379)
        t = RedisPubSubTransport(r, colony_id="colony-a")
        await t.start()
    """

    def __init__(self, client: Any, *, colony_id: str) -> None:
        """Construct Redis transport.

        Args:
            client: ``redis.asyncio.Redis`` instance.
            colony_id: This colony identifier (used as channel prefix).
        """
        self._client = client
        self._colony_id = colony_id
        self._pubsub: Any = None
        self._listener_task: asyncio.Task | None = None
        self._incoming: asyncio.Queue[dict] = asyncio.Queue()

    @property
    def _channel(self) -> str:
        """This colony's inbound channel name."""
        return f"meowcat:federation:{self._colony_id}"

    async def start(self) -> None:
        """Start Redis pub/sub listener."""
        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(self._channel)
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        """Stop Redis pub/sub listener."""
        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
        if self._pubsub:
            await self._pubsub.unsubscribe(self._channel)
            self._pubsub = None

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a message to a specified colony.

        Args:
            topic: Target colony_id.
            payload: Message payload.
        """
        channel = f"meowcat:federation:{topic}"
        line = json.dumps(payload, ensure_ascii=False)
        await self._client.publish(channel, line)

    async def subscribe(self, topic: str) -> AsyncIterator[dict]:
        """Subscribe to this colony's inbound message stream.

        Args:
            topic: This colony_id (for logging).

        Yields:
            Payload dict of each inbound message.
        """
        while True:
            msg = await self._incoming.get()
            yield msg

    async def _listen(self) -> None:
        """Background listener for Redis pub/sub messages."""
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

