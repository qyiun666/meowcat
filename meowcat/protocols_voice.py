# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat voice protocols — mouth/purr/tail output organ interfaces.

v1.0.7: completed Protocol definitions for Mouth/Purr/Tail,
replacing the weak ``protocol=None`` constraint in biology.py.
"""


from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MouthProtocol(Protocol):
    """Mouth — text output hub. Handles final reply formatting and output.

    **Position**: ``("voice", "mouth")``
    **Inbound**: CEREBELLUM, AMYGDALA, BRAINSTEM
    **Outbound**: none (terminal output organ)
    **Reflex Arc**: text_dialogue, danger
    **Implemented by**: app layer (output organ)
    """

    name: str

    async def speak(self, text: str, **kwargs: Any) -> str: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class PurrProtocol(Protocol):
    """Purr — streaming output hub. Pushes reply token-by-token.

    **Position**: ``("voice", "purr")``
    **Inbound**: CEREBELLUM, BRAINSTEM
    **Outbound**: none (terminal output organ)
    **Reflex Arc**: text_dialogue (stream path)
    **Implemented by**: app layer (output organ)
    """

    name: str

    async def stream(self, text: str, **kwargs: Any) -> Any: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class TailProtocol(Protocol):
    """Tail — status bar rendering hub. Handles terminal UI / progress bar rendering.

    **Position**: ``("voice", "tail")``
    **Inbound**: CEREBELLUM, BRAINSTEM
    **Outbound**: none (terminal output organ)
    **Reflex Arc**: none direct
    **Implemented by**: app layer (output organ)
    """

    name: str

    async def render(self, state: dict[str, Any]) -> None: ...

    def diagnose(self) -> dict[str, Any]: ...


__all__ = ["MouthProtocol", "PurrProtocol", "TailProtocol"]
