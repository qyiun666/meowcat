# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) growth organ implementations — 4 classes."""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopAnomalyGrowth,
    NoopCorrectionGrowth,
    NoopCrystallizer,
    NoopRoleEmergence,
)

# =========================================================================
# Growth Organs — 简装修 (in-memory logging)
# =========================================================================


class RenovatedAnomalyGrowth(NoopAnomalyGrowth):
    """简装修 anomaly_growth: in-memory anomaly log with diagnostics."""

    name: str = "renovated_anomaly_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopAnomalyGrowth.__init__(self)
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


class RenovatedCorrectionGrowth(NoopCorrectionGrowth):
    """简装修 correction_growth: in-memory correction log with diagnostics."""

    name: str = "renovated_correction_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopCorrectionGrowth.__init__(self)
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
        entry = {"wrong": wrong[:200], "correct": correct[:200],
                 "topic": topic, "ts": _time.time()}
        self._log.append(entry)
        return {"recorded": True, "total": len(self._log)}


class RenovatedCrystallizer(NoopCrystallizer):
    """简装修 crystallizer: in-memory skill hit counter.

    Tracks how often each skill slug is called, and surfaces hotspots.

    Thresholds are configurable via ``crystallize_threshold`` (min hits for
    a skill to be considered "crystallized") and ``hotspot_threshold`` (min
    hits for a skill to appear in hotspots).
    """

    name: str = "renovated_crystallizer"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        crystallize_threshold: int = 5,
        hotspot_threshold: int = 3,
    ) -> None:
        NoopCrystallizer.__init__(self)
        self._hits: dict[str, int] = {}
        self._crystallize_threshold = crystallize_threshold
        self._hotspot_threshold = hotspot_threshold

    def diagnose(self) -> dict[str, Any]:
        return {"hits": dict(self._hits), "hotspots": self.hotspots(threshold=3)}

    def crystallize(self, slug: str, hit_count: int) -> bool:
        for _name, r in self._run_plugs_sync("crystallize", slug, hit_count):
            if isinstance(r, bool):
                return r
        self._hits[slug] = self._hits.get(slug, 0) + hit_count
        return self._hits[slug] >= self._crystallize_threshold

    def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        for _name, r in self._run_plugs_sync("hotspots", threshold):
            if isinstance(r, list):
                return r
        t = threshold if threshold is not None else self._hotspot_threshold
        result = [(k, v) for k, v in self._hits.items() if v >= t]
        result.sort(key=lambda x: -x[1])
        return result


class RenovatedRoleEmergence(NoopRoleEmergence):
    """简装修 role_emergence: in-memory behavior pattern log with diagnostics."""

    name: str = "renovated_role_emergence"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopRoleEmergence.__init__(self)
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
