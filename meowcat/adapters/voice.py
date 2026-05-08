# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat voice organ adapters — Mouth, Purr, Tail.

v1.2.14: One adapter per voice Protocol.
"""

from __future__ import annotations

from typing import Any

from meowcat.adapters.base import AgentOrgan


class MouthAgent(AgentOrgan):
    """Adapter for MouthProtocol — delegates text output to an external agent.

    Mode C — hooks can fully replace speak.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "speak": {"in": "text: str, **kwargs", "out": "str"},
    }

    async def speak(self, text: str, **kwargs: Any) -> str:
        async for _name, r in self._run_plugs("speak", text, **kwargs):
            return r
        return await self._delegate("speak", text=text, **kwargs)


class PurrAgent(AgentOrgan):
    """Adapter for PurrProtocol — delegates streaming output to an external agent."""

    async def stream(self, text: str, **kwargs: Any) -> Any:
        return await self._delegate("stream", text=text, **kwargs)


class TailAgent(AgentOrgan):
    """Adapter for TailProtocol — delegates status rendering to an external agent."""

    async def render(self, state: dict[str, Any]) -> None:
        await self._delegate("render", state=state)


__all__ = ["MouthAgent", "PurrAgent", "TailAgent"]
