"""meowcat 反射弧 —— 刺激→反应的执行契约。

:class:`Reflex` 三要素：
- ``trigger``: 何时触发（callable(input)→bool）
- ``path``: 神经信号流经的器官序列（校验用）
- ``stages``: 可选的 Stage 列表（有就走 Pipeline；没有就只沿 path 发 EventBus）

:class:`ReflexRegistry` 按 priority 倒序保存，``match(input)`` 返回第一个命中的。

:class:`ReflexArc` (v0.5.9) 封装 registry + events + 可选 nervous，提供
``perceive()`` 反射入口。可独立实例化，不依赖 CatBase。

启动时 ``cat.freeze_nervous_system()`` 会 ``validate(wiring)`` 校验每条 Reflex
的 path 相邻跳在 wiring 里合法，不合法抛 :class:`ReflexPathInvalidError`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Callable

from pydantic import BaseModel, ConfigDict, Field

from meowcat.errors import NoReflexMatchedError, ReflexPathInvalidError
from meowcat.events import EventBus
from meowcat.loop import Lifecycle, NerveEvent
from meowcat.perception import PerceptionContext, infer_modality
from meowcat.pipeline import Pipeline
from meowcat.protocols import StageProtocol
from meowcat.wiring import Organ, Wiring

if TYPE_CHECKING:
    from meowcat.nervous import Nervous

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


class ReflexArc:
    """反射弧子系统（v0.5.9）—— registry + perceive 入口 + path 校验。

    依赖显式注入：

    - ``events``: :class:`EventBus`，必需，perceive 全程 emit 生命周期事件
    - ``nervous``: :class:`Nervous` 可选，仅用于 ``validate_paths()`` 时读取
      ``nervous.wiring`` 校验 reflex.path。``None`` 时跳过校验。

    可独立实例化，不需 CatBase::

        arc = ReflexArc(EventBus())
        arc.register(Reflex(name="x", trigger=..., path=(...)))
        async for ev in arc.perceive("hi", cat=None):
            ...
    """

    def __init__(
        self,
        events: EventBus,
        nervous: "Nervous | None" = None,
    ) -> None:
        self.events = events
        self.nervous = nervous
        self.registry = ReflexRegistry()

    # -- 注册代理 ------------------------------------------------

    def register(self, reflex: Reflex) -> None:
        """注册一条反射弧。"""
        self.registry.register(reflex)

    def unregister(self, name: str) -> bool:
        """按名移除反射。"""
        return self.registry.unregister(name)

    def match(self, input: Any) -> Reflex | None:
        """返回第一个命中的反射。"""
        return self.registry.match(input)

    # -- 校验 --------------------------------------------------------

    def validate_paths(self) -> None:
        """校验已注册的所有 reflex.path 在 nervous.wiring 中合法。

        没有 ``nervous``（独立使用模式）直接跳过校验。
        """
        if self.nervous is None:
            return
        self.registry.validate(self.nervous.wiring)

    # -- 感知入口 ------------------------------------------------

    async def perceive(
        self,
        input: Any,
        *,
        cat: Any = None,
        **extras: Any,
    ) -> AsyncIterator[Any]:
        """反射弧入口：给个刺激，自动走对应神经链路。

        流程：

        1. ``match(input)`` 找到第一个命中的反射；无命中抛
           :class:`NoReflexMatchedError`
        2. 构造 :class:`PerceptionContext`，emit ``lifecycle.perceive_start``
        3. 若 ``reflex.stages`` 非空：用 :class:`Pipeline` 驱动并 yield 事件
           否则：按 ``reflex.path`` 逐跳 emit ``nerve.signal``（让业务 handler 接）
        4. emit ``lifecycle.perceive_end``

        Args:
            input: 外部刺激（任意类型，trigger 自判断）
            cat: 传入 :class:`PerceptionContext.cat`，供 Stage 访问整貓。
                独立使用模式传 ``None`` 即可。
            **extras: 进入 ``PerceptionContext.extras``

        Yields:
            Pipeline 或 reflex path 的中间事件
        """
        reflex = self.registry.match(input)
        if reflex is None:
            raise NoReflexMatchedError(repr(input))

        ctx = PerceptionContext(
            input=input,
            modality=infer_modality(input),
            reflex_name=reflex.name,
            cat=cat,
            extras=dict(extras),
        )

        await self.events.emit(
            Lifecycle.PERCEIVE_START,
            {"input": input, "reflex_name": reflex.name},
        )

        if reflex.stages:
            pipeline = Pipeline(list(reflex.stages))
            async for ev in pipeline.execute(ctx):
                yield ev
        else:
            # 无 Stage：只沿 path 逐跳广播，让业务层 handler 接
            for frm, to in reflex.hops():
                await self.events.emit(
                    NerveEvent.SIGNAL,
                    {"from": frm, "to": to, "method": "__perceive__"},
                )

        await self.events.emit(
            Lifecycle.PERCEIVE_END,
            {"reflex_name": reflex.name, "reply": ctx.final_reply},
        )


__all__ = ["Reflex", "ReflexRegistry", "ReflexArc", "Trigger"]
