"""v2.1.0 RuleSet unit tests — Rule, RuleSet, render, resolve, priority sort.

Tests cover:
    - Rule construction (defaults, full)
    - RuleSet defaults (empty, no rules, no blocks)
    - RuleSet.resolve() — always_on, per_route, wildcard, priority sort
    - RuleSet.render() — roles, context, output blocks, XML rules
    - RuleSet.render() — MD and code block content preservation
"""

from meowcat.ruleset import Rule, RuleSet

# ── Rule tests ────────────────────────────────────────────────────────


class TestRule:
    def test_defaults(self):
        r = Rule("name", "content")
        assert r.priority == "medium"
        assert r.tags == []

    def test_full(self):
        r = Rule("SQL", "参数化", priority="critical", tags=["code", "security"])
        assert r.name == "SQL"
        assert r.priority == "critical"
        assert r.tags == ["code", "security"]

    def test_repr(self):
        r = Rule("N", "C")
        assert repr(
            r) == "Rule(name='N', content='C', priority='medium', tags=[])"


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
    def test_render_role_block(self):
        rs = RuleSet(role_block="<role>expert</role>")
        assert "<role>expert</role>" in rs.render("chat")

    def test_render_context_block(self):
        rs = RuleSet(context_block="<context>fastapi</context>")
        assert "<context>fastapi</context>" in rs.render("chat")

    def test_render_output_format(self):
        rs = RuleSet(output_format_block="<output>json</output>")
        assert "<output>json</output>" in rs.render("chat")

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

    def test_render_md_content_preserved(self):
        rs = RuleSet(always_on=[
            Rule("MD规则", "# 标题\n\n- 列表项"),
        ])
        rendered = rs.render("chat")
        assert "# 标题" in rendered
        assert "- 列表项" in rendered

    def test_render_code_block_preserved(self):
        rs = RuleSet(always_on=[
            Rule("代码规则", "```python\ncursor.execute(sql, params)\n```"),
        ])
        rendered = rs.render("chat")
        assert "```python" in rendered
        assert "cursor.execute(sql, params)" in rendered

    def test_render_mixed_md_and_code(self):
        rs = RuleSet(always_on=[
            Rule("混合规则", "# 标题\n\n- 列表项\n\n```python\ncursor.execute(sql, params)\n```"),
        ])
        rendered = rs.render("chat")
        assert "# 标题" in rendered
        assert "- 列表项" in rendered
        assert "```python" in rendered
        assert "cursor.execute(sql, params)" in rendered

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
