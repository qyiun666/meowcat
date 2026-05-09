# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat default brain organ stubs — no-op implementations satisfying Protocols.

Each Noop* class extends Pluggable (v1.0.7), providing mount_plug / unmount_plug /
_run_plugs plugin capability. HOOKS class variable declares mountable hooks and their suggested signatures.

Three execution modes:
- A First-hit override: first non-default value is returned directly
- B Merge enhancement: all plugin results are merged into the default value
- C Full replacement: first plugin completely replaces default behavior
"""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.anatomy import ImplementationStyle
from meowcat.pluggable import Pluggable


class NoopAmygdala(Pluggable):
    """Default amygdala: never rejects, zero security risk.

    Mode A — assess_safety / assess_tool_risk first-hit override.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
        "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
    }

    name: str = "noop_amygdala"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def is_rejection(self, msg: str) -> bool:
        return False

    def classify_rejection(self, msg: str) -> str:
        return "none"

    def parse_correction(self, msg: str) -> tuple[str, str] | None:
        return None

    async def handle_rejection(
        self,
        msg: str,
        last_candidates: list[Any],
        hippocampus: Any,
    ) -> str:
        return msg

    async def handle_correction(
        self,
        msg: str,
        hippocampus: Any,
    ) -> tuple[str, str] | None:
        return None

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict) and not r.get("safe", True):
                return r
        return {"safe": True, "risk": "none"}

    async def assess_tool_risk(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_tool_risk", tool_name, params):
            if isinstance(r, dict):
                return r
        return {"risk": "low", "reason": "noop"}


class NoopFrontal(Pluggable):
    """Default frontal cortex: does not detect focus shifts, does not save focus.

    Mode A — is_continue / detect_shift first-hit override.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "is_continue": {"in": "msg: str", "out": "bool"},
        "detect_shift": {"in": "msg: str", "out": "bool"},
    }

    name: str = "noop_frontal"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def is_continue(self, msg: str) -> bool:
        async for _name, r in self._run_plugs("is_continue", msg):
            if isinstance(r, bool):
                return r
        return False

    async def detect_shift(self, msg: str) -> bool:
        async for _name, r in self._run_plugs("detect_shift", msg):
            if isinstance(r, bool):
                return r
        return False

    def archive_focus(self) -> None:
        pass

    def update_focus(self, result: Any) -> None:
        pass

    def save(self, path: Any | None = None) -> None:
        pass

    def load(self, path: Any | None = None) -> None:
        pass


class NoopHypothalamus(Pluggable):
    """Default hypothalamus: does not perform maintenance, does not wake entities.

    Mode B — run_maintenance merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "run_maintenance": {"in": "country_code: str|None", "out": "Any"},
    }

    name: str = "noop_hypothalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        result: dict[str, Any] = {
            "decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}
        async for _name, r in self._run_plugs("run_maintenance", country_code):
            if isinstance(r, dict):
                result.update(r)
        return result

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        return {"decayed": 0}

    def compress_long_history(self) -> dict[str, Any]:
        return {"compressed": 0}


class NoopCortex(Pluggable):
    """Default cortex: does not ingest worldviews, does not record weaknesses.

    Mode B — synthesize merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "synthesize": {"in": "max_tokens: int", "out": "str"},
    }

    name: str = "noop_cortex"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        pass

    def record_weakness(self, kind: str, detail: str) -> None:
        pass

    def weaknesses(self) -> list[dict[str, Any]]:
        return []

    async def synthesize(self, max_tokens: int = 400) -> str:
        result = ""
        async for _name, r in self._run_plugs("synthesize", max_tokens):
            if isinstance(r, str):
                result += r
        return result


class NoopBrainstem(Pluggable):
    """Default brainstem: does not build system prompt, does not cancel current task.

    v1.3.6: ``build_system_prompt`` signature updated to match
    :class:`BrainStemProtocol` — accepts ``organ``, ``route``, and
    optional ``cat_self_snapshot``.

    Mode B — build_system_prompt merge enhancement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "build_system_prompt": {"in": "organ: str, route: str, snapshot: Any|None", "out": "str"},
        "compress_context": {"in": "messages: list[dict], max_tokens: int", "out": "list[dict]"},
    }

    name: str = "noop_brainstem"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    inject_cat_self: bool = True

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def build_system_prompt(
        self,
        organ: str,
        route: str,
        cat_self_snapshot: Any | None = None,
    ) -> str:
        parts: list[str] = []
        async for _name, r in self._run_plugs(
            "build_system_prompt", organ, route, cat_self_snapshot
        ):
            if isinstance(r, str) and r:
                parts.append(r)
        return "\n".join(parts) if parts else ""

    async def compress_context(
        self,
        messages: list[dict],
        max_tokens: int = 4000,
    ) -> list[dict]:
        """Compress conversation context to fit token budget.

        Framework default: keep first message + last N messages
        (simple truncation). App layer can override via Pluggable
        ``compress_context`` hook for LLM-based summarization.

        Args:
            messages: List of message dicts (role, content).
            max_tokens: Target token budget (approximate).

        Returns:
            Compressed message list.
        """
        async for _name, r in self._run_plugs(
            "compress_context",
            messages,
            max_tokens,
        ):
            if isinstance(r, list):
                return r
        # Default: keep first + estimate token count, trim from end
        if not messages:
            return messages
        # Rough estimate: 1 token ≈ 4 chars
        budget_chars = max_tokens * 4
        result: list[dict] = [dict(messages[0])]
        used = len(str(messages[0]))
        for msg in reversed(messages[1:]):
            chars = len(str(msg))
            if used + chars <= budget_chars:
                result.insert(1, dict(msg))
                used += chars
            else:
                break
        return result

    def cancel_current(self) -> bool:
        return False


class NoopCerebrum(Pluggable):
    """Default cerebrum: no deep reasoning, no stream generation.

    Mode C — generate / stream_generate full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "str",
        },
        "stream_generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "AsyncIterator[str]",
        },
    }

    name: str = "noop_cerebrum"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate",
            prompt,
            system_prompt,
            temperature,
            max_tokens,
        ):
            if isinstance(r, str):
                return r
        return ""

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate",
            prompt,
            system_prompt,
            temperature,
            max_tokens,
        ):
            return r
        # empty async generator fallback

        async def _empty():
            if False:
                yield ""

        return _empty()

    def reload_config(self) -> None:
        pass


class NoopCerebellum(Pluggable):
    """Default cerebellum: no fast reasoning, no stream generation.

    Mode C — generate / stream_generate full replacement.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "str",
        },
        "stream_generate": {
            "in": "prompt: str, system_prompt: str|None, temperature: float, max_tokens: int|None",
            "out": "AsyncIterator[str]",
        },
    }

    name: str = "noop_cerebellum"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate",
            prompt,
            system_prompt,
            temperature,
            max_tokens,
        ):
            if isinstance(r, str):
                return r
        return ""

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate",
            prompt,
            system_prompt,
            temperature,
            max_tokens,
        ):
            return r

        async def _empty():
            if False:
                yield ""

        return _empty()

    def reload_config(self) -> None:
        pass


class NoopThalamus(Pluggable):
    """Default thalamus: simple routing, no memory retrieval.

    Mode B — locate merge enhancement; hear receives raw sensory input.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "hear": {"in": "raw_input: str | bytes", "out": "dict[str, Any]"},
        "locate": {"in": "msg: str, session_id: str", "out": "LocateResultShape"},
    }

    name: str = "noop_thalamus"
    impl_style: ImplementationStyle = ImplementationStyle.ALGORITHM

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        """Receive raw sensory input, run plugs for preprocessing."""
        result: dict[str, Any] = {"raw_input": raw_input, "route": "chat"}
        async for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def locate(self, msg: str, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": "chat", "entities": [], "snippets": []}
        async for _name, r in self._run_plugs("locate", msg, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result

    def decide_route(self, **kwargs: Any) -> dict[str, Any]:
        return {"route": "chat"}


class NoopHippocampus(Pluggable):
    """Default hippocampus: pure in-memory graph store, lost on process restart.

    Wraps InMemoryGraphStore, implements full HippocampusProtocol methods.
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

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._colony_memory: Any = None  # v1.1.21: SharedMemoryPool for scope=colony

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
        return result

    def add_episode(self, episode: dict[str, Any]) -> str:
        """Add an episode, auto-assign id if missing, return episode_id."""
        eid = episode.get("id") or f"ep_{len(self.episodes)}"
        if "id" not in episode:
            episode["id"] = eid
        self.episodes.append(episode)
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
