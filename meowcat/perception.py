"""meowcat perception context and modality inference.

:class:`PerceptionContext` is the cross-Stage shared state container during
``cat.perceive(input)`` execution; :func:`infer_modality` does coarse modality
inference based on input shape. App layer can customize finer judgments in
Reflex.trigger directly.

Zero meowagent dependency.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from meowcat.protocols import CatProtocol

Modality = Literal["text", "image", "audio", "tool_result", "unknown"]


class PerceptionContext(BaseModel):
    """Execution context for ``cat.perceive``.

    Used by Reflex.stages for shared state; serves as ``ctx`` on the Pipeline.

    v1.0.18: added reply / set_state / get_state / accumulate_reply for Stage
    bypass refactoring (no more bs._xxx private attribute access).
    """

    model_config = {"arbitrary_types_allowed": True}

    input: Any
    """Raw input — text, byte stream, dict, arbitrary object."""

    modality: Modality = "unknown"
    """Inferred input modality."""

    reflex_name: str = ""
    """Matched reflex name."""

    cat: Any = None
    """Back-reference to CatBase instance, for signal in Stages."""

    short_circuited: bool = False
    """Set True after any Stage triggers short_circuit."""

    final_reply: str | None = None
    """Final reply (for CLI/TUI consumption)."""

    reply: str = ""
    """Accumulated reply content across Stages (v1.0.18)."""

    extras: dict[str, Any] = Field(default_factory=dict)
    """Catch-all bag for app-layer custom fields."""

    # ── helpers for cross-Stage state (v1.0.18) ──

    def set_state(self, key: str, value: Any) -> None:
        """Persist a named value in extras for downstream Stages."""
        self.extras[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Read a named value from extras; returns default if missing."""
        return self.extras.get(key, default)

    def accumulate_reply(self, content: str) -> None:
        """Append content to the accumulated reply string."""
        self.reply += content


# -- Modality inference ---------------------------------------------------

_IMAGE_MAGIC: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",    # PNG
    b"\xff\xd8\xff",           # JPEG
    b"GIF87a", b"GIF89a",       # GIF
    b"RIFF",                    # WEBP header
    b"BM",                      # BMP
)

_AUDIO_MAGIC: tuple[bytes, ...] = (
    # WAV (RIFF....WAVE); same magic as WEBP, choose by scenario
    b"RIFF",
    b"ID3",                     # MP3 with ID3 tags
    b"\xff\xfb", b"\xff\xf3",   # MP3 frame header
    b"OggS",                    # OGG
    b"fLaC",                    # FLAC
)


def infer_modality(input: Any) -> Modality:
    """Coarse input modality inference.

    - ``str`` → ``text``
    - ``bytes`` matching image magic → ``image``
    - ``bytes`` matching audio magic → ``audio``
    - ``dict`` with ``tool_result`` key → ``tool_result``
    - otherwise → ``unknown``

    For finer-grained discrimination, write custom logic directly in ``Reflex.trigger``.
    """
    if isinstance(input, str):
        return "text"

    if isinstance(input, (bytes, bytearray)):
        data = bytes(input[:16])
        for magic in _IMAGE_MAGIC:
            if data.startswith(magic):
                return "image"
        for magic in _AUDIO_MAGIC:
            if data.startswith(magic):
                return "audio"
        return "unknown"

    if isinstance(input, dict) and "tool_result" in input:
        return "tool_result"

    return "unknown"


__all__ = ["PerceptionContext", "Modality", "infer_modality"]
