"""meowcat 存储协议 — 持久化存储接口。

全部 typing.Protocol（鸭子类型），零第三方依赖。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol",
]


@runtime_checkable
class GraphStorageProtocol(Protocol):
    """纠缠图持久化存储接口。

    **坐标**: 无（存储层，不占用器官坐标）
    **入边**: 由 Hippocampus 直接持有，不经 wiring 调用
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（存储后端）
    """

    async def load(self, cat_id: str) -> dict[str, Any]: ...
    async def save(self, cat_id: str, graph_data: dict[str, Any]) -> None: ...


@runtime_checkable
class L6StorageProtocol(Protocol):
    """L6 原始对话持久化存储接口。

    **坐标**: 无（存储层，不占用器官坐标）
    **入边**: 由 BrainStem 直接持有，不经 wiring 调用
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（存储后端）
    """

    def append(self, cat_id: str, turn: int,
               user_msg: str, ai_reply: str) -> None: ...

    def load_all(self, cat_id: str) -> list[dict[str, Any]]: ...
    def load_recent(self, cat_id: str,
                    n: int = 20) -> list[dict[str, Any]]: ...

    def total_chars(self, cat_id: str) -> int: ...
    def get_stats(self, cat_id: str) -> dict[str, Any]: ...


@runtime_checkable
class VectorStorageProtocol(Protocol):
    """向量检索存储接口（语义搜索）。

    **坐标**: 无（存储层，不占用器官坐标）
    **入边**: 由 Thalamus 可选持有，不经 wiring 调用
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（存储后端）
    """

    def add(self, text: str, metadata: dict[str, Any]) -> str: ...
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]: ...
    def delete(self, doc_id: str) -> bool: ...


@runtime_checkable
class SharedStorageProtocol(Protocol):
    """Colony 共享记忆存储接口。

    **坐标**: 无（存储层，不占用器官坐标）
    **入边**: 由 ColonyManager 直接持有，不经 wiring 调用
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（存储后端）
    """

    def load(self) -> dict[str, Any]: ...
    def save(self, data: dict[str, Any]) -> None: ...
    def merge(self, delta: dict[str, Any]) -> dict[str, Any]: ...
