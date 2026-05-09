# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default voice/effector organ stubs — no-op implementations satisfying Protocols."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopMouth(Pluggable):
    """Default mouth: does not speak.

    Mode C — speak full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "speak": {"in": "text: str, **kwargs", "out": "str"},
    }

    name: str = "noop_mouth"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def speak(self, text: str, **kwargs: Any) -> str:
        async for _name, r in self._run_plugs("speak", text, **kwargs):
            return r  # type: ignore[no-any-return]
        return ""


class NoopPurr(Pluggable):
    """Default purr: no streaming output.

    Mode C — stream full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "stream": {"in": "text: str, **kwargs", "out": "Any"},
    }

    name: str = "noop_purr"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def stream(self, text: str, **kwargs: Any) -> Any:
        async for _name, r in self._run_plugs("stream", text, **kwargs):
            return r
        return None


class NoopTail(Pluggable):
    """Default tail: does not render any terminal UI.

    Mode C — render full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "render": {"in": "state: dict", "out": "None"},
    }

    name: str = "noop_tail"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def render(self, state: dict[str, Any]) -> None:
        async for _name, _r in self._run_plugs("render", state):
            return None
        return None


class NoopPaws(Pluggable):
    """Default paws: does not execute any tool/command.

    Mode C — execute full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "execute": {"in": "name: str, params: dict", "out": "dict[str, Any]"},
        "on_tool_failure": {
            "in": "tool: str, params: dict, error: str, elapsed: float",
            "out": "dict[str, Any]",
        },
    }

    name: str = "noop_paws"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Unified tool execution entrypoint (v1.0.7)."""
        async for _name, r in self._run_plugs("execute", tool_name, params):
            if isinstance(r, dict):
                return r
        return {"ok": False, "reason": "noop_paws: execute disabled"}

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
