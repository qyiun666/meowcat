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

from meowcat.biology.cat_self_loops import ReflectionLoop
from meowcat.events import SelfEvent
from meowcat.log import MeowLog
from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.biology.cortex import Cortex
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
        default_confidence: Default confidence for recorded capabilities (v2.0: merged from Metacognition).
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
        "_capabilities",
        "_default_confidence",
        "_persona_backup",       # v2.5.0: pre-persona state
        "_persona_capable",      # v2.5.0: persona-level capable override
        "_persona_incapable",    # v2.5.0: persona-level incapable override
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
        default_confidence: float = 0.8,
    ) -> None:
        super().__init__()
        self._personality = personality or {}
        self._cortex = cortex
        self._worldview = worldview or cortex
        self._skills = skills
        self._reflexes = reflexes
        self._scribble_pad = scribble_pad
        self._pineal_gland = pineal_gland
        self._default_confidence = default_confidence
        self._capabilities: dict[str, dict[str, Any]] = {}
        # v2.5.0: persona mask state
        self._persona_backup: dict[str, Any] | None = None
        self._persona_capable: list[str] | None = None
        self._persona_incapable: list[str] | None = None

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

    # -- Metacognition (v2.0: merged from metacognition.py) ----------

    def record_capability(
        self,
        domain: str,
        capable: bool,
        evidence: str = "",
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Record a known capability (or incapability)."""
        conf = confidence if confidence is not None else self._default_confidence
        record = {
            "domain": domain,
            "capable": capable,
            "confidence": min(max(conf, 0.0), 1.0),
            "evidence": evidence[:200],
        }
        self._capabilities[domain] = record
        return dict(record)

    def self_assess(self, domain: str) -> dict[str, Any]:
        """Assess whether the cat is capable in a given domain.

        Known domains return ``{capable, confidence, evidence}``.
        Unknown domains return ``{capable: None, confidence: 0.0,
        suggestion: "explore"}``.
        """
        cap = self._capabilities.get(domain)
        if cap is not None:
            return {
                "domain": domain,
                "capable": cap["capable"],
                "confidence": cap["confidence"],
                "evidence": cap["evidence"],
            }
        return {
            "domain": domain,
            "capable": None,
            "confidence": 0.0,
            "evidence": "",
            "suggestion": "explore",
        }

    def list_capabilities(self) -> list[dict[str, Any]]:
        """List all known capability records, sorted by confidence."""
        return sorted(
            [dict(v) for v in self._capabilities.values()],
            key=lambda x: -x["confidence"],
        )

    def known_domains(self) -> list[str]:
        """Return list of all known domain names."""
        return list(self._capabilities.keys())

    def capable_domains(self) -> list[str]:
        """Return domains where the cat believes itself capable."""
        return [d for d, r in self._capabilities.items() if r["capable"] is True]

    def incapable_domains(self) -> list[str]:
        """Return domains where the cat knows it's incapable."""
        return [d for d, r in self._capabilities.items() if r["capable"] is False]

    # -- Persona (v2.5.0) --------------------------------------------

    def apply_persona(self, persona: Any) -> None:
        """Apply a persona mask to CatSelf.

        Saves the current personality and capabilities as a backup so
        ``remove_persona()`` can restore them later.

        Args:
            persona: :class:`~meowcat.persona.Persona` instance.
        """
        self._persona_backup = {
            "personality": dict(self._personality),
        }
        self._persona_capable = list(
            persona.capable) if persona.capable else None
        self._persona_incapable = list(
            persona.incapable) if persona.incapable else None

        # Overwrite personality with persona's traits
        if persona.personality:
            for k, v in persona.personality.items():
                self._personality[k] = v

    def remove_persona(self) -> None:
        """Remove the current persona mask, restoring the pre-persona state."""
        if self._persona_backup is not None:
            self._personality = self._persona_backup.get("personality", {})
            self._persona_backup = None
        self._persona_capable = None
        self._persona_incapable = None

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
        appropriate (e.g. via ``PinealGland.on_full()`` conditions).

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
        fusion_trigger: str | Callable[[Any],
                                       bool] | None | object = _UNSET_LOOP,
        use_organ_pipeline: bool = False,
    ) -> Any:
        """Pick a default closed loop by name (v2.0: unified ReflectionLoop).

        Returns a loop instance; caller calls ``await loop.run(cat, ...)``.

        Args:
            name: One of ``"conversation"``, ``"task"``, ``"learn"``.
            fusion_trigger: When to trigger PinealGland fusion.
                - ``None`` / ``"auto"``: use mode-default trigger
                - ``"event"``: trigger on conversation_end
                - ``"full:50"``: trigger when ScribblePad has 50+ entries
                - ``"immediate"``: trigger immediately
                - Callable: explicit condition
            use_organ_pipeline: When True, bridge into LoopRegistry (v1.2.20).

        Returns:
            ReflectionLoop instance with a ``run(cat, ...)`` async method.
        """
        if name not in ("conversation", "task", "learn"):
            raise ValueError(
                f"Unknown loop: {name!r}. Choose from: conversation, task, learn",
            )
        kwargs: dict[str, Any] = {"mode": name}
        if fusion_trigger is not _UNSET_LOOP:
            kwargs["fusion_trigger"] = fusion_trigger
        kwargs["use_organ_pipeline"] = use_organ_pipeline
        return ReflectionLoop(**kwargs)

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

        # v2.5.0: persona-capable overrides metacognition
        if self._persona_capable is not None:
            snap.capable_domains = self._persona_capable
        else:
            snap.capable_domains = self.capable_domains()
        if self._persona_incapable is not None:
            snap.incapable_domains = self._persona_incapable
        else:
            snap.incapable_domains = self.incapable_domains()

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
            "known_domains": len(self._capabilities),
            "capable_count": len(self.capable_domains()),
            "incapable_count": len(self.incapable_domains()),
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
        personality: dict[str, Any] | None = None,
        default_confidence: float = 0.8,
    ) -> CatSelf:
        """Create a CatSelf with common defaults wired together.

        Convenience constructor that ensures scribble_pad and pineal_gland
        are present so the closed-loop write-back path works out of the box.

        Args:
            cortex: Cortex instance for worldview/beliefs.
            scribble_pad: ScribblePad for fragment accumulation.
            pineal_gland: PinealGland for insight fusion.
            personality: Initial personality dict.
            default_confidence: Default confidence for recorded capabilities.

        Returns:
            A CatSelf instance with all provided organs wired.
        """
        return cls(
            personality=personality,
            cortex=cortex,
            worldview=cortex,
            scribble_pad=scribble_pad,
            pineal_gland=pineal_gland,
            default_confidence=default_confidence,
        )


__all__ = [
    "CatSelf",
    "SelfSnapshot",
    "ReflectionLoop",
]
