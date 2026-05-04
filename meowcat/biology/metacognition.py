"""Metacognition — L3 worldview: cat's awareness of its own capabilities.

v1.1.27: The metacognition layer enables a cat to assess what it can
and cannot do, forming the basis for auto-delegation and skill-seeking
behaviour.

Usage::

    from meowcat.biology.metacognition import Metacognition

    mc = Metacognition()

    # Record what the cat knows it can/cannot do
    mc.record_capability("frontend", capable=False, evidence="no JS engine")
    mc.record_capability("sql_query", capable=True, evidence="has mysql tool")

    # Assess a domain
    result = mc.self_assess("frontend")
    # → {"capable": False, "confidence": 0.9, "evidence": "no JS engine"}

    # Unfamiliar domain → unknown
    result = mc.self_assess("k8s_deploy")
    # → {"capable": None, "confidence": 0.0, "suggestion": "explore"}

    # Custom assessor
    mc.plug("assessor", my_llm_assessor)
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from typing import Any

from meowcat.pluggable import Pluggable


class Metacognition(Pluggable):
    """Metacognition — L3 worldview: self-awareness of capabilities.

    Framework layer: provides ``self_assess()`` + ``record_capability()``
    + plugin slot for custom assessment algorithms.

    App layer: calls ``self_assess(domain)`` before attempting tasks
    to decide whether to execute directly, delegate to another cat,
    or seek a new tool/skill.

    Args:
        default_confidence: Confidence assigned to newly recorded
            capabilities (default 0.8).
    """

    HOOKS: dict[str, dict[str, str]] = {
        "assessor": {"in": "domain: str, capabilities: dict", "out": "dict | None"},
    }

    __slots__ = ("_capabilities", "_default_confidence")

    def __init__(self, default_confidence: float = 0.8) -> None:
        super().__init__()
        self._default_confidence = default_confidence
        self._capabilities: dict[str, dict[str, Any]] = {}

    # -- Core API ------------------------------------------------------

    def record_capability(
        self,
        domain: str,
        capable: bool,
        evidence: str = "",
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Record a known capability (or incapability).

        Args:
            domain: Capability domain (e.g. "sql_query", "frontend").
            capable: Whether the cat is capable in this domain.
            evidence: Supporting evidence or reason.
            confidence: Confidence in this assessment (default: self._default_confidence).

        Returns:
            The stored capability record.
        """
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
        suggestion: "explore"}`` — signalling that the cat should
        either delegate or learn.

        Args:
            domain: Capability domain to assess.

        Returns:
            Assessment dict.
        """
        # Plugin slot — custom assessor
        for _name, r in self._run_plugs_sync(
            "assessor", domain, dict(self._capabilities),
        ):
            if isinstance(r, dict):
                return r

        return _default_assessor(domain, self._capabilities)

    def list_capabilities(self) -> list[dict[str, Any]]:
        """List all known capability records.

        Returns:
            List of capability dicts.
        """
        return sorted(
            [dict(v) for v in self._capabilities.values()],
            key=lambda x: -x["confidence"],
        )

    def known_domains(self) -> list[str]:
        """Return list of all known domain names."""
        return list(self._capabilities.keys())

    def capable_domains(self) -> list[str]:
        """Return domains where the cat believes itself capable."""
        return [
            d for d, r in self._capabilities.items()
            if r["capable"] is True
        ]

    def incapable_domains(self) -> list[str]:
        """Return domains where the cat knows it's incapable."""
        return [
            d for d, r in self._capabilities.items()
            if r["capable"] is False
        ]

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "known_domains": len(self._capabilities),
            "capable_count": len(self.capable_domains()),
            "incapable_count": len(self.incapable_domains()),
            "capabilities": self.list_capabilities(),
            "plugs": self.list_plugs(),
        }


# -- Default assessor ---------------------------------------------------


def _default_assessor(
    domain: str,
    capabilities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Default self-assessment: direct lookup in known capabilities.

    Returns ``{capable: None, confidence: 0.0, suggestion: "explore"}``
    for unfamiliar domains — a signal to delegate or learn.
    """
    cap = capabilities.get(domain)
    if cap is not None:
        return {
            "domain": domain,
            "capable": cap["capable"],
            "confidence": cap["confidence"],
            "evidence": cap["evidence"],
        }

    # Unknown domain — curiosity trigger
    return {
        "domain": domain,
        "capable": None,
        "confidence": 0.0,
        "evidence": "",
        "suggestion": "explore",
    }


__all__ = ["Metacognition"]
