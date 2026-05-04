"""v1.1.25 Crystallizer L2+L3 + Cortex worldview L1 tests."""

from __future__ import annotations

import pytest

from meowcat.plus.crystallizer import Crystallizer, DefaultDetector
from meowcat.biology.cortex import Cortex, DefaultRuleExtractor


# ════════════════════════════════════════════════════════════════════
# Crystallizer L2: Pattern Crystallization
# ════════════════════════════════════════════════════════════════════

class TestCrystallizerL2:
    """L2: Path-sequence pattern detection → Chain registration."""

    def test_record_sequence_single(self):
        c = Crystallizer()
        c.record_sequence(["locate", "deep_reason", "speak"])
        # not repeated enough
        assert c.detect_patterns() == []

    def test_record_sequence_three_times(self):
        c = Crystallizer()
        seq = ["locate", "deep_reason", "speak"]
        c.record_sequence(seq)
        c.record_sequence(seq)
        c.record_sequence(seq)
        patterns = c.detect_patterns()
        assert len(patterns) == 1
        assert patterns[0][0] == tuple(seq)
        assert patterns[0][1] == 3

    def test_record_sequence_custom_min_repeat(self):
        c = Crystallizer()
        seq = ["a", "b"]
        c.record_sequence(seq)
        c.record_sequence(seq)
        # default min_repeat=3 → not detected
        assert c.detect_patterns() == []
        # custom min_repeat=2 → detected
        assert c.detect_patterns(min_repeat=2) == [(("a", "b"), 2)]

    def test_record_sequence_multiple_patterns(self):
        c = Crystallizer()
        seq_a = ["locate", "speak"]
        seq_b = ["hear", "deep_reason", "speak"]
        for _ in range(3):
            c.record_sequence(seq_a)
        for _ in range(4):
            c.record_sequence(seq_b)

        patterns = c.detect_patterns()
        assert len(patterns) == 2
        # sorted by count descending: seq_b (4) before seq_a (3)
        assert patterns[0][0] == tuple(seq_b)
        assert patterns[0][1] == 4
        assert patterns[1][0] == tuple(seq_a)
        assert patterns[1][1] == 3

    def test_record_sequence_diff_sequences(self):
        c = Crystallizer()
        c.record_sequence(["a"])
        c.record_sequence(["b"])
        c.record_sequence(["a"])
        assert c.detect_patterns(min_repeat=2) == [((("a",), 2))]

    def test_reset_clears_sequences(self):
        c = Crystallizer()
        for _ in range(3):
            c.record_sequence(["a", "b"])
        assert len(c.detect_patterns()) == 1
        c.reset()
        assert c.detect_patterns() == []


# ════════════════════════════════════════════════════════════════════
# Crystallizer L3: Knowledge Crystallization
# ════════════════════════════════════════════════════════════════════

class TestCrystallizerL3:
    """L3: high-confidence correction → permanent knowledge entity."""

    def test_record_correction_single(self):
        c = Crystallizer()
        c.record_correction("python_version", "3.13", confidence=0.5)
        # below default threshold 0.8
        assert c.detect_knowledge() == []

    def test_record_correction_above_threshold(self):
        c = Crystallizer()
        c.record_correction("python_version", "3.13", confidence=0.95)
        knowledge = c.detect_knowledge()
        assert len(knowledge) == 1
        assert knowledge[0]["key"] == "python_version"
        assert knowledge[0]["value"] == "3.13"
        assert knowledge[0]["confidence"] == 0.95
        assert knowledge[0]["count"] == 1

    def test_record_correction_custom_threshold(self):
        c = Crystallizer()
        c.record_correction("db_engine", "InnoDB", confidence=0.7)
        # default 0.8 → not detected
        assert c.detect_knowledge() == []
        # custom 0.6 → detected
        result = c.detect_knowledge(min_confidence=0.6)
        assert len(result) == 1
        assert result[0]["key"] == "db_engine"

    def test_record_correction_multiple(self):
        c = Crystallizer()
        c.record_correction("db_engine", "InnoDB", confidence=0.95)
        c.record_correction("id_type", "uuid", confidence=0.85)
        c.record_correction("timeout", "30s", confidence=0.7)
        knowledge = c.detect_knowledge()
        assert len(knowledge) == 2
        # sorted by confidence descending
        assert knowledge[0]["key"] == "db_engine"
        assert knowledge[1]["key"] == "id_type"

    def test_record_correction_update_existing(self):
        c = Crystallizer()
        c.record_correction("version", "3.12", confidence=0.5)
        # update with higher confidence
        c.record_correction("version", "3.13", confidence=0.95)
        knowledge = c.detect_knowledge()
        assert len(knowledge) == 1
        assert knowledge[0]["value"] == "3.13"
        assert knowledge[0]["confidence"] == 0.95
        assert knowledge[0]["count"] == 2

    def test_record_correction_keep_higher_confidence(self):
        c = Crystallizer()
        c.record_correction("version", "3.13", confidence=0.95)
        # update with lower confidence → keeps 0.95
        c.record_correction("version", "3.12", confidence=0.5)
        knowledge = c.detect_knowledge()
        assert knowledge[0]["confidence"] == 0.95
        assert knowledge[0]["value"] == "3.13"

    def test_reset_clears_corrections(self):
        c = Crystallizer()
        c.record_correction("key", "val", confidence=0.9)
        assert len(c.detect_knowledge()) == 1
        c.reset()
        assert c.detect_knowledge() == []


# ════════════════════════════════════════════════════════════════════
# Crystallizer: L1+L2+L3 coexistence
# ════════════════════════════════════════════════════════════════════

class TestCrystallizerAllLayers:
    """All three layers coexist and reset together."""

    def test_all_layers_independent(self):
        c = Crystallizer()
        # L1
        c.record("tool_a")
        c.record("tool_a")
        # L2
        for _ in range(3):
            c.record_sequence(["a", "b"])
        # L3
        c.record_correction("key", "val", confidence=0.9)

        assert c.total == 2
        assert len(c.detect()) > 0
        assert len(c.detect_patterns()) == 1
        assert len(c.detect_knowledge()) == 1

    def test_reset_clears_all(self):
        c = Crystallizer()
        c.record("tool_a")
        c.record_sequence(["a"])
        c.record_correction("k", "v", 0.9)
        c.reset()

        assert c.total == 0
        assert c.detect() == []
        assert c.detect_patterns() == []
        assert c.detect_knowledge() == []


# ════════════════════════════════════════════════════════════════════
# Cortex: worldview L1 — extract_rules
# ════════════════════════════════════════════════════════════════════

class TestCortex:
    """Cortex worldview L1: rule extraction from L0 facts."""

    def test_extract_rules_empty(self):
        cortex = Cortex()
        assert cortex.extract_rules([]) == []

    def test_extract_rules_single_fact_insufficient(self):
        cortex = Cortex()
        facts = [{"entity": "users", "attr": "id_type", "value": "uuid"}]
        # Need at least 2 observations
        assert cortex.extract_rules(facts) == []

    def test_extract_rules_repeated_pattern(self):
        cortex = Cortex()
        facts = [
            {"entity": "users", "attr": "id_type", "value": "uuid"},
            {"entity": "users", "attr": "id_type", "value": "uuid"},
        ]
        rules = cortex.extract_rules(facts)
        assert len(rules) == 1
        assert rules[0]["if"] == "users.id_type"
        assert rules[0]["then"] == "uuid"
        assert rules[0]["confidence"] == 1.0
        assert rules[0]["count"] == 2

    def test_extract_rules_partial_confidence(self):
        cortex = Cortex()
        facts = [
            {"entity": "users", "attr": "engine", "value": "InnoDB"},
            {"entity": "users", "attr": "engine", "value": "InnoDB"},
            {"entity": "users", "attr": "engine", "value": "MyISAM"},
        ]
        rules = cortex.extract_rules(facts)
        assert len(rules) == 1
        assert rules[0]["then"] == "InnoDB"
        assert rules[0]["confidence"] == pytest.approx(0.67, abs=0.01)
        assert rules[0]["count"] == 2
        assert rules[0]["total"] == 3

    def test_extract_rules_multiple_entities(self):
        cortex = Cortex()
        facts = [
            {"entity": "users", "attr": "id_type", "value": "uuid"},
            {"entity": "users", "attr": "id_type", "value": "uuid"},
            {"entity": "orders", "attr": "status", "value": "pending"},
            {"entity": "orders", "attr": "status", "value": "pending"},
        ]
        rules = cortex.extract_rules(facts)
        assert len(rules) == 2
        # Both have confidence 1.0
        patterns = {(r["if"], r["then"]) for r in rules}
        assert ("users.id_type", "uuid") in patterns
        assert ("orders.status", "pending") in patterns

    def test_extract_rules_sorted_by_confidence(self):
        cortex = Cortex()
        facts = [
            {"entity": "a", "attr": "x", "value": "v1"},
            {"entity": "a", "attr": "x", "value": "v1"},
            {"entity": "a", "attr": "x", "value": "v2"},  # mixed
            {"entity": "b", "attr": "y", "value": "v3"},
            {"entity": "b", "attr": "y", "value": "v3"},
            {"entity": "b", "attr": "y", "value": "v3"},
        ]
        rules = cortex.extract_rules(facts)
        # b.y (3/3=1.0) before a.x (2/3=0.67)
        assert rules[0]["confidence"] > rules[1]["confidence"]

    def test_extract_rules_skips_incomplete_facts(self):
        cortex = Cortex()
        facts = [
            {"entity": "users", "attr": "id_type"},  # missing value
            {"entity": "", "attr": "id_type", "value": "uuid"},  # empty entity
            {"entity": "users", "value": "uuid"},  # missing attr
        ]
        rules = cortex.extract_rules(facts)
        assert rules == []

    def test_extract_rules_handles_non_string_values(self):
        cortex = Cortex()
        facts = [
            {"entity": "config", "attr": "port", "value": 8080},
            {"entity": "config", "attr": "port", "value": 8080},
            {"entity": "config", "attr": "port", "value": 8080},
        ]
        rules = cortex.extract_rules(facts)
        assert len(rules) == 1
        assert rules[0]["then"] == "8080"
        assert rules[0]["confidence"] == 1.0
        assert rules[0]["count"] == 3

    def test_plug_extractor(self):
        cortex = Cortex()
        facts = [{"entity": "a", "attr": "x", "value": "y"}]

        def my_extractor(f):
            return [{"if": "custom", "then": "rule", "confidence": 0.99, "count": 1, "total": 1}]

        cortex.plug("extractor", my_extractor)
        rules = cortex.extract_rules(facts)
        assert len(rules) == 1
        assert rules[0]["if"] == "custom"

    def test_unplug_extractor(self):
        cortex = Cortex()
        facts = [
            {"entity": "t", "attr": "k", "value": "v"},
            {"entity": "t", "attr": "k", "value": "v"},
        ]

        def fake(_f):
            return []

        cortex.plug("extractor", fake)
        assert cortex.extract_rules(facts) == []

        cortex.unplug("extractor", fake)
        rules = cortex.extract_rules(facts)
        assert len(rules) == 1  # back to default

    def test_pluggable_inheritance(self):
        from meowcat.pluggable import Pluggable
        cortex = Cortex()
        assert isinstance(cortex, Pluggable)


# ════════════════════════════════════════════════════════════════════
# DefaultRuleExtractor prefab
# ════════════════════════════════════════════════════════════════════

class TestDefaultRuleExtractor:
    """DefaultRuleExtractor prefab tests."""

    def test_callable_same_as_default(self):
        facts = [
            {"entity": "e", "attr": "a", "value": "v"},
            {"entity": "e", "attr": "a", "value": "v"},
        ]
        default = Cortex().extract_rules(facts)
        prefab = DefaultRuleExtractor()(facts)
        assert default == prefab

    def test_empty_input(self):
        assert DefaultRuleExtractor()([]) == []

    def test_insufficient_facts(self):
        assert DefaultRuleExtractor()(
            [{"entity": "e", "attr": "a", "value": "v"}],
        ) == []
