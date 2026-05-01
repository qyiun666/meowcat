"""meowcat 默认存储 — 纯内存实现，零外部依赖。

用于快速原型和测试。生产环境请用 meowagent 的 SQLite/JSONL 实现。
"""

from __future__ import annotations

from typing import Any


class InMemoryGraphStore:
    """默认纠缠图存储 — 纯 Python dict，进程重启即丢失。"""

    def __init__(self) -> None:
        self._graphs: dict[str, dict[str, Any]] = {}

    async def load(self, cat_id: str) -> dict[str, Any]:
        return self._graphs.get(cat_id, {})

    async def save(self, cat_id: str, graph_data: dict[str, Any]) -> None:
        self._graphs[cat_id] = graph_data


class InMemoryL6Store:
    """默认 L6 对话存储 — 纯 Python list，进程重启即丢失。"""

    def __init__(self) -> None:
        self._records: dict[str, list[dict[str, Any]]] = {}

    def append(self, cat_id: str, turn: int, user_msg: str, ai_reply: str) -> None:
        if cat_id not in self._records:
            self._records[cat_id] = []
        self._records[cat_id].append({
            "turn": turn,
            "user": user_msg,
            "ai": ai_reply,
        })

    def load_all(self, cat_id: str) -> list[dict[str, Any]]:
        return self._records.get(cat_id, [])

    def load_recent(self, cat_id: str, n: int = 20) -> list[dict[str, Any]]:
        records = self._records.get(cat_id, [])
        return records[-n:] if records else []

    def total_chars(self, cat_id: str) -> int:
        records = self._records.get(cat_id, [])
        return sum(
            len(r.get("user", "")) + len(r.get("ai", "")) for r in records
        )

    def get_stats(self, cat_id: str) -> dict[str, Any]:
        records = self._records.get(cat_id, [])
        return {
            "total_turns": len(records),
            "total_chars": self.total_chars(cat_id),
        }
