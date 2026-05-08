# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default storage — pure in-memory implementation, zero external dependencies.

For rapid prototyping and testing. Use meowagent SQLite/JSONL implementations for production.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from meowcat.storage import SharedStore


class InMemoryGraphStore:
    """Default graph store — pure Python dict, lost on process restart."""

    def __init__(self) -> None:
        self._graphs: dict[str, dict[str, Any]] = {}

    async def load(self, cat_uid: str) -> dict[str, Any]:
        return self._graphs.get(cat_uid, {})

    async def save(self, cat_uid: str, graph_data: dict[str, Any]) -> None:
        self._graphs[cat_uid] = graph_data


class InMemoryVectorStore:
    """Default vector store — pure Python dict + cosine similarity, lost on process restart."""

    def __init__(self) -> None:
        import math

        self._math = math
        self._store: dict[str, list[float]] = {}

    async def store(self, entity_id: str, embedding: list[float]) -> None:
        self._store[entity_id] = embedding

    async def search(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> list[str]:
        if not self._store:
            return []
        scored: list[tuple[float, str]] = []
        for eid, emb in self._store.items():
            sim = self._cosine_similarity(embedding, emb)
            scored.append((sim, eid))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [eid for _, eid in scored[:top_k]]

    # -- Protocol compat methods ------------------------------------------
    async def add(self, text: str, metadata: dict[str, Any]) -> str:
        raise NotImplementedError(
            "InMemoryVectorStore.add() is not implemented. "
            "Use InMemoryVectorStore.store(entity_id, embedding) for vector ops, "
            "or use meowcat.storage.VectorStore for text-level add/search/delete."
        )

    async def delete(self, doc_id: str) -> bool:
        return self._store.pop(doc_id, None) is not None

    # -- Internal ----------------------------------------------------
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = self._math.sqrt(sum(x * x for x in a))
        norm_b = self._math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class InMemorySharedStore(SharedStore):
    """Default shared store — pure Python dict, lost on process restart.

    Default implementation for Colony shared memory, suitable for single-process prototypes.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._watchers: dict[str, list[asyncio.Queue]] = {}

    async def get(self, key: str) -> Any:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        # Notify watchers
        self._notify_watchers(key, value)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._notify_watchers(key, None)

    async def list_keys(self) -> list[str]:
        """List all stored keys."""
        return list(self._data.keys())

    async def watch(self, pattern: str) -> Any:
        """Watch key changes matching pattern.

        Returns an AsyncIterator that yields (key, value) tuples on each change.
        Pattern supports prefix matching: key.startswith(pattern).
        """
        q: asyncio.Queue = asyncio.Queue()
        if pattern not in self._watchers:
            self._watchers[pattern] = []
        self._watchers[pattern].append(q)
        try:
            while True:
                item = await q.get()
                yield item
        finally:
            watchers = self._watchers.get(pattern, [])
            if q in watchers:
                watchers.remove(q)

    def _notify_watchers(self, key: str, value: Any) -> None:
        """Notify matching watchers."""
        for pattern, queues in list(self._watchers.items()):
            if key.startswith(pattern):
                for q in queues:
                    with contextlib.suppress(asyncio.QueueFull):
                        q.put_nowait((key, value))

    # -- SharedStore compat methods (override for efficiency) ---------
    async def load(self) -> dict[str, Any]:
        return dict(self._data)

    async def save(self, data: dict[str, Any]) -> None:
        self._data.update(data)
        for key in data:
            self._notify_watchers(key, data[key])

    async def merge(self, delta: dict[str, Any]) -> dict[str, Any]:
        self._data.update(delta)
        for key in delta:
            self._notify_watchers(key, delta[key])
        return dict(self._data)


class InMemoryL6Store:
    """Default L6 conversation store — pure Python list, lost on process restart."""

    def __init__(self) -> None:
        self._records: dict[str, list[dict[str, Any]]] = {}

    def append(self, cat_uid: str, turn: int, user_msg: str, ai_reply: str) -> None:
        if cat_uid not in self._records:
            self._records[cat_uid] = []
        self._records[cat_uid].append(
            {
                "turn": turn,
                "user": user_msg,
                "ai": ai_reply,
            }
        )

    def load_all(self, cat_uid: str) -> list[dict[str, Any]]:
        return self._records.get(cat_uid, [])

    def load_recent(self, cat_uid: str, n: int = 20) -> list[dict[str, Any]]:
        records = self._records.get(cat_uid, [])
        return records[-n:] if records else []

    def total_chars(self, cat_uid: str) -> int:
        records = self._records.get(cat_uid, [])
        return sum(len(r.get("user", "")) + len(r.get("ai", "")) for r in records)

    def get_stats(self, cat_uid: str) -> dict[str, Any]:
        records = self._records.get(cat_uid, [])
        return {
            "total_turns": len(records),
            "total_chars": self.total_chars(cat_uid),
        }
