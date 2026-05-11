"""v2.1.0 RuleSet unit tests — Rule, RuleSet, render, resolve, priority sort.

Tests cover:
    - Rule construction (defaults, full)
    - RuleSet defaults (empty, no rules, no blocks)
    - RuleSet.resolve() — always_on, per_route, wildcard, priority sort
    - RuleSet.render() — roles, context, output blocks, XML rules
    - RuleSet.render() — MD and code block content preservation
"""

from meowcat.ruleset import Rule, RuleSet
import pytest

# ── Rule tests ────────────────────────────────────────────────────────


class TestRule:
    @pytest.mark.parametrize("kwargs, expected_name, expected_priority, expected_tags", [
        ({"name": "name", "content": "content"}, "name", "medium", []),
        ({"name": "SQL", "content": "参数化", "priority": "critical",
          "tags": ["code", "security"]}, "SQL", "critical", ["code", "security"]),
    ])
    def test_construction(self, kwargs, expected_name, expected_priority, expected_tags):
        r = Rule(**kwargs)
        assert r.name == expected_name
        assert r.priority == expected_priority
        assert r.tags == expected_tags

    def test_repr(self):
        r = Rule("N", "C")
        assert repr(
            r) == "Rule(name='N', content='C', priority='medium', mode='inject', tags=[])"


# ── RuleSet tests ─────────────────────────────────────────────────────


class TestRuleSet:
    def test_empty(self):
        rs = RuleSet()
        assert rs.resolve("any") == []
        assert rs.render("any") == ""

    def test_always_on(self):
        rs = RuleSet(always_on=[Rule("R1", "c1")])
        assert len(rs.resolve("chat")) == 1

    def test_per_route(self):
        rs = RuleSet(per_route={"deep_reason": [Rule("SQL", "param")]})
        assert len(rs.resolve("deep_reason")) == 1
        assert rs.resolve("chat") == []

    def test_merge_always_and_route(self):
        rs = RuleSet(
            always_on=[Rule("global", "g")],
            per_route={"deep_reason": [Rule("local", "l")]},
        )
        rules = rs.resolve("deep_reason")
        assert len(rules) == 2

    def test_wildcard_route(self):
        rs = RuleSet(per_route={"*": [Rule("all", "a")]})
        assert len(rs.resolve("any_route")) == 1

    def test_wildcard_does_not_duplicate(self):
        rs = RuleSet(
            per_route={
                "deep_reason": [Rule("specific", "s")],
                "*": [Rule("all", "a")],
            }
        )
        rules = rs.resolve("deep_reason")
        assert len(rules) == 2

    def test_priority_sort(self):
        rs = RuleSet(always_on=[
            Rule("low", "", "low"),
            Rule("critical", "", "critical"),
            Rule("high", "", "high"),
            Rule("medium", "", "medium"),
        ])
        rules = rs.resolve("chat")
        priorities = [r.priority for r in rules]
        assert priorities == ["critical", "high", "medium", "low"]

    def test_priority_sort_defaults_to_medium(self):
        # Unknown priority falls back to 2 (same as "medium").
        # Stable sort preserves insertion order for equal keys.
        rs = RuleSet(always_on=[
            Rule("unknown", "", "nonexistent"),
            Rule("medium", "", "medium"),
        ])
        rules = rs.resolve("chat")
        assert rules[0].name == "unknown"
        assert rules[1].name == "medium"

    def test_resolve_returns_copy_not_reference(self):
        rs = RuleSet(always_on=[Rule("R", "c")])
        rules = rs.resolve("chat")
        rules.append(Rule("extra", "x"))
        # original always_on unchanged
        assert len(rs.always_on) == 1


# ── Render tests ──────────────────────────────────────────────────────


class TestRuleSetRender:
    @pytest.mark.parametrize("kwargs, substring", [
        ({"role_block": "<role>expert</role>"}, "<role>expert</role>"),
        ({"context_block": "<context>fastapi</context>"},
         "<context>fastapi</context>"),
        ({"output_format_block": "<output>json</output>"}, "<output>json</output>"),
    ])
    def test_render_block(self, kwargs, substring):
        rs = RuleSet(**kwargs)
        assert substring in rs.render("chat")

    def test_render_rules_xml(self):
        rs = RuleSet(always_on=[Rule("SQL", "参数化查询", "critical")])
        rendered = rs.render("chat")
        assert "<rules>" in rendered
        assert '<rule name="SQL" priority="critical">' in rendered
        assert "<rule_content>" in rendered
        assert "参数化查询" in rendered
        assert "</rule_content>" in rendered
        assert "</rule>" in rendered
        assert "</rules>" in rendered

    def test_render_empty_rules_no_xml_tags(self):
        rs = RuleSet(role_block="<role>x</role>")
        rendered = rs.render("chat")
        assert "<rules>" not in rendered
        assert "</rules>" not in rendered

    @pytest.mark.parametrize("content, substrings", [
        ("# 标题\n\n- 列表项", ["# 标题", "- 列表项"]),
        ("```python\ncursor.execute(sql, params)\n```",
         ["```python", "cursor.execute(sql, params)"]),
        ("# 标题\n\n- 列表项\n\n```python\ncursor.execute(sql, params)\n```",
         ["# 标题", "- 列表项", "```python", "cursor.execute(sql, params)"]),
    ])
    def test_render_content_preserved(self, content, substrings):
        rs = RuleSet(always_on=[Rule("规则", content)])
        rendered = rs.render("chat")
        for s in substrings:
            assert s in rendered

    def test_render_full_xml_structure(self):
        rs = RuleSet(
            role_block="<role>审计专家</role>",
            context_block="<context>FastAPI+PostgreSQL</context>",
            always_on=[
                Rule("安全", "不要执行危险操作", "critical"),
                Rule("简洁", "回复不超过200字", "high"),
            ],
            output_format_block="<output_format>json</output_format>",
        )
        rendered = rs.render("chat")
        # Check order: role → context → rules → output
        role_idx = rendered.index("<role>")
        context_idx = rendered.index("<context>")
        rules_idx = rendered.index("<rules>")
        output_idx = rendered.index("<output_format>")
        assert role_idx < context_idx < rules_idx < output_idx

    def test_render_multiple_rules_sorted(self):
        rs = RuleSet(always_on=[
            Rule("low", "", "low"),
            Rule("critical", "", "critical"),
        ])
        rendered = rs.render("chat")
        crit_idx = rendered.index("critical")
        low_idx = rendered.index("low")
        assert crit_idx < low_idx
