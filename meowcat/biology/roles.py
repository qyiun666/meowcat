"""CollectiveEmergence — colony-level role detection from behavior patterns.

Observers the colony's ``growth/`` namespace and records per-cat behavior
patterns to detect emergent roles (e.g. "某猫擅长SQL审查", "某猫经常发现异常").

Usage::

    # Lazy-init via Colony property
    roles = await colony.emergence.detect_roles()
    await colony.emergence.record_pattern("planner", "SQL审查",
                                           evidence="发现3次SQL异常")

    # Custom detector via plug
    colony.emergence.plug("detector", my_ml_detector)
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import json
import time as _time
from collections import Counter
from typing import Any, TYPE_CHECKING

from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.colony import Colony

_GROWTH_NS = "growth"
_ROLE_PREFIX = "role:"


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

    # -- Core API ------------------------------------------------------

    async def detect_roles(self, min_events: int = 2) -> list[dict[str, Any]]:
        """Detect emergent roles by scanning growth events.

        The default detector groups anomalies/corrections by ``cat_id``
        and ``reason`` keyword, surfacing cats that specialise in certain
        kinds of detection or correction.

        Args:
            min_events: Minimum events required before a role emerges.

        Returns:
            ``[{"cat_id": ..., "role": ..., "confidence": ..., "evidence": ...}, ...]``
        """
        # Collect all growth events (anomalies + corrections)
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

        # Plugin hook: custom detector
        async for _name, r in self._run_plugs("detector", events):
            if isinstance(r, list):
                return r

        # Default detector: keyword-based role clustering
        return self._default_detect(events, min_events)

    @staticmethod
    def _default_detect(
        events: list[dict[str, Any]], min_events: int,
    ) -> list[dict[str, Any]]:
        """Default role detector — keyword + cat_id clustering."""
        # Group by cat_id → reasons
        cat_reasons: dict[str, list[str]] = {}
        for ev in events:
            cid = ev.get("cat_id", "unknown")
            reason = ev.get("reason", "")
            cat_reasons.setdefault(cid, []).append(reason)

        roles: list[dict[str, Any]] = []
        for cid, reasons in cat_reasons.items():
            if len(reasons) < min_events:
                continue
            counter = Counter(reasons)
            top_reason, top_count = counter.most_common(1)[0]
            role = _infer_role(top_reason)
            roles.append({
                "cat_id": cid,
                "role": role,
                "confidence": min(top_count / max(len(reasons), 1), 1.0),
                "evidence_count": len(reasons),
                "top_reason": top_reason,
            })

        # Persist detected roles to growth namespace
        return roles

    async def record_pattern(
        self, cat_id: str, pattern: str, evidence: str = "",
    ) -> str:
        """Record a behaviour pattern for role emergence in colony storage.

        Args:
            cat_id: Source cat identifier.
            pattern: Behaviour pattern description.
            evidence: Supporting evidence.

        Returns:
            Storage key suffix (``role:{ts}``).
        """
        ts = str(_time.time())
        key = f"{_ROLE_PREFIX}{ts}"
        record = json.dumps({
            "cat_id": cat_id,
            "pattern": pattern,
            "evidence": evidence[:500],
            "ts": ts,
        }, ensure_ascii=False)
        await self._colony.ns_set(_GROWTH_NS, key, record)
        return key

    async def list_patterns(
        self, limit: int = 50, cat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List role patterns, newest first.

        Args:
            limit: Max results.
            cat_id: Optional cat filter.

        Returns:
            List of role pattern records.
        """
        results: list[dict[str, Any]] = []
        keys = await self._colony.ns_list_keys(_GROWTH_NS)
        for k in keys:
            if not k.startswith(_ROLE_PREFIX):
                continue
            raw = await self._colony.ns_get(_GROWTH_NS, k)
            if raw:
                try:
                    rec = json.loads(raw) if isinstance(raw, str) else raw
                    if cat_id is None or rec.get("cat_id") == cat_id:
                        results.append(rec)
                except (json.JSONDecodeError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return results[:limit]

    async def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        from meowcat.biology.growth import CollectiveGrowth
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


# -- Role inference helpers ------------------------------------------

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
    # Fallback: first meaningful word as role hint
    words = reason.strip().split()
    return f"{words[0] if words else '未知'}方向"


__all__ = ["CollectiveEmergence"]
