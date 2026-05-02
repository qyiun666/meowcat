"""meowcat 反射弧 —— 刺激→反应的执行契约。

:class:`Reflex` 三要素：
- ``trigger``: 何时触发（callable(input)→bool）
- ``path``: 神经信号流经的器官序列（校验用）
- ``stages``: 可选的 Stage 列表（有就走 Pipeline；没有就只沿 path 发 EventBus）

:class:`ReflexRegistry` 按 priority 倒序保存，``match(input)`` 返回第一个命中的。

启动时 ``cat.freeze_nervous_system()`` 会 ``validate(wiring)`` 校验每条 Reflex
的 path 相邻跳在 wiring 里合法，不合法抛 :class:`ReflexPathInvalidError`。
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from meowcat.errors import ReflexPathInvalidError
from meowcat.protocols import StageProtocol
from meowcat.wiring import Organ, Wiring

Trigger = Callable[[Any], bool]


class Reflex(BaseModel):
    """一条反射弧。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    """反射名（如 ``text_dialogue`` / ``visual`` / ``danger`` / ``action_order``）。"""

    trigger: Trigger
    """判定输入是否触发本反射的函数。"""

    path: tuple[Organ, ...]
    """神经信号流经的器官序列，至少 2 跳。用于 wiring 合法性校验。"""

    stages: list[StageProtocol] = Field(default_factory=list)
    """可选：具体 Pipeline Stage 列表。

    - 非空：``cat.perceive`` 用 Pipeline 驱动
    - 空   ：``cat.perceive`` 按 path 逐跳发 ``nerve.signal`` 事件（让业务 handler 接）
    """

    priority: int = 0
    """多个反射命中时的优先级，越大越先匹配。"""

    def hops(self) -> list[tuple[Organ, Organ]]:
        """path 相邻跳序列：``[(p0,p1), (p1,p2), ...]``。"""
        return list(zip(self.path[:-1], self.path[1:]))


class ReflexRegistry:
    """反射注册表。"""

    def __init__(self) -> None:
        self._items: list[Reflex] = []

    # -- 写接口 ------------------------------------------------------

    def register(self, reflex: Reflex) -> None:
        """注册反射。按 priority 倒序插入以便 match 时线性扫描。"""
        if len(reflex.path) < 2:
            raise ValueError(
                f"Reflex '{reflex.name}' path must have at least 2 hops",
            )
        # 名字唯一：已有同名则替换
        self._items = [r for r in self._items if r.name != reflex.name]
        self._items.append(reflex)
        self._items.sort(key=lambda r: r.priority, reverse=True)

    def unregister(self, name: str) -> bool:
        """按名移除，不存在返回 False。"""
        before = len(self._items)
        self._items = [r for r in self._items if r.name != name]
        return len(self._items) != before

    # -- 查询接口 ----------------------------------------------------

    def get(self, name: str) -> Reflex | None:
        """按名取回反射，不存在返回 None。"""
        for r in self._items:
            if r.name == name:
                return r
        return None

    def match(self, input: Any) -> Reflex | None:
        """从高优先级到低，返回第一个 trigger 命中的反射，无则 None。"""
        for r in self._items:
            try:
                if r.trigger(input):
                    return r
            except Exception:
                # trigger 不该抛；抛了也当不匹配继续
                continue
        return None

    def all(self) -> list[Reflex]:
        """返回所有已注册反射的快照。"""
        return list(self._items)

    # -- 校验 --------------------------------------------------------

    def validate(self, wiring: Wiring) -> None:
        """校验每条反射的 path 相邻跳在 wiring 里合法。

        有任一不合法立即抛 :class:`ReflexPathInvalidError`。
        """
        for reflex in self._items:
            for hop in reflex.hops():
                frm, to = hop
                if not wiring.is_allowed(frm, to):
                    raise ReflexPathInvalidError(reflex.name, hop)


__all__ = ["Reflex", "ReflexRegistry", "Trigger"]
