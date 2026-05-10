# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Amygdala implementation — regex-based danger/safety assessment."""

from __future__ import annotations

import re
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.presets import KW_BILINGUAL, KeywordPreset
from meowcat.pluggable import Pluggable


class DefaultAmygdala(Pluggable):
    """Amygdala: regex-based danger/safety assessment.

    Accepts a :class:`KeywordPreset` for configurable danger patterns.
    Default: bilingual (zh+en) danger patterns covering SQL injection,
    shell injection, XSS, path traversal, and Chinese-specific threats.

    .. note::

        ``is_rejection`` / ``classify_rejection`` detect *dangerous* input
        (not user negation/correction — that belongs to Whiskers).
        Use ``is_dangerous`` for the same behavior with clearer naming.

    Tool risk assessment is fully configurable via ``dangerous_tools``
    and ``dangerous_paths``, and supports plugin override via the
    ``assess_tool_risk`` hook.

    Mode A — assess_safety / assess_tool_risk first-hit override.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
        "assess_tool_risk": {
            "in": "tool_name: str, params: dict", "out": "dict[str, Any]"
        },
    }

    name: str = "renovated_amygdala"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(
        self,
        danger_patterns: list[re.Pattern] | None = None,
        keyword: KeywordPreset | None = None,
        dangerous_tools: set[str] | None = None,
        dangerous_paths: list[str] | None = None,
    ) -> None:
        Pluggable.__init__(self)
        if danger_patterns:
            self._patterns: list[re.Pattern] = list(danger_patterns)
        elif keyword:
            self._patterns = list(keyword.danger_patterns)
        else:
            self._patterns = list(KW_BILINGUAL.danger_patterns)
        self._dangerous_tools: set[str] = (
            dangerous_tools
            if dangerous_tools is not None
            else {"run_command", "eval", "exec", "shell"}
        )
        self._dangerous_paths: list[str] = (
            dangerous_paths
            if dangerous_paths is not None
            else ["/etc/", "/root/", "~/.ssh/", "C:\\Windows\\"]
        )

    def is_rejection(self, msg: str) -> bool:
        return any(pat.search(msg) for pat in self._patterns)

    def is_dangerous(self, msg: str) -> bool:
        return self.is_rejection(msg)

    def classify_rejection(self, msg: str) -> str:
        if not self.is_rejection(msg):
            return "none"
        return "danger"

    def parse_correction(self, msg: str) -> tuple[str, str] | None:
        return None

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any,
    ) -> str:
        return msg

    async def handle_correction(
        self, msg: str, hippocampus: Any,
    ) -> tuple[str, str] | None:
        return None

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict) and not r.get("safe", True):
                return r
        for pat in self._patterns:
            m = pat.search(user_input)
            if m:
                return {
                    "safe": False,
                    "risk": "high",
                    "pattern": pat.pattern,
                    "match": m.group(),
                }
        return {"safe": True, "risk": "low"}

    def assess_tool_risk(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        for _name, r in self._run_plugs_sync(
            "assess_tool_risk", tool_name, params
        ):
            if isinstance(r, dict):
                return r
        if tool_name in self._dangerous_tools:
            return {"risk": "high", "reason": f"dangerous tool: {tool_name}"}
        if tool_name == "write_file":
            fp = str(params.get("path", params.get("file_path", "")))
            for dp in self._dangerous_paths:
                if dp in fp:
                    return {
                        "risk": "high",
                        "reason": f"write to protected path: {fp}",
                    }
        return {"risk": "low", "reason": "ok"}
