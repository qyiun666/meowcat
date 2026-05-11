# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Persona — mask system for one-click identity switching.

A Persona is a loadable, switchable, serializable identity preset that bundles
six layers of a distilled personality: character, worldview, self-awareness,
domain knowledge, tools, and behavior patterns.

Usage::

    from meowcat.persona import Persona, Belief, KnowledgeSeed, ConnectionSpec, ReflexSpec

    persona = Persona(
        name="musk",
        personality={"tone": "visionary", "language": "en+zh"},
        beliefs=[
            Belief(key="first_principles", value="reason from basic facts", confidence=0.95),
        ],
        capable=["engineering", "physics"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.tools.tool import ToolSpec


@dataclass
class Belief:
    """A conviction the persona holds.

    Maps to ``Cortex.promote_to_belief(key, value, confidence, challengeable)``.
    """

    key: str
    value: str
    confidence: float = 0.8
    challengeable: bool = True

    def __post_init__(self) -> None:
        self.confidence = min(max(self.confidence, 0.0), 1.0)


@dataclass
class ConnectionSpec:
    """Connection between two knowledge entities.

    Maps to ``Hippocampus.connect(from_id, to_id, relation, strength)``.
    """

    to: str
    relation: str
    strength: float = 1.0


@dataclass
class KnowledgeSeed:
    """Initial entity for Hippocampus knowledge graph.

    Maps to ``Hippocampus.add_entity(entity)`` + ``Hippocampus.connect()``.
    """

    entity_type: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    connections: list[ConnectionSpec] = field(default_factory=list)


@dataclass
class ReflexSpec:
    """Predefined reflex arc for the persona.

    Maps to ``ReflexRegistry.register(reflex)``.
    """

    name: str
    trigger: str
    from_organ: tuple[str, str]  # (category, name)
    to_organ: tuple[str, str]
    method: str


@dataclass
class Persona:
    """A loadable identity preset — the mask a cat can wear.

    Bundles personality, beliefs, capabilities, knowledge seeds,
    tools, and reflex arcs into a single switchable package.

    Usage::

        musk = Persona(
            name="musk",
            version="0.1.0",
            description="Elon Musk thinking style",
            personality={"tone": "visionary", "language": "en+zh"},
            beliefs=[Belief(key="first_principles", value="...", confidence=0.95)],
            capable=["engineering", "physics"],
        )

        await colony.register_persona(musk)
        await cat.wear_persona("musk")
    """

    name: str
    version: str = "0.1.0"
    description: str = ""
    # -- CatSelf mapping --
    personality: dict[str, Any] = field(default_factory=dict)
    beliefs: list[Belief] = field(default_factory=list)
    capable: list[str] = field(default_factory=list)
    incapable: list[str] = field(default_factory=list)
    # -- Knowledge seeds --
    knowledge_seeds: list[KnowledgeSeed] = field(default_factory=list)
    # -- Tools --
    tools: list[ToolSpec] = field(default_factory=list)
    # -- Reflex arcs --
    reflex_specs: list[ReflexSpec] = field(default_factory=list)
    # -- Optional sample dialogues --
    sample_dialogues: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for colony namespace storage.

        Nested dataclasses (Belief, KnowledgeSeed, etc.) are recursively
        converted.  ``tools`` (ToolSpec objects) are converted to dicts
        via ``dataclasses.asdict``.

        Returns:
            Dict representation suitable for ``ns_set("personas", name, ...)``.
        """
        from dataclasses import asdict

        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "personality": dict(self.personality),
            "beliefs": [asdict(b) for b in self.beliefs],
            "capable": list(self.capable),
            "incapable": list(self.incapable),
            "knowledge_seeds": [asdict(k) for k in self.knowledge_seeds],
            "tools": [asdict(t) for t in self.tools],
            "reflex_specs": [asdict(r) for r in self.reflex_specs],
            "sample_dialogues": list(self.sample_dialogues),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Persona:
        """Deserialize from a dict (as stored in colony namespace).

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Persona instance.
        """
        beliefs = [Belief(**b) for b in data.get("beliefs", [])]
        capable = data.get("capable", [])
        if isinstance(capable, list):
            capable = [str(c) for c in capable]
        incapable = data.get("incapable", [])
        if isinstance(incapable, list):
            incapable = [str(c) for c in incapable]

        knowledge_seeds: list[KnowledgeSeed] = []
        for kd in data.get("knowledge_seeds", []):
            conns = [ConnectionSpec(**c) for c in kd.pop("connections", [])]
            knowledge_seeds.append(KnowledgeSeed(**kd, connections=conns))

        reflex_specs = [ReflexSpec(**r) for r in data.get("reflex_specs", [])]

        # Tools: ToolSpec objects need special handling since category is a str
        tools_data = data.get("tools", [])
        tools: list[Any] = []
        if tools_data:
            from meowcat.tools.tool import RiskLevel, ToolSpec

            risk_map = {
                "low": RiskLevel.LOW,
                "medium": RiskLevel.MEDIUM,
                "high": RiskLevel.HIGH,
            }
            for td in tools_data:
                risk_str = td.pop("risk", "medium")
                risk = risk_map.get(risk_str, RiskLevel.MEDIUM) if isinstance(
                    risk_str, str) else risk_str
                tools.append(ToolSpec(**td, risk=risk))

        sample = data.get("sample_dialogues", [])
        sample_dialogues: list[tuple[str, str]] = [
            tuple(item) if isinstance(item, list) else item
            for item in sample
        ]

        return cls(
            name=data["name"],
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            personality=data.get("personality", {}),
            beliefs=beliefs,
            capable=capable,
            incapable=incapable,
            knowledge_seeds=knowledge_seeds,
            tools=tools,
            reflex_specs=reflex_specs,
            sample_dialogues=sample_dialogues,
        )


__all__ = [
    "Persona",
    "Belief",
    "KnowledgeSeed",
    "ConnectionSpec",
    "ReflexSpec",
]
