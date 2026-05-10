# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Cortex implementation — in-memory worldview accumulation."""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class DefaultCortex(Pluggable):
    """Cortex: in-memory worldview accumulation.

    Ingests key-value observations into four layers
    (axioms/others/values/self) and synthesizes summary text on demand.

    Mode B — synthesize merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "synthesize": {"in": "max_tokens: int", "out": "str"},
    }

    name: str = "renovated_cortex"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._worldview: dict[str, dict[str, Any]] = {
            "axioms": {},
            "others": {},
            "values": {},
            "self": {},
        }
        self._weakness_log: list[dict[str, Any]] = []

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        if layer in self._worldview:
            self._worldview[layer][key] = {
                "source": source, "value": value, "ts": _time.time(),
            }

    def record_weakness(self, kind: str, detail: str) -> None:
        self._weakness_log.append(
            {"kind": kind, "detail": detail, "ts": _time.time()}
        )

    def weaknesses(self) -> list[dict[str, Any]]:
        return list(self._weakness_log)

    def synthesize(self, max_tokens: int = 400) -> str:
        result = ""
        for _name, r in self._run_plugs_sync("synthesize", max_tokens):
            if isinstance(r, str):
                result += r
        if not result:
            parts: list[str] = []
            for layer, entries in self._worldview.items():
                if entries:
                    summary = ", ".join(
                        f"{k}={v['value']}"
                        for k, v in list(entries.items())[:5]
                    )
                    parts.append(f"[{layer}] {summary}")
            if parts:
                result = "\n".join(parts)
        return result
