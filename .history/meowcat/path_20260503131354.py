"""meowcat atomic paths — Path dataclass + PathRegistry + built-in path table.

A Path is an immutable neural signal recipe: from which organ, to which organ,
call which method. PathRegistry manages all registered paths, providing
name-based lookup and execution.

For external developers::

    from meowcat.path import Path, BUILTIN_PATHS

    # View built-in paths
    for p in BUILTIN_PATHS:
        print(f"{p.name}: {p.from_organ} -> {p.to_organ}.{p.method} [{p.mode}]")

    # Execute via cat
    result = await cat.path_registry.run("locate", query="hello")

This file has zero third-party dependencies and zero meowagent imports.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from meowcat.anatomy import (
    AMYGDALA,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORTEX,
    EARS,
    FRONTAL,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    THALAMUS,
)
from meowcat.wiring import Organ


@dataclass(frozen=True)
class Path:
    """An immutable atomic neural signal recipe.

    Each Path describes one ``cat.signal(from_organ, to_organ, method,
    **kwargs)`` call. Path objects are immutable and can be composed into
    :class:`Loop` (v0.5.28) to form closed loops.

    Attributes:
        name: Unique path name, e.g. ``"locate"``
        from_organ: Signal source organ coordinate
        to_organ: Signal target organ coordinate
        method: Method name to call on the target organ
        mode: ``"read"`` or ``"write"``, marking read/write semantics
        description: Human-readable description
    """

    name: str
    from_organ: Organ
    to_organ: Organ
    method: str
    mode: str = "read"
    description: str = ""

    def __post_init__(self) -> None:
        if self.mode not in ("read", "write"):
            raise ValueError(
                f"mode must be 'read' or 'write', got {self.mode!r}")


# -- Builtin path table ------------------------------------------------------

BUILTIN_PATHS: tuple[Path, ...] = (
    # -- Memory domain --
    Path("locate",             THALAMUS,    THALAMUS,
         "locate",             "read",  "Retrieve memories (thalamus self-loop)"),
    Path("remember",           BRAINSTEM,   HIPPOCAMPUS,
         "remember",           "write", "Store memory"),
    Path("get_entity",         THALAMUS,    HIPPOCAMPUS,
         "get_entity",         "read",  "Read single entity"),
    Path("get_all",            THALAMUS,    HIPPOCAMPUS,
         "get_all",            "read",  "Read all entities"),
    Path("fts_search",         THALAMUS,    HIPPOCAMPUS,
         "fts_search",         "read",  "Full-text search"),
    Path("add_entity",         BRAINSTEM,   HIPPOCAMPUS,
         "add_entity",         "write", "Add entity"),
    Path("add_episode",        BRAINSTEM,   HIPPOCAMPUS,
         "add_episode",        "write", "Add episode"),
    Path("connect",            BRAINSTEM,   HIPPOCAMPUS,
         "connect",            "write", "Connect entities"),
    Path("record_access",      BRAINSTEM,   HIPPOCAMPUS,
         "record_access",      "write", "Record access"),
    Path("set_dormant",        BRAINSTEM,   HIPPOCAMPUS,
         "set_dormant",        "write", "Set dormant"),
    Path("append_content",     BRAINSTEM,   HIPPOCAMPUS,
         "append_content",     "write", "Append content"),
    Path("update_importance",  BRAINSTEM,   HIPPOCAMPUS,
         "update_importance",  "write", "Update importance"),
    Path("set_last_seen",      BRAINSTEM,   HIPPOCAMPUS,
         "set_last_seen",      "write", "Set last seen"),
    # -- Reasoning domain --
    Path("deep_reason",        THALAMUS,    CEREBRUM,
         "generate",           "read",  "Deep reason"),
    # -- Output domain --
    Path("speak",              CEREBELLUM,  MOUTH,
         "speak",              "write", "Output reply"),
    Path("hear",               EARS,        THALAMUS,
         "hear",               "read",  "Receive input"),
    # -- Maintenance domain --
    Path("decay",              HYPOTHALAMUS, HIPPOCAMPUS,
         "decay",             "write", "Decay memory"),
    Path("weaken_connections", HYPOTHALAMUS, HIPPOCAMPUS,
         "weaken_connections", "write", "Weaken connections"),
    Path("cleanup_orphans",    HYPOTHALAMUS, HIPPOCAMPUS,
         "cleanup_orphan_connections", "write", "Cleanup orphan connections"),
    # -- Tool execution domain --
    Path("execute_tool",       CEREBELLUM,  PAWS,
         "interact_with_tool",  "write", "Execute tool"),
    # -- Self-loop paths (v0.5.28b added, from == to, bypass wiring) --
    Path("decide_route",       THALAMUS,    THALAMUS,
         "decide_route",        "read",  "Routing decision"),
    Path("assess_safety",      AMYGDALA,    AMYGDALA,
         "assess_safety",       "read",  "Safety assessment"),
    # -- Synthesis domain --
    Path("synthesize",         BRAINSTEM,   CORTEX,
         "synthesize",          "read",  "Worldview synthesis"),
    # -- Orchestration domain (v1.0.15) --
    Path("workflow_create",     BRAINSTEM,   HIPPOCAMPUS,
         "add_entity",          "write", "Create workflow"),
    Path("workflow_checkpoint", BRAINSTEM,   HIPPOCAMPUS,
         "append_content",      "write", "Write checkpoint"),
    Path("workflow_resume",     BRAINSTEM,   HIPPOCAMPUS,
         "get_entity",          "read",  "Resume workflow"),
)


def register_builtin_paths(registry: "PathRegistry") -> None:
    """将内置路径注册到 PathRegistry。

    Args:
        registry: 路径注册中心实例
    """
    for p in BUILTIN_PATHS:
        registry.register(p)


# -- PathRegistry -------------------------------------------------

@dataclass
class PathRegistry:
    """路径注册中心 — 管理 Path 的注册、查询和执行。

    用法::

        registry = PathRegistry()
        register_builtin_paths(registry)

        # 查询
        path = registry.get("locate")
        all_paths = registry.list_all()

        # 执行
        result = await registry.run(cat, "locate", query="hello")
    """

    _paths: dict[str, Path] = field(default_factory=dict, init=False)
    _paths_list: list[Path] = field(default_factory=list, init=False)

    def register(self, path: Path) -> None:
        """注册一条路径。同名路径覆盖旧值。

        Args:
            path: Path 实例

        Raises:
            TypeError: path 不是 Path 实例
        """
        if not isinstance(path, Path):
            raise TypeError(
                f"Expected Path instance, got {type(path).__name__}"
            )
        # 覆盖旧值（同名路径后注册覆盖前注册）
        if path.name in self._paths:
            self._paths_list.remove(self._paths[path.name])
        self._paths[path.name] = path
        self._paths_list.append(path)

    def get(self, name: str) -> Path | None:
        """按名查找路径。

        Args:
            name: 路径名称

        Returns:
            Path 对象，不存在返回 None
        """
        return self._paths.get(name)

    def list_all(self) -> list[Path]:
        """返回所有已注册路径列表（注册顺序）。"""
        return list(self._paths_list)

    async def run(self, cat: Any, name: str, **kwargs: Any) -> Any:
        """执行一条路径。

        等价于::

            path = registry.get(name)
            cat.signal(path.from_organ, path.to_organ, path.method, **kwargs)

        Args:
            cat: CatBase 实例（需支持 ``cat.signal(from, to, method, **kwargs)``）
            name: 路径名称
            **kwargs: 转发给目标方法的参数

        Returns:
            目标方法的返回值

        Raises:
            KeyError: 路径不存在
        """
        path = self.get(name)
        if path is None:
            raise KeyError(f"Path '{name}' not found in registry")

        # 自环：from == to，直接调本地方法（不走 wiring 校验，wiring 无自环边）
        if path.from_organ == path.to_organ:
            organ = cat.organ(*path.to_organ)
            method = getattr(organ, path.method)
            result = method(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

        return await cat.signal(
            path.from_organ, path.to_organ, path.method, **kwargs,
        )


__all__ = ["Path", "PathRegistry", "BUILTIN_PATHS", "register_builtin_paths"]
