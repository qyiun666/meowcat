# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""FocusStore — persistence protocol and default JSON implementation for Frontal focus state.

T-22 (v1.3.6): Framework-level protocol for persisting the Frontal lobe's
focus/topic tracking state.  App layer plugs in concrete storage (file, SQLite,
Redis, etc.).  The default ``JsonFocusStore`` writes to a local JSON file with
atomic write semantics.

Lifecycle integration (via ``factory.py``):
    - ``on_start`` → load focus state from store → populate ``RenovatedFrontal``
    - ``on_shutdown`` → save focus state to store

Usage::

    from meowcat.focus import JsonFocusStore

    store = JsonFocusStore("/path/to/focus.json")
    state = await store.load()

    state.topics.append("database design, sql")
    await store.save(state)
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── FocusState ───────────────────────────────────────────────────────


@dataclass
class FocusState:
    """Serializable focus state for persistence.

    Attributes:
        topics:            Archived topic keyword lists (one entry per
                           ``archive_focus()`` call).
        current_keywords:  Active keyword set for the current focus.
        threshold:         Topic shift detection threshold (0..1).
    """

    topics: list[str] = field(default_factory=list)
    current_keywords: list[str] = field(default_factory=list)
    threshold: float = 0.3


# ── FocusStore (protocol) ────────────────────────────────────────────


class FocusStore(ABC):
    """Abstract persistence for Frontal focus state.

    Framework-layer: defines the interface.
    App-layer: plugs in concrete storage (file, SQLite, Redis, etc.).
    """

    @abstractmethod
    async def save(self, state: FocusState) -> None:
        """Persist focus state.

        Args:
            state: The current focus state to save.
        """

    @abstractmethod
    async def load(self) -> FocusState | None:
        """Load previously persisted focus state.

        Returns:
            ``FocusState`` if saved state exists, ``None`` otherwise.
        """


# ── JsonFocusStore (default) ─────────────────────────────────────────


class JsonFocusStore(FocusStore):
    """Default JSON file-based focus store with atomic writes.

    Writes to a temporary file first, then atomically renames to the
    target path to avoid data corruption on interrupted writes.

    Args:
        file_path:  Path to the JSON file for persistence.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    @property
    def file_path(self) -> Path:
        """The JSON file path used for persistence."""
        return self._file_path

    # ── FocusStore interface ──────────────────────────────────────

    async def save(self, state: FocusState) -> None:
        """Persist focus state as JSON (atomic write).

        Args:
            state: The current focus state to save.
        """
        data: dict[str, Any] = {
            "topics": state.topics,
            "current_keywords": state.current_keywords,
            "threshold": state.threshold,
        }

        # Ensure parent directory exists
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix=".focus_",
            dir=str(self._file_path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(self._file_path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    async def load(self) -> FocusState | None:
        """Load previously persisted focus state from JSON.

        Returns:
            ``FocusState`` if the file exists and is valid JSON,
            ``None`` otherwise.
        """
        if not self._file_path.exists():
            return None

        try:
            raw = self._file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return FocusState(
                topics=data.get("topics", []),
                current_keywords=data.get("current_keywords", []),
                threshold=data.get("threshold", 0.3),
            )
        except (json.JSONDecodeError, OSError, TypeError):
            return None

    # ── Management ────────────────────────────────────────────────

    async def delete(self) -> None:
        """Remove the persisted focus file."""
        try:
            self._file_path.unlink(missing_ok=True)
        except OSError:
            pass

    # ── Diagnostics ───────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "file_path": str(self._file_path),
            "exists": self._file_path.exists(),
            "file_size": (
                self._file_path.stat().st_size
                if self._file_path.exists()
                else 0
            ),
        }
