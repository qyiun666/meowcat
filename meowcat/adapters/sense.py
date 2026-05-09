# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat sense organ adapters — Ears, Eyes, Whiskers, Paws.

v1.2.14: One adapter per sense Protocol.
"""

from __future__ import annotations

from typing import Any

from meowcat.adapters.base import AgentOrgan


class EarsAgent(AgentOrgan):
    """Adapter for EarsProtocol — delegates input processing to an external agent."""

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        return await self._delegate("hear", raw_input=raw_input)

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        fn = getattr(self._agent, "extract_keywords", None)
        if fn:
            result = fn(text=text, top_k=top_k)
            return result if isinstance(result, list) else []
        return []

    def detect_language(self, text: str) -> str:
        fn = getattr(self._agent, "detect_language", None)
        if fn:
            result = fn(text=text)
            return result if isinstance(result, str) else "unknown"
        return "unknown"

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]:
        fn = getattr(self._agent, "tag_emotion", None)
        if fn:
            result = fn(episode=episode)
            return result if isinstance(result, dict) else episode
        return episode


class EyesAgent(AgentOrgan):
    """Adapter for EyesProtocol — delegates visual input processing to an external agent."""

    async def see(
        self,
        image_data: bytes,
        mime_type: str = "image/png",
    ) -> dict[str, Any]:
        return await self._delegate("see", image_data=image_data, mime_type=mime_type)


class WhiskersAgent(AgentOrgan):
    """Adapter for WhiskersProtocol — delegates environment perception to an external agent."""

    async def feel_input(self, text: str) -> dict[str, Any]:
        return await self._delegate("feel_input", text=text)

    async def feel_output(
        self,
        output: str,
        expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._delegate(
            "feel_output",
            output=output,
            expected_schema=expected_schema,
        )

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]:
        fn = getattr(self._agent, "detect_drift", None)
        if fn:
            result = fn(recent_outputs=recent_outputs)
            return result if isinstance(result, dict) else {"drift": False}
        return {"drift": False}

    def check_hallucination(
        self,
        reply: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        fn = getattr(self._agent, "check_hallucination", None)
        if fn:
            result = fn(reply=reply, session_id=session_id)
            return result if isinstance(result, dict) else {"hallucination": False}
        return {"hallucination": False}

    def detect_blind_spot(
        self,
        recent_queries: list[str],
        known_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        fn = getattr(self._agent, "detect_blind_spot", None)
        if fn:
            result = fn(
                recent_queries=recent_queries,
                known_topics=known_topics or [],
            )
            return result if isinstance(result, list) else []
        return []


class PawsAgent(AgentOrgan):
    """Adapter for PawsProtocol — delegates tool execution to an external agent.

    The backing agent should implement ``execute(tool_name, params) -> dict``.

    Mode C — hooks can fully replace execute.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "execute": {"in": "name: str, params: dict", "out": "dict[str, Any]"},
        "on_tool_failure": {
            "in": "tool: str, params: dict, error: str, elapsed: float",
            "out": "dict[str, Any]",
        },
    }

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        async for _name, r in self._run_plugs("execute", tool_name, params):
            if isinstance(r, dict):
                return r
        return await self._delegate("execute", tool_name=tool_name, params=params)

    def on_tool_failure(
        self,
        tool_name: str,
        params: dict[str, Any],
        error: str,
        elapsed_ms: float = 0,
    ) -> dict[str, Any]:
        fn = getattr(self._agent, "on_tool_failure", None)
        if fn:
            result = fn(
                tool_name=tool_name,
                params=params,
                error=error,
                elapsed_ms=elapsed_ms,
            )
            return result if isinstance(result, dict) else {"recorded": False}
        return {"recorded": False}


__all__ = ["EarsAgent", "EyesAgent", "WhiskersAgent", "PawsAgent"]
