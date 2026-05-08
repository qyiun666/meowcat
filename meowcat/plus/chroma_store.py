# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus ChromaStore — ChromaDB-backed vector store.

Implements ``meowcat.protocols_storage.VectorStorageProtocol`` for
semantic search and knowledge retrieval. Provides a simple key-value
memory backed by ChromaDB embeddings.

Usage::

    from meowcat.plus.chroma_store import ChromaStore

    store = ChromaStore(collection="my_knowledge")
    doc_id = store.add("Cats are great pets", {"source": "wiki"})
    results = store.search("feline animals", k=3)
    store.delete(doc_id)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChromaStore:
    """ChromaDB-backed vector store for semantic search.

    Implements the ``meowcat.protocols_storage.VectorStorageProtocol``
    interface. Lazily imports ``chromadb`` on first use.

    Supports multiple named collections; each instance operates on
    a single collection.

    Args:
        collection: Collection name (default ``"meowcat"``).
        persist_dir: Directory for persistent storage. If None, uses
            in-memory only (data lost on process exit).
        embedding_fn: Optional custom embedding function. If None,
            uses ChromaDB's default all-MiniLM-L6-v2.

    Implements ``diagnose()`` for :class:`meowcat.diagnose.Stethoscope`.
    """

    def __init__(
        self,
        collection: str = "meowcat",
        *,
        persist_dir: str | None = None,
        embedding_fn: object | None = None,
    ) -> None:
        self._collection_name = collection
        self._persist_dir = persist_dir
        self._embedding_fn = embedding_fn
        self._client: Any = None
        self._collection: Any = None

    # -- Diagnosable interface ---------------------------------------

    def diagnose(self) -> dict[str, object]:
        """Read-only snapshot for Stethoscope probing."""
        return {
            "collection": self._collection_name,
            "persist_dir": self._persist_dir or "in-memory",
            "count": self.count() if self._collection is not None else 0,
            "initialized": self._client is not None,
        }

    # -- VectorStorageProtocol ---------------------------------------

    def add(self, text: str, metadata: dict[str, Any]) -> str:
        """Add a document to the vector store.

        Args:
            text: Document text content.
            metadata: Key-value metadata (source, tags, etc.).

        Returns:
            The generated document ID.
        """
        col = self._require_collection()
        doc_id = _make_id(text, metadata)
        col.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id],
        )
        logger.debug("ChromaStore added doc: %s", doc_id)
        return doc_id

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Semantic search for similar documents.

        Args:
            query: Search query text.
            k: Number of top results to return (default 5).

        Returns:
            List of results, each with ``id``, ``text``, ``metadata``,
            and ``distance``.
        """
        col = self._require_collection()
        results = col.query(query_texts=[query], n_results=k)
        items: list[dict[str, Any]] = []
        if not results.get("ids") or not results["ids"][0]:
            return items
        for i, doc_id in enumerate(results["ids"][0]):
            item: dict[str, Any] = {
                "id": doc_id,
                "text": (results.get("documents") or [[""]])[0][i],
                "metadata": (results.get("metadatas") or [[""]])[0][i] or {},
            }
            if results.get("distances") and results["distances"][0]:
                item["distance"] = results["distances"][0][i]
            items.append(item)
        return items

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID.

        Args:
            doc_id: Document ID returned by :meth:`add`.

        Returns:
            ``True`` if document existed and was deleted.
        """
        col = self._require_collection()
        try:
            col.delete(ids=[doc_id])
            return True
        except Exception as exc:
            logger.warning("ChromaStore delete failed: %s", exc)
            return False

    # -- Additional API ----------------------------------------------

    def count(self) -> int:
        """Return number of documents in the collection."""
        if self._collection is None:
            return 0
        return self._collection.count()

    def list_collections(self) -> list[str]:
        """List all available collection names."""
        client = self._require_client()
        return [c.name for c in client.list_collections()]

    # -- Internal helpers --------------------------------------------

    def _require_client(self) -> Any:
        """Ensure chromadb client is initialized."""
        if self._client is not None:
            return self._client
        try:
            import chromadb  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "chromadb not installed. Install with: pip install chromadb"
            ) from None

        settings_kwargs: dict[str, object] = {}
        if self._persist_dir:
            settings = chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
            settings_kwargs["settings"] = settings
            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                **settings_kwargs,
            )
        else:
            self._client = chromadb.Client()
        logger.info(
            "ChromaDB client initialized (persist=%s)",
            self._persist_dir or "in-memory",
        )
        return self._client

    def _require_collection(self) -> Any:
        """Ensure collection is available, creating if needed."""
        if self._collection is not None:
            return self._collection
        client = self._require_client()
        kwargs: dict[str, object] = {"name": self._collection_name}
        if self._embedding_fn is not None:
            kwargs["embedding_function"] = self._embedding_fn
        self._collection = client.get_or_create_collection(**kwargs)
        return self._collection


def _make_id(text: str, metadata: dict[str, Any]) -> str:
    """Generate a short unique ID from text + metadata."""
    import hashlib
    import json

    seed = json.dumps({"text": text[:200], "meta": metadata}, sort_keys=True, default=str)
    return hashlib.md5(seed.encode()).hexdigest()[:12]
