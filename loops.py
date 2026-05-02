"""meowcat 闭环 — Loop dataclass + LoopRegistry + 5 个默认闭环。

闭环 = Chain + 触发事件 + 退出事件。Loop 组合已有 Chain，通过事件挂载到
猫的生命周期中，形成自动化执行回路。

对外部开发者的体验::

    from meowcat.loops import Loop, BUILTIN_LOOPS, CONVERSATION_LOOP

    # 查看内置闭环
    for lp in BUILTIN_LOOPS:
        print(f"{lp.name}: trigger={lp.trigger}, chain={lp.chain.name}")

    # 通过 cat 执行
    result = await cat.run_loop("conversation", message="你好")

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from meowcat.chain import BUILTIN_CHAINS, Chain
from meowcat.loop import Lifecycle


# -- 从 BUILTIN_CHAINS 查找复用 Chain ---------------------------------

_MAINTENANCE_CHAIN: Chain = next(
    (c for c in BUILTIN_CHAINS if c.name == "maintenance"),
)
_DIAGNOSTIC_CHAIN: Chain = next(
    (c for c in BUILTIN_CHAINS if c.name == "diagnostic"),
)


# -- Loop dataclass -------------------------------------------------

@dataclass(frozen=True)
class Loop:
    """一组命名的闭环：Chain + 触发/退出事件。

    闭环封装了一条 :class:`Chain` 的执行加上生命周期事件的触发。
    触发事件在 chain 执行前发出，退出事件在 chain 执行后发出。

    Attributes:
        name: 闭环唯一名称，如 ``"conversation"``
        description: 人类可读描述
        chain: 关联的链路
        trigger: 触发事件名（None 表示手动触发）
        exit_event: 退出事件名（None 表示不发出退出事件）
    """

    name: str
    description: str
    chain: Chain
    trigger: str | None = None
    exit_event: str | None = None


# -- 5 个默认闭环 ---------------------------------------------------

CONVERSATION_LOOP: Loop = Loop(
    "conversation",
    "常规对话闭环 — 听→路由→找→推理→说→记",
    chain=Chain(
        "conversation_chain",
        ("hear", "decide_route", "locate", "deep_reason", "speak", "remember"),
        "对话链",
    ),
    trigger=Lifecycle.PERCEIVE_START,
)

TOOL_EXECUTION_LOOP: Loop = Loop(
    "tool_execution",
    "工具执行闭环 — 听→路由→执行→说→记",
    chain=Chain(
        "tool_loop_chain",
        ("hear", "decide_route", "execute_tool", "speak", "remember"),
        "工具链",
    ),
    trigger="orchestrate.start",
)

DANGER_RESPONSE_LOOP: Loop = Loop(
    "danger_response",
    "危险响应闭环 — 安全评估",
    chain=Chain(
        "danger_chain",
        ("assess_safety",),
        "危险链",
    ),
    trigger="amygdala.alert",
)

MAINTENANCE_LOOP: Loop = Loop(
    "maintenance",
    "自维护闭环 — 衰减+清理",
    chain=_MAINTENANCE_CHAIN,
    trigger="heartbeat.tick",
)

DIAGNOSTIC_LOOP: Loop = Loop(
    "diagnostic",
    "诊断闭环 — 走 Stethoscope 体检",
    chain=_DIAGNOSTIC_CHAIN,
    trigger=None,  # 手动触发
)

BUILTIN_LOOPS: tuple[Loop, ...] = (
    CONVERSATION_LOOP,
    TOOL_EXECUTION_LOOP,
    DANGER_RESPONSE_LOOP,
    MAINTENANCE_LOOP,
    DIAGNOSTIC_LOOP,
)


def register_default_loops(
    loop_registry: "LoopRegistry",
    chain_registry: Any,
) -> None:
    """将 5 个默认闭环及其关联 Chain 注册到注册中心。

    对每条内置闭环：
    1. 如果其 Chain 尚未注册，则先注册 Chain
    2. 注册 Loop

    Args:
        loop_registry: 闭环注册中心实例
        chain_registry: 链路注册中心实例（需支持 register/get）
    """
    for lp in BUILTIN_LOOPS:
        if chain_registry.get(lp.chain.name) is None:
            chain_registry.register(lp.chain)
        loop_registry.register(lp)


# -- LoopRegistry ---------------------------------------------------

@dataclass
class LoopRegistry:
    """闭环注册中心 — 管理 Loop 的注册、查询和执行。

    用法::

        registry = LoopRegistry()
        register_default_loops(registry, cat.chain_registry)

        # 查询
        loop = registry.get("conversation")
        all_loops = registry.list_all()

        # 执行
        result = await registry.run(cat, "conversation", message="你好")
    """

    _loops: dict[str, Loop] = field(default_factory=dict, init=False)
    _loops_list: list[Loop] = field(default_factory=list, init=False)

    def register(self, loop: Loop) -> None:
        """注册一条闭环。同名闭环覆盖旧值。

        Args:
            loop: Loop 实例

        Raises:
            TypeError: loop 不是 Loop 实例
        """
        if not isinstance(loop, Loop):
            raise TypeError(
                f"Expected Loop instance, got {type(loop).__name__}",
            )
        if loop.name in self._loops:
            self._loops_list.remove(self._loops[loop.name])
        self._loops[loop.name] = loop
        self._loops_list.append(loop)

    def get(self, name: str) -> Loop | None:
        """按名查找闭环。

        Args:
            name: 闭环名称

        Returns:
            Loop 对象，不存在返回 None
        """
        return self._loops.get(name)

    def list_all(self) -> list[Loop]:
        """返回所有已注册闭环列表（注册顺序）。"""
        return list(self._loops_list)

    async def run(self, cat: Any, name: str, **initial_input: Any) -> dict[str, Any]:
        """执行一个闭环：触发事件 → 跑 chain → 退出事件。

        Args:
            cat: CatBase 实例（需支持 emit/chain_registry.run）
            name: 闭环名称
            **initial_input: 初始输入

        Returns:
            chain 执行结果（dict）

        Raises:
            KeyError: 闭环不存在，或 chain 不存在
        """
        loop = self.get(name)
        if loop is None:
            raise KeyError(f"Loop '{name}' not found in registry")

        # 触发事件
        if loop.trigger:
            await cat.emit(loop.trigger, initial_input)

        # 执行链
        result = await cat.chain_registry.run(
            cat, loop.chain.name, **initial_input,
        )

        # 退出事件
        if loop.exit_event:
            await cat.emit(loop.exit_event, result)

        return result


# -- LoopSequence dataclass (v1.0.4) ----------------------------------

@dataclass(frozen=True)
class LoopSequence:
    """元闭环 — 多个 Loop 的顺序/事件驱动组合。

    组合模型第五层::

        Path → Chain → Loop → LoopSequence

    LoopSequence 将多个已注册的闭环组装为一个更大的执行单元。

    Attributes:
        name: 元闭环唯一名称
        description: 人类可读描述
        loops: 已注册的 ``Loop`` 名称序列
        mode: ``"sequential"`` — 顺序执行，前一步结果传给下一步；
              ``"event_driven"`` — 并发执行，各自监听触发事件
        stop_on_error: ``True`` — 任何 Loop 失败立刻抛异常停止后续；
                       ``False`` — 跳过失败的 Loop 继续执行
    """

    name: str
    description: str = ""
    loops: tuple[str, ...] = ()
    mode: str = "sequential"
    stop_on_error: bool = True

    def __post_init__(self) -> None:
        if self.mode not in ("sequential", "event_driven"):
            raise ValueError(
                f"mode must be 'sequential' or 'event_driven', "
                f"got {self.mode!r}"
            )


# -- 内置 LoopSequence -----------------------------------------------

DAILY_MAINTENANCE_SEQ: LoopSequence = LoopSequence(
    "daily_maintenance",
    "日常维护 — 自维护后体检",
    loops=("maintenance", "diagnostic"),
    mode="sequential",
)

BUILTIN_LOOPSEQS: tuple[LoopSequence, ...] = (
    DAILY_MAINTENANCE_SEQ,
)


# -- LoopSequenceRegistry (v1.0.4) ------------------------------------

@dataclass
class LoopSequenceRegistry:
    """元闭环注册中心 — 管理 LoopSequence 的注册、查询和执行。

    用法::

        registry = LoopSequenceRegistry()
        registry.register(DAILY_MAINTENANCE_SEQ)

        # 执行
        result = await registry.run(cat, "daily_maintenance")
    """

    _seqs: dict[str, LoopSequence] = field(default_factory=dict, init=False)
    _seqs_list: list[LoopSequence] = field(default_factory=list, init=False)

    def register(self, seq: LoopSequence) -> None:
        """注册一条元闭环。同名覆盖旧值。

        Args:
            seq: LoopSequence 实例

        Raises:
            TypeError: seq 不是 LoopSequence 实例
        """
        if not isinstance(seq, LoopSequence):
            raise TypeError(
                f"Expected LoopSequence instance, got {type(seq).__name__}"
            )
        if seq.name in self._seqs:
            self._seqs_list.remove(self._seqs[seq.name])
        self._seqs[seq.name] = seq
        self._seqs_list.append(seq)

    def get(self, name: str) -> LoopSequence | None:
        """按名查找元闭环。

        Args:
            name: 元闭环名称

        Returns:
            LoopSequence 对象，不存在返回 None
        """
        return self._seqs.get(name)

    def list_all(self) -> list[LoopSequence]:
        """返回所有已注册元闭环列表（注册顺序）。"""
        return list(self._seqs_list)

    async def run(
        self, cat: Any, name: str, **initial_input: Any,
    ) -> dict[str, Any]:
        """执行一条元闭环。

        **sequential 模式**：按 ``loops`` 顺序执行，前一步返回值作为下一步
        的 kwargs，最后一步结果返回。

        **event_driven 模式**：所有 Loop 并发执行，各自获得相同的
        ``initial_input``。结果按 Loop 名为 key 收集。

        Args:
            cat: CatBase 实例（需支持 ``cat.loop_registry.run(cat, name, **kw)``）
            name: 元闭环名称
            **initial_input: 初始输入

        Returns:
            最后一步结果（sequential）或 ``{loop_name: result, ...}``
            （event_driven）

        Raises:
            KeyError: 元闭环不存在，或引用的 Loop 不存在
            Exception: 某 Loop 失败且 ``stop_on_error=True``
        """
        import asyncio

        seq = self.get(name)
        if seq is None:
            raise KeyError(f"LoopSequence '{name}' not found in registry")

        if not seq.loops:
            return {"": dict(initial_input)}

        if seq.mode == "sequential":
            return await self._run_sequential(
                cat, seq, **initial_input,
            )
        return await self._run_event_driven(
            cat, seq, **initial_input,
        )

    async def _run_sequential(
        self, cat: Any, seq: LoopSequence, **initial_input: Any,
    ) -> dict[str, Any]:
        """顺序执行 loops，前一步结果传给下一步。"""
        current_input: dict[str, Any] = dict(initial_input)
        last_result: Any = current_input

        for loop_name in seq.loops:
            try:
                last_result = await cat.loop_registry.run(
                    cat, loop_name, **current_input,
                )
                if isinstance(last_result, dict):
                    current_input = last_result
                else:
                    current_input = {"_result": last_result}
            except Exception:
                if seq.stop_on_error:
                    raise
                # stop_on_error=False → 跳过失败继续
                current_input = dict(initial_input)

        if isinstance(last_result, dict):
            return last_result
        return {"_result": last_result}

    async def _run_event_driven(
        self, cat: Any, seq: LoopSequence, **initial_input: Any,
    ) -> dict[str, Any]:
        """并发执行 loops，各自获得相同的 initial_input。"""
        import asyncio

        async def _run_one(loop_name: str) -> tuple[str, Any]:
            try:
                result = await cat.loop_registry.run(
                    cat, loop_name, **initial_input,
                )
                return (loop_name, result)
            except Exception as e:
                if seq.stop_on_error:
                    raise
                return (loop_name, {"_error": str(e)})

        tasks = [asyncio.create_task(_run_one(ln)) for ln in seq.loops]
        results: dict[str, Any] = {}

        if seq.stop_on_error:
            # gather 模式：任一失败即传播异常，其余 task 被取消
            gathered = await asyncio.gather(*tasks)
            for loop_name, result in gathered:
                results[loop_name] = result
        else:
            # 容忍错误：逐个等待，收集全部结果
            for t in asyncio.as_completed(tasks):
                try:
                    loop_name, result = await t
                    results[loop_name] = result
                except Exception as e:
                    # 找到失败的那个 task
                    for i, task in enumerate(tasks):
                        if task.done() and task.exception():
                            results[seq.loops[i]] = {
                                "_error": str(task.exception()),
                            }
                            break

        return results


__all__ = [
    "Loop", "LoopRegistry",
    "CONVERSATION_LOOP", "TOOL_EXECUTION_LOOP",
    "DANGER_RESPONSE_LOOP", "MAINTENANCE_LOOP", "DIAGNOSTIC_LOOP",
    "BUILTIN_LOOPS", "register_default_loops",
    "LoopSequence", "LoopSequenceRegistry",
    "DAILY_MAINTENANCE_SEQ", "BUILTIN_LOOPSEQS",
]
