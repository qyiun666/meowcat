"""meowcat 原子路径 — Path dataclass + PathRegistry + 内置路径表。

路径是一段不可变的神经信号配方：从哪个器官、到哪个器官、调哪个方法。
PathRegistry 管理所有已注册路径，提供按名查询和执行能力。

对外部开发者的体验::

    from meowcat.path import Path, BUILTIN_PATHS

    # 查看内置路径
    for p in BUILTIN_PATHS:
        print(f"{p.name}: {p.from_organ} -> {p.to_organ}.{p.method} [{p.mode}]")

    # 通过 cat 执行
    result = await cat.path_registry.run("locate", query="hello")

本文件零第三方依赖，零 meowagent import。
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
    """一段不可变的原子神经信号配方。

    每条 Path 描述一次 ``cat.signal(from_organ, to_organ, method, **kwargs)``
    调用。Path 对象不可变，可被组合进 :class:`Loop`（v0.5.28）中形成闭环。

    Attributes:
        name: 路径唯一名称，如 ``"locate"``
        from_organ: 信号发起方器官坐标
        to_organ: 信号接收方器官坐标
        method: 目标器官上调用的方法名
        mode: ``"read"`` 或 ``"write"``，标记读写语义
        description: 人类可读描述
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


# -- 内置路径表 ----------------------------------------------------

BUILTIN_PATHS: tuple[Path, ...] = (
    # ── 记忆域 ──
    Path("locate",             THALAMUS,    THALAMUS,
         "locate",             "read",  "检索记忆（丘脑自环）"),
    Path("remember",           BRAINSTEM,   HIPPOCAMPUS,
         "remember",           "write", "存储记忆"),
    Path("get_entity",         THALAMUS,    HIPPOCAMPUS,
         "get_entity",         "read",  "读取单条实体"),
    Path("get_all",            THALAMUS,    HIPPOCAMPUS,
         "get_all",            "read",  "读取全部实体"),
    Path("fts_search",         THALAMUS,    HIPPOCAMPUS,
         "fts_search",         "read",  "全文检索"),
    Path("add_entity",         BRAINSTEM,   HIPPOCAMPUS,
         "add_entity",         "write", "新增实体"),
    Path("add_episode",        BRAINSTEM,   HIPPOCAMPUS,
         "add_episode",        "write", "新增情景"),
    Path("connect",            BRAINSTEM,   HIPPOCAMPUS,
         "connect",            "write", "连接实体"),
    Path("record_access",      BRAINSTEM,   HIPPOCAMPUS,
         "record_access",      "write", "记录访问"),
    Path("set_dormant",        BRAINSTEM,   HIPPOCAMPUS,
         "set_dormant",        "write", "设置休眠"),
    Path("append_content",     BRAINSTEM,   HIPPOCAMPUS,
         "append_content",     "write", "追加内容"),
    Path("update_importance",  BRAINSTEM,   HIPPOCAMPUS,
         "update_importance",  "write", "更新重要性"),
    Path("set_last_seen",      BRAINSTEM,   HIPPOCAMPUS,
         "set_last_seen",      "write", "设置最近活跃"),
    # ── 推理域 ──
    Path("deep_reason",        THALAMUS,    CEREBRUM,
         "generate",           "read",  "深度推理"),
    # ── 输出域 ──
    Path("speak",              CEREBELLUM,  MOUTH,
         "speak",              "write", "输出回复"),
    Path("hear",               EARS,        THALAMUS,
         "hear",               "read",  "接收输入"),
    # ── 维护域 ──
    Path("decay",              HYPOTHALAMUS, HIPPOCAMPUS,
         "decay",             "write", "衰减记忆"),
    Path("weaken_connections", HYPOTHALAMUS, HIPPOCAMPUS,
         "weaken_connections", "write", "弱化连接"),
    Path("cleanup_orphans",    HYPOTHALAMUS, HIPPOCAMPUS,
         "cleanup_orphan_connections", "write", "清理孤立连接"),
    # ── 工具执行域 ──
    Path("execute_tool",       CEREBELLUM,  PAWS,
         "interact_with_tool",  "write", "执行工具"),
    # ── 自环路（v0.5.28b 新增，from == to，不走 wiring）──
    Path("decide_route",       THALAMUS,    THALAMUS,
         "decide_route",        "read",  "路由决策"),
    Path("assess_safety",      AMYGDALA,    AMYGDALA,
         "assess_safety",       "read",  "安全评估"),
    # ── 综合域 ──
    Path("synthesize",         BRAINSTEM,   CORTEX,
         "synthesize",          "read",  "世界观综合"),
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
