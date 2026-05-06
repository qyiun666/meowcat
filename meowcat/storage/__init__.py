# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat storage layer — shared storage abstract base + built-in backends.

``meowcat/storage/`` has zero meowagent dependency.
"""

from __future__ import annotations
from meowcat.storage.jsonl_l6_store import JsonlL6Store
from meowcat.storage.sqlite_graph_store import SqliteGraphStore
from meowcat.storage.vector_store import VectorStore

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class SharedStore(ABC):
    """Abstract base class for shared key-value storage backends.

    Colony delegates namespace/cat-level storage through this interface.
    Concrete implementations: :class:`~meowcat.defaults.stores.InMemorySharedStore`,
    SQLiteSharedStore (v1.1.19), etc.

    Usage::

        store = InMemorySharedStore()
        await store.set("key", "value")
        assert await store.get("key") == "value"
    """

    # -- Core API (must implement) ------------------------------------

    @abstractmethod
    async def get(self, key: str) -> Any: ...
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    @abstractmethod
    async def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def list_keys(self) -> list[str]: ...

# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    @abstractmethod
    async def watch(self, pattern: str) -> AsyncIterator[tuple[str, Any]]:
        """Watch key changes matching prefix *pattern*. Yields (key, value)."""
        ...

    # -- SharedStorageProtocol compat (delegates to Core API) ----------

    async def load(self) -> dict[str, Any]:
        """Load all data as dict (protocol compat)."""
        result: dict[str, Any] = {}
        for k in await self.list_keys():
            result[k] = await self.get(k)
        return result

    async def save(self, data: dict[str, Any]) -> None:
        """Bulk save dict entries (protocol compat)."""
        for k, v in data.items():
            await self.set(k, v)

    async def merge(self, delta: dict[str, Any]) -> dict[str, Any]:
        """Merge delta and return full state (protocol compat)."""
        await self.save(delta)
        return await self.load()


__all__ = ["SharedStore", "SqliteGraphStore", "JsonlL6Store", "VectorStore"]

