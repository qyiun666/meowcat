"""meowcat 神经通路图（Wiring）—— 猫的神经解剖约束。

Wiring 是一张 **有向图 + 黑名单**，声明哪些器官间的调用是合法的。
``CatBase.signal(from, to, method, ...)`` 在调度前查此图，
非法调用抛 :class:`IllegalNeuralPathError`。

设计要点：

- **节点** = ``(category, name)`` 二元组，如 ``("brain", "cerebellum")``
- **边** = 允许 A 调用 B（方向敏感；双向互通需注册两条边）
- **黑名单** 优先级高于白名单：即使有 connect，forbid 一旦命中立即否决
- **冻结** freeze 后任何写操作抛 :class:`MeowCatError`，防止业务代码运行期篡改约束

本文件零第三方依赖，纯 stdlib。
"""

from __future__ import annotations

from typing import Iterable

from meowcat.errors import IllegalNeuralPathError, MeowCatError

# (category, name) 例：("brain","cerebellum")、("sense","paws")
Organ = tuple[str, str]
Edge = tuple[Organ, Organ]


class Wiring:
    """神经通路有向图（含黑名单）。

    典型用法::

        w = Wiring()
        w.connect(("brain", "cerebellum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        w.freeze()
        assert w.is_allowed(("brain", "cerebellum"), ("sense", "paws"))
        w.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))
        # 抛 IllegalNeuralPathError
    """

    def __init__(self) -> None:
        self._allowed: set[Edge] = set()
        self._forbidden: set[Edge] = set()
        self._frozen: bool = False

    # -- 写接口 ------------------------------------------------------

    def connect(self, from_organ: Organ, to_organ: Organ) -> None:
        """声明一条"允许 from→to 调用"的通路。

        重复 connect 幂等。若该边已在黑名单中，当前实现 **不报错**，
        仅记录白名单；查询时以黑名单为准（总是禁止）。
        """
        self._ensure_mutable()
        _validate_organ(from_organ, "from_organ")
        _validate_organ(to_organ, "to_organ")
        self._allowed.add((from_organ, to_organ))

    def forbid(self, from_organ: Organ, to_organ: Organ) -> None:
        """声明一条"禁止 from→to 调用"的通路。优先级高于 connect。"""
        self._ensure_mutable()
        _validate_organ(from_organ, "from_organ")
        _validate_organ(to_organ, "to_organ")
        self._forbidden.add((from_organ, to_organ))

    def freeze(self) -> None:
        """冻结图。之后 connect / forbid 都抛 :class:`MeowCatError`。"""
        self._frozen = True

    # -- 查询接口 ----------------------------------------------------

    def is_allowed(self, from_organ: Organ, to_organ: Organ) -> bool:
        """A 能否调用 B？黑名单 > 白名单。"""
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            return False
        return edge in self._allowed

    def assert_allowed(
        self, from_organ: Organ, to_organ: Organ,
    ) -> None:
        """非法则抛 :class:`IllegalNeuralPathError`。"""
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            raise IllegalNeuralPathError(
                from_organ, to_organ, reason="forbidden by wiring",
            )
        if edge not in self._allowed:
            raise IllegalNeuralPathError(
                from_organ, to_organ, reason="not connected in wiring",
            )

    @property
    def frozen(self) -> bool:
        """wiring 是否已冻结。"""
        return self._frozen

    # -- 内省（只读） -----------------------------------------------

    def edges(self) -> frozenset[Edge]:
        """当前所有允许边的不可变快照。"""
        return frozenset(self._allowed)

    def forbids(self) -> frozenset[Edge]:
        """当前所有禁止边的不可变快照。"""
        return frozenset(self._forbidden)

    def is_organ_wired(self, organ: Organ) -> bool:
        """器官是否出现在任意允许边中（作为源或目标）。"""
        for frm, to in self._allowed:
            if organ in (frm, to):
                if (frm, to) not in self._forbidden:
                    return True
        return False

    def snapshot(self) -> "WiringSnapshot":
        """返回当前图的不可变视图，便于反射执行时冻结读取。"""
        return WiringSnapshot(
            allowed=frozenset(self._allowed),
            forbidden=frozenset(self._forbidden),
        )

    # -- 便利方法 ----------------------------------------------------

    def connect_many(self, edges: Iterable[Edge]) -> None:
        """批量注册允许边。"""
        for frm, to in edges:
            self.connect(frm, to)

    def forbid_many(self, edges: Iterable[Edge]) -> None:
        """批量注册禁止边。"""
        for frm, to in edges:
            self.forbid(frm, to)

    # -- 内部 --------------------------------------------------------

    def _ensure_mutable(self) -> None:
        if self._frozen:
            raise MeowCatError(
                "Wiring is frozen; call freeze() happens only after assembly",
            )


class WiringSnapshot:
    """Wiring 的不可变快照（只读视图）。"""

    __slots__ = ("_allowed", "_forbidden")

    def __init__(
        self,
        allowed: frozenset[Edge],
        forbidden: frozenset[Edge],
    ) -> None:
        self._allowed = allowed
        self._forbidden = forbidden

    def is_allowed(self, from_organ: Organ, to_organ: Organ) -> bool:
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            return False
        return edge in self._allowed

    @property
    def allowed(self) -> frozenset[Edge]:
        return self._allowed

    @property
    def forbidden(self) -> frozenset[Edge]:
        return self._forbidden


def _validate_organ(organ: Organ, label: str) -> None:
    """断言 organ 是 ``(str, str)`` 二元组。"""
    if (
        not isinstance(organ, tuple)
        or len(organ) != 2
        or not all(isinstance(x, str) and x for x in organ)
    ):
        raise ValueError(
            f"{label} must be (category:str, name:str), got {organ!r}",
        )


__all__ = ["Wiring", "WiringSnapshot", "Organ", "Edge"]
