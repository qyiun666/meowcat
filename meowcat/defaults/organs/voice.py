# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default voice/effector organ implementations — merged Noop+Renovated.

Each Noop* class now includes the renovated (简装修) behavior by default,
providing usable stdout output, streaming tracking, status bar, and tool
registry integration out of the box.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable

_logger = logging.getLogger("meowcat.organs")


class NoopMouth(Pluggable):
    """Default mouth: prints replies to stdout, returns formatted text.

    Mode C — speak full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "speak": {"in": "text: str, **kwargs", "out": "str"},
    }

    name: str = "renovated_mouth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, output_stream: Any = None) -> None:
        Pluggable.__init__(self)
        self._output = output_stream or sys.stdout

    def diagnose(self) -> dict[str, Any]:
        return {"renovated": True, "stream": str(self._output)}

    async def speak(self, text: str, **kwargs: Any) -> str:
        async for _name, r in self._run_plugs("speak", text, **kwargs):
            return r  # type: ignore[no-any-return]
        self._output.write(text + "\n")
        self._output.flush()
        _logger.info("speak: %s", text[:200])
        return text


class NoopPurr(Pluggable):
    """Default purr: streaming status tracker.

    Mode C — stream full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "stream": {"in": "text: str, **kwargs", "out": "Any"},
    }

    name: str = "renovated_purr"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)
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


class NoopTail(Pluggable):
    """Default tail: status bar rendering with debug logging.

    Mode C — render full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "render": {"in": "state: dict", "out": "None"},
    }

    name: str = "renovated_tail"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

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


class NoopPaws(Pluggable):
    """Default paws: tool registry integration with security gate.

    Looks up tools in the cat's tool_registry and executes with try/except.
    Mode C — execute full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "execute": {"in": "name: str, params: dict", "out": "dict[str, Any]"},
        "on_tool_failure": {
            "in": "tool: str, params: dict, error: str, elapsed: float",
            "out": "dict[str, Any]",
        },
    }

    name: str = "renovated_paws"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self, tool_registry: Any = None) -> None:
        Pluggable.__init__(self)
        self._tool_registry = tool_registry

    def diagnose(self) -> dict[str, Any]:
        registered = (
            [t.name for t in self._tool_registry.list_all()]
            if self._tool_registry
            else []
        )
        return {"tools": registered, "count": len(registered)}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Unified tool execution entrypoint (v1.0.7)."""
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

    # v1.1.26: learn from tool execution failures
    async def on_tool_failure(
        self,
        tool_name: str,
        params: dict[str, Any],
        error: str,
        elapsed_ms: float = 0,
    ) -> dict[str, Any]:
        """Default: no-op — records nothing.

        App layer can mount an ``"on_tool_failure"`` plug to enable.
        """
        async for _name, r in self._run_plugs(
            "on_tool_failure",
            tool_name,
            params,
            error,
            elapsed_ms,
        ):
            if isinstance(r, dict):
                return r
        return {"recorded": False}
