"""meowcat Pluggable mixin — plug/unplug hooks onto Noop organs.

v1.0.7: mount_plug / unmount_plug / _run_plugs on all 15 Noop organs,
allowing app-layer plugins on framework defaults (LLM safety check, TTS adapter, etc.).

Three execution modes (chosen by each Noop class, not enforced by Pluggable):
- A First-hit: return first non-default result
- B Merge-enhance: merge all plugin results into defaults
- C Full-replace: first plugin completely replaces default behavior
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class Pluggable:
    """Pluggable mixin — hook register/unregister/run for organs.

    **Usage**::

        class NoopAmygdala(Pluggable):
            HOOKS: dict[str, dict[str, str]] = {
                "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
                "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
            }

            async def assess_safety(self, user_input: str) -> dict[str, Any]:
                for _name, r in self._run_plugs("assess_safety", user_input):
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

    def _run_plugs(
        self, hook: str, *args: Any, **kwargs: Any
    ) -> Iterator[tuple[str, Any]]:
        """Run plugins in registration order, yielding (hook_name, result).

        Callers decide how to handle results (first-hit / merge / replace).

        Args:
            hook: hook name.
            *args: positional arguments passed to plugins.
            **kwargs: keyword arguments passed to plugins.

        Yields:
            ``(hook_name, result)`` tuple, once per registered plugin.
        """
        for fn in self._plugs.get(hook, ()):
            yield hook, fn(*args, **kwargs)

    def list_plugs(self) -> dict[str, int]:
        """List all mounted hooks and their plugin counts.

        Returns:
            ``{hook_name: plugin_count}``.
        """
        return {h: len(fns) for h, fns in self._plugs.items()}


__all__ = ["Pluggable"]
