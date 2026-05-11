# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default hippocampus stub — in-memory graph store implementing HippocampusProtocol."""

from __future__ import annotations

import logging
import re
import time as _time
from collections import deque
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable
from meowcat.tree import TreeNode

logger = logging.getLogger(__name__)


class DefaultHippocampus(Pluggable):
    """Default hippocampus: in-memory graph store with auto-indexing and optional persistence.

    Merged into DefaultHippocampus (v2.0).
    Implements full HippocampusProtocol methods.
    Mode B — remember / recall merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "remember": {
            "in": "user_msg: str, ai_reply: str, cat_uid: str, model: str",
            "out": "Any",
        },
        "recall": {
            "in": "query: str, limit: int",
            "out": "list[dict]",
        },
    }

    name: str = "noop_hippocampus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    _entities: dict[str, dict[str, Any]] | None = None
    _episodes: list[dict[str, Any]] | None = None

    # Instance-only: set by factory lifecycle hook before on_start
    cat_uid: str = ""

    def __init__(self, episode_store: Any | None = None) -> None:
        Pluggable.__init__(self)
        self._colony_memory: Any = None  # v1.1.21: SharedMemoryPool for scope=colony
        self._keyword_index: dict[str, set[str]] = {}
        self._episode_store = episode_store
        # v2.0: KnowledgeTree storage
        self._trees: dict[str, dict[str, Any]] = {}

    # -- Lazy-init properties (subclasses that super().__init__()
    #    avoid creating unused InMemoryGraphStore) -------------------

    @property
    def entities(self) -> dict[str, dict[str, Any]]:
        if self._entities is None:
            self._entities = {}
        return self._entities

    @entities.setter
    def entities(self, value: dict[str, dict[str, Any]]) -> None:
        self._entities = value

    @property
    def episodes(self) -> list[dict[str, Any]]:
        if self._episodes is None:
            self._episodes = []
        return self._episodes

    @episodes.setter
    def episodes(self, value: list[dict[str, Any]]) -> None:
        self._episodes = value

    # -- v1.1.21 Colony memory injection -----------------------------

    def set_colony_memory(self, memory_pool: Any) -> None:
        """Inject colony shared memory pool for cross-cat search.

        Called by Colony during cat creation.  When set, ``locate(scope='colony')``
        searches the colony's ``SharedMemoryPool`` instead of returning empty.
        """
        self._colony_memory = memory_pool

    # -- Memory storage -----------------------------------------------

    async def remember(
        self,
        user_msg: str,
        ai_reply: str,
        cat_uid: str,
        model: str,
    ) -> Any:
        result: dict[str, Any] = {"user_msg": user_msg, "ai_reply": ai_reply}
        async for _name, r in self._run_plugs(
            "remember",
            user_msg,
            ai_reply,
            cat_uid,
            model,
        ):
            if isinstance(r, dict):
                result.update(r)
        kws = _extract_keywords(f"{user_msg} {ai_reply}", top_k=10)
        for kw in kws:
            self._keyword_index.setdefault(kw, set()).add(user_msg[:80])
        return result

    def add_episode(self, episode: dict[str, Any]) -> str:
        """Add an episode, auto-assign id if missing, return episode_id."""
        eid = episode.get("id") or f"ep_{len(self.episodes)}"
        if "id" not in episode:
            episode["id"] = eid
        self.episodes.append(episode)
        if self._episode_store is not None:
            try:
                store_cat_uid = self.cat_uid or episode.get(
                    "cat_uid", "unknown")
                self._episode_store.append(store_cat_uid, dict(episode))
            except Exception:
                logger.warning(
                    "Failed to persist episode %s to store", eid, exc_info=True
                )
        return eid

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        """Get a single episode by id."""
        for ep in self.episodes:
            if ep.get("id") == episode_id:
                return ep
        return None

    def get_episodes(self, ids: list[str]) -> list[dict[str, Any]]:
        """Batch get episodes by ids."""
        id_set = set(ids)
        return [ep for ep in self.episodes if ep.get("id") in id_set]

    def add_entity(self, entity: dict[str, Any]) -> None:
        eid = entity.get("id", entity.get(
            "entity_id", str(len(self.entities))))
        self.entities[eid] = entity

    # -- Memory retrieval --------------------------------------------

    def fts_search(
        self,
        cat_uid: str,
        keywords: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Full-text search memory (simple keyword matching)."""
        results: list[dict[str, Any]] = []
        kws = keywords.lower().split()
        for ep in self.episodes:
            text = (ep.get("user_msg", "") + " " +
                    ep.get("ai_reply", "")).lower()
            if any(kw in text for kw in kws):
                results.append(ep)
                if len(results) >= limit:
                    break
        return results

    async def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Semantic recall memory (simple impl: delegates to fts_search)."""
        base = self.fts_search("", query, limit)
        async for _name, r in self._run_plugs("recall", query, limit):
            if isinstance(r, list):
                return r
        return base

    # -- Search boundary (v1.1.8) + cross-cat (v1.1.21) ------------

    def locate(self, query: str, scope: str = "self") -> list[dict[str, Any]]:
        """Search with scope boundary enforcement.

        Args:
            query: Search query string.
            scope: ``"self"`` to search own hippocampus,
                   ``"colony"`` to search colony shared storage only.

        Returns:
            List of matching entries.

        Raises:
            ValueError: Invalid scope value.
        """
        if scope not in ("self", "colony"):
            raise ValueError(
                f"Invalid search scope '{scope}': must be 'self' or 'colony'")
        if scope == "self":
            return self.fts_search("", query)
        # scope == "colony": cross-cat search via colony SharedMemoryPool (v1.1.21)
        if self._colony_memory is not None:
            return self._colony_memory.keyword_search(query)
        return []

    # -- v1.1.21 Delegation snapshot ---------------------------------

    def snapshot(self, *topics: str, scope: str = "colony") -> dict[str, Any]:
        """Extract a memory context slice for delegation.

        Gathers relevant memories from own hippocampus and (optionally)
        the colony shared memory pool, packaged as a portable snapshot
        that can be injected into a kitten via ``memory_snapshot``.

        Args:
            *topics: Topic strings to gather context for.
            scope: ``"self"`` for own hippocampus only,
                   ``"colony"`` to include colony shared memories.

        Returns:
            ``{"topics": [...], "context": [...], "created_at": ...}``
        """
        import time as _time

        context: list[dict[str, Any]] = []
        for topic in topics:
            # own hippocampus memories
            for ep in self.fts_search("", topic, limit=5):
                context.append(
                    {
                        "type": "self",
                        "source": "episode",
                        "topic": topic,
                        "content": ep,
                    }
                )
            # colony shared memories
            if scope == "colony" and self._colony_memory is not None:
                for cm in self._colony_memory.keyword_search(topic, k=5):
                    context.append(
                        {
                            "type": "colony",
                            "source": "shared_memory",
                            "topic": topic,
                            "content": cm,
                        }
                    )
        return {
            "topics": list(topics),
            "context": context,
            "created_at": _time.time(),
        }

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self.entities.get(entity_id)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        for e in self.entities.values():
            if e.get("name") == name:
                return e
        return None

    def get_all(self) -> list[dict[str, Any]]:
        return list(self.entities.values())

    def get_related(self, entity_id: str) -> list[dict[str, Any]]:
        entity = self.entities.get(entity_id)
        if not entity:
            return []
        related: list[dict[str, Any]] = []
        for conn in entity.get("connections", []):
            target_id = conn.get("to", conn.get("target"))
            if target_id and target_id in self.entities:
                related.append(self.entities[target_id])
        return related

    # -- Connection operations ---------------------------------------

    def connect(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        strength: float = 1.0,
    ) -> None:
        if from_id in self.entities:
            self.entities[from_id].setdefault("connections", []).append(
                {
                    "to": to_id,
                    "relation": relation,
                    "strength": strength,
                }
            )

    def weaken_connections(self, entity_id: str, factor: float = 0.5) -> None:
        entity = self.entities.get(entity_id)
        if not entity:
            return
        for conn in entity.get("connections", []):
            conn["strength"] = conn.get("strength", 1.0) * factor

    def cleanup_orphan_connections(self, days_threshold: int = 7) -> int:
        now = _time.time()
        threshold_sec = days_threshold * 86400
        removed = 0
        for _eid, entity in list(self.entities.items()):
            connections = entity.get("connections", [])
            kept = []
            for conn in connections:
                target_id = conn.get("to", conn.get("target"))
                if target_id and target_id in self.entities:
                    last = self.entities[target_id].get("_last_accessed", 0)
                    if now - last < threshold_sec:
                        kept.append(conn)
                    else:
                        removed += 1
                else:
                    removed += 1
            entity["connections"] = kept
        return removed

    # -- Maintenance ------------------------------------------------

    def decay(self, now: Any | None = None) -> int:
        if now is None:
            now = _time.time()
        decayed = 0
        for entity in self.entities.values():
            if entity.get("importance", 0.0) > 0:
                entity["importance"] = max(0, entity["importance"] - 0.01)
                decayed += 1
        return decayed

    def stats(self, session_id: str | None = None) -> dict[str, Any]:
        return {
            "entities": len(self.entities),
            "episodes": len(self.episodes),
            "connections": sum(len(e.get("connections", [])) for e in self.entities.values()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"entities": dict(self.entities), "episodes": list(self.episodes)}

    def from_dict(self, d: dict[str, Any]) -> None:
        self.entities = d.get("entities", {})
        self.episodes = d.get("episodes", [])

    # -- Lifecycle ---------------------------------------------------

    async def _load_from_store(self) -> None:
        if self._episode_store is None or not self.cat_uid:
            return
        try:
            records = self._episode_store.load_all(self.cat_uid)
            for ep in records:
                if ep.get("id") not in {e.get("id") for e in self.episodes}:
                    self.episodes.append(ep)
        except Exception:
            logger.warning(
                "Failed to load episodes from store for cat_uid=%s",
                self.cat_uid,
                exc_info=True,
            )

    async def _flush_to_store(self) -> None:
        pass  # write-through: add_episode already persists immediately

    # -- v0.5.26 wrapper methods ------------------------------------

    def record_access(self, entity_id: str, delta: int = 1) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["_last_accessed"] = _time.time()
            self.entities[entity_id].setdefault("access_count", 0)
            self.entities[entity_id]["access_count"] += delta

    def set_dormant(self, entity_id: str, dormant: bool) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["dormant"] = dormant

    def append_content(
        self,
        entity_id: str,
        text: str,
        max_total: int | None = None,
    ) -> None:
        if entity_id in self.entities:
            existing = self.entities[entity_id].get("content", "")
            new_content = existing + text
            if max_total is not None and len(new_content) > max_total:
                new_content = new_content[-max_total:]
            self.entities[entity_id]["content"] = new_content

    def update_importance(self, entity_id: str, importance: float) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["importance"] = max(
                0.0, min(1.0, importance))

    def set_last_seen(self, entity_id: str, ts: str) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["last_seen"] = ts

    # -- v1.0.15 long-workflow query --------------------------------

    def list_active_workflows(self, cat_uid: str) -> list[dict[str, Any]]:
        """List all incomplete workflow entities.

        Filters entities with type="workflow" and status active/awaiting_user.
        """
        results: list[dict[str, Any]] = []
        for eid, entity in self.entities.items():
            if entity.get("type") != "workflow":
                continue
            if entity.get("status") not in ("active", "awaiting_user"):
                continue
            if entity.get("cat_uid") != cat_uid:
                continue
            results.append({"entity_id": eid, **entity})
        return results

    # -- v2.0 KnowledgeTree methods ----------------------------------

    def build_tree(self, entity_id: str, root: TreeNode) -> int:
        nodes: dict[str, TreeNode] = {}
        queue: deque[TreeNode] = deque([root])
        while queue:
            node = queue.popleft()
            nodes[node.id] = node
        self._trees[entity_id] = {"root": root, "nodes": nodes}
        return len(nodes)

    def get_tree(self, entity_id: str) -> TreeNode | None:
        tree = self._trees.get(entity_id)
        return tree["root"] if tree else None

    def delete_tree(self, entity_id: str) -> None:
        self._trees.pop(entity_id, None)

    def search_tree(self, entity_id: str, keyword: str, limit: int = 5) -> list[TreeNode]:
        tree = self._trees.get(entity_id)
        if not tree:
            return []
        kw = keyword.lower()
        results: list[tuple[int, TreeNode]] = []
        for node in tree["nodes"].values():
            score = 0
            if kw in node.name.lower():
                score = 3
            if kw in node.path.lower():
                score = max(score, 2)
            if node.summary and kw in node.summary.lower():
                score = max(score, 1)
            if score > 0:
                results.append((score, node))
        results.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in results[:limit]]

    def query_subtree(self, entity_id: str, node_id: str, max_depth: int = 2) -> list[TreeNode]:
        tree = self._trees.get(entity_id)
        if not tree:
            return []
        target = tree["nodes"].get(node_id)
        if target is None:
            return []
        children_map: dict[str, list[TreeNode]] = {}
        for n in tree["nodes"].values():
            if n.parent_id:
                children_map.setdefault(n.parent_id, []).append(n)
        results: list[TreeNode] = [target]
        frontier: deque[TreeNode] = deque([target])
        depth = 0
        while frontier and depth < max_depth:
            depth += 1
            for _ in range(len(frontier)):
                parent = frontier.popleft()
                for child in children_map.get(parent.id, []):
                    results.append(child)
                    frontier.append(child)
        return results

    def check_stale(self, entity_id: str) -> list[str]:
        tree = self._trees.get(entity_id)
        if not tree:
            return []
        stale: list[str] = []
        for nid, node in tree["nodes"].items():
            if node.entity_id not in self.entities:
                stale.append(nid)
        return stale


def _extract_keywords(text, top_k=5, stop_words=None):
    if stop_words is None:
        return []
    words = re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())
    filtered = [w for w in words if w not in stop_words and len(w) > 1]
    seen = set()
    result = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            result.append(w)
            if len(result) >= top_k:
                break
    return result
