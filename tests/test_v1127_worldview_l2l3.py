# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.1.27 Worldview L2+L3 — beliefs + metacognition tests."""

from __future__ import annotations

import pytest

from meowcat.biology.cortex import Cortex
from meowcat.biology.metacognition import Metacognition


# ════════════════════════════════════════════════════════════════════
# Cortex L2: Beliefs
# ════════════════════════════════════════════════════════════════════

class TestCortexBeliefs:
    """L2 worldview: belief promotion, challenge, and retrieval."""

    def test_promote_new_belief(self):
        c = Cortex()
        belief = c.promote_to_belief(
            "parametrized_sql", "always use params", 0.95)
        assert belief["key"] == "parametrized_sql"
        assert belief["value"] == "always use params"
        assert belief["confidence"] == 0.95
        assert belief["challengeable"] is True
        assert belief["count"] == 1

    def test_promote_existing_higher_confidence_updates(self):
        c = Cortex()
        c.promote_to_belief("key", "old_val", 0.5)
        c.promote_to_belief("key", "new_val", 0.9)
        beliefs = c.get_beliefs()
        assert len(beliefs) == 1
        assert beliefs[0][1] == "new_val"
        assert beliefs[0][2] == 0.9

    def test_promote_existing_lower_confidence_keeps_old(self):
        c = Cortex()
        c.promote_to_belief("key", "high_val", 0.9)
        c.promote_to_belief("key", "low_val", 0.5)
        beliefs = c.get_beliefs()
        assert beliefs[0][1] == "high_val"
        assert beliefs[0][2] == 0.9

    def test_promote_unchallengeable(self):
        c = Cortex()
        c.promote_to_belief("core", "never change", 1.0, challengeable=False)
        beliefs = c.get_beliefs()
        assert beliefs[0][3] is False  # challengeable flag

    def test_get_beliefs_empty(self):
        c = Cortex()
        assert c.get_beliefs() == []

    def test_get_beliefs_filtered(self):
        c = Cortex()
        c.promote_to_belief("a", "v1", 0.9)
        c.promote_to_belief("b", "v2", 0.5)
        c.promote_to_belief("c", "v3", 0.3)
        assert len(c.get_beliefs(min_confidence=0.7)) == 1
        assert len(c.get_beliefs(min_confidence=0.4)) == 2
        assert len(c.get_beliefs(min_confidence=0.2)) == 3

    def test_get_beliefs_sorted_by_confidence(self):
        c = Cortex()
        c.promote_to_belief("low", "v", 0.3)
        c.promote_to_belief("high", "v", 0.95)
        c.promote_to_belief("mid", "v", 0.6)
        beliefs = c.get_beliefs()
        assert beliefs[0][2] >= beliefs[1][2] >= beliefs[2][2]

    def test_challenge_reduces_confidence(self):
        c = Cortex()
        c.promote_to_belief("k", "v", 0.9)
        result = c.challenge_belief("k", "counter evidence", 0.3)
        assert result is not None
        assert result["confidence"] == 0.6
        assert result["challenge_count"] == 1

    def test_challenge_nonexistent(self):
        c = Cortex()
        assert c.challenge_belief("nonexistent") is None

    def test_challenge_unchallengeable_no_effect(self):
        c = Cortex()
        c.promote_to_belief("core", "v", 1.0, challengeable=False)
        result = c.challenge_belief("core", "try", 0.5)
        assert result["confidence"] == 1.0  # unchanged

    def test_challenge_below_threshold_removes_belief(self):
        c = Cortex()
        c.promote_to_belief("weak", "v", 0.5)
        result = c.challenge_belief("weak", "strong counter", 0.3)
        assert result is None  # belief removed
        assert c.get_beliefs() == []

    def test_multiple_challenges_cumulative(self):
        c = Cortex()
        c.promote_to_belief("k", "v", 0.9)
        c.challenge_belief("k", "e1", 0.2)
        c.challenge_belief("k", "e2", 0.2)
        result = c.challenge_belief("k", "e3", 0.2)
        assert result is not None
        assert result["confidence"] == 0.3  # 0.9 - 0.6 = 0.3

    def test_plug_belief(self):
        c = Cortex()

        def custom_belief(key, value, confidence, challengeable):
            return {"key": key, "value": "OVERRIDDEN", "confidence": 0.99, "challengeable": False, "count": 99}

        c.plug("belief", custom_belief)
        belief = c.promote_to_belief("k", "original", 0.5)
        assert belief["value"] == "OVERRIDDEN"
        assert belief["confidence"] == 0.99

    def test_diagnose_includes_beliefs(self):
        c = Cortex()
        c.promote_to_belief("k", "v", 0.8)
        info = c.diagnose()
        assert info["beliefs_count"] == 1
        assert info["beliefs"][0]["key"] == "k"


# ════════════════════════════════════════════════════════════════════
# Cortex L1 + L2 coexistence (ensure L1 still works)
# ════════════════════════════════════════════════════════════════════

class TestCortexL1L2Coexistence:
    """L1 rule extraction and L2 beliefs don't interfere."""

    def test_l1_still_works_after_l2(self):
        c = Cortex()
        # L2: add a belief
        c.promote_to_belief("sql", "use params", 0.9)
        # L1: extract rules
        facts = [
            {"entity": "users", "attr": "id_type", "value": "uuid"},
            {"entity": "users", "attr": "id_type", "value": "uuid"},
        ]
        rules = c.extract_rules(facts)
        assert len(rules) == 1
        assert rules[0]["if"] == "users.id_type"
        # Beliefs still intact
        assert len(c.get_beliefs()) == 1


# ════════════════════════════════════════════════════════════════════
# Metacognition L3: self-awareness
# ════════════════════════════════════════════════════════════════════

class TestMetacognition:
    """L3 worldview: cat's self-assessment of capabilities."""

    def test_record_capability(self):
        mc = Metacognition()
        rec = mc.record_capability("sql_query", True, "has mysql tool")
        assert rec["domain"] == "sql_query"
        assert rec["capable"] is True
        assert rec["confidence"] == 0.8  # default
        assert rec["evidence"] == "has mysql tool"

    def test_record_capability_custom_confidence(self):
        mc = Metacognition()
        rec = mc.record_capability("frontend", False, "no JS", 0.6)
        assert rec["confidence"] == 0.6

    def test_record_capability_confidence_clamped(self):
        mc = Metacognition()
        rec = mc.record_capability("x", True, "", 1.5)
        assert rec["confidence"] == 1.0
        rec2 = mc.record_capability("y", False, "", -0.5)
        assert rec2["confidence"] == 0.0

    def test_self_assess_known_capable(self):
        mc = Metacognition()
        mc.record_capability("sql_query", True, "has mysql", 0.9)
        result = mc.self_assess("sql_query")
        assert result["capable"] is True
        assert result["confidence"] == 0.9
        assert result["evidence"] == "has mysql"

    def test_self_assess_known_incapable(self):
        mc = Metacognition()
        mc.record_capability("frontend", False, "no JS")
        result = mc.self_assess("frontend")
        assert result["capable"] is False
        assert result["confidence"] == 0.8

    def test_self_assess_unknown_domain(self):
        mc = Metacognition()
        result = mc.self_assess("k8s_deploy")
        assert result["capable"] is None
        assert result["confidence"] == 0.0
        assert result["suggestion"] == "explore"

    def test_known_domains(self):
        mc = Metacognition()
        mc.record_capability("a", True, "")
        mc.record_capability("b", False, "")
        assert set(mc.known_domains()) == {"a", "b"}

    def test_capable_domains(self):
        mc = Metacognition()
        mc.record_capability("a", True, "")
        mc.record_capability("b", False, "")
        mc.record_capability("c", True, "")
        assert mc.capable_domains() == ["a", "c"]

    def test_incapable_domains(self):
        mc = Metacognition()
        mc.record_capability("a", True, "")
        mc.record_capability("b", False, "")
        assert mc.incapable_domains() == ["b"]

    def test_list_capabilities_sorted(self):
        mc = Metacognition()
        mc.record_capability("low", True, "", 0.3)
        mc.record_capability("high", True, "", 0.95)
        caps = mc.list_capabilities()
        assert caps[0]["domain"] == "high"
        assert caps[1]["domain"] == "low"

    def test_plug_assessor(self):
        mc = Metacognition()
        mc.record_capability("x", True, "")

        def custom_assessor(domain, capabilities):
            return {"domain": domain, "capable": "MAYBE", "confidence": 0.5}

        mc.plug("assessor", custom_assessor)
        result = mc.self_assess("x")
        assert result["capable"] == "MAYBE"

    def test_pluggable_inheritance(self):
        from meowcat.pluggable import Pluggable
        mc = Metacognition()
        assert isinstance(mc, Pluggable)

    def test_diagnose(self):
        mc = Metacognition()
        mc.record_capability("a", True, "ev", 0.9)
        mc.record_capability("b", False, "ev", 0.5)
        info = mc.diagnose()
        assert info["known_domains"] == 2
        assert info["capable_count"] == 1
        assert info["incapable_count"] == 1
        assert "plugs" in info


# ════════════════════════════════════════════════════════════════════
# Integration: BlindSpotDetector + Metacognition synergy
# ════════════════════════════════════════════════════════════════════

class TestBlindSpotMetacognitionIntegration:
    """When metacognition finds unknown domain → curiosity triggers blind spot detection."""

    def test_unknown_domain_suggests_explore(self):
        mc = Metacognition()
        mc.record_capability("python", True, "expert")
        result = mc.self_assess("rust")
        assert result["suggestion"] == "explore"
        # This is the signal for BlindSpotDetector to analyse

