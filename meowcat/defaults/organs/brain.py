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
