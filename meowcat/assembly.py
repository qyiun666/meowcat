"""meowcat 装配骨架 — 猫的基类。

meowcat 定义猫的骨架和生命周期，meowagent 子类决定用什么材料的器官。

骨架做四件事：

1. **注册/查找器官**（``mount`` / ``organ``）——附可选 Protocol 校验
2. **事件总线**（``on`` / ``emit``）——神经信号
3. **神经突触**（``signal``）——器官互访的唯一合法通道，wiring 校验
4. **生命周期**（``start`` / ``shutdown`` / ``perceive``）

不做：具体器官实例化、配置加载、IO——这些都是 meowagent 的事。

v0.5.1 在 v0.5.0 骨架上新增 wiring/reflex/perceive 三件套：真约束 + 反射入口。
"""

from __future__ import annotations

import inspect
from typing import Any, AsyncIterator

from meowcat import biology
from meowcat.errors import (
    IllegalNeuralPathError,
    NoReflexMatchedError,
    OrganNotMountedError,
    OrganProtocolMismatchError,
)
from meowcat.events import EventBus, Handler
from meowcat.loop import Lifecycle, NerveEvent
from meowcat.perception import PerceptionContext, infer_modality
from meowcat.pipeline import Pipeline
from meowcat.reflex import Reflex, ReflexRegistry
from meowcat.wiring import Organ, Wiring


class CatBase:
    """猫装配基类。"""

    def __init__(self, cat_id: str) -> None:
        self.cat_id = cat_id
        self._organs: dict[str, dict[str, Any]] = {}
        self._events: EventBus = EventBus()
        # v0.5.1 新增：神经系统
        self.wiring: Wiring = Wiring()
        self.reflexes: ReflexRegistry = ReflexRegistry()

    # -- 器官注册 ----------------------------------------------------

    def mount(
        self,
        category: str,
        name: str,
        organ: Any,
        *,
        protocol: type | None = None,
    ) -> None:
        """挂载一个器官。

        Args:
            category: 器官分类（``brain`` / ``sense`` / ``voice`` / ``storage`` 等）
            name: 器官名（``hippocampus`` / ``ears`` / ``tail`` 等）
            organ: 具体实现实例
            protocol: 可选 ``@runtime_checkable`` Protocol 类，
                非 None 时 ``isinstance(organ, protocol)`` 校验，
                不匹配抛 :class:`OrganProtocolMismatchError`。
        """
        if protocol is not None and not isinstance(organ, protocol):
            raise OrganProtocolMismatchError(
                category, name, protocol, organ,
            )
        self._organs.setdefault(category, {})[name] = organ

    def organ(self, category: str, name: str) -> Any:
        """取出一个已挂载的器官。未挂载抛 :class:`OrganNotMountedError`。"""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            raise OrganNotMountedError(category, name)
        return bucket[name]

    def organs(self, category: str) -> dict[str, Any]:
        """返回某个分类下所有器官的快照（只读拷贝）。"""
        return dict(self._organs.get(category, {}))

    def has_organ(self, category: str, name: str) -> bool:
        """检查器官是否已挂载。"""
        return name in self._organs.get(category, {})

    def unmount(self, category: str, name: str) -> bool:
        """卸载一个器官，不存在返回 False。"""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            return False
        del bucket[name]
        return True

    def assert_organs_mounted(
        self, required: list[tuple[str, str]],
    ) -> None:
        """断言必需器官已挂载，否则抛 :class:`OrganNotMountedError`。

        用于子类（如应用层主猫 Cat）在 ``__init__`` 末尾校验解剖完整性。
        具体“主猫必须有哪些器官”由应用层决定，meowcat 只提供校验机制。

        Args:
            required: ``[(category, name), ...]`` 必需器官清单
        """
        for category, name in required:
            if not self.has_organ(category, name):
                raise OrganNotMountedError(category, name)

    # -- 事件 --------------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """注册事件 handler（装饰器或函数调用两种用法）。"""
        return self._events.on(event, handler)

    def off(self, event: str, handler: Handler) -> bool:
        """注销事件 handler。"""
        return self._events.off(event, handler)

    async def emit(self, event: str, payload: Any = None) -> None:
        """触发事件。"""
        await self._events.emit(event, payload)

    @property
    def events(self) -> EventBus:
        """暴露底层 EventBus 给子类做深度定制（一般不需要用到）。"""
        return self._events

    # -- 神经突触（v0.5.1 新增）------------------------------------

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """器官互访的唯一合法通道。

        流程：

        1. ``wiring.assert_allowed(from, to)``——非法抛
           :class:`IllegalNeuralPathError`
        2. emit ``nerve.signal`` 事件（便于调试/埋点）
        3. 从 ``self.organs(to_organ[0])`` 取出目标器官
        4. ``getattr(target, method)(*args, **kwargs)``，
           若返回 awaitable 自动 await

        Args:
            from_organ: 调用方器官坐标 ``(category, name)``
            to_organ: 目标器官坐标 ``(category, name)``
            method: 目标上要调用的方法名
            *args, **kwargs: 转发给目标方法

        Returns:
            目标方法的返回值（已 unwrap 过 awaitable）
        """
        self.wiring.assert_allowed(from_organ, to_organ)

        await self._events.emit(
            NerveEvent.SIGNAL,
            {
                "from": from_organ,
                "to": to_organ,
                "method": method,
            },
        )

        target = self.organ(*to_organ)
        fn = getattr(target, method)
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    # -- 神经系统装配 ------------------------------------------------

    def wire_default_nervous_system(self) -> None:
        """一键装配生物学默认神经通路表。

        等价于调用 :func:`meowcat.biology.apply_default_wiring(self.wiring)`。
        可在 ``__init__`` 末尾调用，也可由应用层按需延后。
        """
        biology.apply_default_wiring(self.wiring)

    def register_reflex(self, reflex: Reflex) -> None:
        """注册一条反射弧。"""
        self.reflexes.register(reflex)

    def freeze_nervous_system(self) -> None:
        """冻结 wiring 并校验所有已注册反射 path 合法。

        一般在应用层完成 ``mount`` + ``register_reflex`` 后调用。
        之后 ``wiring.connect/forbid`` 都会抛；任一 reflex path
        不合法则抛 :class:`ReflexPathInvalidError`。
        """
        self.reflexes.validate(self.wiring)
        self.wiring.freeze()

    # -- 感知入口 ----------------------------------------------------

    async def perceive(
        self,
        input: Any,
        **extras: Any,
    ) -> AsyncIterator[Any]:
        """猫对外的唯一反射入口：给个刺激，自动走对应神经链路。

        流程：

        1. ``reflexes.match(input)`` 找到第一个命中的反射；
           无命中抛 :class:`NoReflexMatchedError`
        2. 构造 :class:`PerceptionContext`，emit ``lifecycle.perceive_start``
        3. 若 ``reflex.stages`` 非空：用 :class:`Pipeline` 驱动并 yield 事件
           否则：按 ``reflex.path`` 逐跳 emit ``nerve.signal``（让业务 handler 接）
        4. emit ``lifecycle.perceive_end``

        Returns:
            事件流（``AsyncIterator``）。调用方用 ``async for`` 消费。
            ctx.final_reply 也会被顺带回写。
        """
        reflex = self.reflexes.match(input)
        if reflex is None:
            raise NoReflexMatchedError(repr(input))

        ctx = PerceptionContext(
            input=input,
            modality=infer_modality(input),
            reflex_name=reflex.name,
            cat=self,
            extras=dict(extras),
        )

        await self._events.emit(
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
                # path 在 freeze 时已校验过，这里直接走 signal 广播点
                await self._events.emit(
                    NerveEvent.SIGNAL,
                    {"from": frm, "to": to, "method": "__perceive__"},
                )

        await self._events.emit(
            Lifecycle.PERCEIVE_END,
            {"reflex_name": reflex.name, "reply": ctx.final_reply},
        )

    # -- 装配工具 ----------------------------------------------------

    def _assemble(self, *, reflex_stages: list[Any] | None = None) -> None:
        """自动扫描 ``self`` 上的器官属性并完成骨架装配。

        扫描已知器官名、mount 到 ``_organs``、
        装配默认神经系统、注册默认 reflex、冻结。

        子类只需在 ``__init__`` 末尾调用一次。

        Args:
            reflex_stages: 默认 text_dialogue reflex 的 stages 列表。
                           为 None 则使用空列表。

        Usage::

            class MyCat(CatBase):
                def __init__(self, cat_id):
                    super().__init__(cat_id)
                    self.cerebrum = MyCerebrum()
                    # ... 创建所有器官 ...
                    self._assemble(reflex_stages=[MyStage()])
        """
        from meowcat.biology import DEFAULT_REFLEX_PATHS
        from meowcat.reflex import Reflex

        _BRAIN_NAMES = {
            "hippocampus", "thalamus", "amygdala", "frontal",
            "hypothalamus", "cerebellum", "cerebrum", "brainstem", "cortex",
        }
        _SENSE_NAMES = {"ears", "eyes", "whiskers", "paws"}
        _VOICE_NAMES = {"mouth", "purr", "tail"}

        for name in _BRAIN_NAMES:
            obj = getattr(self, name, None)
            if obj is not None:
                self.mount("brain", name, obj)

        for name in _SENSE_NAMES:
            obj = getattr(self, name, None)
            if obj is not None:
                self.mount("sense", name, obj)

        for name in _VOICE_NAMES:
            obj = getattr(self, name, None)
            if obj is not None:
                self.mount("voice", name, obj)

        self.wire_default_nervous_system()

        if "text_dialogue" in DEFAULT_REFLEX_PATHS:
            path = list(DEFAULT_REFLEX_PATHS["text_dialogue"])
            self.register_reflex(Reflex(
                name="text_dialogue",
                trigger=lambda x: isinstance(x, str) and not x.startswith("/"),
                path=path,
                stages=reflex_stages if reflex_stages is not None else [],
            ))

        self.freeze_nervous_system()

    # -- 生命周期 ----------------------------------------------------

    async def start(self) -> None:
        """启动猫。子类可重写，**务必调用 ``await super().start()``**。"""
        await self._events.emit(Lifecycle.START, {"cat": self})

    async def shutdown(self) -> None:
        """关闭猫。子类可重写，**务必调用 ``await super().shutdown()``**。"""
        await self._events.emit(Lifecycle.SHUTDOWN, {"cat": self})


class KittenBase(CatBase):
    """分身猫基类 — wiring 裁剪版 CatBase。

    继承 CatBase 完整骨架（mount/signal/perceive/reflexes），但：

    - 默认装配 ``apply_kitten_wiring``（cerebrum→hippocampus 禁止，
      分身猫只读记忆不写入）
    - ``signal()`` 重写：校验 ``KITTEN_FORBIDDEN_METHODS``，
      阻止分身猫调用 ``spawn_kitten`` / ``absorb_merge`` 等主猫专属方法

    用法::

        from meowcat.assembly import KittenBase

        class KittenAgent(KittenBase):
            def __init__(self, kitten_id: str, ...):
                super().__init__(kitten_id)
                # 再挂载分身猫需要的器官...
            def wire_default_nervous_system(self):
                biology.apply_kitten_wiring(self.wiring)

    v0.5.4 新增。
    """

    def __init__(self, cat_id: str) -> None:
        super().__init__(cat_id)
        # 分身猫默认装配受限 wiring（不 freeze，由应用层决定时机）
        biology.apply_kitten_wiring(self.wiring)

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """分身猫信号——比主猫多一层方法黑名单校验。"""
        if method in biology.KITTEN_FORBIDDEN_METHODS:
            raise IllegalNeuralPathError(
                from_organ, to_organ,
                reason=f"分身猫禁止调用 '{method}'（主猫专属能力）",
            )
        return await super().signal(from_organ, to_organ, method, *args, **kwargs)

    def wire_default_nervous_system(self) -> None:
        """分身猫专用 wiring 装配（裁剪版）。"""
        biology.apply_kitten_wiring(self.wiring)


__all__ = ["CatBase", "KittenBase"]
