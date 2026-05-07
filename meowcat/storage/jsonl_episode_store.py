# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""JsonlEpisodeStore — JSONL-backed episode persistence with byte-offset index.

Appends each episode as one JSON line in ``{data_dir}/{cat_uid}.episodes.jsonl``
and maintains a byte-offset index at ``{data_dir}/{cat_uid}.episodes.idx.json``
for O(1) single-episode lookup.

Usage::

    store = JsonlEpisodeStore("/data/episodes")
    eid = store.append("my-cat", {"user_msg": "hi", "ai_reply": "hello"})
    ep = store.get("my-cat", eid)
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


class JsonlEpisodeStore:
    """Persistent episode store backed by JSONL + byte-offset index.

    Zero external dependencies (stdlib only).  Thread-safe for append
    (``write`` + ``flush`` per line); reads are idempotent.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self._dir = Path(data_dir).resolve()
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- Public API ------------------------------------------------------

    def append(self, cat_uid: str, episode: dict[str, Any]) -> str:
        """Append an episode, auto-assign id if missing, return episode_id.

        Writes one JSON line to the cat's JSONL file and records the byte
        offset in the index for O(1) lookup.
        """
        eid = episode.get("id") or f"ep_{uuid.uuid4().hex[:8]}"
        if "id" not in episode:
            episode["id"] = eid

        fp = self._file_path(cat_uid)
        offset = fp.stat().st_size if fp.exists() else 0

        line = json.dumps(episode, ensure_ascii=False) + "\n"
        with open(fp, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()

        index = self._load_index(cat_uid)
        index[eid] = offset
        self._save_index(cat_uid, index)
        return eid

    def get(self, cat_uid: str, episode_id: str) -> dict[str, Any] | None:
        """Get a single episode by id (O(1) byte-offset lookup)."""
        index = self._load_index(cat_uid)
        offset = index.get(episode_id)
        if offset is None:
            return None
        fp = self._file_path(cat_uid)
        if not fp.exists():
            return None
        with open(fp, "r", encoding="utf-8") as fh:
            fh.seek(offset)
            line = fh.readline()
            if line:
                return json.loads(line.strip())  # type: ignore[no-any-return]
        return None

    def get_batch(
        self, cat_uid: str, ids: list[str],
    ) -> list[dict[str, Any]]:
        """Batch get episodes by ids."""
        index = self._load_index(cat_uid)
        fp = self._file_path(cat_uid)
        if not fp.exists():
            return []
        result: list[dict[str, Any]] = []
        with open(fp, "r", encoding="utf-8") as fh:
            for eid in ids:
                offset = index.get(eid)
                if offset is not None:
                    fh.seek(offset)
                    line = fh.readline()
                    if line:
                        result.append(json.loads(line.strip()))
        return result

    def load_all(self, cat_uid: str) -> list[dict[str, Any]]:
        """Load all episodes for *cat_uid*."""
        return self._read_lines(cat_uid)

    def get_stats(self, cat_uid: str) -> dict[str, Any]:
        """Return ``{"total_episodes": N}``."""
        index = self._load_index(cat_uid)
        return {"total_episodes": len(index)}

    # -- Internal -------------------------------------------------------

    def _file_path(self, cat_uid: str) -> Path:
        return self._dir / f"{cat_uid}.episodes.jsonl"

    def _index_path(self, cat_uid: str) -> Path:
        return self._dir / f"{cat_uid}.episodes.idx.json"

    def _load_index(self, cat_uid: str) -> dict[str, int]:
        """Load byte-offset index, return empty dict if not found."""
        ip = self._index_path(cat_uid)
        if not ip.exists():
            return {}
        with open(ip, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            # json keys are always str, but values may be int or float
            return {str(k): int(v) for k, v in data.items()}
        return {}

    def _save_index(self, cat_uid: str, index: dict[str, int]) -> None:
        """Atomically write byte-offset index."""
        ip = self._index_path(cat_uid)
        tmp = ip.with_suffix(ip.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(index, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, ip)

    def _read_lines(self, cat_uid: str) -> list[dict[str, Any]]:
        """Read and parse all lines from the JSONL file."""
        fp = self._file_path(cat_uid)
        if not fp.exists():
            return []
        result: list[dict[str, Any]] = []
        with open(fp, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    result.append(json.loads(line))  # type: ignore[arg-type]
        return result
