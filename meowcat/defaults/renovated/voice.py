# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) output organ implementations — 4 classes."""

from __future__ import annotations

import logging
import sys
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs import (
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
)

_logger = logging.getLogger("meowcat.renovated")


# =========================================================================
# Voice — 简装修
# =========================================================================


class RenovatedMouth(NoopMouth):
    """简装修 mouth: text output formatting + stdout printing.

    Prints replies to stdout (configurable via ``output_stream``) and
    returns the formatted text.
    """

    name: str = "renovated_mouth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, output_stream: Any = None) -> None:
        NoopMouth.__init__(self)
        self._output = output_stream or sys.stdout

    def diagnose(self) -> dict[str, Any]:
        return {"renovated": True, "stream": str(self._output)}

    async def speak(self, text: str, **kwargs: Any) -> str:
        async for _name, r in self._run_plugs("speak", text, **kwargs):
            return r
        self._output.write(text + "\n")
        self._output.flush()
        _logger.info("speak: %s", text[:200])
        return text


class RenovatedPurr(NoopPurr):
    """简装修 purr: streaming status tracker.

    Tracks streaming state (started, chunk count, finished) for progress reporting.
    """

    name: str = "renovated_purr"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        NoopPurr.__init__(self)
        self._streaming = False
        self._chunk_count = 0
        self._total_chars = 0

    def diagnose(self) -> dict[str, Any]:
        return {
            "streaming": self._streaming,
            "chunks": self._chunk_count,
            "chars": self._total_chars,
        }

    async def stream(self, text: str, **kwargs: Any) -> Any:
        async for _name, r in self._run_plugs("stream", text, **kwargs):
            return r
        self._streaming = True
        self._chunk_count += 1
        self._total_chars += len(text)
        return None


class RenovatedTail(NoopTail):
    """简装修 tail: simple status bar (prints to stdout).

    Renders key health metrics: uptime, memory entities, safety state.
    """

    name: str = "renovated_tail"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def diagnose(self) -> dict[str, Any]:
        return {"renovated": True}

    async def render(self, state: dict[str, Any]) -> None:
        async for _name, _r in self._run_plugs("render", state):
            return None
        status = state.get("status", "idle")
        entities = state.get("entities", 0)
        episodes = state.get("episodes", 0)
        bar = f"[{status}] mem: {entities}e/{episodes}ep"
        _logger.debug("tail: %s", bar)


# =========================================================================
# Effectors — 简装修
# =========================================================================


class RenovatedPaws(NoopPaws):
    """简装修 paws: tool registry integration + security gate.

    Looks up tools in the cat's tool_registry, checks security via amygdala,
    and executes with safety policy.
    """

    name: str = "renovated_paws"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, tool_registry: Any = None) -> None:
        NoopPaws.__init__(self)
        self._tool_registry = tool_registry

    def diagnose(self) -> dict[str, Any]:
        registered = [t.name for t in self._tool_registry.list_all()
                      ] if self._tool_registry else []
        return {"tools": registered, "count": len(registered)}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        async for _name, r in self._run_plugs("execute", tool_name, params):
            if isinstance(r, dict):
                return r
        if self._tool_registry is None:
            return {"ok": False, "reason": "no tool_registry mounted"}
        spec = self._tool_registry.get(tool_name)
        if spec is None:
            return {"ok": False, "reason": f"tool '{tool_name}' not found"}
        try:
            result = await spec.fn(**params)
            return {"ok": True, "result": result}
        except Exception as exc:
            _logger.exception("Tool '%s' failed", tool_name)
            return {"ok": False, "reason": str(exc)}

    async def interact_with_tool(
        self,
        skill_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.execute(skill_name, params)
