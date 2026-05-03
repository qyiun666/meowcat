"""meowcat event bus — cat's neural signal system.

Zero business semantics:
- Event names are strings (prefer constants from ``meowcat.loop``)
- handlers can be sync or async; ``emit`` auto-awaits awaitable return values
- Failed handlers are not swallowed; exceptions propagate to caller (framework does not decide for business logic)

P-02 philosophy: minimal code. EventBus only does "event name → callback list" dispatch.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any, Callable


Handler = Callable[..., Any]

__all__ = ["EventBus", "Handler"]


class EventBus:
    """Cat nervous system: event name ↔ handler list."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    # -- Registration --------------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """Register a handler.

        Two usages:

            bus.on("locate.pre", my_handler)

            @bus.on("locate.pre")
            def my_handler(payload): ...
        """
        if handler is None:
            def decorator(fn: Handler) -> Handler:
                self._handlers[event].append(fn)
                return fn
            return decorator
        self._handlers[event].append(handler)
        return handler

    def off(self, event: str, handler: Handler) -> bool:
        """Unregister a handler. Returns False if not found, never raises."""
        lst = self._handlers.get(event)
        if not lst or handler not in lst:
            return False
        lst.remove(handler)
        return True

    def clear(self, event: str | None = None) -> None:
        """Clear handlers for a specific event or all events."""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)

    # -- Trigger --------------------------------------------------------

    async def emit(self, event: str, payload: Any = None) -> None:
        """Trigger handlers in registration order; auto-awaits awaitable return values.

        Handlers accept 0 or 1 parameter:
        - ``def h(): ...``         → called with no argument
        - ``def h(payload): ...``  → called with payload
        """
        for handler in list(self._handlers.get(event, [])):
            result = self._invoke(handler, payload)
            if inspect.isawaitable(result):
                await result

    @staticmethod
    def _invoke(handler: Handler, payload: Any) -> Any:
        """Decide whether to pass payload based on handler parameter count."""
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            return handler(payload)
        if len(sig.parameters) == 0:
            return handler()
        return handler(payload)

    # -- Introspection --------------------------------------------------------

    def handlers(self, event: str) -> list[Handler]:
        """Return a snapshot of registered handlers (for testing/debugging)."""
        return list(self._handlers.get(event, []))

    def events(self) -> list[str]:
        """Return names of all events that have handlers."""
        return [e for e, hs in self._handlers.items() if hs]
