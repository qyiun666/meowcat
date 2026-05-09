# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Cortex — cerebral cortex with four-layer worldview (L0→L1→L2→L3).

- **L1**: extract rules from repeated L0 patterns (``extract_rules``)
- **L2**: beliefs — promoted principles with confidence and challengeability (v1.1.27)
- **L3**: metacognition — cat's awareness of its own capabilities (v2.0: built into CatSelf)

Extensible via ``"extractor"`` and ``"belief"`` plugin slots.

Usage::

    from meowcat.biology.cortex import Cortex

    cortex = Cortex()

    # L0 → L1: extract rules from facts
    facts = [
        {"entity": "users", "attr": "id_type", "value": "uuid"},
        {"entity": "users", "attr": "id_type", "value": "uuid"},
    ]
    rules = cortex.extract_rules(facts)

    # L1 → L2: promote rules to beliefs
    cortex.promote_to_belief("parametrized_sql", "always use params", 0.95)
    cortex.get_beliefs()  # → [(key, value, confidence, challengeable)]

    # L2: challenge beliefs (lowers confidence)
    cortex.challenge_belief("parametrized_sql", "ORM handles this", 0.3)

    # Custom plugins
    cortex.plug("extractor", my_ml_rule_extractor)
    cortex.plug("belief", my_belief_update_policy)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from meowcat.pluggable import Pluggable


class Cortex(Pluggable):
    """Cerebral cortex — worldview storage and rule extraction.

    Framework layer: provides ``extract_rules()`` + plugin slot for
    custom rule extraction algorithms.

    App layer: decides when to call ``extract_rules()`` (after each
    PinealGland trigger, during reflection, etc.) and how to use
    extracted rules (verify, store, surface to user).

    Worldview layers:
    - **L0**: raw facts (Hippocampus entities/observations)
    - **L1**: rules inferred from repeated L0 patterns (this module)
    - **L2**: beliefs — principles with confidence and challengeability (v1.1.27)
    - **L3**: metacognition — cat's awareness of its own capabilities (v2.0: built into CatSelf)
    """

    HOOKS: dict[str, dict[str, str]] = {
        "extractor": {"in": "facts: list[dict]", "out": "list[dict]"},
        "belief": {
            "in": "key: str, value: str, confidence: float, challengeable: bool",
            "out": "dict | None",
        },
    }

    __slots__ = ("_beliefs",)

    def __init__(self) -> None:
        super().__init__()
        # L2 beliefs: {key: {"value": ..., "confidence": 0.0-1.0, "challengeable": bool}}
        self._beliefs: dict[str, dict[str, Any]] = {}

    # ── Core API ─────────────────────────────────────────────────

    def extract_rules(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract L1 rules from L0 facts.

        Runs the ``"extractor"`` plugin chain, falling back to
        :class:`DefaultRuleExtractor` if no plugin is registered.

        L1 rules take the form: ``{"if": pattern, "then": value,
        "confidence": 0.0-1.0, "count": int}``.

        Args:
            facts: Raw L0 fact dicts, each containing at minimum
                ``"entity"`` and ``"attr"`` / ``"value"`` keys.

        Returns:
            List of rule dicts sorted by confidence descending.
        """
        for _name, r in self._run_plugs_sync("extractor", facts):
            if isinstance(r, list):
                return r
        return _default_rule_extractor(facts)

    # ── L2: Beliefs (v1.1.27) ────────────────────────────────────

    def promote_to_belief(
        self,
        key: str,
        value: str,
        confidence: float = 0.8,
        *,
        challengeable: bool = True,
    ) -> dict[str, Any]:
        """Promote a rule or insight to an L2 belief.

        Beliefs are principles the cat holds with a confidence score.
        Unlike L1 rules (which are statistical patterns), L2 beliefs
        represent the cat's "convictions" about how things work.

        If the belief already exists, confidence is updated only if
        the new confidence is higher.

        Args:
            key: Belief identifier (e.g. "parametrized_sql").
            value: Belief statement (e.g. "always use params").
            confidence: Initial confidence 0.0-1.0.
            challengeable: Whether this belief can be challenged and revised.

        Returns:
            The belief dict as stored.
        """
        # Plugin hook — can override or veto
        for _name, r in self._run_plugs_sync("belief", key, value, confidence, challengeable):
            if isinstance(r, dict):
                self._beliefs[key] = r
                return r

        existing = self._beliefs.get(key)
        if existing and existing["confidence"] >= confidence:
            existing["count"] = existing.get("count", 1) + 1
            return dict(existing)

        belief = {
            "key": key,
            "value": value,
            "confidence": min(max(confidence, 0.0), 1.0),
            "challengeable": challengeable,
            "count": existing.get("count", 0) + 1 if existing else 1,
        }
        self._beliefs[key] = belief
        return dict(belief)

    def challenge_belief(
        self,
        key: str,
        evidence: str = "",
        impact: float = 0.3,
    ) -> dict[str, Any] | None:
        """Challenge an existing belief, lowering its confidence.

        Only challengeable beliefs can be challenged. Unchallengeable
        beliefs (core principles) remain untouched.

        When confidence drops below 0.3, the belief is removed
        (the cat "changes its mind").

        Args:
            key: Belief identifier to challenge.
            evidence: Counter-evidence description.
            impact: How much to reduce confidence (0.0-1.0).

        Returns:
            Updated belief dict, or None if the belief was removed
            or doesn't exist.
        """
        belief = self._beliefs.get(key)
        if belief is None:
            return None
        if not belief["challengeable"]:
            return dict(belief)

        belief["confidence"] = round(
            max(belief["confidence"] - impact, 0.0),
            2,
        )
        belief["challenge_count"] = belief.get("challenge_count", 0) + 1
        belief["last_challenge"] = evidence[:200]

        if belief["confidence"] < 0.3:
            self._beliefs.pop(key, None)
            return None

        return dict(belief)

    def get_beliefs(
        self,
        min_confidence: float = 0.0,
    ) -> list[tuple[str, str, float, bool]]:
        """List all current beliefs.

        Args:
            min_confidence: Minimum confidence filter.

        Returns:
            List of ``(key, value, confidence, challengeable)`` tuples,
            sorted by confidence descending.
        """
        result = [
            (k, b["value"], b["confidence"], b["challengeable"])
            for k, b in self._beliefs.items()
            if b["confidence"] >= min_confidence
        ]
        result.sort(key=lambda x: -x[2])
        return result

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot of all worldview layers."""
        return {
            "beliefs_count": len(self._beliefs),
            "beliefs": [
                {"key": k, "value": b["value"], "confidence": b["confidence"]}
                for k, b in self._beliefs.items()
            ],
            "plugs": self.list_plugs(),
        }


# ── Prefab (开箱即用，可替换) ──────────────────────────────────


def _default_rule_extractor(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Default L1 rule extractor: repeated entity-attribute→value patterns.

    Groups facts by ``(entity, attr)``, collects all observed values,
    and returns rules for value sets that repeat. Confidence is based
    on how often the dominant value appears vs. total observations.

    Returns:
        List of ``{if, then, confidence, count, total}`` dicts.
    """
    if not facts:
        return []

    # Group by (entity, attr) → list of values
    groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for f in facts:
        entity = f.get("entity", "")
        attr = f.get("attr", "")
        value = f.get("value")
        if entity and attr and value is not None:
            groups[(entity, attr)].append(value)

    rules: list[dict[str, Any]] = []
    for (entity, attr), values in groups.items():
        total = len(values)
        if total < 2:
            continue  # need at least 2 observations for a rule

        # Count occurrences of each distinct value
        value_counts: dict[str, int] = defaultdict(int)
        for v in values:
            key = str(v)
            value_counts[key] += 1

        # Pick dominant value
        dominant_val, dominant_count = max(
            value_counts.items(),
            key=lambda x: x[1],
        )
        confidence = dominant_count / total

        rules.append(
            {
                "if": f"{entity}.{attr}",
                "then": dominant_val,
                "confidence": round(confidence, 2),
                "count": dominant_count,
                "total": total,
            }
        )

    rules.sort(key=lambda x: -x["confidence"])
    return rules


class DefaultRuleExtractor:
    """Default L1 rule extractor: frequency-based pattern detection.

    Finds ``(entity, attr) → value`` pairs that consistently appear
    across L0 facts and promotes them to L1 rules when confidence
    exceeds internal threshold.

    Usage::

        cortex.plug("extractor", DefaultRuleExtractor())
    """

    def __call__(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _default_rule_extractor(facts)


__all__ = ["Cortex", "DefaultRuleExtractor"]
