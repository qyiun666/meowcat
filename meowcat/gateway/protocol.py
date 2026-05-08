# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Gateway protocol layer — I/O abstraction between colony and outside world.

Gateway = the colony's skin, all protocol adapters plug into the same Gateway.
1 Colony : 1 Gateway : N Adapters.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SignalContext:
    """Context injected into the cat with each external message. Carried implicitly by all signals.

    Core design: same cat, same Hippocampus, different session_id for different platforms.
    """

    session_id: str
    """Session identifier. e.g. ``"cli-20260503"`` / ``"feishu-group-abc"`` / ``"desktop-zt"``."""

    platform: str
    """Platform identifier. e.g. ``"cli"`` / ``"http"`` / ``"ws"`` / ``"feishu"`` / ``"wechat"`` / ``"desktop"``."""

    user_id: str = "unknown"
    """External user identifier."""

    target_cat: str | None = None
    """Target cat uid within the colony. None = delegate to FrontDesk.

    Set by Adapters that know which cat to route to (e.g. a Feishu bot
    always routes to analyst).  When None, Gateway delegates to FrontDesk
    for routing decision.
    """

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    """ISO 8601 timestamp. Auto-generated at construction."""


@runtime_checkable
class IoAdapterProtocol(Protocol):
    """I/O adapter protocol — Gateway plugin, handles send/receive for one protocol/pipe.

    Each Adapter instance independently manages its own connections/listeners. Gateway does not care
    how Adapter internally sends/receives, only requires it to bridge to cat's nervous system via callbacks.
    """

    name: str
    """Adapter unique identifier. Same name on mount overwrites."""

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """Start listen loop. Calls back on receiving external messages, blocks until stop().

        Args:
            on_message: called on complete message, returns cat's reply text
            on_stream:  called on streaming message, returns async iterator
        """
        ...

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """Send complete reply."""
        ...

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """Send streaming chunk."""
        ...

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """Streaming end marker."""
        ...

    async def stop(self) -> None:
        """Stop listening."""
        ...


@runtime_checkable
class FrontDeskProtocol(Protocol):
    """FrontDesk protocol — Gateway's built-in receptionist.

    All external messages flow through the FrontDesk.  When ``ctx.target_cat``
    is set, the default implementation forwards to that cat via
    ``colony.get_cat().perceive()``.  When unset, returns a placeholder reply.

    Application layer can subclass :class:`DefaultFrontDesk` or implement
    this protocol directly to add security gates, audit logging, rate
    limiting, or custom routing logic.
    """

    async def route(
        self,
        text: str,
        ctx: SignalContext,
        colony: Any,
    ) -> str | None:
        """Route an external message to a cat or return a placeholder reply.

        Args:
            text: Incoming message text.
            ctx: Signal context (session_id, platform, target_cat, etc.).
            colony: The Colony instance owning all cats.

        Returns:
            Reply string, or None for no reply.
        """
        ...


@runtime_checkable
class GatewayProtocol(Protocol):
    """Gateway protocol — sole external I/O entry. 1:1 bound to one colony."""

    async def start(self) -> None:
        """Start gateway, begin receiving messages from all Adapters."""
        ...

    async def stop(self) -> None:
        """Shut down gateway, stop all Adapters."""
        ...

    def mount_adapter(self, adapter: IoAdapterProtocol) -> None:
        """Mount a protocol adapter. Same name overwrites."""
        ...

    def unmount_adapter(self, name: str) -> None:
        """Unmount a protocol adapter. No-op if not found."""
        ...


__all__ = [
    "SignalContext",
    "IoAdapterProtocol",
    "FrontDeskProtocol",
    "GatewayProtocol",
    "HTTP_REASONS",
]


# RFC 7230 HTTP reason phrases — shared by all HTTP-based adapters
HTTP_REASONS: dict[int, str] = {
    200: "OK",
    400: "Bad Request",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
}
