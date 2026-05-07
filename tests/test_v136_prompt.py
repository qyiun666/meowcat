# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.3.6 OrganPrompt + BrainStem 拼装 + CatSelf 注入 + 路由 fallback 全覆盖测试.

Covers:
- OrganPrompt dataclass
- RenovatedBrainstem 7-step assembly chain
- CatSelf injection (personality + beliefs + capabilities)
- inject_cat_self toggle
- Route template fallback chain
- NoopBrainstem new signature
- BrainStemProtocol runtime_checkable
- BrainStemAgent delegation
"""

from __future__ import annotations

import asyncio

import pytest

from meowcat.defaults.renovated import RenovatedBrainstem
from meowcat.defaults.organs import NoopBrainstem
from meowcat.defaults.presets import OrganPrompt, PROMPT_ZH, PROMPT_DEFAULT, PromptPreset
from meowcat.biology.cat_self import SelfSnapshot
from meowcat.protocols_brain import BrainStemProtocol
from meowcat.adapters.brain import BrainstemAgent


# =========================================================================
# OrganPrompt dataclass
# =========================================================================


class TestOrganPrompt:
    """OrganPrompt basic construction and defaults."""

    def test_default_construction(self):
        op = OrganPrompt()
        assert op.identity == ""
        assert op.perspective == ""
        assert op.output_format == ""
        assert op.route_templates == {}

    def test_full_construction(self):
        op = OrganPrompt(
            identity="你是一个大脑",
            perspective="视角声明",
            output_format="<think>\n<reply>",
            route_templates={"chat": "chat模板", "tool": "tool模板"},
        )
        assert op.identity == "你是一个大脑"
        assert op.perspective == "视角声明"
        assert op.output_format == "<think>\n<reply>"
        assert op.route_templates == {"chat": "chat模板", "tool": "tool模板"}

    def test_partial_construction(self):
        op = OrganPrompt(identity="只有身份")
        assert op.identity == "只有身份"
        assert op.perspective == ""
        assert op.output_format == ""
        assert op.route_templates == {}


# =========================================================================
# RenovatedBrainstem — basic (no organ_prompts, no snapshot)
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemBasic:

    async def test_basic_fallback(self):
        """No organ_prompts, no snapshot → pure PromptPreset fallback."""
        bs = RenovatedBrainstem(cat_name="Kitty", prompt=PROMPT_ZH)
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "Kitty" in result
        assert "请简洁" in result  # PROMPT_ZH.post_prompt

    async def test_default_prompt_when_none(self):
        """Prompt=None → PROMPT_DEFAULT."""
        bs = RenovatedBrainstem(cat_name="Test")
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "Test" in result

    async def test_route_not_in_templates(self):
        """Unknown route → fallback template."""
        bs = RenovatedBrainstem(cat_name="Kitty")
        result = await bs.build_system_prompt("cerebrum", "unknown_route")
        assert "Kitty" in result
        assert len(result) > 10

    async def test_different_organs_same_result_without_organ_prompts(self):
        """Without organ_prompts, cerebrum and cerebellum get same route template."""
        bs = RenovatedBrainstem(cat_name="Kitty")
        r1 = await bs.build_system_prompt("cerebrum", "chat")
        r2 = await bs.build_system_prompt("cerebellum", "chat")
        assert r1 == r2


# =========================================================================
# RenovatedBrainstem — with OrganPrompt
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemOrganPrompt:

    @pytest.fixture
    def brainstem(self):
        return RenovatedBrainstem(
            cat_name="Kitty",
            language="zh",
            domain="tech",
            prompt=PROMPT_ZH,
            organ_prompts={
                "cerebrum": OrganPrompt(
                    identity="你是 {name} 的大脑皮层，负责深度推理。用 {language} 回答。",
                    perspective="你可访问所有工具和记忆。",
                    output_format="<thinking>\n</thinking>\n<response>\n</response>",
                    route_templates={
                        "chat": "[cerebrum-chat] 你是 {name}，领域 {domain}。"},
                ),
                "cerebellum": OrganPrompt(
                    identity="你是 {name} 的小脑，负责快速响应。",
                    perspective="你只做模式匹配。",
                ),
            },
        )

    async def test_identity_injection(self, brainstem):
        """OrganPrompt.identity appears in output."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "大脑皮层" in result
        assert "深度推理" in result

    async def test_perspective_injection(self, brainstem):
        """OrganPrompt.perspective appears in output."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "所有工具和记忆" in result

    async def test_output_format_injection(self, brainstem):
        """OrganPrompt.output_format appears after route template."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "<thinking>" in result
        assert "</response>" in result

    async def test_variable_substitution(self, brainstem):
        """{name} {language} {domain} are substituted."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "Kitty" in result
        assert "{name}" not in result
        assert "{language}" not in result

    async def test_different_organs_different_prompts(self, brainstem):
        """Cerebrum and cerebellum produce different prompts."""
        r1 = await brainstem.build_system_prompt("cerebrum", "chat")
        r2 = await brainstem.build_system_prompt("cerebellum", "chat")
        assert r1 != r2
        assert "大脑皮层" in r1
        assert "小脑" in r2

    async def test_organ_with_no_organ_prompt_falls_back(self, brainstem):
        """Unknown organ → falls back to PromptPreset."""
        result = await brainstem.build_system_prompt("thalamus", "chat")
        assert "大脑皮层" not in result
        assert "小脑" not in result

    async def test_route_template_override(self, brainstem):
        """OrganPrompt.route_templates overrides PromptPreset.templates."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "[cerebrum-chat]" in result

    async def test_cerebellum_no_output_format(self, brainstem):
        """Cerebellum has no output_format → output_format section omitted."""
        result = await brainstem.build_system_prompt("cerebellum", "chat")
        assert "<thinking>" not in result

    async def test_parts_separated_by_double_newline(self, brainstem):
        """Sections separated by \\n\\n."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "\n\n" in result

    async def test_pre_prompt_appears_first(self, brainstem):
        """pre_prompt is the first section."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                pre_prompt="[PRE] 前置声明",
                templates={"chat": "你是 {name}。"},
                post_prompt="[POST] 后置安全",
            ),
            organ_prompts={
                "cerebrum": OrganPrompt(identity="ID: 大脑皮层"),
            },
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert result.startswith("[PRE]")

    async def test_post_prompt_appears_last(self, brainstem):
        """post_prompt is the last section (after output_format)."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert result.rstrip().endswith("不要编造信息。")


# =========================================================================
# RenovatedBrainstem — CatSelf injection
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemCatSelf:

    @pytest.fixture
    def brainstem(self):
        return RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PROMPT_ZH,
            organ_prompts={
                "cerebrum": OrganPrompt(
                    identity="你是 {name} 的大脑皮层。",
                    output_format="<thinking>\n</thinking>",
                ),
            },
        )

    @pytest.fixture
    def full_snapshot(self):
        return SelfSnapshot(
            personality={"tone": "专业严谨", "language": "zh"},
            beliefs=[
                ("sql", "参数化SQL 永远用参数", 0.95, True),
                ("user_id", "用户表 id 类型是 uuid", 0.90, False),
                ("dry", "重复两次以上就提取", 0.80, True),
            ],
            capable_domains=["SQL查询", "Python开发", "架构设计"],
            incapable_domains=["前端开发", "K8s部署"],
        )

    async def test_self_awareness_block_present(self, brainstem, full_snapshot):
        """CatSelf injection block appears with '自我认知' header."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        assert "## 自我认知" in result

    async def test_personality_injection(self, brainstem, full_snapshot):
        """Personality tone appears."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        assert "专业严谨" in result

    async def test_beliefs_injection(self, brainstem, full_snapshot):
        """Beliefs appear with confidence."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        assert "参数化SQL 永远用参数" in result
        assert "95%" in result

    async def test_capable_domains_injection(self, brainstem, full_snapshot):
        """Capable domains appear."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        assert "SQL查询" in result
        assert "Python开发" in result

    async def test_incapable_domains_injection(self, brainstem, full_snapshot):
        """Incapable domains appear."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        assert "前端开发" in result
        assert "K8s部署" in result

    async def test_cat_self_between_route_and_output_format(self, brainstem, full_snapshot):
        """CatSelf block appears between route template and output_format."""
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=full_snapshot,
        )
        cat_self_idx = result.index("## 自我认知")
        output_idx = result.index("<thinking>")
        assert cat_self_idx < output_idx

    async def test_no_snapshot_skips_injection(self, brainstem):
        """cat_self_snapshot=None → no self-awareness block."""
        result = await brainstem.build_system_prompt("cerebrum", "chat")
        assert "## 自我认知" not in result

    async def test_empty_personality(self, brainstem):
        """Empty personality dict → no personality line."""
        snap = SelfSnapshot(personality={})
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "性格" not in result

    async def test_tone_only_personality(self, brainstem):
        """Personality with only tone → tone shown without language."""
        snap = SelfSnapshot(personality={"tone": "友好"})
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "友好" in result
        assert "使用" not in result  # no "使用 {lang} 交流"

    async def test_tone_and_language_personality(self, brainstem):
        """Personality with tone + language → full line."""
        snap = SelfSnapshot(personality={"tone": "幽默", "language": "en"})
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "幽默" in result
        assert "en" in result

    async def test_empty_beliefs(self, brainstem):
        """Empty beliefs list → no beliefs section."""
        snap = SelfSnapshot(
            personality={"tone": "x", "language": "zh"},
            beliefs=[],
        )
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "坚信的法则" not in result

    async def test_empty_capable_domains(self, brainstem):
        """Empty capable_domains → no capable line."""
        snap = SelfSnapshot(
            personality={"tone": "x", "language": "zh"},
            capable_domains=[],
        )
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "擅长的领域" not in result

    async def test_beliefs_limited_to_10(self, brainstem):
        """More than 10 beliefs → only first 10 shown."""
        beliefs = [(f"key{i}", f"val{i}", 0.9, True) for i in range(20)]
        snap = SelfSnapshot(
            personality={"tone": "x", "language": "zh"},
            beliefs=beliefs,
        )
        result = await brainstem.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert "val0" in result
        assert "val9" in result
        assert "val10" not in result


# =========================================================================
# inject_cat_self toggle
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemInjectionToggle:

    @pytest.fixture
    def snapshot(self):
        return SelfSnapshot(
            personality={"tone": "专业", "language": "zh"},
            beliefs=[("k", "v", 0.9, True)],
        )

    async def test_inject_cat_self_default_true(self, snapshot):
        """Default inject_cat_self is True."""
        bs = RenovatedBrainstem()
        assert bs.inject_cat_self is True

    async def test_inject_cat_self_false_skips(self, snapshot):
        """inject_cat_self=False → no injection."""
        bs = RenovatedBrainstem()
        bs.inject_cat_self = False
        result = await bs.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snapshot,
        )
        assert "## 自我认知" not in result

    async def test_inject_cat_self_true_injects(self, snapshot):
        """inject_cat_self=True → injection present."""
        bs = RenovatedBrainstem()
        bs.inject_cat_self = True
        result = await bs.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snapshot,
        )
        assert "## 自我认知" in result

    async def test_toggle_back_to_false(self, snapshot):
        """Toggle inject_cat_self back to False after True."""
        bs = RenovatedBrainstem()
        bs.inject_cat_self = True
        r1 = await bs.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snapshot,
        )
        assert "## 自我认知" in r1

        bs.inject_cat_self = False
        r2 = await bs.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snapshot,
        )
        assert "## 自我认知" not in r2


# =========================================================================
# Route template fallback chain
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemFallback:

    async def test_organ_route_first_priority(self):
        """OrganPrompt.route_templates has highest priority."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                templates={"chat": "PROMPT_CHAT"},
                fallback="PROMPT_FALLBACK",
            ),
            organ_prompts={
                "cerebrum": OrganPrompt(
                    route_templates={"chat": "ORGAN_CHAT"},
                ),
            },
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "ORGAN_CHAT" in result
        assert "PROMPT_CHAT" not in result

    async def test_prompt_template_second_priority(self):
        """PromptPreset.templates used when OrganPrompt has no route override."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                templates={"chat": "PROMPT_CHAT"},
                fallback="PROMPT_FALLBACK",
            ),
            organ_prompts={
                "cerebrum": OrganPrompt(
                    route_templates={},  # no route overrides
                ),
            },
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "PROMPT_CHAT" in result

    async def test_fallback_third_priority(self):
        """PromptPreset.fallback used when route not in templates."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                templates={},  # empty
                fallback="PROMPT_FALLBACK",
            ),
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "PROMPT_FALLBACK" in result

    async def test_organ_route_for_specific_route_overrides_prompt(self):
        """Organ route_template for 'tool' overrides PromptPreset 'tool'."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                templates={"tool": "PROMPT_TOOL"},
            ),
            organ_prompts={
                "cerebrum": OrganPrompt(
                    route_templates={"tool": "ORGAN_TOOL"},
                ),
            },
        )
        result = await bs.build_system_prompt("cerebrum", "tool")
        assert "ORGAN_TOOL" in result
        assert "PROMPT_TOOL" not in result

    async def test_organ_route_only_overrides_specific_route(self):
        """Organ overrides 'chat' but not 'tool'."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(
                name="test",
                templates={"chat": "PROMPT_CHAT", "tool": "PROMPT_TOOL"},
            ),
            organ_prompts={
                "cerebrum": OrganPrompt(
                    route_templates={"chat": "ORGAN_CHAT"},
                ),
            },
        )
        r_chat = await bs.build_system_prompt("cerebrum", "chat")
        r_tool = await bs.build_system_prompt("cerebrum", "tool")
        assert "ORGAN_CHAT" in r_chat
        assert "PROMPT_TOOL" in r_tool

    async def test_hardcoded_fallback_when_all_empty(self):
        """When both templates and fallback are empty → hardcoded default."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PromptPreset(name="test", templates={}, fallback=""),
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "MeowCat" in result
        assert "helpful AI assistant" in result


# =========================================================================
# NoopBrainstem — new signature (v1.3.6)
# =========================================================================


@pytest.mark.asyncio
class TestNoopBrainstemV136:

    async def test_new_signature_accepts_organ_and_route(self):
        """NoopBrainstem accepts organ + route + optional snapshot."""
        nb = NoopBrainstem()
        result = await nb.build_system_prompt("cerebrum", "chat")
        assert result == ""

    async def test_new_signature_with_snapshot(self):
        """NoopBrainstem accepts snapshot (ignores it)."""
        nb = NoopBrainstem()
        snap = SelfSnapshot(personality={"tone": "x"})
        result = await nb.build_system_prompt(
            "cerebrum", "chat", cat_self_snapshot=snap,
        )
        assert result == ""

    async def test_inject_cat_self_default_true(self):
        """NoopBrainstem.inject_cat_self defaults to True."""
        nb = NoopBrainstem()
        assert nb.inject_cat_self is True

    async def test_plug_still_works_with_new_signature(self):
        """Plugs receive organ, route, snapshot."""
        nb = NoopBrainstem()
        nb.mount_plug(
            "build_system_prompt",
            lambda organ, route, snapshot=None: f"{organ}/{route}",
        )
        result = await nb.build_system_prompt("cerebrum", "chat")
        assert result == "cerebrum/chat"


# =========================================================================
# BrainStemProtocol runtime_checkable
# =========================================================================


class TestBrainStemProtocolV136:

    def test_valid_implementation(self):
        """A class with inject_cat_self + build_system_prompt(organ, route, snapshot) passes."""
        class ValidBS:
            inject_cat_self: bool = True

            def build_system_prompt(
                self, organ: str, route: str, cat_self_snapshot=None,
            ) -> str:
                return ""

            def cancel_current(self) -> bool:
                return False

        assert isinstance(ValidBS(), BrainStemProtocol)

    def test_missing_inject_cat_self_fails(self):
        """Missing inject_cat_self → not a BrainStemProtocol."""
        class NoInject:
            def build_system_prompt(
                self, organ: str, route: str, cat_self_snapshot=None,
            ) -> str:
                return ""

            def cancel_current(self) -> bool:
                return False

        assert not isinstance(NoInject(), BrainStemProtocol)

    def test_old_signature_fails(self):
        """Old build_system_prompt(route) still passes (duck typing), but no inject_cat_self."""
        class OldBS:
            def build_system_prompt(self, route: str) -> str:
                return ""

            def cancel_current(self) -> bool:
                return False

        # Missing inject_cat_self → fails runtime check
        assert not isinstance(OldBS(), BrainStemProtocol)

    def test_renovated_brainstem_passes(self):
        """RenovatedBrainstem is a BrainStemProtocol."""
        assert isinstance(RenovatedBrainstem(), BrainStemProtocol)

    def test_noop_brainstem_passes(self):
        """NoopBrainstem is a BrainStemProtocol."""
        assert isinstance(NoopBrainstem(), BrainStemProtocol)


# =========================================================================
# BrainStemAgent — delegation (v1.3.6)
# =========================================================================


class TestBrainStemAgentV136:

    def test_delegation_new_signature(self):
        """BrainStemAgent delegates with organ + route + snapshot."""
        class PromptAgent:
            async def build_system_prompt(
                self, organ, route, cat_self_snapshot=None,
            ):
                return f"{organ}|{route}"

        agent = BrainstemAgent(PromptAgent())
        result = asyncio.run(
            agent.build_system_prompt("cerebrum", "chat"),
        )
        assert result == "cerebrum|chat"

    def test_delegation_with_snapshot(self):
        """BrainStemAgent passes snapshot through."""
        class PromptAgent:
            async def build_system_prompt(
                self, organ, route, cat_self_snapshot=None,
            ):
                return f"snap={cat_self_snapshot is not None}"

        agent = BrainstemAgent(PromptAgent())
        snap = SelfSnapshot(personality={"tone": "x"})
        result = asyncio.run(
            agent.build_system_prompt(
                "cerebrum", "tool", cat_self_snapshot=snap,
            ),
        )
        assert "snap=True" in result


# =========================================================================
# RenovatedBrainstem properties & diagnose
# =========================================================================


class TestRenovatedBrainstemProperties:

    def test_organ_prompts_property_empty(self):
        """organ_prompts property returns empty dict by default."""
        bs = RenovatedBrainstem()
        assert bs.organ_prompts == {}

    def test_organ_prompts_property_with_data(self):
        """organ_prompts property returns the dict."""
        op = OrganPrompt(identity="test")
        bs = RenovatedBrainstem(organ_prompts={"cerebrum": op})
        assert "cerebrum" in bs.organ_prompts
        assert bs.organ_prompts["cerebrum"] is op

    def test_diagnose_includes_organ_prompts(self):
        """diagnose() includes organ_prompts keys."""
        bs = RenovatedBrainstem(
            organ_prompts={
                "cerebrum": OrganPrompt(),
                "cerebellum": OrganPrompt(),
            },
        )
        diag = bs.diagnose()
        assert "organ_prompts" in diag
        assert set(diag["organ_prompts"]) == {"cerebrum", "cerebellum"}

    def test_diagnose_includes_inject_cat_self(self):
        """diagnose() includes inject_cat_self."""
        bs = RenovatedBrainstem()
        diag = bs.diagnose()
        assert diag["inject_cat_self"] is True

    def test_diagnose_includes_prompt_preset(self):
        """diagnose() includes prompt_preset name."""
        bs = RenovatedBrainstem(prompt=PROMPT_ZH)
        diag = bs.diagnose()
        assert diag["prompt_preset"] == "zh"


# =========================================================================
# Plugin override chain
# =========================================================================


@pytest.mark.asyncio
class TestRenovatedBrainstemPlugin:

    async def test_plugin_full_override(self):
        """Plugin returning a string completely replaces the assembly chain."""
        bs = RenovatedBrainstem(
            cat_name="Kitty",
            prompt=PROMPT_ZH,
            organ_prompts={
                "cerebrum": OrganPrompt(identity="BRAIN_LAYER"),
            },
        )
        bs.mount_plug(
            "build_system_prompt",
            lambda organ, route, snapshot=None: "PLUGIN_OVERRIDE",
        )
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert result == "PLUGIN_OVERRIDE"

    async def test_plugin_multiple_merge(self):
        """Multiple plugins → concatenated."""
        bs = RenovatedBrainstem()
        bs.mount_plug("build_system_prompt", lambda *a, **kw: "LINE1")
        bs.mount_plug("build_system_prompt", lambda *a, **kw: "LINE2")
        result = await bs.build_system_prompt("cerebrum", "chat")
        assert "LINE1" in result
        assert "LINE2" in result
