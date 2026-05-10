# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Hypothalamus implementation — background maintenance with TTL decay."""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopHypothalamus(Pluggable):
    """Hypothalamus: background maintenance with configurable TTL decay.

    Runs memory decay on the hippocampus organ if accessible via cat ref.

    Mode B — run_maintenance merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "run_maintenance": {"in": "country_code: str|None", "out": "Any"},
    }

    name: str = "renovated_hypothalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, decay_ttl_days: int = 30) -> None:
        Pluggable.__init__(self)
        self._decay_ttl_days = decay_ttl_days
        self._last_maintenance: float = 0.0

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        result: dict[str, Any] = {
            "decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}
        async for _name, r in self._run_plugs("run_maintenance", country_code):
            if isinstance(r, dict):
                result.update(r)
        self._last_maintenance = _time.time()
        return result

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        return {"decayed": 0, "ttl_days": self._decay_ttl_days}

    def compress_long_history(self) -> dict[str, Any]:
        return {"compressed": 0}
