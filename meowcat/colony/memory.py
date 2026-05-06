# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""SharedMemoryPool — colony-level shared memory for cross-cat knowledge sharing.

Integrates with Colony's namespace storage and optional VectorStore for
semantic recall. Cats add memories here for colony-wide sharing; recall
searches across all shared memories.

Usage::

    # Access via Colony.memory (lazy-init)
    await colony.memory.remember("用户喜欢 Python 3.12", {"cat": "planner"})
    results = await colony.memory.recall("Python 版本", k=5)
    await colony.memory.forget("abc123")
"""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from meowcat.colony import Colony
    from meowcat.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

_MEMORY_NS = "knowledge"
_MEMORY_KEY_PREFIX = "mem:"


class SharedMemoryPool:
    """Colony-level shared memory pool with optional vector search.

    Attached to a :class:`~meowcat.colony.Colony` via ``colony.memory``,
    lazily initialised on first access.  Uses the colony's namespace
    storage (``knowledge/``) for persistence and optionally a
    :class:`~meowcat.storage.vector_store.VectorStore` for semantic search.

    Args:
        colony: The parent colony instance.
        vector_store: Optional vector backend; if None, creates a default
            :class:`VectorStore` in memory-only mode.
    """

    def __init__(
        self,
        colony: Colony,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._colony = colony
        self._vector = vector_store

    # -- Core API ------------------------------------------------------

    async def remember(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a shared memory entry.

        Writes to colony namespace storage (``knowledge/mem:{id}``) for
        persistence, and indexes in the vector store for semantic recall.

        Args:
            text: Memory content text.
            metadata: Optional metadata (source cat, timestamp, tags).

        Returns:
            The generated memory ID.
        """
        meta = dict(metadata or {})
        doc_id = (await self._ensure_vector()).add(text, meta)

        # Persist via colony namespace
        record = {"id": doc_id, "text": text, "metadata": meta}
        await self._colony.ns_set(
            _MEMORY_NS, f"{_MEMORY_KEY_PREFIX}{doc_id}",
            json.dumps(record, ensure_ascii=False),
        )
        logger.debug("SharedMemory: remembered %s", doc_id)
        return doc_id

    async def recall(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search across shared memories.

        Args:
            query: Search query text.
            k: Number of top results to return.

        Returns:
            List of results with ``id``, ``text``, ``metadata``, ``score``.
        """
        vs = await self._ensure_vector()
        return vs.search(query, k=k)

    async def forget(self, memory_id: str) -> bool:
        """Remove a shared memory entry by ID.

        Args:
            memory_id: Memory ID returned by :meth:`remember`.

        Returns:
            ``True`` if the memory existed and was deleted.
        """
        vs = await self._ensure_vector()
        deleted = vs.delete(memory_id)
        if deleted:
            await self._colony.ns_delete(
                _MEMORY_NS, f"{_MEMORY_KEY_PREFIX}{memory_id}")
        return deleted

    async def list_all(self) -> list[dict[str, Any]]:
        """List all shared memory entries.

        Returns:
            List of memory records (``id``, ``text``, ``metadata``).
        """
        keys = await self._colony.ns_list_keys(_MEMORY_NS)
        results: list[dict[str, Any]] = []
        for k in keys:
            if k.startswith(_MEMORY_KEY_PREFIX):
                raw = await self._colony.ns_get(_MEMORY_NS, k)
                if raw:
                    results.append(json.loads(raw))
        return results
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    async def count(self) -> int:
        """Number of shared memory entries."""
        vs = await self._ensure_vector()
        return vs.count()
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    def keyword_search(
        self,
        query: str,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Sync keyword search across shared memories — for Hippocampus.locate(scope='colony').

        Performs simple case-insensitive keyword matching on stored memory
        text fields.  No async / vector-store dependency.

        Args:
            query: Search query (space-separated keywords).
            k: Max results to return.

        Returns:
            List of ``{"id", "text", "metadata", "score"}`` dicts.
        """
        kws = query.lower().split()
        results: list[dict[str, Any]] = []
        for record in self._get_all_sync():
            text = record.get("text", "").lower()
            score = sum(1 for kw in kws if kw in text) / max(len(kws), 1)
            if score > 0:
                results.append({
                    "id": record.get("id", ""),
                    "text": record.get("text", ""),
                    "metadata": record.get("metadata", {}),
                    "score": score,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def _get_all_sync(self) -> list[dict[str, Any]]:
        """Return all stored memory records (sync subset).

        Direct-access path on ``InMemorySharedStore._data`` — avoids
        async calls.  Raises ``NotImplementedError`` for non-in-memory
        storage backends (persistent backends must use async ``list_all()``).
        """
        import json as _json
        storage = getattr(self._colony, '_storage', None)
        if storage is None:
            return []
        if not hasattr(storage, '_data'):
            raise NotImplementedError(
                "keyword_search requires InMemorySharedStore backend; "
                f"got {type(storage).__name__}. Use async recall() instead."
            )
        data: dict = storage._data
        prefix = f"{self._colony._NS_PREFIX}/{_MEMORY_NS}/{_MEMORY_KEY_PREFIX}"
        results: list[dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(key, str) and key.startswith(prefix):
                try:
                    results.append(
                        _json.loads(value) if isinstance(
                            value, str) else value
                    )
                except (_json.JSONDecodeError, TypeError):
                    pass
        return results

    # -- Internal ------------------------------------------------------

    async def _ensure_vector(self) -> VectorStore:
        """Lazy-init vector store if not provided."""
        if self._vector is None:
            from meowcat.storage.vector_store import VectorStore  # noqa: PLC0415
            self._vector = VectorStore()
            # Load existing persisted memories into vector store
            for record in await self.list_all():
                self._vector.add(record["text"], record["metadata"])
        return self._vector

