# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default growth organ implementations — in-memory logging with diagnostics."""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopAnomalyGrowth(Pluggable):
    """Default anomaly growth: in-memory anomaly log with diagnostics.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {
            "in": "reason: str, snippet: str, confidence: float, phase: str, session_id: str",
            "out": "Any",
        },
    }

    name: str = "renovated_anomaly_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._log: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"anomalies": len(self._log), "recent": self._log[-5:]}

    def record(
        self,
        reason: str,
        snippet: str,
        confidence: float = 0.8,
        phase: str = "input",
        session_id: str = "",
    ) -> Any:
        for _name, r in self._run_plugs_sync(
            "record", reason, snippet, confidence, phase, session_id
        ):
            if isinstance(r, dict):
                return r
        entry = {
            "reason": reason,
            "snippet": snippet[:200],
            "confidence": confidence,
            "phase": phase,
            "ts": _time.time(),
        }
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class NoopCorrectionGrowth(Pluggable):
    """Default correction growth: in-memory correction log with diagnostics.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {"in": "wrong: str, correct: str, session_id: str, topic: str", "out": "Any"},
    }

    name: str = "renovated_correction_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._log: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"corrections": len(self._log), "recent": self._log[-5:]}

    def record(
        self,
        wrong: str,
        correct: str,
        session_id: str = "",
        topic: str = "",
    ) -> Any:
        for _name, r in self._run_plugs_sync("record", wrong, correct, session_id, topic):
            if isinstance(r, dict):
                return r
        entry = {
            "wrong": wrong[:200],
            "correct": correct[:200],
            "topic": topic,
            "ts": _time.time(),
        }
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class NoopCrystallizer(Pluggable):
    """Default crystallizer: in-memory skill hit counter with hotspot detection.

    Tracks how often each skill slug is called, and surfaces hotspots.

    Thresholds are configurable via ``crystallize_threshold`` (min hits for
    a skill to be considered "crystallized") and ``hotspot_threshold`` (min
    hits for a skill to appear in hotspots).

    Mode C — crystallize / hotspots full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "crystallize": {"in": "slug: str, hit_count: int", "out": "bool"},
        "hotspots": {"in": "threshold: int|None", "out": "list[tuple[str,int]]"},
    }

    name: str = "renovated_crystallizer"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        crystallize_threshold: int = 5,
        hotspot_threshold: int = 3,
    ) -> None:
        Pluggable.__init__(self)
        self._hits: dict[str, int] = {}
        self._crystallize_threshold = crystallize_threshold
        self._hotspot_threshold = hotspot_threshold

    def diagnose(self) -> dict[str, Any]:
        return {"hits": dict(self._hits), "hotspots": self.hotspots(threshold=3)}

    # type: ignore[override]
    def crystallize(self, slug: str, hit_count: int) -> bool:
        for _name, r in self._run_plugs_sync("crystallize", slug, hit_count):
            if isinstance(r, bool):
                return r
        self._hits[slug] = self._hits.get(slug, 0) + hit_count
        return self._hits[slug] >= self._crystallize_threshold

    # type: ignore[override]
    def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        for _name, r in self._run_plugs_sync("hotspots", threshold):
            if isinstance(r, list):
                return r
        t = threshold if threshold is not None else self._hotspot_threshold
        result = [(k, v) for k, v in self._hits.items() if v >= t]
        result.sort(key=lambda x: -x[1])
        return result


class NoopRoleEmergence(Pluggable):
    """Default role emergence: in-memory behavior pattern log with diagnostics.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {"in": "pattern: str, evidence: str", "out": "Any"},
    }

    name: str = "renovated_role_emergence"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._patterns: list[dict[str, Any]] = []

    def diagnose(self) -> dict[str, Any]:
        return {"patterns": len(self._patterns), "recent": self._patterns[-5:]}

    def record(self, pattern: str, evidence: str) -> Any:
        for _name, r in self._run_plugs_sync("record", pattern, evidence):
            if isinstance(r, dict):
                return r
        entry = {"pattern": pattern,
                 "evidence": evidence[:200], "ts": _time.time()}
        self._patterns.append(entry)
        return {"recorded": True, "total": len(self._patterns)}
