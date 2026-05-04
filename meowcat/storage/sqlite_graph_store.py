"""SqliteGraphStore — SQLite-backed persistent graph storage.

Implements :class:`~meowcat.protocols_storage.GraphStorageProtocol` using
stdlib ``sqlite3``, zero external dependencies.  Each cat's entanglement
graph is stored as a JSON blob keyed by ``cat_id``.

Usage::

    store = SqliteGraphStore("/data/cat_graphs.db")
    await store.save("my-cat", {"entities": [...], "connections": [...]})
    data = await store.load("my-cat")
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteGraphStore:
    """Persistent graph store backed by a single SQLite database file.

    Implements ``GraphStorageProtocol`` (load/save).  Uses a simple
    key-value table where ``cat_id`` is the primary key and
    ``graph_data`` holds the JSON-serialised graph dict.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path).resolve()
        self._ensure_table()

    # -- Protocol (GraphStorageProtocol) ---------------------------------

    async def load(self, cat_id: str) -> dict[str, Any]:
        """Load the persisted graph data for *cat_id*, or ``{}`` if missing."""
        row = self._query_one(
            "SELECT graph_data FROM cat_graphs WHERE cat_id = ?", (cat_id,))
        if row is None:
            return {}
        return json.loads(row[0])  # type: ignore[no-any-return]

    async def save(self, cat_id: str, graph_data: dict[str, Any]) -> None:
        """Persist *graph_data* for *cat_id* (upsert)."""
        blob = json.dumps(graph_data, ensure_ascii=False)
        self._execute(
            "INSERT OR REPLACE INTO cat_graphs(cat_id, graph_data) VALUES (?, ?)",
            (cat_id, blob),
        )

    # -- Internal helpers --------------------------------------------------

    def _ensure_table(self) -> None:
        self._execute(
            "CREATE TABLE IF NOT EXISTS cat_graphs ("
            "  cat_id TEXT PRIMARY KEY,"
            "  graph_data TEXT NOT NULL"
            ")"
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _execute(self, sql: str, params: tuple = ()) -> None:
        with self._connect() as conn:
            conn.execute(sql, params)

    def _query_one(self, sql: str, params: tuple = ()) -> Any:
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchone()
