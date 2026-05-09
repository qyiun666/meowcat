# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default sense organ stubs — no-op implementations satisfying Protocols."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopEars(Pluggable):
    """Default ears: cannot detect keywords, language fixed as unknown.

    Mode B — hear / extract_keywords merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "hear": {"in": "raw: str|bytes", "out": "dict[str, Any]"},
        "extract_keywords": {"in": "text: str, top_k: int", "out": "list[str]"},
    }

    name: str = "noop_ears"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        result: dict[str, Any] = {"text": str(
            raw_input), "keywords": [], "language": "unknown"}
        async for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        result: list[str] = []
        async for _name, r in self._run_plugs("extract_keywords", text, top_k):
            if isinstance(r, list):
                result.extend(r)
        return result

    def detect_language(self, text: str) -> str:
        return "unknown"

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]:
        """Default emotion tagging: return as-is, no modification."""
        return episode


class NoopEyes(Pluggable):
    """Default eyes: cannot see any images.

    Mode C — see full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "see": {"in": "image: bytes, mime: str", "out": "dict[str, Any]"},
    }

    name: str = "noop_eyes"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def see(self, image_data: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        async for _name, r in self._run_plugs("see", image_data, mime_type):
            if isinstance(r, dict):
                return r
        return {}


class NoopWhiskers(Pluggable):
    """Default whiskers: no input sensation, no output drift detection.

    Mode B — feel_input / feel_output / check_hallucination merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "feel_input": {"in": "text: str", "out": "dict[str, Any]"},
        "feel_output": {"in": "output: str, schema: dict", "out": "dict[str, Any]"},
        "check_hallucination": {"in": "reply: str, session_id: str", "out": "dict[str, Any]"},
        "detect_blind_spot": {"in": "queries: list[str], known: list[str]", "out": "list[dict]"},
    }

    name: str = "noop_whiskers"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def feel_input(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        async for _name, r in self._run_plugs("feel_input", text):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def feel_output(
        self,
        output: str,
        expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        async for _name, r in self._run_plugs("feel_output", output, expected_schema):
            if isinstance(r, dict):
                result.update(r)
        return result

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]:
        return {"drift": False}

    async def check_hallucination(
        self,
        reply: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"hallucination": False}
        async for _name, r in self._run_plugs("check_hallucination", reply, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result

    # v1.1.26: curiosity-driven blind spot detection
    async def detect_blind_spot(
        self,
        recent_queries: list[str],
        known_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Default: returns empty — no blind spots detected.

        App layer can mount a ``"detect_blind_spot"`` plug to enable.
        """
        async for _name, r in self._run_plugs(
            "detect_blind_spot",
            recent_queries,
            known_topics or [],
        ):
            if isinstance(r, list):
                return r
        return []
