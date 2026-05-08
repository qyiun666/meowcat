# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Gateway subsystem — the colony's skin (sole external I/O entry/exit).

Gateway is the only I/O abstraction layer between the colony and the outside world.
All protocol adapters (HTTP / WebSocket / Webhook / CLI / IPC) plug into the same Gateway.

**1 Colony : 1 Gateway : N Adapters.**

All messages pass through the FrontDesk (a Protocol + Pluggable receptionist).
When ``ctx.target_cat`` is set, the default FrontDesk forwards to that cat.
When unset, it returns a placeholder reply.

Concrete adapters (HttpAdapter, WsAdapter, etc.) moved to ``meowcat.plus.gateway``
in v1.2.22 as optional batteries. Use::

    from meowcat.plus.gateway import HttpAdapter, CliAdapter

Usage example::

    from meowcat import Colony, Gateway
    from meowcat.plus.gateway import HttpAdapter
    from meowcat.gateway.front_desk import DefaultFrontDesk

    colony = Colony("my-colony")
    gw = Gateway(colony)  # uses DefaultFrontDesk
    gw.mount_adapter(HttpAdapter(port=8000))
    await gw.start()  # blocking, all Adapters run in parallel
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.gateway.protocol import (
    FrontDeskProtocol,
    GatewayProtocol,
    IoAdapterProtocol,
    SignalContext,
)

if TYPE_CHECKING:
    from meowcat.colony import Colony


class Gateway:
    """The colony's skin — sole external I/O entry/exit.

    Not an organ (not mounted to OrganHost); an independent subsystem
    composing with Colony, not inheriting.

    All messages pass through the FrontDesk (Protocol + Pluggable).
    Application layer swaps ``front_desk`` to add security gates,
    audit logging, rate limiting, or custom routing.
    """

    def __init__(
        self,
        colony: Colony,
        front_desk: FrontDeskProtocol | None = None,
    ) -> None:
        self.colony = colony
        self._front_desk: FrontDeskProtocol = front_desk or DefaultFrontDesk()
        self._adapters: dict[str, IoAdapterProtocol] = {}

    @property
    def front_desk(self) -> FrontDeskProtocol:
        """The FrontDesk receptionist (read-only after construction)."""
        return self._front_desk

    # -- Adapter management --------------------------------------------------

    def mount_adapter(self, adapter: IoAdapterProtocol) -> None:
        """Mount a protocol adapter. Same name overwrites."""
        self._adapters[adapter.name] = adapter

    def unmount_adapter(self, name: str) -> None:
        """Unmount a protocol adapter. No-op if not found."""
        self._adapters.pop(name, None)

    @property
    def adapter_names(self) -> list[str]:
        """List of mounted adapter names."""
        return list(self._adapters.keys())

    # -- Lifecycle ----------------------------------------------------

    async def start(self) -> None:
        """Start serve() loops of all Adapters, running in parallel."""
        if not self._adapters:
            return
        tasks = []
        for adapter in self._adapters.values():
            tasks.append(
                asyncio.create_task(
                    adapter.serve(self._on_message, self._on_stream),
                )
            )
        # all Adapters run in parallel, any exception propagates
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop all Adapters."""
        for adapter in self._adapters.values():
            await adapter.stop()

    # -- Internal callbacks (Adapter → FrontDesk → cat nervous system) --------

    async def _on_message(self, text: str, ctx: SignalContext) -> str | None:
        """Receive external message → FrontDesk.route() → return reply."""
        return await self._front_desk.route(text, ctx, self.colony)

    async def _on_stream(
        self,
        text: str,
        ctx: SignalContext,
    ) -> AsyncIterator[str] | None:
        """Streaming version — currently delegates to non-streaming route().

        Future: FrontDesk may gain a ``route_stream()`` method for
        streaming-to-streaming pass-through.
        """
        reply = await self._front_desk.route(text, ctx, self.colony)
        if reply is not None:

            async def _wrap():
                yield reply

            return _wrap()
        return None


__all__ = [
    "Gateway",
    "SignalContext",
    "IoAdapterProtocol",
    "FrontDeskProtocol",
    "GatewayProtocol",
]
