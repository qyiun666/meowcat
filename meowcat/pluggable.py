# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Pluggable mixin — plug/unplug hooks onto Noop organs.

v1.0.7: mount_plug / unmount_plug / _run_plugs on all 15 Noop organs,
allowing app-layer plugins on framework defaults (LLM safety check, TTS adapter, etc.).

v1.2.16: _run_plugs → async generator with automatic await for async plugins.
Sync plugins still work (isawaitable returns False).

Three execution modes (chosen by each Noop class, not enforced by Pluggable):
- A First-hit: return first non-default result
- B Merge-enhance: merge all plugin results into defaults
- C Full-replace: first plugin completely replaces default behavior
"""


from __future__ import annotations

import inspect
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

_log = logging.getLogger(__name__)


class Pluggable:
    """Pluggable mixin — hook register/unregister/run for organs.

    **Usage**::

        class NoopAmygdala(Pluggable):
            HOOKS: dict[str, dict[str, str]] = {
                "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
                "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
            }

            async def assess_safety(self, user_input: str) -> dict[str, Any]:
                async for _name, r in self._run_plugs("assess_safety", user_input):
                    if isinstance(r, dict) and not r.get("safe", True):
                        return r
                return {"safe": True, "risk": "none"}

    ``__slots__`` only allocates ``_plugs`` dict for Pluggable,
    without interfering with subclass ``__dict__`` or ``__slots__``.
    """

    __slots__ = ("_plugs",)

    # Subclasses declare mountable hooks with suggested signatures (doc only, no runtime effect)
    HOOKS: dict[str, dict[str, str]] = {}

    def __init__(self) -> None:
        self._plugs: dict[str, list[Callable[..., Any]]] = {}

    def mount_plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """Mount a plugin on the specified hook.

        Args:
            hook: hook name (e.g. ``"assess_safety"``).
            fn: plugin function/coroutine, signature should be compatible with the hook's suggested input/output.
        """
        if hook not in self._plugs:
            self._plugs[hook] = []
        self._plugs[hook].append(fn)

    def unmount_plug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """Unmount a plugin.

        Args:
            hook: hook name.
            fn: specific function to unmount; None removes all plugins on this hook.
        """
        if hook not in self._plugs:
            return
        if fn is None:
            self._plugs[hook].clear()
            self._plugs.pop(hook, None)
        else:
            self._plugs[hook] = [f for f in self._plugs[hook] if f is not fn]
            if not self._plugs[hook]:
                self._plugs.pop(hook, None)

    # Aliases (v1.1.6) — plug/unplug for consistency with Colony and design docs

    def plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """Alias for :meth:`mount_plug`."""
        self.mount_plug(hook, fn)

    def unplug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """Alias for :meth:`unmount_plug`."""
        self.unmount_plug(hook, fn)

    async def _run_plugs(
        self, hook: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[tuple[str, Any]]:
        """Run plugins in registration order, yielding (hook_name, result).

        v1.2.16: Now an async generator — automatically awaits async plugins.
        Sync plugins are yielded as-is; async plugins are awaited before yielding.

        Callers decide how to handle results (first-hit / merge / replace).
        Callers MUST use ``async for``.

        Args:
            hook: hook name.
            *args: positional arguments passed to plugins.
            **kwargs: keyword arguments passed to plugins.

        Yields:
            ``(hook_name, result)`` tuple, once per registered plugin.
        """
        for fn in self._plugs.get(hook, ()):
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            yield hook, result

    def _run_plugs_sync(
        self, hook: str, *args: Any, **kwargs: Any
    ) -> Iterator[tuple[str, Any]]:
        """Sync variant — iterate plugins without await.

        For callers that cannot use ``async for`` (property setters,
        sync public API methods).  Async plugin results will be returned
        as coroutine objects — callers must handle this themselves.

        Prefer :meth:`_run_plugs` for new async-capable code.

        Args:
            hook: hook name.
            *args: positional arguments passed to plugins.
            **kwargs: keyword arguments passed to plugins.

        Yields:
            ``(hook_name, result)`` tuple, once per registered plugin.
        """
        for fn in self._plugs.get(hook, ()):
            result = fn(*args, **kwargs)
            if inspect.iscoroutine(result):
                _log.debug(
                    "_run_plugs_sync hook '%s' plugin %s returned coroutine — "
                    "use async variant (_run_plugs) instead",
                    hook, getattr(fn, '__name__', fn),
                )
            yield hook, result

    async def _run_plugs_async(
        self, slot: str, *args: Any, **kwargs: Any
    ) -> AsyncIterator[tuple[str, Any]]:
        """Async plug runner — auto-detects coroutines, handles object plugs.

        Unlike :meth:`_run_plugs` which expects callables, this method also
        handles plug *objects* by looking up ``slot`` as an attribute.
        Useful when middleware/hooks are registered as objects rather than
        bare callables.

        Args:
            slot: hook/slot name.
            *args: positional arguments passed to plug.
            **kwargs: keyword arguments passed to plug.

        Yields:
            ``(plug_name, result)`` tuple, once per registered plug.
        """
        plugs = list(self._plugs.get(slot, []))
        for plug in plugs:
            cb = plug if callable(plug) else getattr(plug, slot, None)
            if cb is not None:
                result = cb(*args, **kwargs)
                if inspect.iscoroutine(result):
                    result = await result
                yield (getattr(plug, "name", plug.__class__.__name__), result)

    def list_plugs(self) -> dict[str, int]:
        """List all mounted hooks and their plugin counts.

        Returns:
            ``{hook_name: plugin_count}``.
        """
        return {h: len(fns) for h, fns in self._plugs.items()}


__all__ = ["Pluggable"]
