# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat sense protocols — ears/eyes/whiskers/paws sensory organ interfaces.

All typing.Protocol (duck typing), zero third-party dependencies.
"""


from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "EarsProtocol", "EyesProtocol", "WhiskersProtocol", "PawsProtocol",
]


@runtime_checkable
class EarsProtocol(Protocol):
    """Ears — text and audio input reception hub. All external text/voice enters the nervous system here.

    **Position**: ``("sense", "ears")``
    **Inbound**: none (pure input, only receives external calls)
    **Outbound**: THALAMUS
    **Reflex Arc**: text_dialogue, danger, action_order
    **Implemented by**: app layer (sensory organ)
    """
    name: str
    async def hear(self, raw_input: str | bytes) -> dict[str, Any]: ...
    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]: ...
    def detect_language(self, text: str) -> str: ...
    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]: ...


# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

@runtime_checkable
class EyesProtocol(Protocol):
    """Eyes — image/video visual input.
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    v1.0.8: scan_screen / describe removed (app-layer specific),
    keeping only the generic see method.

    **Position**: ``("sense", "eyes")``
    **Inbound**: none (pure input, only receives external calls)
    **Outbound**: THALAMUS
    **Reflex Arc**: visual (EYES→THALAMUS→CEREBRUM→CEREBELLUM→MOUTH)
    **Implemented by**: app layer (sensory organ)
    """
    name: str

    async def see(self, image_data: bytes,
                  mime_type: str = "image/png") -> dict[str, Any]: ...


@runtime_checkable
class WhiskersProtocol(Protocol):
    """Whiskers — environment perception and safety detection. Input/output sensing, drift detection, hallucination check.

    **Position**: ``("sense", "whiskers")``
    **Inbound**: none (pure input, only receives external calls)
    **Outbound**: THALAMUS
    **Reflex Arc**: none direct; called via feel_input/feel_output in Pipeline
    **Implemented by**: app layer (sensory organ)
    """
    name: str
    async def feel_input(self, text: str) -> dict[str, Any]: ...
    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]: ...

    def check_hallucination(
        self, reply: str, session_id: str | None = None) -> dict[str, Any]: ...

    # v1.1.26 active growth: curiosity-driven blind spot detection
    def detect_blind_spot(
        self, recent_queries: list[str], known_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class PawsProtocol(Protocol):
    """Paws — tool execution and file operations. Effector for Skills + MCP tool calls.

    **Position**: ``("sense", "paws")``
    **Inbound**: CEREBELLUM (only inbound; brain does not directly connect to limbs)
    **Outbound**: none (terminal effector, only accepts commands, never initiates calls)
    **Reflex Arc**: action_order (EARS→THALAMUS→AMYGDALA→CEREBELLUM→PAWS)
    **Implemented by**: app layer (sensory organ)
    """
    name: str

    async def execute(self, tool_name: str,
                      params: dict[str, Any]) -> dict[str, Any]: ...

    # v1.1.26 active growth: learn from tool execution failures
    def on_tool_failure(
        self, tool_name: str, params: dict[str, Any],
        error: str, elapsed_ms: float = 0,
    ) -> dict[str, Any]: ...

    # -- deprecated (v1.0.8, internally delegates to execute) -----------
    async def touch_file(self, path: str, content: str |
                         None = None) -> dict[str, Any]: ...

    async def run_command(self, command: str, **
                          kwargs: Any) -> dict[str, Any]: ...

    async def interact_with_tool(
        self, skill_name: str, params: dict[str, Any]) -> dict[str, Any]: ...

