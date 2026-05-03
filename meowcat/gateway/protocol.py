"""meowcat Gateway protocol layer — I/O abstraction between cat and outside world.

Gateway = the cat's skin, all protocol adapters plug into the same Gateway.
1 cat : 1 Gateway : N Adapters.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol, runtime_checkable


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

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
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
class GatewayProtocol(Protocol):
    """Gateway protocol — sole external I/O entry. 1:1 bound to one cat."""

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


__all__ = ["SignalContext", "IoAdapterProtocol", "GatewayProtocol"]
