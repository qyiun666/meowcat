# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.1.5 — LLM 货架 + 级联查找测试
===================================

验证:
    1. TestModelConfig           — ModelConfig 创建和字段
    2. TestLLMShelf            — Colony.llm_shelf / stock / unstock
    3. TestPickLLM             — pick_llm 命名/默认/空货架/缺失
    4. TestPickLLMPlugin       — on_pick 插件自定义领取
    5. TestAssembleCat         — assemble_cat LLM 解析
    6. TestToolCascade         — ToolRegistry 双层查找
    7. TestSkillCascade        — SkillRegistry 双层查找
"""

from __future__ import annotations

import pytest

from meowcat.colony import Colony
from meowcat.models import ModelConfig
from meowcat.tools.skill import Skill, SkillRegistry, SkillSpec
from meowcat.tools.tool import Tool, ToolRegistry, ToolSpec

# -- 1. ModelConfig --------------------------------------------------------

class TestModelConfig:
    """ModelConfig 基础构造和字段。"""

    def test_defaults(self) -> None:
        cfg = ModelConfig(model="gpt-4o-mini")
        assert cfg.model == "gpt-4o-mini"
        assert cfg.provider == "openai"
        assert cfg.api_key == ""
        assert cfg.base_url == ""
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096
        assert cfg.extra == {}

    def test_custom(self) -> None:
        cfg = ModelConfig(
            model="deepseek-v3",
            provider="deepseek",
            api_key="sk-xxx",
            base_url="https://api.deepseek.com",
            temperature=0.3,
            max_tokens=8192,
            extra={"top_p": 0.9},
        )
        assert cfg.model == "deepseek-v3"
        assert cfg.provider == "deepseek"
        assert cfg.base_url == "https://api.deepseek.com"
        assert cfg.extra["top_p"] == 0.9


# -- 2. LLM 货架 ---------------------------------------------------------

class TestLLMShelf:
    """Colony LLM 货架属性操作。"""

    def test_empty_shelf_by_default(self) -> None:
        colony = Colony("test")
        assert colony.llm_shelf == {}

    def test_shelf_from_init(self) -> None:
        shelf = {"fast": ModelConfig(model="gpt-4o-mini")}
        colony = Colony("test", llm_shelf=shelf)
        assert "fast" in colony.llm_shelf
        assert colony.llm_shelf["fast"].model == "gpt-4o-mini"

    def test_stock_unstock(self) -> None:
        colony = Colony("test")
        fast = ModelConfig(model="gpt-4o-mini")
        smart = ModelConfig(model="gpt-4o")

        colony.stock_llm("fast", fast)
        colony.stock_llm("smart", smart)
        assert len(colony.llm_shelf) == 2

        removed = colony.unstock_llm("fast")
        assert removed is True
        assert "fast" not in colony.llm_shelf
        assert "smart" in colony.llm_shelf

    def test_unstock_nonexistent(self) -> None:
        colony = Colony("test")
        assert colony.unstock_llm("nope") is False

    def test_stock_overwrite(self) -> None:
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))
        colony.stock_llm("fast", ModelConfig(model="gpt-4o"))
        assert colony.llm_shelf["fast"].model == "gpt-4o"

    def test_shelf_is_copy(self) -> None:
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))
        shelf_copy = colony.llm_shelf
        shelf_copy["new"] = ModelConfig(model="fake")
        # 原始货架不受影响
        assert "new" not in colony.llm_shelf


# -- 3. pick_llm ---------------------------------------------------------

class TestPickLLM:
    """pick_llm 级联查找。"""

    def test_pick_by_name(self) -> None:
        colony = Colony("test")
        fast = ModelConfig(model="gpt-4o-mini")
        smart = ModelConfig(model="gpt-4o")
        colony.stock_llm("fast", fast)
        colony.stock_llm("smart", smart)

        assert colony.pick_llm("smart") is smart
        assert colony.pick_llm("fast") is fast

    def test_pick_first_available(self) -> None:
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))
        colony.stock_llm("smart", ModelConfig(model="gpt-4o"))

        picked = colony.pick_llm()
        # 返回第一个 (dict 保持插入顺序)
        assert picked.model == "gpt-4o-mini"

    def test_pick_empty_shelf_raises(self) -> None:
        colony = Colony("test")
        with pytest.raises(ValueError, match="empty"):
            colony.pick_llm()

    def test_pick_missing_name_raises(self) -> None:
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))
        with pytest.raises(KeyError, match="smart"):
            colony.pick_llm("smart")


# -- 4. on_pick plugin ---------------------------------------------------

class TestPickLLMPlugin:
    """on_pick 插件自定义领取策略。"""

    def test_on_pick_plugin_overrides(self) -> None:
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))
        colony.stock_llm("smart", ModelConfig(model="gpt-4o"))

        # 插件: 始终返回 "smart"
        colony.plug("on_pick", lambda name, shelf: shelf["smart"])

        picked = colony.pick_llm("fast")  # 请求 "fast", 插件返回 "smart"
        assert picked.model == "gpt-4o"

    def test_on_pick_fallback_uses_default(self) -> None:
        """插件不返回 ModelConfig 时回退到默认逻辑。"""
        colony = Colony("test")
        colony.stock_llm("fast", ModelConfig(model="gpt-4o-mini"))

        # 插件返回 None (不匹配)
        colony.plug("on_pick", lambda name, shelf: None)

        picked = colony.pick_llm("fast")
        assert picked.model == "gpt-4o-mini"


# -- 5. assemble_cat -----------------------------------------------------

class TestAssembleCat:
    """assemble_cat LLM 解析。"""

    def test_assemble_with_named_llm(self) -> None:
        colony = Colony("test")
        colony.stock_llm("smart", ModelConfig(model="gpt-4o"))

        cat = colony.assemble_cat(name="planner", llm="smart")
        assert cat._llm_config.model == "gpt-4o"
        assert cat.name == "planner"
        assert cat.container is colony

    def test_assemble_with_own_llm(self) -> None:
        colony = Colony("test")
        own = ModelConfig(model="claude-3-opus", provider="anthropic")

        cat = colony.assemble_cat(name="planner", llm=own)
        assert cat._llm_config is own
        assert cat._llm_config.provider == "anthropic"

    def test_assemble_auto_pick(self) -> None:
        colony = Colony("test")
        colony.stock_llm("default", ModelConfig(model="gpt-4o-mini"))

        cat = colony.assemble_cat(name="planner")
        assert cat._llm_config.model == "gpt-4o-mini"

    def test_assemble_cat_is_registered(self) -> None:
        colony = Colony("test")
        colony.stock_llm("default", ModelConfig(model="gpt-4o-mini"))

        cat = colony.assemble_cat(name="planner")
        assert colony.list_cats() == [cat.cat_uid]
        assert colony.get_cat(cat.cat_uid) is cat

    def test_assemble_with_parent_id(self) -> None:
        colony = Colony("test")
        colony.stock_llm("default", ModelConfig(model="gpt-4o-mini"))

        kitten = colony.assemble_cat(name="kitten", parent_id="main-cat")
        assert kitten.parent_id == "main-cat"
        assert kitten._llm_config.model == "gpt-4o-mini"


# -- 6. ToolRegistry 双层查找 --------------------------------------------

class TestToolCascade:
    """ToolRegistry.resolve 私有 → 共享级联。"""

    def _make_tool(self, name: str) -> Tool:
        return Tool(ToolSpec(name=name, description=f"Tool {name}"))

    def test_resolve_private_first(self) -> None:
        private = ToolRegistry()
        shared = ToolRegistry()
        private.set_shared(shared)

        t = self._make_tool("my_tool")
        private.register(t)

        assert private.resolve("my_tool") is t

    def test_resolve_fallthrough_to_shared(self) -> None:
        private = ToolRegistry()
        shared = ToolRegistry()
        private.set_shared(shared)

        t = self._make_tool("shared_tool")
        shared.register(t)

        assert private.resolve("shared_tool") is t

    def test_resolve_private_shadows_shared(self) -> None:
        private = ToolRegistry()
        shared = ToolRegistry()
        private.set_shared(shared)

        t_private = self._make_tool("same_name")
        t_shared = self._make_tool("same_name")
        private.register(t_private)
        shared.register(t_shared)

        assert private.resolve("same_name") is t_private

    def test_resolve_not_found(self) -> None:
        private = ToolRegistry()
        shared = ToolRegistry()
        private.set_shared(shared)

        assert private.resolve("nope") is None

    def test_resolve_without_shared(self) -> None:
        private = ToolRegistry()
        # 未设置 shared
        assert private.resolve("nope") is None


# -- 7. SkillRegistry 双层查找 -------------------------------------------

class TestSkillCascade:
    """SkillRegistry.resolve 私有 → 共享级联。"""

    def _make_skill(self, name: str) -> Skill:
        return Skill(SkillSpec(name=name, description=f"Skill {name}"))

    def test_resolve_private_first(self) -> None:
        private = SkillRegistry()
        shared = SkillRegistry()
        private.set_shared(shared)

        s = self._make_skill("my_skill")
        private.register(s)

        assert private.resolve("my_skill") is s

    def test_resolve_fallthrough_to_shared(self) -> None:
        private = SkillRegistry()
        shared = SkillRegistry()
        private.set_shared(shared)

        s = self._make_skill("shared_skill")
        shared.register(s)

        assert private.resolve("shared_skill") is s

    def test_resolve_not_found(self) -> None:
        private = SkillRegistry()
        shared = SkillRegistry()
        private.set_shared(shared)

        assert private.resolve("nope") is None

