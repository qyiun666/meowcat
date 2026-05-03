"""meowcat 默认器官桩 — 满足 Protocol 的空操作实现。

每个 Noop* 类均继承 Pluggable（v1.0.7），提供 mount_plug / unmount_plug /
_run_plugs 插件能力。HOOKS 类变量声明可挂载的 hook 及其建议签名。

三种执行模式：
- A 首命中覆盖：首个非默认值直接返回
- B 合并增强：所有插件结果 merge 到默认值
- C 完全替代：首个插件直接替代默认行为
"""

from __future__ import annotations

import time as _time
from typing import Any

from meowcat.defaults.stores import InMemoryGraphStore
from meowcat.pluggable import Pluggable


# ===================================================================
# 脑区
# ===================================================================


class NoopAmygdala(Pluggable):
    """默认杏仁核：永不拒绝，零安全风险。

    模式 A — assess_safety / assess_tool_risk 首命中覆盖。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
        "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
    }

    name: str = "noop_amygdala"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def is_rejection(self, msg: str) -> bool:
        return False

    def classify_rejection(self, msg: str) -> str:
        return "none"

    def parse_correction(self, msg: str) -> tuple[str, str] | None:
        return None

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any,
    ) -> str:
        return msg

    async def handle_correction(
        self, msg: str, hippocampus: Any,
    ) -> tuple[str, str] | None:
        return None

    async def assess_safety(self, user_input: str) -> dict[str, Any]:
        for _name, r in self._run_plugs("assess_safety", user_input):
            if isinstance(r, dict) and not r.get("safe", True):
                return r
        return {"safe": True, "risk": "none"}

    @staticmethod
    def assess_tool_risk(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"risk": "low", "reason": "noop"}


class NoopFrontal(Pluggable):
    """默认前额叶：不检测焦点转移，不保存焦点。

    模式 A — is_continue / detect_shift 首命中覆盖。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "is_continue": {"in": "msg: str", "out": "bool"},
        "detect_shift": {"in": "msg: str", "out": "bool"},
    }

    name: str = "noop_frontal"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def is_continue(self, msg: str) -> bool:
        for _name, r in self._run_plugs("is_continue", msg):
            if isinstance(r, bool):
                return r
        return False

    def detect_shift(self, msg: str) -> bool:
        for _name, r in self._run_plugs("detect_shift", msg):
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
    """默认下丘脑：不执行维护，不唤醒实体。

    模式 B — run_maintenance 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "run_maintenance": {"in": "country_code: str|None", "out": "Any"},
    }

    name: str = "noop_hypothalamus"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def run_maintenance(self, country_code: str | None = None) -> Any:
        result: dict[str, Any] = {
            "decayed": 0, "orphans_cleaned": 0, "woke": 0, "suggestions": []}
        for _name, r in self._run_plugs("run_maintenance", country_code):
            if isinstance(r, dict):
                result.update(r)
        return result

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]:
        return {"decayed": 0}

    def compress_long_history(self) -> dict[str, Any]:
        return {"compressed": 0}


class NoopCortex(Pluggable):
    """默认皮质：不摄入世界观，不记录弱点。

    模式 B — synthesize 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "synthesize": {"in": "max_tokens: int", "out": "str"},
    }

    name: str = "noop_cortex"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def ingest(self, source: str, layer: str, key: str, value: Any) -> None:
        pass

    def record_weakness(self, kind: str, detail: str) -> None:
        pass

    def weaknesses(self) -> list[dict[str, Any]]:
        return []

    def synthesize(self, max_tokens: int = 400) -> str:
        result = ""
        for _name, r in self._run_plugs("synthesize", max_tokens):
            if isinstance(r, str):
                result += r
        return result


class NoopBrainstem(Pluggable):
    """默认脑干：不构建 system prompt，不取消当前任务。

    模式 B — build_system_prompt 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "build_system_prompt": {"in": "route: str", "out": "str"},
    }

    name: str = "noop_brainstem"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def build_system_prompt(self, route: str) -> str:
        parts: list[str] = []
        for _name, r in self._run_plugs("build_system_prompt", route):
            if isinstance(r, str) and r:
                parts.append(r)
        return "\n".join(parts) if parts else ""

    def cancel_current(self) -> bool:
        return False


# ===================================================================
# 感官
# ===================================================================


class NoopEars(Pluggable):
    """默认耳朵：听不出关键词，语言固定 unknown。

    模式 B — hear / extract_keywords 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "hear": {"in": "raw: str|bytes", "out": "dict[str, Any]"},
        "extract_keywords": {"in": "text: str, top_k: int", "out": "list[str]"},
    }

    name: str = "noop_ears"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def hear(self, raw_input: str | bytes) -> dict[str, Any]:
        result: dict[str, Any] = {"text": str(
            raw_input), "keywords": [], "language": "unknown"}
        for _name, r in self._run_plugs("hear", raw_input):
            if isinstance(r, dict):
                result.update(r)
        return result

    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]:
        result: list[str] = []
        for _name, r in self._run_plugs("extract_keywords", text, top_k):
            if isinstance(r, list):
                result.extend(r)
        return result

    def detect_language(self, text: str) -> str:
        return "unknown"

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]:
        """默认情绪标注：原样返回，不做修改。"""
        return episode


class NoopEyes(Pluggable):
    """默认眼睛：看不见任何图像。

    模式 C — see 完全替代。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "see": {"in": "image: bytes, mime: str", "out": "dict[str, Any]"},
    }

    name: str = "noop_eyes"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def see(self, image_data: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        for _name, r in self._run_plugs("see", image_data, mime_type):
            if isinstance(r, dict):
                return r
        return {}


class NoopWhiskers(Pluggable):
    """默认胡须：无输入感觉，无输出漂移检测。

    模式 B — feel_input / feel_output / check_hallucination 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "feel_input": {"in": "text: str", "out": "dict[str, Any]"},
        "feel_output": {"in": "output: str, schema: dict", "out": "dict[str, Any]"},
        "check_hallucination": {"in": "reply: str, session_id: str", "out": "dict[str, Any]"},
    }

    name: str = "noop_whiskers"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def feel_input(self, text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for _name, r in self._run_plugs("feel_input", text):
            if isinstance(r, dict):
                result.update(r)
        return result

    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for _name, r in self._run_plugs("feel_output", output, expected_schema):
            if isinstance(r, dict):
                result.update(r)
        return result

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]:
        return {"drift": False}

    def check_hallucination(
        self, reply: str, session_id: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {"hallucination": False}
        for _name, r in self._run_plugs("check_hallucination", reply, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result


# ===================================================================
# 嗓音
# ===================================================================


class NoopMouth(Pluggable):
    """默认嘴巴：不说话。

    模式 C — speak 完全替代。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "speak": {"in": "text: str, **kwargs", "out": "str"},
    }

    name: str = "noop_mouth"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def speak(self, text: str, **kwargs: Any) -> str:
        for _name, r in self._run_plugs("speak", text, **kwargs):
            return r  # type: ignore[no-any-return]
        return ""


class NoopPurr(Pluggable):
    """默认咕噜：不流式输出。

    模式 C — stream 完全替代。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "stream": {"in": "text: str, **kwargs", "out": "Any"},
    }

    name: str = "noop_purr"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def stream(self, text: str, **kwargs: Any) -> Any:
        for _name, r in self._run_plugs("stream", text, **kwargs):
            return r
        return None


class NoopTail(Pluggable):
    """默认尾巴：不渲染任何终端 UI。

    模式 C — render 完全替代。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "render": {"in": "state: dict", "out": "None"},
    }

    name: str = "noop_tail"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def render(self, state: dict[str, Any]) -> None:
        for _name, r in self._run_plugs("render", state):
            return None
        return None


# ===================================================================
# 效应器
# ===================================================================


class NoopPaws(Pluggable):
    """默认爪子：不执行任何工具/命令。

    模式 C — execute 完全替代。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "execute": {"in": "name: str, params: dict", "out": "dict[str, Any]"},
    }

    name: str = "noop_paws"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    def diagnose(self) -> dict[str, Any]:
        return {}

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """统一工具执行入口（v1.0.7 新增）。"""
        for _name, r in self._run_plugs("execute", tool_name, params):
            if isinstance(r, dict):
                return r
        return {"ok": False, "reason": "noop_paws: execute disabled"}

    async def touch_file(
        self, path: str, content: str | None = None,
    ) -> dict[str, Any]:
        return await self.execute("touch_file", {"path": path, "content": content})

    async def run_command(self, command: str, **kwargs: Any) -> dict[str, Any]:
        return await self.execute("run_command", {"command": command, **kwargs})

    async def interact_with_tool(
        self, skill_name: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.execute(skill_name, params)


# ===================================================================
# 新增 v1.0.7: NoopThalamus + NoopHippocampus
# ===================================================================


class NoopThalamus(Pluggable):
    """默认丘脑：简单路由，不做记忆检索。

    模式 B — locate 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "locate": {"in": "msg: str, session_id: str", "out": "LocateResultShape"},
    }

    name: str = "noop_thalamus"

    def __init__(self) -> None:
        Pluggable.__init__(self)

    async def locate(self, msg: str, session_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "route": "chat", "entities": [], "snippets": []}
        for _name, r in self._run_plugs("locate", msg, session_id):
            if isinstance(r, dict):
                result.update(r)
        return result

    def decide_route(self, **kwargs: Any) -> dict[str, Any]:
        return {"route": "chat"}


class NoopHippocampus(Pluggable):
    """默认海马体：纯内存图存储，进程重启即丢失。

    封装 InMemoryGraphStore，实现 HippocampusProtocol 全套方法。
    模式 B — remember / recall 合并增强。
    """

    HOOKS: dict[str, dict[str, str]] = {
        "remember": {
            "in": "user_msg: str, ai_reply: str, cat_id: str, model: str",
            "out": "Any",
        },
        "recall": {
            "in": "query: str, limit: int",
            "out": "list[dict]",
        },
    }

    name: str = "noop_hippocampus"

    def __init__(self) -> None:
        Pluggable.__init__(self)
        self._store = InMemoryGraphStore()
        self.entities: dict[str, dict[str, Any]] = {}
        self.episodes: list[dict[str, Any]] = []

    # -- 记忆存储 ---------------------------------------------------

    async def remember(
        self, user_msg: str, ai_reply: str, cat_id: str, model: str,
    ) -> Any:
        result: dict[str, Any] = {"user_msg": user_msg, "ai_reply": ai_reply}
        for _name, r in self._run_plugs(
            "remember", user_msg, ai_reply, cat_id, model,
        ):
            if isinstance(r, dict):
                result.update(r)
        return result

    def add_episode(self, episode: dict[str, Any]) -> None:
        self.episodes.append(episode)

    def add_entity(self, entity: dict[str, Any]) -> None:
        eid = entity.get("id", entity.get(
            "entity_id", str(len(self.entities))))
        self.entities[eid] = entity

    # -- 记忆检索 ---------------------------------------------------

    def fts_search(
        self, cat_id: str, keywords: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """全文搜索记忆（简单关键词匹配）。"""
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

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """语义召回记忆（简单实现：委托 fts_search）。"""
        base = self.fts_search("", query, limit)
        for _name, r in self._run_plugs("recall", query, limit):
            if isinstance(r, list):
                return r
        return base

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

    # -- 连接操作 ---------------------------------------------------

    def connect(
        self, from_id: str, to_id: str, relation: str, strength: float = 1.0,
    ) -> None:
        if from_id in self.entities:
            self.entities[from_id].setdefault("connections", []).append({
                "to": to_id, "relation": relation, "strength": strength,
            })

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
        for eid, entity in list(self.entities.items()):
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

    # -- 维护 -------------------------------------------------------

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
            "connections": sum(
                len(e.get("connections", [])) for e in self.entities.values()
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"entities": dict(self.entities), "episodes": list(self.episodes)}

    def from_dict(self, d: dict[str, Any]) -> None:
        self.entities = d.get("entities", {})
        self.episodes = d.get("episodes", [])

    # -- v0.5.26 封装方法 -------------------------------------------

    def record_access(self, entity_id: str, delta: int = 1) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["_last_accessed"] = _time.time()
            self.entities[entity_id].setdefault("access_count", 0)
            self.entities[entity_id]["access_count"] += delta

    def set_dormant(self, entity_id: str, dormant: bool) -> None:
        if entity_id in self.entities:
            self.entities[entity_id]["dormant"] = dormant

    def append_content(
        self, entity_id: str, text: str, max_total: int | None = None,
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

    # -- v1.0.15 长流程 workflow 查询 --------------------------------

    def list_active_workflows(self, cat_id: str) -> list[dict[str, Any]]:
        """列出所有未完成的 workflow 实体。

        过滤 type="workflow" 且 status 为 active/awaiting_user 的实体。
        """
        results: list[dict[str, Any]] = []
        for eid, entity in self.entities.items():
            if entity.get("type") != "workflow":
                continue
            if entity.get("status") not in ("active", "awaiting_user"):
                continue
            if entity.get("cat_id") != cat_id:
                continue
            results.append({"entity_id": eid, **entity})
        return results
