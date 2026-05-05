"""CollectiveGrowth — colony-level anomaly/correction growth synced to SharedStorage.

Wraps a :class:`~meowcat.colony.Colony` and pushes anomaly / correction
records into the ``growth/`` namespace so every cat can learn from
every other cat's mistakes.

Usage::

    # Lazy-init via Colony property
    await colony.growth.record_anomaly("planner", "DB schema mismatch",
                                        snippet="table users not found")
    await colony.growth.record_correction("executor", "DROP TABLE",
                                           correct="DELETE WHERE id=...", topic="SQL安全")

    # Custom strategy via plug
    colony.growth.plug("strategy", my_custom_threshold)
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import json
import time as _time
from typing import Any, TYPE_CHECKING

from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.colony import Colony

_GROWTH_NS = "growth"
_ANOMALY_PREFIX = "anomaly:"
_CORRECTION_PREFIX = "correction:"


class CollectiveGrowth(Pluggable):
    """Colony-level growth — records anomalies and corrections to SharedStorage.

    Attached to a :class:`~meowcat.colony.Colony` via ``colony.growth``,
    lazily initialised on first access.  Uses the colony's ``growth/``
    namespace for persistence, enabling cross-cat learning.

    Args:
        colony: The parent colony instance.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "strategy": {"in": "cat_uid: str, event: dict", "out": "bool | None"},
    }

    def __init__(self, colony: Colony) -> None:
        Pluggable.__init__(self)
        self._colony = colony

    # -- Core API ------------------------------------------------------

    async def record_anomaly(
        self,
        cat_uid: str,
        reason: str,
        snippet: str = "",
        confidence: float = 0.8,
        phase: str = "input",
    ) -> str:
        """Record an anomaly to the colony growth namespace.

        Args:
            cat_uid: Source cat identifier.
            reason: Anomaly description.
            snippet: Relevant context snippet (truncated to 500 chars).
            confidence: Detection confidence 0.0-1.0.
            phase: Pipeline phase where anomaly was detected.

        Returns:
            Storage key suffix (``anomaly:{ts}``).
        """
        # Strategy hook — can veto recording
        async for _name, r in self._run_plugs(
            "strategy", cat_uid,
            {"type": "anomaly", "reason": reason, "confidence": confidence},
        ):
            if r is False:
                return ""

        ts = str(_time.time())
        key = f"{_ANOMALY_PREFIX}{ts}"
        record = json.dumps({
            "cat_uid": cat_uid,
            "reason": reason,
            "snippet": snippet[:500],
            "confidence": confidence,
            "phase": phase,
            "ts": ts,
        }, ensure_ascii=False)
        await self._colony.ns_set(_GROWTH_NS, key, record)
        return key

    async def record_correction(
        self,
        cat_uid: str,
        wrong: str,
        correct: str,
        topic: str = "",
    ) -> str:
        """Record a user correction to the colony growth namespace.

        Args:
            cat_uid: Source cat identifier.
            wrong: The incorrect statement or action.
            correct: The corrected version.
            topic: Optional topic tag.

        Returns:
            Storage key suffix (``correction:{ts}``).
        """
        # Strategy hook — can veto recording
        async for _name, r in self._run_plugs(
            "strategy", cat_uid,
            {"type": "correction", "wrong": wrong, "topic": topic},
        ):
            if r is False:
                return ""

        ts = str(_time.time())
        key = f"{_CORRECTION_PREFIX}{ts}"
        record = json.dumps({
            "cat_uid": cat_uid,
            "wrong": wrong[:500],
            "correct": correct[:500],
            "topic": topic,
            "ts": ts,
        }, ensure_ascii=False)
        await self._colony.ns_set(_GROWTH_NS, key, record)
        return key

    # -- Query ---------------------------------------------------------

    async def list_anomalies(
        self, limit: int = 20, cat_uid: str | None = None,
    ) -> list[dict[str, Any]]:
        """List recent anomalies, newest first.

        Args:
            limit: Max results to return.
            cat_uid: Optional filter by source cat.

        Returns:
            List of anomaly records.
        """
        results: list[dict[str, Any]] = []
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        for k in keys:
            if not k.startswith(_ANOMALY_PREFIX):
                continue
            raw = await self._colony.ns_get(_GROWTH_NS, k)
            if raw:
                try:
                    record = json.loads(raw) if isinstance(raw, str) else raw
                    if cat_uid is None or record.get("cat_uid") == cat_uid:
                        results.append(record)
                except (json.JSONDecodeError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return results[:limit]

    async def list_corrections(
        self, limit: int = 20, cat_uid: str | None = None,
    ) -> list[dict[str, Any]]:
        """List recent corrections, newest first.

        Args:
            limit: Max results to return.
            cat_uid: Optional filter by source cat.

        Returns:
            List of correction records.
        """
        results: list[dict[str, Any]] = []
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        for k in keys:
            if not k.startswith(_CORRECTION_PREFIX):
                continue
            raw = await self._colony.ns_get(_GROWTH_NS, k)
            if raw:
                try:
                    record = json.loads(raw) if isinstance(raw, str) else raw
                    if cat_uid is None or record.get("cat_uid") == cat_uid:
                        results.append(record)
                except (json.JSONDecodeError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return results[:limit]

    async def count(self) -> dict[str, int]:
        """Return counts of stored anomalies and corrections.

        Returns:
            ``{"anomalies": n, "corrections": m}``.
        """
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        a = sum(1 for k in keys if k.startswith(_ANOMALY_PREFIX))
        c = sum(1 for k in keys if k.startswith(_CORRECTION_PREFIX))
        return {"anomalies": a, "corrections": c}

    async def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        cnt = await self.count()
        cnt["growth_ns"] = _GROWTH_NS
        cnt["plugs"] = self.list_plugs()
        return cnt


__all__ = ["CollectiveGrowth"]
