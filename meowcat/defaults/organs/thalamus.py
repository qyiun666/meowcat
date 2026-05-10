# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Default Thalamus implementation — keyword routing + command detection."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs._brain_helpers import _detect_command, _extract_keywords
from meowcat.defaults.presets import KW_BILINGUAL, KeywordPreset
from meowcat.pluggable import Pluggable


class NoopThalamus(Pluggable):
    """Thalamus: keyword routing + command detection.

    Accepts a :class:`KeywordPreset` for configurable command patterns and
    priority keywords. Default: bilingual (zh+en).

    Detects command patterns for routing, falls back to basic keyword analysis.

    Mode B — locate merge enhancement; hear receives raw sensory input.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "hear": {"in": "raw_input: str | bytes", "out": "dict[str, Any]"},
        "locate": {"in": "msg: str, session_id: str", "out": "LocateResultShape"},
    }

    name: str = "renovated_thalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, keyword: KeywordPreset | None = None) -> None:
        Pluggable.__init__(self)
        self._keyword = keyword or KW_BILINGUAL

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        """Receive raw sensory input, run plugs for preprocessing."""
        result: dict[str, Any] = {"raw_input": raw_input, "route": "chat"}
        async for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def locate(self, msg: str, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": "chat", "entities": [], "snippets": []}
        async for _name, r in self._run_plugs("locate", msg, session_id):
            if isinstance(r, dict):
                result.update(r)
        cmd_route = _detect_command(msg, self._keyword)
        if cmd_route:
            result["route"] = cmd_route
        return result

    def decide_route(self, **kwargs: Any) -> dict[str, Any]:
        msg = kwargs.get("text", kwargs.get("message", ""))
        cmd_route = _detect_command(msg, self._keyword)
        return {
            "route": cmd_route or "chat",
            "keywords": _extract_keywords(
                msg, stop_words=self._keyword.stop_words
            ),
        }
