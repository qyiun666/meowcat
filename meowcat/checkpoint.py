# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""General-purpose checkpoint store for orchestration snapshots.

T-24 (v1.3.6): Framework-layer checkpoint persistence protocol + default
JSON-file implementation.  Each checkpoint is a best-effort snapshot of
arbitrary ``dict`` data keyed by a string ID.

Usage::

    store = JsonCheckpointStore("/data/checkpoints")
    await store.save("task-001", {"step": 3, "results": [...]})
    snap = await store.load("task-001")
    await store.delete("task-001")
"""

from __future__ import annotations

import contextlib
import json as _json
import os as _os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class CheckpointConfig:
    """Configuration for checkpoint storage.

    Attributes:
        data_dir:  Directory where checkpoint JSON files are stored.
        autosave:  Whether to enable auto-save on shutdown (T-10 lifecycle).
    """

    data_dir: str = "./data/checkpoints"
    autosave: bool = True


# ── CheckpointStore — abstract base ────────────────────────────────────


class CheckpointStore(ABC):
    """Abstract base class for general-purpose checkpoint persistence.

    Framework-layer: defines the interface for saving/loading
    arbitrary checkpoint snapshots as ``dict[str, Any]``, keyed by
    a string identifier.  Not tied to any specific data model.

    App-layer: plugs in concrete storage (JSON file, SQLite, Redis, etc.).

    Lifecycle: ``JsonCheckpointStore`` supports registering ``on_start`` /
    ``on_shutdown`` hooks on a :class:`~meowcat.assembly.CatBase` instance
    for automatic load/save.
    """

    # ── Core API (subclass must implement) ──────────────────────────

    @abstractmethod
    async def save(self, key: str, data: dict[str, Any]) -> None:
        """Persist a checkpoint snapshot.

        Args:
            key:  Unique checkpoint identifier.
            data: Arbitrary dict payload to persist.
        """
        ...

    @abstractmethod
    async def load(self, key: str) -> dict[str, Any] | None:
        """Load a checkpoint snapshot.

        Args:
            key: Unique checkpoint identifier.

        Returns:
            The persisted dict, or ``None`` if no checkpoint exists.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a checkpoint.

        Args:
            key: Unique checkpoint identifier.
        """
        ...

    @abstractmethod
    async def list_keys(self) -> list[str]:
        """List all checkpoint keys currently persisted.

        Returns:
            Sorted list of checkpoint identifiers.
        """
        ...


# ── JsonCheckpointStore — default JSON-file implementation ────────────


class JsonCheckpointStore(CheckpointStore):
    """JSON-file-based checkpoint store — default implementation.

    Each checkpoint is persisted as a single JSON file:
    ``{data_dir}/{key}.checkpoint.json``

    Uses atomic write (write-to-tmp + rename) to avoid partial files
    on crash.  Zero external dependencies (stdlib only).

    Lifecycle integration (T-10)::

        store = JsonCheckpointStore("/data/checkpoints")
        cat.on_shutdown(lambda c: store.save_all())   # auto-flush
        cat.on_start(lambda c: store.load_all())       # auto-restore

    Usage::

        store = JsonCheckpointStore("/data/checkpoints")
        await store.save("orchestrator-001", {"dag": {...}, "progress": 0.5})
        snap = await store.load("orchestrator-001")
        keys = await store.list_keys()
    """

    _SUFFIX: str = ".checkpoint.json"

    def __init__(self, data_dir: str | Path = "./data/checkpoints") -> None:
        self._config = CheckpointConfig(data_dir=str(data_dir))
        self._dir = Path(self._config.data_dir).resolve()
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> CheckpointConfig:
        """Current configuration (read-only)."""
        return CheckpointConfig(
            data_dir=self._config.data_dir,
            autosave=self._config.autosave,
        )

    # ── Core API ────────────────────────────────────────────────────

    async def save(self, key: str, data: dict[str, Any]) -> None:
        """Persist *data* for *key* with atomic file replacement."""
        import anyio

        await anyio.to_thread.run_sync(self._save_sync, key, data)

    def _save_sync(self, key: str, data: dict[str, Any]) -> None:
        fp = self._file_path(key)
        fp.parent.mkdir(parents=True, exist_ok=True)
        tmp = fp.with_suffix(fp.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            _json.dump(data, fh, ensure_ascii=False, default=str, indent=2)
            fh.flush()
            _os.fsync(fh.fileno())
        _os.replace(tmp, fp)

    async def load(self, key: str) -> dict[str, Any] | None:
        """Load checkpoint for *key*, or ``None``."""
        import anyio

        return await anyio.to_thread.run_sync(self._load_sync, key)

    def _load_sync(self, key: str) -> dict[str, Any] | None:
        fp = self._file_path(key)
        if not fp.exists():
            return None
        with open(fp, encoding="utf-8") as fh:
            return _json.load(fh)  # type: ignore[no-any-return]

    async def delete(self, key: str) -> None:
        """Remove checkpoint for *key* (no-op if missing)."""
        import anyio

        await anyio.to_thread.run_sync(self._delete_sync, key)

    def _delete_sync(self, key: str) -> None:
        fp = self._file_path(key)
        with contextlib.suppress(Exception):
            fp.unlink(missing_ok=True)

    async def list_keys(self) -> list[str]:
        """List all checkpoint keys, sorted."""
        import anyio

        return await anyio.to_thread.run_sync(self._list_keys_sync)

    def _list_keys_sync(self) -> list[str]:
        keys: list[str] = []
        for fp in self._dir.rglob(f"*{self._SUFFIX}"):
            rel = fp.relative_to(self._dir)
            stem = str(rel)[: -len(self._SUFFIX)]
            keys.append(stem)
        return sorted(keys)

    async def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all checkpoints into a ``{key: data}`` dict.

        Useful for lifecycle restore on startup.
        """
        result: dict[str, dict[str, Any]] = {}
        for key in await self.list_keys():
            data = await self.load(key)
            if data is not None:
                result[key] = data
        return result

    # ── Diagnostics ────────────────────────────────────────────────

    def _file_path(self, key: str) -> Path:
        return self._dir / f"{key}{self._SUFFIX}"

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot."""
        return {
            "data_dir": str(self._dir),
            "autosave": self._config.autosave,
        }
