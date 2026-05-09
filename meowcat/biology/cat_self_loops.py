# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""Default closed loops — framework prefabs for CatSelf.

Extracted from ``biology/cat_self.py`` (v1.3.9 T-05) to keep both files ≤500 lines.

Contains three loops that the ``CatSelf.loop()`` dispatcher returns:
- :class:`DefaultConversationLoop` — conv. turn
- :class:`DefaultTaskLoop` — task execution
- :class:`DefaultLearnLoop` — learning cycle

Usage::

    from meowcat.biology.cat_self_loops import DefaultConversationLoop
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from meowcat.events import SelfEvent
from meowcat.log import MeowLog

_log = MeowLog.get("meowcat.cat_self_loops")


class DefaultConversationLoop:
    """Default conversation closed loop.

    Flow: read self → perceive dialogue → respond → scribble → reflect.

    Fusion trigger: ``on_event("conversation_end")`` by default.

    When ``use_organ_pipeline=True`` (v1.2.20), the loop bridges into
    the physical LoopRegistry layer via ``cat.perceive()``, executing
    actual organ-to-organ signals through the reflex arc.

    **Framework stub note** (v1.2.33): When ``use_organ_pipeline=False``
    (default), the reply is a hardcoded placeholder string.  This is
    intentional — the framework provides *skeleton* loops.  App layers
    should either set ``use_organ_pipeline=True`` or subclass/replace
    this loop to inject a real LLM brain.

    Usage::

        loop = cat.cat_self.loop("conversation")
        response = await loop.run(cat, "帮我查表结构")

        # Bridged mode
        loop = cat.cat_self.loop("conversation", use_organ_pipeline=True)
        response = await loop.run(cat, "帮我查表结构")
    """

    def __init__(
        self,
        fusion_strategy: Callable[[Any], bool] | None = None,
        use_organ_pipeline: bool = False,
    ) -> None:
        self._fusion = fusion_strategy
        self._use_organ_pipeline = use_organ_pipeline

    async def run(self, cat: Any, message: str) -> str:
        """Execute one conversation turn.

        Args:
            cat: CatBase instance (provides perceive + organs).
            message: Incoming message text.

        Returns:
            Response string.
        """
        snap = await cat.cat_self.before_act("conversation")
        cat._current_snapshot = snap
        _log.debug(
            "conversation_loop: snapshot",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )
        _log.info(
            SelfEvent.SNAPSHOT,
            reason="conversation",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )

        # -- Bridge: organ pipeline (v1.2.20) ------------------------
        if self._use_organ_pipeline:
            reply = await self._run_organ_pipeline(cat, message)
        else:
            reply = f"[conversation] received: {message[:100]}"

        if cat.cat_self.scribble_pad:
            cat.cat_self.scribble_pad.scribble({"in": message[:200]})
        await cat.cat_self.after_act(
            "conversation_turn",
            {"msg_len": len(message)},
        )
        _log.info(SelfEvent.REFLECT, reason="conversation")
        if cat.cat_self.pineal_gland:
            from meowcat.biology.fusion_cycle import FusionCycle

            strategy = (
                self._fusion
                if self._fusion is not None
                else FusionCycle.on_event("conversation_end")
            )
            cat.cat_self.pineal_gland.trigger_if(strategy)
        else:
            _log.debug(
                "conversation loop: pineal_gland is None, fusion skipped")
        return reply

    async def _run_organ_pipeline(self, cat: Any, message: str) -> str:
        """Bridge: execute organ pipeline via cat.perceive() / cat.run_loop().

        v1.2.20: When ``use_organ_pipeline=True``, the cognitive loop
        delegates to the physical LoopRegistry layer.  ``cat.perceive()``
        fires the reflex arc; we collect stage events and extract the
        final reply from the pipeline context.

        Falls back to ``cat.run_loop("conversation", message=...)`` if
        ReflexArc is disabled.
        """
        # Try reflex arc first (perceive → reflex → stages → reply)
        try:
            pipeline_events: list[Any] = []
            async for ev in cat.perceive(message):
                pipeline_events.append(ev)
            # Extract reply from pipeline context if available
            if pipeline_events:
                last = pipeline_events[-1]
                if hasattr(last, "reply"):
                    return str(last.reply)
                if isinstance(last, dict) and "reply" in last:
                    return str(last["reply"])
            if pipeline_events:
                return str(pipeline_events[-1])
        except Exception as e:
            _log.debug(
                "organ_pipeline: perceive failed, falling back", error=str(e)[:120])

        # Fallback: use LoopRegistry's conversation loop
        try:
            result = await cat.run_loop("conversation", message=message)
            if isinstance(result, dict):
                return str(result.get("reply", result.get("result", str(result))))
            return str(result)
        except Exception as e:
            _log.warning("organ_pipeline: run_loop also failed",
                         error=str(e)[:120])
            return f"[conversation] received: {message[:100]}"


class DefaultTaskLoop:
    """Default task closed loop.

    Flow: read self → analyse task → decompose → execute → observe →
    scribble → reflect.

    Fusion trigger: ``on_full(50)`` by default.

    When ``use_organ_pipeline=True`` (v1.2.20), the loop bridges into
    the physical LoopRegistry layer via ``cat.run_loop("tool_execution")``,
    executing actual organ-to-organ signals for task decomposition.

    **Framework stub note** (v1.2.33): When ``use_organ_pipeline=False``
    (default), the result is a hardcoded placeholder dict
    ``{"task": ..., "status": "planned"}``.  App layers should either
    set ``use_organ_pipeline=True`` or subclass/replace this loop.

    Usage::

        loop = cat.cat_self.loop("task")
        result = await loop.run(cat, "部署到生产环境")
    """

    def __init__(
        self,
        fusion_strategy: Callable[[Any], bool] | None = None,
        use_organ_pipeline: bool = False,
    ) -> None:
        self._fusion = fusion_strategy
        self._use_organ_pipeline = use_organ_pipeline

    async def run(self, cat: Any, task: str) -> dict[str, Any]:
        """Execute one task.

        Args:
            cat: CatBase instance.
            task: Task description.

        Returns:
            Task result dict.
        """
        snap = await cat.cat_self.before_act("task")
        cat._current_snapshot = snap
        _log.debug(
            "task_loop: snapshot",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )
        _log.info(
            SelfEvent.SNAPSHOT,
            reason="task",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )

        # -- Bridge: organ pipeline (v1.2.20) ------------------------
        if self._use_organ_pipeline:
            result = await self._run_organ_pipeline(cat, task)
        else:
            result = {"task": task, "status": "planned"}

        if cat.cat_self.scribble_pad:
            cat.cat_self.scribble_pad.scribble({"task": task[:200]})
        await cat.cat_self.after_act(
            "task_completed",
            {"task": task[:100], "status": result.get("status")},
        )
        _log.info(SelfEvent.REFLECT, reason="task")
        if cat.cat_self.pineal_gland:
            from meowcat.biology.fusion_cycle import FusionCycle

            strategy = self._fusion if self._fusion is not None else FusionCycle.on_full(
                50)
            cat.cat_self.pineal_gland.trigger_if(strategy)
        else:
            _log.debug("task loop: pineal_gland is None, fusion skipped")
        return result

    async def _run_organ_pipeline(
        self,
        cat: Any,
        task: str,
    ) -> dict[str, Any]:
        """Bridge: execute task via organ pipeline.

        v1.2.20: Delegates to ``cat.run_loop("tool_execution", task=...)``
        for actual organ-to-organ task decomposition.
        """
        try:
            result = await cat.run_loop("tool_execution", task=task)
            if isinstance(result, dict):
                return result
            return {"task": task, "status": "completed", "result": result}
        except Exception as e:
            _log.warning("organ_pipeline: task run_loop failed",
                         error=str(e)[:120])
            return {"task": task, "status": "planned"}


class DefaultLearnLoop:
    """Default learning closed loop.

    Flow: detect blind spot → explore → learn → verify → scribble →
    reflect → write back.

    Fusion trigger: immediate ``trigger()`` when ``fusion_strategy`` is None;
    ``trigger_if(fusion_strategy)`` otherwise.

    When ``use_organ_pipeline=True`` (v1.2.20), the loop bridges into
    the physical LoopRegistry layer via ``cat.run_loop("diagnostic")``
    to run a full diagnostic checkup as part of the learning cycle.

    **Framework stub note** (v1.2.33): When ``use_organ_pipeline=False``
    (default), the result is a hardcoded placeholder dict
    ``{"topic": ..., "learned": True}``.  App layers should either
    set ``use_organ_pipeline=True`` or subclass/replace this loop.

    Usage::

        loop = cat.cat_self.loop("learn")
        result = await loop.run(cat, "Kubernetes 网络模型")
    """

    def __init__(
        self,
        fusion_strategy: Callable[[Any], bool] | None = None,
        use_organ_pipeline: bool = False,
    ) -> None:
        self._fusion = fusion_strategy
        self._use_organ_pipeline = use_organ_pipeline

    async def run(self, cat: Any, topic: str) -> dict[str, Any]:
        """Execute one learning cycle.

        Args:
            cat: CatBase instance.
            topic: Topic to learn about.

        Returns:
            Learning result dict.
        """
        snap = await cat.cat_self.before_act("learn")
        cat._current_snapshot = snap
        _log.debug(
            "learn_loop: snapshot",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )
        _log.info(
            SelfEvent.SNAPSHOT,
            reason="learn",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )

        # -- Bridge: organ pipeline (v1.2.20) ------------------------
        if self._use_organ_pipeline:
            result = await self._run_organ_pipeline(cat, topic)
        else:
            result = {"topic": topic, "learned": True}

        if cat.cat_self.scribble_pad:
            cat.cat_self.scribble_pad.scribble({"learned": topic})
        await cat.cat_self.after_act(
            "learn_completed",
            {"topic": topic},
        )
        _log.info(SelfEvent.REFLECT, reason="learn")
        if cat.cat_self.pineal_gland:
            if self._fusion is not None:
                cat.cat_self.pineal_gland.trigger_if(self._fusion)
            else:
                cat.cat_self.pineal_gland.trigger()
        else:
            _log.debug("learn loop: pineal_gland is None, fusion skipped")
        return result

    async def _run_organ_pipeline(
        self,
        cat: Any,
        topic: str,
    ) -> dict[str, Any]:
        """Bridge: execute learning via organ pipeline.

        v1.2.20: Runs ``cat.run_loop("diagnostic")`` to perform a full
        organ checkup, then records the diagnostic results as learning
        output.
        """
        try:
            diag = await cat.run_loop("diagnostic", topic=topic)
            return {
                "topic": topic,
                "learned": True,
                "diagnostic": diag if isinstance(diag, dict) else {"result": diag},
            }
        except Exception as e:
            _log.warning("organ_pipeline: learn run_loop failed",
                         error=str(e)[:120])
            return {"topic": topic, "learned": True}


__all__ = [
    "DefaultConversationLoop",
    "DefaultTaskLoop",
    "DefaultLearnLoop",
]
