"""JsonlL6Store — JSONL-based persistent L6 conversation storage.

Implements :class:`~meowcat.protocols_storage.L6StorageProtocol` using
stdlib ``json`` + ``pathlib``, zero external dependencies.  Each cat's
raw dialogue turns are appended as one JSON line per turn in
``{data_dir}/{cat_id}.jsonl``.

Usage::

    store = JsonlL6Store("/data/conversations")
    store.append("my-cat", 1, "Hello", "Hi there!")
    turns = store.load_all("my-cat")
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlL6Store:
    """Persistent L6 raw-dialogue store backed by JSONL files.

    Implements ``L6StorageProtocol``: append / load_all / load_recent /
    total_chars / get_stats.  Thread-safe as each append writes a
    complete line atomically (``write`` + ``flush``).
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._dir = Path(data_dir).resolve()
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- Protocol (L6StorageProtocol) -----------------------------------

    def append(self, cat_id: str, turn: int,
               user_msg: str, ai_reply: str) -> None:
        """Append one dialogue turn to the cat's JSONL file."""
        record = {"turn": turn, "user": user_msg, "ai": ai_reply}
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(self._file_path(cat_id), "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()

    def load_all(self, cat_id: str) -> list[dict[str, Any]]:
        """Load all conversation turns for *cat_id*."""
        return self._read_lines(cat_id)

    def load_recent(self, cat_id: str, n: int = 20) -> list[dict[str, Any]]:
        """Load the most recent *n* turns."""
        lines = self._read_lines(cat_id)
        return lines[-n:] if lines else []

    def total_chars(self, cat_id: str) -> int:
        """Total characters (user + ai) across all turns."""
        return sum(
            len(r.get("user", "")) + len(r.get("ai", ""))
            for r in self._read_lines(cat_id)
        )

    def get_stats(self, cat_id: str) -> dict[str, Any]:
        """Return ``{"total_turns": N, "total_chars": C}``."""
        records = self._read_lines(cat_id)
        return {
            "total_turns": len(records),
            "total_chars": self.total_chars(cat_id),
        }

    # -- Internal -------------------------------------------------------

    def _file_path(self, cat_id: str) -> Path:
        return self._dir / f"{cat_id}.jsonl"

    def _read_lines(self, cat_id: str) -> list[dict[str, Any]]:
        """Read and parse all lines from {cat_id}.jsonl (idempotent)."""
        fp = self._file_path(cat_id)
        if not fp.exists():
            return []
        result: list[dict[str, Any]] = []
        with open(fp, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    result.append(json.loads(line)  # type: ignore[arg-type]
                                  )
        return result
