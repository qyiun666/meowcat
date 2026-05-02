"""meowcat Pipeline 执行器 — 串 Stage 的骨架。

Stage 的 Protocol 定义见 :mod:`meowcat.protocols` （``StageProtocol``），
StageEvent / PipelineContext 的数据形状见 :mod:`meowcat.models`。

本模块只提供 :class:`Pipeline` 执行器：按顺序驱动 Stage、遇到 ``short_circuit``
事件即停止。不负责 Stage 具体实现。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from meowcat.protocols import StageProtocol


class Pipeline:
    """顺序执行 Stage 清单，短路中止。

    Stage 通过 ``async def run(ctx) -> AsyncIterator`` 产出事件。
    任一 Stage 产出 ``kind == "short_circuit"`` 事件后，Pipeline 停止调用
    后续 Stage，并把 ``ctx.short_circuited = True`` / ``ctx.final_reply = ev.reply``
    （若 ctx 支持赋值这两个字段）。
    """

    def __init__(self, stages: list[StageProtocol]) -> None:
        self.stages: list[StageProtocol] = list(stages)

    async def execute(self, ctx: Any) -> AsyncIterator[Any]:
        """按顺序驱动所有 Stage，yield 所有事件。"""
        for stage in self.stages:
            async for ev in stage.run(ctx):
                yield ev
                if getattr(ev, "kind", None) == "short_circuit":
                    self._mark_short_circuit(ctx, ev)
                    return

    @staticmethod
    def _mark_short_circuit(ctx: Any, ev: Any) -> None:
        """把短路状态回写到 ctx。ctx 可以是 dataclass 或 pydantic BaseModel，
        没有对应字段时静默跳过，不替业务决定。"""
        try:
            ctx.short_circuited = True
        except (AttributeError, ValueError):
            pass
        try:
            ctx.final_reply = getattr(ev, "reply", None)
        except (AttributeError, ValueError):
            pass


__all__ = ["Pipeline"]
