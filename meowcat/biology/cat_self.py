# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""CatSelf — unified self model + three default closed loops.

v1.2.0: The single entry/exit point for all organ read/write paths.
Every organ's path converges at CatSelf = ultimate start + ultimate end.

Usage::

    from meowcat.biology.cat_self import CatSelf, SelfSnapshot

    cat_self = CatSelf(
        personality={"tone": "friendly", "language": "zh"},
        cortex=cortex,
        skills=skill_registry,
        scribble_pad=pad,
    )

    # Before action: freeze snapshot
    snap = cat_self.before_act("conversation")

    # After action: scribble + reflect
    cat_self.after_act("answered user question", {"topic": "SQL"})

    # Default loops (framework prefabs)
    loop = cat_self.loop("conversation")
    response = await loop.run(cat, "帮我查表结构")
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from meowcat.biology.cat_self_loops import (
    DefaultConversationLoop,
    DefaultLearnLoop,
    DefaultTaskLoop,
)
from meowcat.events import SelfEvent
from meowcat.log import MeowLog
from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.biology.cortex import Cortex
    from meowcat.biology.metacognition import Metacognition
    from meowcat.biology.pineal_gland import PinealGland
    from meowcat.biology.scribble_pad import ScribblePad

_log = MeowLog.get("meowcat.cat_self")

_UNSET_LOOP = object()  # sentinel for CatSelf.loop() fusion_strategy


@dataclass
class SelfSnapshot:
    """Frozen self-image captured before an action.

    Injected into organ contexts so every organ sees the same
    consistent self-state during a single action.

    Attributes:
        personality: Copy of current personality dict.
        beliefs: Cortex L2 beliefs as (key, value, confidence, challengeable).
        skill_names: Names of registered skills.
        reflex_names: Names of registered reflexes.
        capable_domains: Metacognition domains the cat knows it can handle.
        incapable_domains: Metacognition domains the cat knows it cannot handle.
        scribble_count: Current scribble pad entry count.
    """

    personality: dict[str, Any] = field(default_factory=dict)
    beliefs: list[tuple[str, str, float, bool]] = field(default_factory=list)
    skill_names: list[str] = field(default_factory=list)
    reflex_names: list[str] = field(default_factory=list)
    capable_domains: list[str] = field(default_factory=list)
    incapable_domains: list[str] = field(default_factory=list)
    scribble_count: int = 0


class CatSelf(Pluggable):
    """Unified self — all organs read from here, all growth writes back here.

    Framework layer responsibilities:
    - ``before_act()`` / ``after_act()`` loop nodes
    - ``loop()`` dispatcher for three default closed loops
    - Plugin slots for customising any link in the chain

    App layer responsibilities:
    - Wire organs into CatSelf (personality, cortex, skills, reflexes, etc.)
    - Call ``before_act()`` / ``after_act()`` at action boundaries
    - Trigger PinealGland fusion when appropriate

    Plugin slots:
        ``"before_act"`` — pre-action hook, can override snapshot
        ``"after_act"`` — post-action hook, can override write-back

    Args:
        personality: Initial personality dict (tone, language, etc.).
        cortex: Cortex instance for worldview/beliefs access.
        worldview: Separate worldview instance (defaults to cortex).
        skills: SkillRegistry for capability tracking.
        reflexes: ReflexRegistry for reflex awareness.
        scribble_pad: ScribblePad for fragment accumulation.
        pineal_gland: PinealGland for insight fusion.
        metacognition: Metacognition for self-awareness.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "before_act": {"in": "reason: str", "out": "SelfSnapshot | None"},
        "after_act": {"in": "summary: str, impact: dict", "out": "None"},
    }

    __slots__ = (
        "_personality",
        "_cortex",
        "_worldview",
        "_skills",
        "_reflexes",
        "_scribble_pad",
        "_pineal_gland",
        "_metacognition",
    )

    def __init__(
        self,
        *,
        personality: dict[str, Any] | None = None,
        cortex: Cortex | None = None,
        worldview: Cortex | None = None,
        skills: Any | None = None,
        reflexes: Any | None = None,
        scribble_pad: ScribblePad | None = None,
        pineal_gland: PinealGland | None = None,
        metacognition: Metacognition | None = None,
    ) -> None:
        super().__init__()
        self._personality = personality or {}
        self._cortex = cortex
        self._worldview = worldview or cortex
        self._skills = skills
        self._reflexes = reflexes
        self._scribble_pad = scribble_pad
        self._pineal_gland = pineal_gland
        self._metacognition = metacognition

    # -- Properties -------------------------------------------------

    @property
    def personality(self) -> dict[str, Any]:
        """Current personality traits (mutable)."""
        return self._personality

    @personality.setter
    def personality(self, value: dict[str, Any]) -> None:
        self._personality = value

    @property
    def cortex(self) -> Any:
        """Cortex instance for worldview/beliefs access."""
        return self._cortex

    @property
    def worldview(self) -> Any:
        """Worldview instance (defaults to cortex if not set separately)."""
        return self._worldview

    @property
    def skills(self) -> Any:
        """SkillRegistry for capability tracking."""
        return self._skills

    @property
    def reflexes(self) -> Any:
        """ReflexRegistry for reflex awareness."""
        return self._reflexes

    @property
    def scribble_pad(self) -> ScribblePad | None:
        """ScribblePad for fragment accumulation."""
        return self._scribble_pad

    @property
    def pineal_gland(self) -> PinealGland | None:
        """PinealGland for insight fusion."""
        return self._pineal_gland

    @property
    def metacognition(self) -> Metacognition | None:
        """Metacognition for self-awareness."""
        return self._metacognition

    # -- Loop nodes -------------------------------------------------

    async def before_act(self, reason: str) -> SelfSnapshot:
        """Freeze current self snapshot. Call before every action.

        Plugin ``"before_act"`` can return a custom :class:`SelfSnapshot`
        to override the default. This allows app-layer to inject custom
        context into the snapshot.

        Args:
            reason: Why the action is starting (e.g. "conversation", "task").

        Returns:
            Frozen self snapshot for consistent organ context.
        """
        async for _name, r in self._run_plugs("before_act", reason):
            if isinstance(r, SelfSnapshot):
                return r
        return self._build_snapshot()

    async def after_act(self, summary: str, impact: dict[str, Any] | None = None) -> None:
        """Write back after action: scribble summary + log.

        Plugin ``"after_act"`` can override or extend the default.
        App layer should also trigger PinealGland fusion when
        appropriate (e.g. via ``FusionCycle`` conditions).

        Args:
            summary: One-line summary of what happened.
            impact: Structured impact data for downstream processing.
        """
        impact = impact or {}
        async for _name, _r in self._run_plugs("after_act", summary, impact):
            pass

        if self._scribble_pad is not None:
            self._scribble_pad.scribble(
                {
                    "summary": summary,
                    "impact": impact,
                }
            )
        else:
            _log.warning(
                "after_act: scribble_pad is None, growth write-back disabled")
        _log.debug("after_act", summary=summary[:80])
        _log.info(SelfEvent.REFLECT,
                  summary=summary[:80], impact_keys=list(impact.keys()))

    # -- Default loops (framework prefabs) --------------------------

    def loop(
        self,
        name: Literal["conversation", "task", "learn"],
        *,
        fusion_strategy: Callable[[Any], bool] | None = _UNSET_LOOP,  # type: ignore[assignment]
        use_organ_pipeline: bool = False,
    ) -> Any:
        """Pick a default closed loop by name.

        Returns a loop instance; caller calls ``await loop.run(cat, ...)``.

        Args:
            name: One of ``"conversation"``, ``"task"``, ``"learn"``.
            fusion_strategy: Optional FusionCycle predicate. When None,
                conversation=tick-event, task=on-full-50, learn=immediate.
                Pass a Callable to override the default fusion trigger.
            use_organ_pipeline: When True, the loop bridges into
                LoopRegistry (physical layer) via ``cat.perceive()`` or
                ``cat.run_loop()``, executing actual organ-to-organ signals
                instead of just self read/write. Default False (v1.2.20).

        Returns:
            Loop instance with a ``run(cat, ...)`` async method.
        """
        _loops: dict[str, type] = {
            "conversation": DefaultConversationLoop,
            "task": DefaultTaskLoop,
            "learn": DefaultLearnLoop,
        }
        if name not in _loops:
            raise ValueError(
                f"Unknown loop: {name!r}. Choose from: {list(_loops)}",
            )
        kwargs: dict[str, Any] = {}
        if fusion_strategy is not _UNSET_LOOP:
            kwargs["fusion_strategy"] = fusion_strategy
        kwargs["use_organ_pipeline"] = use_organ_pipeline
        return _loops[name](**kwargs)

    # -- Internal ---------------------------------------------------

    def _build_snapshot(self) -> SelfSnapshot:
        """Build default self snapshot from all wired organs."""
        snap = SelfSnapshot(personality=dict(self._personality))

        if self._cortex is not None:
            try:
                snap.beliefs = self._cortex.get_beliefs()
            except Exception as e:
                _log.warning(
                    "_build_snapshot: cortex.get_beliefs() failed", error=str(e)[:120])

        if self._skills is not None:
            try:
                snap.skill_names = [s.name for s in self._skills.list_all()]
            except Exception as e:
                _log.warning(
                    "_build_snapshot: skills.list_all() failed", error=str(e)[:120])

        if self._reflexes is not None:
            try:
                snap.reflex_names = [r.name for r in self._reflexes.all()]
            except Exception as e:
                _log.warning(
                    "_build_snapshot: reflexes access failed", error=str(e)[:120])

        if self._metacognition is not None:
            try:
                snap.capable_domains = self._metacognition.capable_domains()
                snap.incapable_domains = self._metacognition.incapable_domains()
            except Exception as e:
                _log.warning(
                    "_build_snapshot: metacognition access failed", error=str(e)[:120])

        if self._scribble_pad is not None:
            snap.scribble_count = self._scribble_pad.count()

        return snap

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot of CatSelf wiring."""
        return {
            "has_cortex": self._cortex is not None,
            "has_worldview": self._worldview is not None,
            "has_skills": self._skills is not None,
            "has_reflexes": self._reflexes is not None,
            "has_scribble_pad": self._scribble_pad is not None,
            "has_pineal_gland": self._pineal_gland is not None,
            "has_metacognition": self._metacognition is not None,
            "personality_keys": list(self._personality.keys()),
            "plugs": self.list_plugs(),
        }

    @classmethod
    def with_defaults(
        cls,
        *,
        cortex: Cortex | None = None,
        scribble_pad: ScribblePad | None = None,
        pineal_gland: PinealGland | None = None,
        metacognition: Metacognition | None = None,
        personality: dict[str, Any] | None = None,
    ) -> CatSelf:
        """Create a CatSelf with common defaults wired together.

        Convenience constructor that ensures scribble_pad and pineal_gland
        are present so the closed-loop write-back path works out of the box.

        Args:
            cortex: Cortex instance for worldview/beliefs.
            scribble_pad: ScribblePad for fragment accumulation.
            pineal_gland: PinealGland for insight fusion.
            metacognition: Metacognition for self-awareness.
            personality: Initial personality dict.

        Returns:
            A CatSelf instance with all provided organs wired.
        """
        return cls(
            personality=personality,
            cortex=cortex,
            worldview=cortex,
            scribble_pad=scribble_pad,
            pineal_gland=pineal_gland,
            metacognition=metacognition,
        )


__all__ = [
    "CatSelf",
    "SelfSnapshot",
    "DefaultConversationLoop",
    "DefaultTaskLoop",
    "DefaultLearnLoop",
]
