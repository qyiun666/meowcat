# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""ScribblePad — cat's private scratchpad for fragment accumulation.

插座式设计: framework provides storage + slots, app-layer decides
WHEN to write, WHAT format, and WHEN to fuse.

Usage::

    from meowcat.biology.scribble_pad import ScribblePad

    pad = ScribblePad(capacity=100)
    pad.scribble({"type": "summary", "text": "用户喜欢Python 3.12"})
    pad.scribble({"type": "decision", "action": "approved"})

    # Preview
    recent = pad.peek(10)

    # Drain for PinealGland fusion
    fragments = pad.drain()
"""

from __future__ import annotations

from typing import Any

from meowcat.log import MeowLog
from meowcat.pluggable import Pluggable

_log = MeowLog.get("meowcat.scribble_pad")


class ScribblePad(Pluggable):
    """Cat's private scratchpad — socket-style fragment accumulator.

    Framework layer responsibilities:
    - ``scribble()`` storage interface
    - capacity management
    - plugin slots for custom logic

    App layer responsibilities:
    - When to call ``scribble()`` (every turn? batch? timer?)
    - What format (summary? raw? structured JSON?)
    - When to trigger fusion (full? timer? event? manual?)

    Args:
        capacity: Max entries before ``is_full()`` returns True. Default 200.
        max_capacity_enforce: If True, ``scribble()`` rejects writes when
            pad is full (default False, silently accepts all writes).
    """

    HOOKS: dict[str, dict[str, str]] = {
        "on_scribble": {"in": "payload: Any", "out": "Any | None"},
        "on_drain": {"in": "entries: list[Any]", "out": "list[Any] | None"},
        "post_filter": {"in": "payload: Any, entries: list[Any]", "out": "bool | None"},
    }

    __slots__ = ("_entries", "_capacity", "_enforce_capacity")

    def __init__(self, capacity: int = 200, *, max_capacity_enforce: bool = False) -> None:
        super().__init__()
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self._capacity = capacity
        self._entries: list[Any] = []
        self._enforce_capacity = max_capacity_enforce

    # -- Core API ------------------------------------------------------

    def scribble(self, payload: Any) -> None:
        """Write a fragment to the pad. App decides what to push.

        Calls ``on_scribble`` plugin chain (fire-and-forget), then applies
        ``post_filter`` chain — if any filter returns False, the payload
        is dropped.

        Args:
            payload: Any fragment — dict, str, list, whatever the app needs.
        """
        # on_scribble hook (fire-and-forget)
        for _name, _r in self._run_plugs_sync("on_scribble", payload):
            pass

        # post_filter chain — any False vetoes the write
        for _name, ok in self._run_plugs_sync("post_filter", payload, list(self._entries)):
            if ok is False:
                return

        # Capacity enforcement
        if self._enforce_capacity and self.is_full():
            _log.warning("scribble rejected (pad full)", capacity=self._capacity)
            return

        self._entries.append(payload)

    def peek(self, n: int = 50) -> list[Any]:
        """Preview the most recent *n* entries without removing them.

        Args:
            n: Number of recent entries. Negative = all.

        Returns:
            Shallow copy of recent entries (newest last).
        """
        if n < 0:
            return list(self._entries)
        return self._entries[-n:] if n > 0 else []

    def drain(self) -> list[Any]:
        """Remove all entries and return them (for fusion by PinealGland).

        Calls ``on_drain`` plugin chain before clearing — plugins can
        compress, archive, or transform entries before they're returned.

        Returns:
            All accumulated entries (possibly transformed by ``on_drain``).
        """
        # on_drain hook — plugins can transform entries
        entries = list(self._entries)
        for _name, r in self._run_plugs_sync("on_drain", entries):
            if isinstance(r, list):
                entries = r  # last plugin output wins

        self._entries.clear()
        return entries

    def is_full(self) -> bool:
        """Whether entries have reached capacity."""
        return len(self._entries) >= self._capacity

    def count(self) -> int:
        """Current entry count."""
        return len(self._entries)

    @property
    def capacity(self) -> int:
        """Max entry capacity."""
        return self._capacity

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "count": self.count(),
            "capacity": self._capacity,
            "is_full": self.is_full(),
            "plugs": self.list_plugs(),
        }


# -- Prefabs (开箱即用，可替换) ------------------------------------------


class DefaultScribbleFilter:
    """Default post_filter: deduplicate exact-match payloads.

    Usage::

        pad.plug("post_filter", DefaultScribbleFilter())
    """

    def __call__(self, payload: Any, entries: list[Any]) -> bool | None:
        # Check last 20 entries for exact match
        recent = entries[-20:] if len(entries) > 20 else entries
        if any(e == payload for e in recent):
            _log.debug("scribble dup filtered")
            return False
        return None  # pass through (don't veto)


class DefaultScribbleLogger:
    """Default on_scribble: log every write to MeowLog debug.

    Usage::

        pad.plug("on_scribble", DefaultScribbleLogger())
    """

    def __call__(self, payload: Any) -> None:
        _log.debug("scribble", payload=str(payload)[:120])


class DefaultScribblePersister:
    """Default on_drain plugin: persists drained entries to JSONL storage.

    Usage::

        from meowcat.storage.l6_store import JsonlL6Store
        store = JsonlL6Store(Path("./data/scribbles.jsonl"))
        pad.plug("on_drain", DefaultScribblePersister(store))
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    def __call__(self, entries: list[Any]) -> list[Any] | None:
        if not entries:
            return None
        try:
            for entry in entries:
                self._store.append(entry)
            _log.debug("scribble persisted", count=len(entries))
        except Exception as e:
            _log.warning("scribble persist failed", error=str(e)[:120])
        return None  # don't transform, pass through


__all__ = [
    "ScribblePad",
    "DefaultScribbleFilter",
    "DefaultScribbleLogger",
    "DefaultScribblePersister",
]
