# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default growth organ stubs — no-op implementations satisfying Protocols."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopAnomalyGrowth(Pluggable):
    """Default anomaly growth: does not record anomaly patterns.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {
            "in": "reason: str, snippet: str, confidence: float, phase: str, session_id: str",
            "out": "Any",
        },
    }

    name: str = "noop_anomaly_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def record(
        self,
        reason: str,
        snippet: str,
        confidence: float = 0.8,
        phase: str = "input",
        session_id: str = "",
    ) -> Any:
        result: dict[str, Any] = {"recorded": False}
        async for _name, r in self._run_plugs(
            "record",
            reason,
            snippet,
            confidence,
            phase,
            session_id,
        ):
            if isinstance(r, dict):
                result.update(r)
        return result


class NoopCorrectionGrowth(Pluggable):
    """Default correction growth: does not record user corrections.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {"in": "wrong: str, correct: str, session_id: str, topic: str", "out": "Any"},
    }

    name: str = "noop_correction_growth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def record(
        self,
        wrong: str,
        correct: str,
        session_id: str = "",
        topic: str = "",
    ) -> Any:
        result: dict[str, Any] = {"recorded": False}
        async for _name, r in self._run_plugs(
            "record",
            wrong,
            correct,
            session_id,
            topic,
        ):
            if isinstance(r, dict):
                result.update(r)
        return result


class NoopCrystallizer(Pluggable):
    """Default crystallizer: does not crystallize skills.

    Mode C — crystallize / hotspots full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "crystallize": {"in": "slug: str, hit_count: int", "out": "bool"},
        "hotspots": {"in": "threshold: int|None", "out": "list[tuple[str,int]]"},
    }

    name: str = "noop_crystallizer"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def crystallize(self, slug: str, hit_count: int) -> bool:
        async for _name, r in self._run_plugs("crystallize", slug, hit_count):
            if isinstance(r, bool):
                return r
        return False

    async def hotspots(self, threshold: int | None = None) -> list[tuple[str, int]]:
        async for _name, r in self._run_plugs("hotspots", threshold):
            if isinstance(r, list):
                return r
        return []


class NoopRoleEmergence(Pluggable):
    """Default role emergence: does not record role patterns.

    Mode B — record merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "record": {"in": "pattern: str, evidence: str", "out": "Any"},
    }

    name: str = "noop_role_emergence"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def record(self, pattern: str, evidence: str) -> Any:
        result: dict[str, Any] = {"recorded": False}
        async for _name, r in self._run_plugs("record", pattern, evidence):
            if isinstance(r, dict):
                result.update(r)
        return result
