# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""VectorStore — lightweight vector store with keyword matching, zero dependencies.

Implements :class:`~meowcat.protocols_storage.VectorStorageProtocol` using
stdlib-only keyword matching (Jaccard similarity on token sets). Optionally
accepts an embedding function for semantic search. Supports JSONL-backed
persistence for process survival.

Usage::

    store = VectorStore(persist_path="./memory.jsonl")
    doc_id = store.add("Cats are great pets", {"source": "wiki"})
    results = store.search("feline animals", k=3)
    store.delete(doc_id)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VectorStore:
    """Lightweight vector store — keyword-based similarity search.

    Implements ``VectorStorageProtocol`` (add / search / delete). Uses
    Jaccard similarity on tokenised text for zero-dependency keyword
    matching.  An optional *embedding_fn* upgrades to full semantic
    search (caller provides e.g. ``sentence-transformers`` model).

    JSONL persistence is activated when *persist_path* is given; each
    ``add`` / ``delete`` atomically writes one line per document.

    Args:
        persist_path: File path for JSONL persistence (None = in-memory).
        embedding_fn: Optional ``(text: str) -> list[float]`` for semantic search.
    """

    def __init__(
        self,
        persist_path: str | Path | None = None,
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._docs: dict[str, dict[str, Any]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        self._embedding_fn = embedding_fn
        if self._persist_path:
            self._load()

    # -- VectorStorageProtocol -----------------------------------------

    def add(self, text: str, metadata: dict[str, Any]) -> str:
        """Add a document and return its generated ID."""
        doc_id = _make_id(text, metadata)
        self._docs[doc_id] = {"text": text, "metadata": metadata}
        if self._persist_path:
            self._append_jsonl({"id": doc_id, "text": text, "metadata": metadata})
        logger.debug("VectorStore added doc: %s", doc_id)
        return doc_id

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search top-*k* similar documents by keyword (or embedding) score."""
        if not self._docs:
            return []

        if self._embedding_fn is not None:
            return self._semantic_search(query, k)
        return self._keyword_search(query, k)

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID. Returns True if it existed."""
        existed = doc_id in self._docs
        self._docs.pop(doc_id, None)
        if existed and self._persist_path:
            self._rewrite_jsonl()
        return existed

    # -- Utility -------------------------------------------------------

    def count(self) -> int:
        """Number of stored documents."""
        return len(self._docs)

    def diagnose(self) -> dict[str, object]:
        """Read-only snapshot for Stethoscope probing."""
        return {
            "count": len(self._docs),
            "persist_path": str(self._persist_path) if self._persist_path else "in-memory",
            "has_embedding": self._embedding_fn is not None,
        }

    # -- Internal: keyword search --------------------------------------

    def _keyword_search(self, query: str, k: int) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
        scored: list[tuple[float, str]] = []
        for doc_id, doc in self._docs.items():
            doc_tokens = _tokenize(doc["text"])
            score = _jaccard(query_tokens, doc_tokens)
            if score > 0:
                scored.append((score, doc_id))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": doc_id,
                "text": self._docs[doc_id]["text"],
                "metadata": self._docs[doc_id]["metadata"],
                "score": score,
            }
            for score, doc_id in scored[:k]
        ]

    # -- Internal: semantic search (with embedding_fn) -----------------

    def _semantic_search(self, query: str, k: int) -> list[dict[str, Any]]:
        assert self._embedding_fn is not None
        query_vec = self._embedding_fn(query)
        scored: list[tuple[float, str]] = []
        for doc_id, doc in self._docs.items():
            if "_embedding" not in doc:
                doc["_embedding"] = self._embedding_fn(doc["text"])
            score = _cosine(query_vec, doc["_embedding"])
            scored.append((score, doc_id))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": doc_id,
                "text": self._docs[doc_id]["text"],
                "metadata": self._docs[doc_id]["metadata"],
                "score": score,
            }
            for score, doc_id in scored[:k]
        ]

    # -- Internal: JSONL persistence -----------------------------------

    def _load(self) -> None:
        assert self._persist_path is not None
        if not self._persist_path.exists():
            return
        with open(self._persist_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                self._docs[rec["id"]] = {"text": rec["text"], "metadata": rec["metadata"]}

    def _append_jsonl(self, record: dict[str, Any]) -> None:
        assert self._persist_path is not None
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(self._persist_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def _rewrite_jsonl(self) -> None:
        assert self._persist_path is not None
        with open(self._persist_path, "w", encoding="utf-8") as fh:
            for doc_id, doc in self._docs.items():
                fh.write(
                    json.dumps(
                        {"id": doc_id, "text": doc["text"], "metadata": doc["metadata"]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )


# -- Helpers ------------------------------------------------------------


def _make_id(text: str, metadata: dict[str, Any]) -> str:
    """Generate a short unique ID from text + metadata."""
    import hashlib

    seed = json.dumps({"text": text[:200], "meta": metadata}, sort_keys=True, default=str)
    return hashlib.sha256(seed.encode()).hexdigest()[:12]


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of lowercased tokens (2+ chars).

    Handles both ASCII words and CJK characters as bigrams.
    """
    import re

    tokens: set[str] = set()
    # ASCII / Latin / Cyrillic words (2+ chars)
    tokens.update(t.lower() for t in re.findall(r"[\u0041-\u024F\u0400-\u04FF]{2,}", text))
    # CJK characters → bigrams for partial matching
    cjk = re.findall(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF]", text)
    for i in range(len(cjk)):
        tokens.add(cjk[i])  # unigram
        if i + 1 < len(cjk):
            tokens.add(cjk[i] + cjk[i + 1])  # bigram
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity coefficient."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    import math

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
