# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

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

from __future__ import annotations

import json
import time as _time
from collections import Counter
from typing import TYPE_CHECKING, Any

from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.colony import Colony

_GROWTH_NS = "growth"
_ANOMALY_PREFIX = "anomaly:"
_CORRECTION_PREFIX = "correction:"
_ROLE_PREFIX = "role:"


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
            "strategy",
            cat_uid,
            {"type": "anomaly", "reason": reason, "confidence": confidence},
        ):
            if r is False:
                return ""

        ts = str(_time.time())
        key = f"{_ANOMALY_PREFIX}{ts}"
        record = json.dumps(
            {
                "cat_uid": cat_uid,
                "reason": reason,
                "snippet": snippet[:500],
                "confidence": confidence,
                "phase": phase,
                "ts": ts,
            },
            ensure_ascii=False,
        )
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
            "strategy",
            cat_uid,
            {"type": "correction", "wrong": wrong, "topic": topic},
        ):
            if r is False:
                return ""

        ts = str(_time.time())
        key = f"{_CORRECTION_PREFIX}{ts}"
        record = json.dumps(
            {
                "cat_uid": cat_uid,
                "wrong": wrong[:500],
                "correct": correct[:500],
                "topic": topic,
                "ts": ts,
            },
            ensure_ascii=False,
        )
        await self._colony.ns_set(_GROWTH_NS, key, record)
        return key

    # -- Query ---------------------------------------------------------

    async def list_anomalies(
        self,
        limit: int = 20,
        cat_uid: str | None = None,
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
        self,
        limit: int = 20,
        cat_uid: str | None = None,
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
        cnt: dict[str, Any] = await self.count()
        cnt["growth_ns"] = _GROWTH_NS
        cnt["plugs"] = self.list_plugs()
        return cnt


# -- Role emergence (v2.0: merged from roles.py) --------------------


class CollectiveEmergence(Pluggable):
    """Colony-level role emergence — detects emergent roles from behavior.

    Attached to a :class:`~meowcat.colony.Colony` via ``colony.emergence``,
    lazily initialised on first access.  Scans the colony's ``growth/``
    namespace for anomaly/correction patterns and surfaces emergent
    specialisations across cats.

    Args:
        colony: The parent colony instance.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "detector": {"in": "events: list[dict]", "out": "list[dict] | None"},
    }

    def __init__(self, colony: Colony) -> None:
        Pluggable.__init__(self)
        self._colony = colony

    async def detect_roles(self, min_events: int = 2) -> list[dict[str, Any]]:
        """Detect emergent roles by scanning growth events."""
        events: list[dict[str, Any]] = []
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        for k in keys:
            raw = await self._colony.ns_get(_GROWTH_NS, k)
            if raw:
                try:
                    ev = json.loads(raw) if isinstance(raw, str) else raw
                    ev["_key"] = k
                    events.append(ev)
                except (json.JSONDecodeError, TypeError):
                    pass

        async for _name, r in self._run_plugs("detector", events):
            if isinstance(r, list):
                return r

        return self._default_detect(events, min_events)

    @staticmethod
    def _default_detect(
        events: list[dict[str, Any]],
        min_events: int,
    ) -> list[dict[str, Any]]:
        """Default role detector — keyword + cat_uid clustering."""
        cat_reasons: dict[str, list[str]] = {}
        for ev in events:
            cid = ev.get("cat_uid", "unknown")
            reason = ev.get("reason", "")
            cat_reasons.setdefault(cid, []).append(reason)

        roles: list[dict[str, Any]] = []
        for cid, reasons in cat_reasons.items():
            if len(reasons) < min_events:
                continue
            counter = Counter(reasons)
            top_reason, top_count = counter.most_common(1)[0]
            role = _infer_role(top_reason)
            roles.append(
                {
                    "cat_uid": cid,
                    "role": role,
                    "confidence": min(top_count / max(len(reasons), 1), 1.0),
                    "evidence_count": len(reasons),
                    "top_reason": top_reason,
                }
            )
        return roles

    async def record_pattern(
        self,
        cat_uid: str,
        pattern: str,
        evidence: str = "",
    ) -> str:
        """Record a behaviour pattern for role emergence in colony storage."""
        ts = str(_time.time())
        key = f"{_ROLE_PREFIX}{ts}"
        record = json.dumps(
            {
                "cat_uid": cat_uid,
                "pattern": pattern,
                "evidence": evidence[:500],
                "ts": ts,
            },
            ensure_ascii=False,
        )
        await self._colony.ns_set(_GROWTH_NS, key, record)
        return key

    async def list_patterns(
        self,
        limit: int = 50,
        cat_uid: str | None = None,
    ) -> list[dict[str, Any]]:
        """List role patterns, newest first."""
        results: list[dict[str, Any]] = []
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        for k in keys:
            if not k.startswith(_ROLE_PREFIX):
                continue
            raw = await self._colony.ns_get(_GROWTH_NS, k)
            if raw:
                try:
                    rec = json.loads(raw) if isinstance(raw, str) else raw
                    if cat_uid is None or rec.get("cat_uid") == cat_uid:
                        results.append(rec)
                except (json.JSONDecodeError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return results[:limit]

    async def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        growth = CollectiveGrowth(self._colony)
        counts = await growth.count()
        patterns = await self.list_patterns(limit=5)
        return {
            "anomalies": counts.get("anomalies", 0),
            "corrections": counts.get("corrections", 0),
            "role_patterns": len(patterns),
            "recent_patterns": patterns,
            "plugs": self.list_plugs(),
        }


_ROLE_KEYWORDS: dict[str, str] = {
    "sql": "SQL审查",
    "安全": "安全审计",
    "异常": "异常检测",
    "表": "数据结构",
    "schema": "Schema审查",
    "权限": "权限管理",
    "性能": "性能优化",
    "bug": "Bug修复",
    "错误": "纠错专家",
    "error": "纠错专家",
}


def _infer_role(reason: str) -> str:
    """Infer role name from reason text via keyword matching."""
    for kw, role in _ROLE_KEYWORDS.items():
        if kw.lower() in reason.lower():
            return role
    words = reason.strip().split()
    return f"{words[0] if words else '未知'}方向"


__all__ = ["CollectiveGrowth", "CollectiveEmergence"]
