# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Gateway subsystem — the cat's skin (sole external I/O entry/exit).

Gateway is the only I/O abstraction layer between the cat and the outside world.
All protocol adapters (HTTP / WebSocket / Webhook / CLI / IPC) plug into the same Gateway.

**1 cat : 1 Gateway : N Adapters.**

Concrete adapters (HttpAdapter, WsAdapter, etc.) moved to ``meowcat.plus.gateway``
in v1.2.22 as optional batteries. Use::

    from meowcat.plus.gateway import HttpAdapter, CliAdapter

Usage example::

    from meowcat import create_cat, Gateway
    from meowcat.plus.gateway import HttpAdapter, CliAdapter

    cat = create_cat("my-cat", cerebrum=MyBrain())
    gw = Gateway(cat)
    gw.mount_adapter(HttpAdapter(port=8000))
    gw.mount_adapter(CliAdapter())
    await gw.start()  # blocking, all Adapters run in parallel
"""


from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict

from meowcat.gateway.protocol import (
    IoAdapterProtocol,
    GatewayProtocol,
    SignalContext,
)

if TYPE_CHECKING:
    from meowcat.assembly import CatBase


class Gateway:
    """The cat's skin — sole external I/O entry/exit.

    Not an organ (not mounted to OrganHost); an independent subsystem composing with CatBase, not inheriting.
    """

    def __init__(self, cat: CatBase) -> None:
        self.cat = cat
        self._adapters: Dict[str, IoAdapterProtocol] = {}

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
            tasks.append(asyncio.create_task(
                adapter.serve(self._on_message, self._on_stream),
            ))
        # all Adapters run in parallel, any exception propagates
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """Stop all Adapters."""
        for adapter in self._adapters.values():
            await adapter.stop()

    # -- Internal callbacks (Adapter → cat nervous system) -----------------------------

    async def _on_message(self, text: str, ctx: SignalContext) -> str | None:
        """Receive external message → inject into cat → return reply."""
        async for event in self.cat.perceive(text, context=ctx):
            if event.kind == "output":
                return event.content
            if event.kind == "short_circuit" and event.reply:
                return event.reply
        return None

    async def _on_stream(
        self, text: str, ctx: SignalContext,
    ) -> AsyncIterator[str] | None:
        """Streaming version — iterate event by event.

        Concrete behavior depends on how Purr.stream() / Mouth.speak() yield
        in Pipeline Stages. This only iterates perceive() results.
        """
        async for event in self.cat.perceive(text, context=ctx):
            if event.kind == "output":
                yield event.content
            elif event.kind == "thinking":
                yield event.content


__all__ = [
    "Gateway",
    "SignalContext",
    "IoAdapterProtocol",
    "GatewayProtocol",
]

