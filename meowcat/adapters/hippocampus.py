# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat HippocampusAgent adapter.

Extracted from ``adapters/brain.py`` (v1.3.9) to keep each file ≤500 lines.
"""

from __future__ import annotations

from typing import Any

from meowcat.adapters.base import AgentOrgan
from meowcat.tree import TreeNode


class HippocampusAgent(AgentOrgan):
    """Adapter for HippocampusProtocol — delegates memory ops to an external agent/skill.

    The backing agent should implement at minimum ``locate``, ``remember``, and
    ``fts_search``.  Other methods default to no-op stubs if absent on the agent.
    """

    async def locate(self, query: str, scope: str = "self") -> list[dict[str, Any]]:
        return await self._delegate("locate", query=query, scope=scope)

    async def remember(
        self,
        user_msg: str,
        ai_reply: str,
        cat_uid: str,
        model: str,
    ) -> Any:
        return await self._delegate(
            "remember",
            user_msg=user_msg,
            ai_reply=ai_reply,
            cat_uid=cat_uid,
            model=model,
        )

    def fts_search(
        self,
        cat_uid: str,
        keywords: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        fn = getattr(self._agent, "fts_search", None)
        if fn is None:
            return []
        result = fn(cat_uid=cat_uid, keywords=keywords, limit=limit)
        return result if isinstance(result, list) else []

    # -- Optional delegation: only call agent if method exists ---------

    def add_episode(self, episode: Any) -> str:
        fn = getattr(self._agent, "add_episode", None)
        if fn:
            result = fn(episode=episode)
            return result if isinstance(result, str) else ""
        return ""

    def get_episode(self, episode_id: str) -> Any | None:
        fn = getattr(self._agent, "get_episode", None)
        if fn:
            return fn(episode_id=episode_id)
        return None

    def get_episodes(self, ids: list[str]) -> list[Any]:
        fn = getattr(self._agent, "get_episodes", None)
        if fn:
            result = fn(ids=ids)
            return result if isinstance(result, list) else []
        return []

    def add_entity(self, entity: Any) -> None:
        fn = getattr(self._agent, "add_entity", None)
        if fn:
            fn(entity=entity)

    def decay(self, now: Any | None = None) -> int:
        fn = getattr(self._agent, "decay", None)
        if fn:
            result = fn(now=now)
            return result if isinstance(result, int) else 0
        return 0

    def stats(self, session_id: str | None = None) -> dict[str, Any]:
        fn = getattr(self._agent, "stats", None)
        if fn:
            result = fn(session_id=session_id)
            return result if isinstance(result, dict) else {}
        return {}

    def to_dict(self) -> dict[str, Any]:
        fn = getattr(self._agent, "to_dict", None)
        if fn:
            result = fn()
            return result if isinstance(result, dict) else {}
        return {}

    def from_dict(self, d: dict[str, Any]) -> None:
        fn = getattr(self._agent, "from_dict", None)
        if fn:
            fn(d=d)

    def get_entity(self, entity_id: str) -> Any | None:
        fn = getattr(self._agent, "get_entity", None)
        if fn:
            return fn(entity_id=entity_id)
        return None

    def get_by_name(self, name: str) -> Any | None:
        fn = getattr(self._agent, "get_by_name", None)
        if fn:
            return fn(name=name)
        return None

    def get_all(self) -> list[Any]:
        fn = getattr(self._agent, "get_all", None)
        if fn:
            result = fn()
            return result if isinstance(result, list) else []
        return []

    def get_related(self, entity_id: str) -> list[Any]:
        fn = getattr(self._agent, "get_related", None)
        if fn:
            result = fn(entity_id=entity_id)
            return result if isinstance(result, list) else []
        return []

    def connect(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        strength: float = 1.0,
    ) -> None:
        fn = getattr(self._agent, "connect", None)
        if fn:
            fn(from_id=from_id, to_id=to_id, relation=relation, strength=strength)

    def weaken_connections(self, entity_id: str, factor: float = 0.5) -> None:
        fn = getattr(self._agent, "weaken_connections", None)
        if fn:
            fn(entity_id=entity_id, factor=factor)

    def cleanup_orphan_connections(self, days_threshold: int = 7) -> int:
        fn = getattr(self._agent, "cleanup_orphan_connections", None)
        if fn:
            result = fn(days_threshold=days_threshold)
            return result if isinstance(result, int) else 0
        return 0

    # -- Wrapper methods (v0.5.26) -----------------------------------

    def record_access(self, entity_id: str, delta: int = 1) -> None:
        fn = getattr(self._agent, "record_access", None)
        if fn:
            fn(entity_id=entity_id, delta=delta)

    def set_dormant(self, entity_id: str, dormant: bool) -> None:
        fn = getattr(self._agent, "set_dormant", None)
        if fn:
            fn(entity_id=entity_id, dormant=dormant)

    def append_content(
        self,
        entity_id: str,
        text: str,
        max_total: int | None = None,
    ) -> None:
        fn = getattr(self._agent, "append_content", None)
        if fn:
            fn(entity_id=entity_id, text=text, max_total=max_total)

    def update_importance(self, entity_id: str, importance: float) -> None:
        fn = getattr(self._agent, "update_importance", None)
        if fn:
            fn(entity_id=entity_id, importance=importance)

    def set_last_seen(self, entity_id: str, ts: str) -> None:
        fn = getattr(self._agent, "set_last_seen", None)
        if fn:
            fn(entity_id=entity_id, ts=ts)

    def list_active_workflows(self, cat_uid: str) -> list[dict[str, Any]]:
        fn = getattr(self._agent, "list_active_workflows", None)
        if fn:
            result = fn(cat_uid=cat_uid)
            return result if isinstance(result, list) else []
        return []

    def set_colony_memory(self, memory_pool: Any) -> None:
        fn = getattr(self._agent, "set_colony_memory", None)
        if fn:
            fn(memory_pool=memory_pool)

    def snapshot(self, *topics: str, scope: str = "colony") -> dict[str, Any]:
        fn = getattr(self._agent, "snapshot", None)
        if fn:
            result = fn(*topics, scope=scope)
            return result if isinstance(result, dict) else {}
        return {}

    # -- v2.0 KnowledgeTree delegation ---------------------------------

    def get_tree(self, entity_id: str) -> TreeNode | None:
        fn = getattr(self._agent, "get_tree", None)
        if fn:
            result = fn(entity_id=entity_id)
            return result if isinstance(result, TreeNode) else None
        return None

    def build_tree(self, entity_id: str, root: TreeNode) -> int:
        fn = getattr(self._agent, "build_tree", None)
        if fn:
            result = fn(entity_id=entity_id, root=root)
            return result if isinstance(result, int) else 0
        return 0

    def delete_tree(self, entity_id: str) -> None:
        fn = getattr(self._agent, "delete_tree", None)
        if fn:
            fn(entity_id=entity_id)

    def search_tree(
        self,
        entity_id: str,
        keyword: str,
        limit: int = 5,
    ) -> list[TreeNode]:
        fn = getattr(self._agent, "search_tree", None)
        if fn:
            result = fn(entity_id=entity_id, keyword=keyword, limit=limit)
            return result if isinstance(result, list) else []
        return []

    def query_subtree(
        self,
        entity_id: str,
        node_id: str,
        max_depth: int = 2,
    ) -> list[TreeNode]:
        fn = getattr(self._agent, "query_subtree", None)
        if fn:
            result = fn(entity_id=entity_id,
                        node_id=node_id, max_depth=max_depth)
            return result if isinstance(result, list) else []
        return []

    def check_stale(self, entity_id: str) -> list[str]:
        fn = getattr(self._agent, "check_stale", None)
        if fn:
            result = fn(entity_id=entity_id)
            return result if isinstance(result, list) else []
        return []


__all__ = ["HippocampusAgent"]
