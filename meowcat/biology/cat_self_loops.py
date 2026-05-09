# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""ReflectionLoop — unified closed loop for CatSelf (v2.0: 3 classes → 1).

Replaces ``DefaultConversationLoop``, ``DefaultTaskLoop``, and
``DefaultLearnLoop`` with a single ``ReflectionLoop`` class parameterised
by ``mode`` and ``fusion_trigger``.

Usage::

    from meowcat.biology.cat_self_loops import ReflectionLoop

    loop = ReflectionLoop(mode="conversation", fusion_trigger="event")
    reply = await loop.run(cat, "你好")

    loop = ReflectionLoop(mode="task", fusion_trigger="full:50")
    result = await loop.run(cat, "部署到生产环境")

    loop = ReflectionLoop(mode="learn", fusion_trigger="immediate")
    result = await loop.run(cat, "Kubernetes 网络模型")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from meowcat.biology.pineal_gland import PinealGland
from meowcat.events import SelfEvent
from meowcat.log import MeowLog

_log = MeowLog.get("meowcat.cat_self_loops")

LoopMode = Literal["conversation", "task", "learn"]
FusionTrigger = Literal["auto", "event", "full:50", "immediate"]

_DEFAULT_TRIGGERS: dict[LoopMode, str] = {
    "conversation": "event",
    "task": "full:50",
    "learn": "immediate",
}


class ReflectionLoop:
    """Unified closed loop — replaces 3 default loop classes.

    Flow: read self → execute (perceive / task / diagnostic) → scribble →
    reflect → fusion.

    Args:
        mode: ``"conversation"`` / ``"task"`` / ``"learn"``.
        fusion_trigger: When to trigger PinealGland fusion.
            - ``"auto"``: use mode-default trigger (event / full:50 / immediate)
            - ``"event"``: trigger on ``conversation_end`` event
            - ``"full:50"``: trigger when ScribblePad has 50+ entries
            - ``"immediate"``: trigger immediately after action
            - Callable: explicit ``Callable[[ScribblePad], bool]`` condition
        use_organ_pipeline: When True, bridges into LoopRegistry via
            ``cat.perceive()`` or ``cat.run_loop()``. Default False.

    Usage::

        loop = cat.cat_self.loop("conversation")
        response = await loop.run(cat, "帮我查表结构")
    """

    def __init__(
        self,
        mode: LoopMode,
        fusion_trigger: str
        | Callable[[Any], bool]
        | None = None,
        use_organ_pipeline: bool = False,
    ) -> None:
        if mode not in _DEFAULT_TRIGGERS:
            raise ValueError(
                f"Unknown mode: {mode!r}. Choose from: {list(_DEFAULT_TRIGGERS)}"
            )
        self._mode = mode
        self._use_organ_pipeline = use_organ_pipeline

        # Resolve fusion trigger
        if fusion_trigger is None or fusion_trigger == "auto":
            trigger_str = _DEFAULT_TRIGGERS[mode]
        elif callable(fusion_trigger):
            self._fusion = fusion_trigger
            return
        elif isinstance(fusion_trigger, str):
            trigger_str = fusion_trigger
        else:
            raise ValueError(
                f"Invalid fusion_trigger: {fusion_trigger!r}"
            )

        # Convert string trigger to callable
        self._fusion = _resolve_trigger(trigger_str)

    async def run(self, cat: Any, input: str) -> Any:
        """Execute one loop iteration.

        Args:
            cat: CatBase instance.
            input: Incoming message / task / topic.

        Returns:
            Response string (conversation) or result dict (task / learn).
        """
        snap = await cat.cat_self.before_act(self._mode)
        cat._current_snapshot = snap
        _log.debug(
            f"{self._mode}_loop: snapshot",
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )
        _log.info(
            SelfEvent.SNAPSHOT,
            reason=self._mode,
            beliefs=len(snap.beliefs),
            skills=len(snap.skill_names),
            scribbles=snap.scribble_count,
        )

        # Execute mode-specific pipeline
        if self._use_organ_pipeline:
            result = await self._run_organ_pipeline(cat, input)
        else:
            result = self._stub_result(input)

        # Scribble
        if cat.cat_self.scribble_pad:
            cat.cat_self.scribble_pad.scribble(
                {self._mode: input[:200]}
            )

        # After-act
        if self._mode == "conversation":
            await cat.cat_self.after_act(
                "conversation_turn", {"msg_len": len(input)}
            )
        elif self._mode == "task":
            await cat.cat_self.after_act(
                "task_completed",
                {"task": input[:100], "status": result.get(
                    "status") if isinstance(result, dict) else None},
            )
        else:
            await cat.cat_self.after_act(
                "learn_completed", {"topic": input}
            )

        _log.info(SelfEvent.REFLECT, reason=self._mode)

        # Fusion
        if cat.cat_self.pineal_gland:
            cat.cat_self.pineal_gland.trigger_if(self._fusion)
        else:
            _log.debug(
                f"{self._mode} loop: pineal_gland is None, fusion skipped"
            )

        return result

    def _stub_result(self, input: str) -> Any:
        """Placeholder result when organ pipeline is disabled."""
        if self._mode == "conversation":
            return f"[conversation] received: {input[:100]}"
        elif self._mode == "task":
            return {"task": input, "status": "planned"}
        else:
            return {"topic": input, "learned": True}

    async def _run_organ_pipeline(self, cat: Any, input: str) -> Any:
        """Bridge: execute via organ pipeline.

        v1.2.20: Delegates to LoopRegistry layer via cat.perceive()
        or cat.run_loop().
        """
        if self._mode == "conversation":
            return await self._pipeline_conversation(cat, input)
        elif self._mode == "task":
            return await self._pipeline_task(cat, input)
        else:
            return await self._pipeline_learn(cat, input)

    async def _pipeline_conversation(self, cat: Any, message: str) -> str:
        try:
            pipeline_events: list[Any] = []
            async for ev in cat.perceive(message):
                pipeline_events.append(ev)
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
                "organ_pipeline: perceive failed, falling back",
                error=str(e)[:120],
            )
        try:
            result = await cat.run_loop("conversation", message=message)
            if isinstance(result, dict):
                return str(result.get("reply", result.get("result", str(result))))
            return str(result)
        except Exception as e:
            _log.warning(
                "organ_pipeline: run_loop also failed",
                error=str(e)[:120],
            )
            return f"[conversation] received: {message[:100]}"

    async def _pipeline_task(self, cat: Any, task: str) -> dict[str, Any]:
        try:
            result = await cat.run_loop("tool_execution", task=task)
            if isinstance(result, dict):
                return result
            return {"task": task, "status": "completed", "result": result}
        except Exception as e:
            _log.warning(
                "organ_pipeline: task run_loop failed",
                error=str(e)[:120],
            )
            return {"task": task, "status": "planned"}

    async def _pipeline_learn(self, cat: Any, topic: str) -> dict[str, Any]:
        try:
            diag = await cat.run_loop("diagnostic", topic=topic)
            return {
                "topic": topic,
                "learned": True,
                "diagnostic": diag if isinstance(diag, dict) else {"result": diag},
            }
        except Exception as e:
            _log.warning(
                "organ_pipeline: learn run_loop failed",
                error=str(e)[:120],
            )
            return {"topic": topic, "learned": True}


def _resolve_trigger(trigger_str: str) -> Callable[[Any], bool]:
    """Convert string trigger name to a callable condition."""
    if trigger_str == "event":
        return PinealGland.on_event("conversation_end")
    elif trigger_str == "full:50":
        return PinealGland.on_full(50)
    elif trigger_str == "immediate":
        def _always(_pad: Any) -> bool:
            return True
        _always.__name__ = "immediate"  # type: ignore[attr-defined]
        return _always
    else:
        raise ValueError(f"Unknown trigger: {trigger_str!r}")


__all__ = ["ReflectionLoop"]
