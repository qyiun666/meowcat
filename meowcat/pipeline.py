# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Pipeline executor — skeleton for chaining Stages.

Stage Protocol definition: :mod:`meowcat.protocols` (``StageProtocol``).
StageEvent / PipelineContext data shapes: :mod:`meowcat.models`.

This module only provides :class:`Pipeline` executor: drives Stages sequentially,
stops on ``short_circuit`` event. Not responsible for Stage implementation.
"""


from __future__ import annotations

from typing import Any, AsyncIterator

from meowcat.protocols import StageProtocol


class Pipeline:
    """Execute Stage list sequentially with short-circuit stop.

    Stages yield events via ``async def run(ctx) -> AsyncIterator``.
    When any Stage yields ``kind == "short_circuit"``, Pipeline stops calling
    subsequent Stages and sets ``ctx.short_circuited = True`` / ``ctx.final_reply = ev.reply``
    (if ctx supports assigning these two fields).
    """

    def __init__(self, stages: list[StageProtocol]) -> None:
        self.stages: list[StageProtocol] = list(stages)
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    async def execute(self, ctx: Any) -> AsyncIterator[Any]:
        """Drive all Stages in order, yielding all events."""
        for stage in self.stages:
            async for ev in stage.run(ctx):
                yield ev
                if getattr(ev, "kind", None) == "short_circuit":
                    self._mark_short_circuit(ctx, ev)
                    return

    @staticmethod
    def _mark_short_circuit(ctx: Any, ev: Any) -> None:
        """Write short-circuit state back to ctx. ctx can be a dataclass or pydantic BaseModel;
        silently skips if fields are missing — does not decide for the business layer."""
        try:
            ctx.short_circuited = True
        except AttributeError:
            pass
        try:
            ctx.final_reply = getattr(ev, "reply", None)
        except AttributeError:
            pass


__all__ = ["Pipeline"]

