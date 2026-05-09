# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""简装修 (renovated) hippocampus — enhanced in-memory graph store with auto-indexing."""

from __future__ import annotations

from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.defaults.organs.hippocampus import NoopHippocampus

from ._helpers import _extract_keywords


class RenovatedHippocampus(NoopHippocampus):
    """简装修 hippocampus: enhanced in-memory graph store with auto-indexing.

    Builds on NoopHippocampus (which already wraps InMemoryGraphStore) and adds
    automatic keyword indexing on ``remember()``.

    v1.3.6: Accepts optional ``episode_store`` (:class:`~meowcat.storage.JsonlEpisodeStore`)
    for persistent episode storage.  Lifecycle methods ``_load_from_store()``
    and ``_flush_to_store()`` are called by the cat's ``on_start`` / ``on_shutdown``
    hooks registered during assembly.
    """

    name: str = "renovated_hippocampus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    # Instance-only: set by factory lifecycle hook before on_start
    cat_uid: str = ""

    def __init__(
        self,
        episode_store: Any | None = None,
    ) -> None:
        NoopHippocampus.__init__(self)
        self._keyword_index: dict[str, set[str]] = {}
        self._episode_store = episode_store

    async def remember(
        self,
        user_msg: str,
        ai_reply: str,
        cat_uid: str,
        model: str,
    ) -> Any:
        result = await NoopHippocampus.remember(self, user_msg, ai_reply, cat_uid, model)
        kws = _extract_keywords(f"{user_msg} {ai_reply}", top_k=10)
        for kw in kws:
            self._keyword_index.setdefault(kw, set()).add(user_msg[:80])
        return result

    def fts_search(
        self,
        cat_uid: str,
        keywords: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        results = NoopHippocampus.fts_search(self, cat_uid, keywords, limit)
        kws = set(keywords.lower().split())
        for kw in kws:
            if kw in self._keyword_index:
                for snippet in self._keyword_index[kw]:
                    if not any(r.get("user_msg", "")[:80] == snippet for r in results):
                        results.append(
                            {"keyword_match": kw, "snippet": snippet})
        return results[:limit]

    # -- v1.3.6: Episode persistence + lifecycle -----------------------

    async def _load_from_store(self) -> None:
        """Load all persisted episodes from store into in-memory list.

        Called by the cat's ``on_start`` hook registered during assembly.
        Safe to call when ``_episode_store`` is None (no-op).
        """
        if self._episode_store is None or not self.cat_uid:
            return
        try:
            records = self._episode_store.load_all(self.cat_uid)
            for ep in records:
                if ep.get("id") not in {e.get("id") for e in self.episodes}:
                    self.episodes.append(ep)
        except Exception:
            pass  # best-effort load; never crash on IO error

    async def _flush_to_store(self) -> None:
        """Ensure all in-memory episodes are persisted.

        Called by the cat's ``on_shutdown`` hook registered during assembly.
        Since :meth:`add_episode` already writes-through to the store,
        this is a no-op for the default JSONL store.  Custom stores that
        buffer writes can override.
        """
        pass  # write-through: add_episode already persists immediately

    def add_episode(self, episode: dict[str, Any]) -> str:
        """Add episode, persist to store if available."""
        eid = NoopHippocampus.add_episode(self, episode)
        if self._episode_store is not None:
            try:
                store_cat_uid = self.cat_uid or episode.get(
                    "cat_uid", "unknown")
                self._episode_store.append(store_cat_uid, dict(episode))
            except Exception:
                pass  # persistence is best-effort; never crash on IO error
        return eid

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        """Get episode, in-memory lookup."""
        if self._episode_store is not None:
            try:
                ep = NoopHippocampus.get_episode(self, episode_id)
                if ep is not None:
                    return ep
            except Exception:
                pass
        return NoopHippocampus.get_episode(self, episode_id)

    def get_episodes(self, ids: list[str]) -> list[dict[str, Any]]:
        """Batch get episodes, in-memory only."""
        return NoopHippocampus.get_episodes(self, ids)
