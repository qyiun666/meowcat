"""meowcat brain-area organ adapters.

v1.2.14: One adapter per brain Protocol — CerebrumAgent, CerebellumAgent,
ThalamusAgent, HippocampusAgent, AmygdalaAgent, BrainstemAgent,
FrontalAgent, HypothalamusAgent, CortexAgent.

Each adapter delegates every Protocol method to its backing agent/skill
via ``self._delegate("method", **kw)``.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from typing import Any

from meowcat.adapters.base import AgentOrgan


class CerebrumAgent(AgentOrgan):
    """Adapter for Cerebrum / LLMBrainProtocol — delegates reasoning to an external agent.

    Mode C — hooks can fully replace generate / stream_generate.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "generate": {"in": "prompt, system_prompt, temperature, max_tokens", "out": "str"},
        "stream_generate": {"in": "prompt, system_prompt, temperature, max_tokens", "out": "AsyncIterator[str]"},
    }

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate", prompt, system_prompt, temperature, max_tokens,
        ):
            if isinstance(r, str):
                return r
        return await self._delegate(
            "generate", prompt=prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate", prompt, system_prompt, temperature, max_tokens,
        ):
            return r
        return await self._delegate(
            "stream_generate", prompt=prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )

    def reload_config(self) -> None:
        try:
            self._agent.reload_config()
        except (AttributeError, Exception):
            pass


class CerebellumAgent(AgentOrgan):
    """Adapter for Cerebellum / LLMBrainProtocol — delegates fast reasoning to an external agent.

    Mode C — hooks can fully replace generate / stream_generate.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "generate": {"in": "prompt, system_prompt, temperature, max_tokens", "out": "str"},
        "stream_generate": {"in": "prompt, system_prompt, temperature, max_tokens", "out": "AsyncIterator[str]"},
    }

    async def generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> str:
        async for _name, r in self._run_plugs(
            "generate", prompt, system_prompt, temperature, max_tokens,
        ):
            if isinstance(r, str):
                return r
        return await self._delegate(
            "generate", prompt=prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None,
        temperature: float = 0.7, max_tokens: int | None = None,
    ) -> Any:
        async for _name, r in self._run_plugs(
            "stream_generate", prompt, system_prompt, temperature, max_tokens,
        ):
            return r
        return await self._delegate(
            "stream_generate", prompt=prompt, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )

    def reload_config(self) -> None:
        try:
            self._agent.reload_config()
        except (AttributeError, Exception):
            pass


class ThalamusAgent(AgentOrgan):
    """Adapter for ThalamusProtocol — delegates routing decisions to an external agent."""

    async def locate(self, msg: str, session_id: str) -> Any:
        return await self._delegate("locate", msg=msg, session_id=session_id)

    def decide_route(self, **kwargs: Any) -> dict[str, Any]:
        fn = getattr(self._agent, "decide_route", None)
        if fn is None:
            return {"route": "chat"}
        result = fn(**kwargs)
        return result if isinstance(result, dict) else {"route": "chat"}


class HippocampusAgent(AgentOrgan):
    """Adapter for HippocampusProtocol — delegates memory ops to an external agent/skill.

    The backing agent should implement at minimum ``locate``, ``remember``, and
    ``fts_search``.  Other methods default to no-op stubs if absent on the agent.
    """

    async def locate(self, query: str, scope: str = "self") -> list[dict[str, Any]]:
        return await self._delegate("locate", query=query, scope=scope)

    async def remember(
        self, user_msg: str, ai_reply: str, cat_uid: str, model: str,
    ) -> Any:
        return await self._delegate(
            "remember", user_msg=user_msg, ai_reply=ai_reply,
            cat_uid=cat_uid, model=model,
        )

    def fts_search(
        self, cat_uid: str, keywords: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        fn = getattr(self._agent, "fts_search", None)
        if fn is None:
            return []
        result = fn(cat_uid=cat_uid, keywords=keywords, limit=limit)
        return result if isinstance(result, list) else []

    # -- Optional delegation: only call agent if method exists ---------

    def add_episode(self, episode: Any) -> None:
        fn = getattr(self._agent, "add_episode", None)
        if fn:
            fn(episode=episode)

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
        self, from_id: str, to_id: str, relation: str, strength: float = 1.0,
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
        self, entity_id: str, text: str, max_total: int | None = None,
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


class AmygdalaAgent(AgentOrgan):
    """Adapter for AmygdalaProtocol — delegates safety checks to an external agent.

    Mode A — assess_safety / assess_tool_risk first-hit override from hooks.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
        "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
    }

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict):
                return r
        return await self._delegate("assess_safety", user_input=user_input)

    async def assess_tool_risk(
        self, tool_name: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        async for _name, r in self._run_plugs("assess_tool_risk", tool_name, params):
            if isinstance(r, dict):
                return r
        fn = getattr(self._agent, "assess_tool_risk", None)
        if fn is None:
            return {"risk": "low", "reason": "delegated_noop"}
        result = fn(tool_name=tool_name, params=params)
        return result if isinstance(result, dict) else {"risk": "low"}

    def is_rejection(self, msg: str) -> bool:
        fn = getattr(self._agent, "is_rejection", None)
        if fn:
            result = fn(msg=msg)
            return bool(result)
        return False

    def classify_rejection(self, msg: str) -> str:
        fn = getattr(self._agent, "classify_rejection", None)
        if fn:
            result = fn(msg=msg)
            return result if isinstance(result, str) else "none"
        return "none"

    def parse_correction(self, msg: str) -> tuple[str, str] | None:
        fn = getattr(self._agent, "parse_correction", None)
        if fn:
            result = fn(msg=msg)
            if isinstance(result, tuple) and len(result) == 2:
                return result
        return None

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any,
    ) -> str:
        fn = getattr(self._agent, "handle_rejection", None)
        if fn is None:
            return msg
        return await self._delegate(
            "handle_rejection", msg=msg,
            last_candidates=last_candidates, hippocampus=hippocampus,
        )

    async def handle_correction(
        self, msg: str, hippocampus: Any,
    ) -> tuple[str, str] | None:
        fn = getattr(self._agent, "handle_correction", None)
        if fn is None:
            return None
        result = await self._delegate(
            "handle_correction", msg=msg, hippocampus=hippocampus,
        )
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return None


class BrainstemAgent(AgentOrgan):
    """Adapter for BrainStemProtocol — delegates prompt building to an external agent."""

    async def build_system_prompt(self, route: str) -> str:
        return await self._delegate("build_system_prompt", route=route)

    def cancel_current(self) -> bool:
        fn = getattr(self._agent, "cancel_current", None)
        if fn:
            result = fn()
            return bool(result)
        return False


class FrontalAgent(AgentOrgan):
    """Adapter for FrontalCortexProtocol — delegates focus/working-memory to an external agent."""

    def detect_shift(self, msg: str) -> bool:
        fn = getattr(self._agent, "detect_shift", None)
        if fn:
            return bool(fn(msg=msg))
        return False

    def is_continue(self, msg: str) -> bool:
        fn = getattr(self._agent, "is_continue", None)
        if fn:
            return bool(fn(msg=msg))
        return False

    def archive_focus(self) -> None:
        fn = getattr(self._agent, "archive_focus", None)
        if fn:
            fn()

    def update_focus(self, result: Any) -> None:
        fn = getattr(self._agent, "update_focus", None)
        if fn:
            fn(result=result)

    def save(self, path: Any | None = None) -> None:
        fn = getattr(self._agent, "save", None)
        if fn:
            fn(path=path)

    def load(self, path: Any | None = None) -> None:
        fn = getattr(self._agent, "load", None)
        if fn:
            fn(path=path)


class HypothalamusAgent(AgentOrgan):
    """Adapter for HypothalamusProtocol — delegates maintenance to an external agent."""

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        return await self._delegate("run_maintenance", country_code=country_code)

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        fn = getattr(self._agent, "decay_memories", None)
        if fn:
            result = fn(now=now)
            return result if isinstance(result, dict) else {}
        return {"decayed": 0}

    def compress_long_history(self) -> dict[str, Any]:
        fn = getattr(self._agent, "compress_long_history", None)
        if fn:
            result = fn()
            return result if isinstance(result, dict) else {}
        return {"compressed": 0}


class CortexAgent(AgentOrgan):
    """Adapter for CortexProtocol — delegates worldview ingestion to an external agent."""

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        fn = getattr(self._agent, "ingest", None)
        if fn:
            fn(source=source, layer=layer, key=key, value=value)

    def record_weakness(self, kind: str, detail: str) -> None:
        fn = getattr(self._agent, "record_weakness", None)
        if fn:
            fn(kind=kind, detail=detail)

    def weaknesses(self) -> list[dict[str, Any]]:
        fn = getattr(self._agent, "weaknesses", None)
        if fn:
            result = fn()
            return result if isinstance(result, list) else []
        return []

    def synthesize(self, max_tokens: int = 400) -> str:
        fn = getattr(self._agent, "synthesize", None)
        if fn:
            result = fn(max_tokens=max_tokens)
            return str(result) if result else ""
        return ""


__all__ = [
    "CerebrumAgent",
    "CerebellumAgent",
    "ThalamusAgent",
    "HippocampusAgent",
    "AmygdalaAgent",
    "BrainstemAgent",
    "FrontalAgent",
    "HypothalamusAgent",
    "CortexAgent",
]
