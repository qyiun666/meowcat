# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.6.0 integration tests — F1: Amygdala fast_pass + Rule mode, F2: Skill loading."""

import re
import tempfile
from pathlib import Path

import pytest

from meowcat.defaults.organs.amygdala import DefaultAmygdala
from meowcat.plus.skill_loader import SkillLoader
from meowcat.ruleset import Rule, RuleSet
from meowcat.tools.skill import Skill, SkillRegistry, SkillSpec
from meowcat.tools.tool import ToolRegistry


# ── F1: Rule mode (inject / intercept) ──────────────────────────────

class TestRuleMode:
    def test_default_mode_is_inject(self):
        r = Rule("test", "content")
        assert r.mode == "inject"

    def test_mode_intercept(self):
        r = Rule("test", "content", mode="intercept")
        assert r.mode == "intercept"

    def test_mode_preserved_in_repr(self):
        r = Rule("test", "content", mode="intercept")
        assert "mode='intercept'" in repr(r)


# ── F1: RuleSet get_intercept_rules ─────────────────────────────────

class TestRuleSetIntercept:
    def test_get_intercept_rules_empty_by_default(self):
        rs = RuleSet(always_on=[Rule("r", "c")])
        assert rs.get_intercept_rules("chat") == []

    def test_get_intercept_rules_filters_by_mode(self):
        rs = RuleSet(always_on=[
            Rule("inject", "inject content", mode="inject"),
            Rule("intercept", "intercept content", mode="intercept"),
        ])
        rules = rs.get_intercept_rules("chat")
        assert len(rules) == 1
        assert rules[0].name == "intercept"

    def test_get_intercept_rules_with_per_route(self):
        rs = RuleSet(
            always_on=[Rule("global", "g", mode="intercept")],
            per_route={"deep_reason": [Rule("local", "l", mode="intercept")]},
        )
        rules = rs.get_intercept_rules("deep_reason")
        assert len(rules) == 2
        assert [r.name for r in rules] == ["global", "local"]

    def test_get_intercept_rules_ignores_wildcard_inject(self):
        # default mode=inject
        rs = RuleSet(per_route={"*": [Rule("all", "a")]})
        assert rs.get_intercept_rules("any") == []


# ── F1: RuleSet render excludes intercept ───────────────────────────

class TestRuleSetRenderIntercept:
    def test_render_excludes_intercept_rules(self):
        rs = RuleSet(always_on=[
            Rule("hidden", "should not appear", mode="intercept"),
        ])
        rendered = rs.render("chat")
        assert "hidden" not in rendered
        assert "should not appear" not in rendered

    def test_render_includes_inject_only(self):
        rs = RuleSet(always_on=[
            Rule("visible", "should appear", mode="inject"),
            Rule("hidden", "should not appear", mode="intercept"),
        ])
        rendered = rs.render("chat")
        assert "visible" in rendered
        assert "should appear" in rendered
        assert "hidden" not in rendered

    def test_render_backward_compat(self):
        """Existing rules without explicit mode should render unchanged."""
        rs = RuleSet(always_on=[Rule("SQL", "param query", "critical")])
        rendered = rs.render("chat")
        assert "SQL" in rendered
        assert "param query" in rendered
        assert "<rules>" in rendered


# ── F1: Amygdala fast_pass ──────────────────────────────────────────

class TestAmygdalaFastPass:
    def test_fast_pass_no_patterns_returns_none(self):
        a = DefaultAmygdala()
        assert a.fast_pass("DROP DATABASE users") is None

    def test_fast_pass_matching_pattern(self):
        a = DefaultAmygdala(
            fast_pass_patterns=[re.compile(r"DROP\s+DATABASE", re.IGNORECASE)]
        )
        result = a.fast_pass("DROP DATABASE users;")
        assert result is not None
        assert result["safe"] is False
        assert result["risk"] == "high"
        assert result["fast_pass"] is True
        assert "DROP DATABASE" in str(result["match"])

    def test_fast_pass_non_matching_input(self):
        a = DefaultAmygdala(
            fast_pass_patterns=[re.compile(r"DROP\s+DATABASE", re.IGNORECASE)]
        )
        assert a.fast_pass("SELECT * FROM users") is None
        assert a.fast_pass("hello world") is None

    def test_fast_pass_multiple_patterns(self):
        a = DefaultAmygdala(fast_pass_patterns=[
            re.compile(r"DROP\s+DATABASE", re.IGNORECASE),
            re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
        ])
        # Match first
        result = a.fast_pass("DROP DATABASE prod")
        assert result is not None
        # Match second
        result2 = a.fast_pass("rm -rf / --no-preserve-root")
        assert result2 is not None
        # Match neither
        assert a.fast_pass("ls -la") is None

    def test_fast_pass_returns_match_info(self):
        a = DefaultAmygdala(
            fast_pass_patterns=[re.compile(
                r"DELETE\s+FROM\s+(\w+)", re.IGNORECASE)]
        )
        result = a.fast_pass("DELETE FROM users WHERE 1=1")
        assert result is not None
        assert result["pattern"] is not None

    @pytest.mark.anyio
    async def test_assess_safety_respects_fast_pass(self):
        a = DefaultAmygdala(
            fast_pass_patterns=[re.compile(r"HACK", re.IGNORECASE)]
        )
        # fast_pass should catch this before general patterns
        result = await a.assess_safety("HACK the planet")
        assert result["safe"] is False
        assert result.get("fast_pass") is True

    @pytest.mark.anyio
    async def test_assess_safety_falls_through_when_fast_pass_unsure(self):
        a = DefaultAmygdala(
            fast_pass_patterns=[re.compile(r"HACK", re.IGNORECASE)]
        )
        # fast_pass won't match, falls through to general patterns
        result = await a.assess_safety("hello world")
        # safe unless general patterns match
        assert result["safe"] is True


# ── F2: SkillSpec disable_model_invocation ──────────────────────────

class TestSkillSpecDisableModel:
    def test_default_is_false(self):
        spec = SkillSpec(name="test", description="test")
        assert spec.disable_model_invocation is False

    def test_explicit_true(self):
        spec = SkillSpec(name="test", description="test",
                         disable_model_invocation=True)
        assert spec.disable_model_invocation is True


# ── F2: SkillRegistry list_for_model ────────────────────────────────

class TestSkillRegistryListForModel:
    def test_list_for_model_excludes_disabled(self):
        reg = SkillRegistry()
        reg.register(Skill(SkillSpec(name="visible", description="v")))
        reg.register(Skill(SkillSpec(
            name="hidden", description="h", disable_model_invocation=True)))
        model_skills = reg.list_for_model()
        names = [s.name for s in model_skills]
        assert "visible" in names
        assert "hidden" not in names

    def test_list_all_still_includes_disabled_skills(self):
        reg = SkillRegistry()
        reg.register(Skill(SkillSpec(name="visible", description="v")))
        reg.register(Skill(SkillSpec(
            name="hidden", description="h", disable_model_invocation=True)))
        all_skills = reg.list_all()
        names = [s.name for s in all_skills]
        assert "visible" in names
        assert "hidden" in names  # list_all shows all

    def test_list_for_model_respects_enabled_only(self):
        reg = SkillRegistry()
        s = Skill(SkillSpec(name="visible", description="v"))
        s.disable()
        reg.register(s)
        assert reg.list_for_model() == []
        assert reg.list_for_model(enabled_only=False) == [s]

    def test_list_for_model_all_visible(self):
        reg = SkillRegistry()
        reg.register(Skill(SkillSpec(name="a", description="a")))
        reg.register(Skill(SkillSpec(name="b", description="b")))
        assert len(reg.list_for_model()) == 2


# ── F2: SkillLoader YAML parsing ────────────────────────────────────

class TestSkillLoaderDisableModelInvocation:
    def test_parse_disable_model_invocation_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text("""---
name: my_skill
description: A skill
disable_model_invocation: false
---
# Body content
""")
            loader = SkillLoader(skills_dir=Path(tmpdir))
            tools = loader.scan_directory()
            assert len(tools) == 1
            assert tools[0].spec.disable_model_invocation is False

    def test_parse_disable_model_invocation_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text("""---
name: secret_skill
description: A hidden skill
disable_model_invocation: true
---
# Body content
""")
            loader = SkillLoader(skills_dir=Path(tmpdir))
            tools = loader.scan_directory()
            assert len(tools) == 1
            assert tools[0].spec.disable_model_invocation is True

    def test_parse_disable_model_invocation_default_false(self):
        """When field is absent, default should be false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text("""---
name: normal_skill
description: A normal skill
---
# Body content
""")
            loader = SkillLoader(skills_dir=Path(tmpdir))
            tools = loader.scan_directory()
            assert len(tools) == 1
            assert tools[0].spec.disable_model_invocation is False

    def test_register_to_tool_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = Path(tmpdir) / "SKILL.md"
            skill_file.write_text("""---
name: test
description: A test
---
Body
""")
            loader = SkillLoader(skills_dir=Path(tmpdir))
            tools = loader.scan_directory()
            reg = ToolRegistry()
            loader.register_all(reg)
            assert reg.get("test") is not None
