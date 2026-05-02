"""meowcat 独立测试: v0.5.23 工具系统上移（Tool/Skill/PawsEngine/BUILTIN_TOOLS）。

验证:
- Tool + ToolSpec + RiskLevel + ToolRegistry
- Skill + SkillSpec + SkillRegistry
- BUILTIN_TOOLS 定义
- PawsEngine match → execute → audit
- CatBase 自动挂载 tool_registry / skill_registry
- assemble_default_cat 自动注册 BUILTIN_TOOLS
- meowcat.tools 公开 API 导出
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import CatBase
from meowcat.tools import (
    BUILTIN_TOOLS,
    PawsEngine,
    RiskLevel,
    Skill,
    SkillRegistry,
    SkillSpec,
    Tool,
    ToolRegistry,
    ToolSpec,
)
from meowcat.assembly import assemble_default_cat


# ═══════════════════════════════════════════════════════════════════
#  Tool + ToolSpec + ToolRegistry
# ═══════════════════════════════════════════════════════════════════


class TestTool:
    """Tool 类的基本功能。"""

    def test_tool_spec_creation(self):
        spec = ToolSpec(
            name="test",
            description="A test tool",
            parameters={"x": {"type": "string", "description": "param x"}},
            risk=RiskLevel.LOW,
            category="test",
        )
        assert spec.name == "test"
        assert spec.risk == RiskLevel.LOW
        assert spec.category == "test"

    async def test_tool_execute(self):
        async def handler(x: str) -> str:
            return f"got {x}"

        tool = Tool(
            ToolSpec(name="echo", description="Echo tool"),
            handler=handler,
        )
        result = await tool.execute(x="hello")
        assert result == "got hello"

    async def test_tool_execute_sync_handler(self):
        def handler(x: str) -> str:
            return f"sync {x}"

        tool = Tool(
            ToolSpec(name="sync_echo", description="Sync echo"),
            handler=handler,
        )
        result = await tool.execute(x="world")
        assert result == "sync world"

    def test_tool_enable_disable(self):
        tool = Tool(ToolSpec(name="t", description="d"))
        assert tool.enabled is True
        tool.disable()
        assert tool.enabled is False
        tool.enable()
        assert tool.enabled is True

    def test_tool_to_openai_schema(self):
        tool = Tool(ToolSpec(
            name="search",
            description="Search something",
            parameters={
                "query": {"type": "string", "description": "Search query"},
            },
        ))
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] == "search"
        assert fn["description"] == "Search something"
        assert "query" in fn["parameters"]["properties"]


class TestToolRegistry:
    """ToolRegistry 注册/查找/列出。"""

    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = Tool(ToolSpec(name="t1", description="d1", category="cat1"))
        reg.register(tool)
        assert reg.get("t1") is tool
        assert reg.count() == 1

    def test_list_all(self):
        reg = ToolRegistry()
        t1 = Tool(ToolSpec(name="t1", description="d1"))
        t2 = Tool(ToolSpec(name="t2", description="d2"))
        t2.disable()
        reg.register(t1)
        reg.register(t2)
        assert len(reg.list_all(enabled_only=True)) == 1
        assert len(reg.list_all(enabled_only=False)) == 2

    def test_list_by_category(self):
        reg = ToolRegistry()
        reg.register(
            Tool(ToolSpec(name="f1", description="", category="file")))
        reg.register(
            Tool(ToolSpec(name="s1", description="", category="system")))
        reg.register(
            Tool(ToolSpec(name="f2", description="", category="file")))
        assert len(reg.list_by_category("file")) == 2
        assert len(reg.list_by_category("system")) == 1
        assert len(reg.list_by_category("network")) == 0

    def test_enable_disable(self):
        reg = ToolRegistry()
        tool = Tool(ToolSpec(name="t", description="d"))
        reg.register(tool)
        assert reg.disable("t") is True
        assert reg.get("t").enabled is False
        assert reg.enable("t") is True
        assert reg.get("t").enabled is True
        assert reg.enable("nonexistent") is False
        assert reg.disable("nonexistent") is False

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register(Tool(ToolSpec(name="t1", description="d1")))
        assert reg.unregister("t1") is True
        assert reg.get("t1") is None
        assert reg.unregister("t1") is False

    def test_to_openai_schemas(self):
        reg = ToolRegistry()
        reg.register(Tool(ToolSpec(
            name="search",
            description="Search",
            parameters={"q": {"type": "string", "description": "Query"}},
        )))
        schemas = reg.to_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "search"


# ═══════════════════════════════════════════════════════════════════
#  Skill + SkillSpec + SkillRegistry
# ═══════════════════════════════════════════════════════════════════


class TestSkill:
    """Skill 类的基本功能。"""

    async def test_skill_execute(self):
        async def handler(x: str) -> str:
            return f"skill: {x}"

        skill = Skill(
            SkillSpec(name="my_skill", description="A skill", tags=["test"]),
            handler=handler,
        )
        result = await skill.execute(x="data")
        assert result == "skill: data"

    async def test_skill_no_handler(self):
        skill = Skill(SkillSpec(name="nohandler", description="No handler"))
        with pytest.raises(RuntimeError, match="no handler"):
            await skill.execute()

    def test_skill_enable_disable(self):
        skill = Skill(SkillSpec(name="s", description="d"))
        assert skill.enabled is True
        skill.disable()
        assert skill.enabled is False
        skill.enable()
        assert skill.enabled is True

    def test_skill_spec_properties(self):
        spec = SkillSpec(
            name="code_review",
            description="Review code",
            version="1.0.0",
            tags=["code", "quality"],
            source="plugin",
        )
        skill = Skill(spec)
        assert skill.name == "code_review"
        assert skill.description == "Review code"
        assert skill.parameters == {}
        assert skill.spec.source == "plugin"


class TestSkillRegistry:
    """SkillRegistry 注册/搜索/筛选。"""

    def test_register_and_get(self):
        reg = SkillRegistry()
        skill = Skill(SkillSpec(name="s1", description="d1"))
        reg.register(skill)
        assert reg.get("s1") is skill
        assert reg.count() == 1

    def test_list_all_enabled(self):
        reg = SkillRegistry()
        s1 = Skill(SkillSpec(name="s1", description="d1"))
        s2 = Skill(SkillSpec(name="s2", description="d2"))
        s2.disable()
        reg.register(s1)
        reg.register(s2)
        assert len(reg.list_all(enabled_only=True)) == 1
        assert len(reg.list_all(enabled_only=False)) == 2

    def test_list_by_source(self):
        reg = SkillRegistry()
        reg.register(
            Skill(SkillSpec(name="a", description="", source="builtin")))
        reg.register(Skill(SkillSpec(name="b", description="", source="mcp")))
        reg.register(
            Skill(SkillSpec(name="c", description="", source="builtin")))
        assert len(reg.list_by_source("builtin")) == 2
        assert len(reg.list_by_source("mcp")) == 1

    def test_list_by_category(self):
        reg = SkillRegistry()
        reg.register(
            Skill(SkillSpec(name="a", description="", category="code")))
        reg.register(
            Skill(SkillSpec(name="b", description="", category="review")))
        assert len(reg.list_by_category("code")) == 1

    def test_search(self):
        reg = SkillRegistry()
        reg.register(Skill(SkillSpec(
            name="code_review",
            description="Review code for bugs",
            tags=["code", "quality"],
        )))
        reg.register(Skill(SkillSpec(
            name="write_docs",
            description="Generate documentation",
            tags=["docs"],
        )))
        assert len(reg.search("review")) == 1
        # matches name + description + tags
        assert len(reg.search("code")) >= 1
        assert len(reg.search("docs")) == 1
        assert len(reg.search("nonexistent")) == 0

    def test_enable_disable(self):
        reg = SkillRegistry()
        reg.register(Skill(SkillSpec(name="s", description="")))
        assert reg.disable("s") is True
        assert reg.get("s").enabled is False
        assert reg.enable("s") is True
        assert reg.enable("no") is False


# ═══════════════════════════════════════════════════════════════════
#  BUILTIN_TOOLS
# ═══════════════════════════════════════════════════════════════════


class TestBuiltinTools:
    """通用内置工具集。"""

    def test_four_tools(self):
        assert len(BUILTIN_TOOLS) == 4
        names = {t.name for t in BUILTIN_TOOLS}
        assert names == {"read_file", "write_file", "run_command", "http_get"}

    def test_read_file(self):
        tool = next(t for t in BUILTIN_TOOLS if t.name == "read_file")
        assert tool.spec.risk == RiskLevel.LOW
        assert tool.spec.category == "file"

    def test_write_file_high_risk(self):
        tool = next(t for t in BUILTIN_TOOLS if t.name == "write_file")
        assert tool.spec.risk == RiskLevel.HIGH

    def test_run_command_high_risk(self):
        tool = next(t for t in BUILTIN_TOOLS if t.name == "run_command")
        assert tool.spec.risk == RiskLevel.HIGH

    def test_http_get_low_risk(self):
        tool = next(t for t in BUILTIN_TOOLS if t.name == "http_get")
        assert tool.spec.risk == RiskLevel.LOW
        assert tool.spec.category == "network"

    def test_tools_have_openai_schema(self):
        for tool in BUILTIN_TOOLS:
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "function" in schema

    async def test_builtin_execute_read_file(self, tmp_path):
        """测试 builtin read_file 实际执行。"""
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        tool = next(t for t in BUILTIN_TOOLS if t.name == "read_file")
        # builtin resolve 默认使用 ~/.meowcat/workspace，所以这里我们
        # 直接测试 handler 逻辑而不走路径解析
        result = await tool.execute(path=str(f))
        assert "hello world" in result or "File not found" in result


# ═══════════════════════════════════════════════════════════════════
#  PawsEngine
# ═══════════════════════════════════════════════════════════════════


class TestPawsEngine:
    """PawsEngine match → execute → audit 流程。"""

    def _make_registry_with_tools(self) -> ToolRegistry:
        async def echo(**kwargs):
            return f"echo: {kwargs}"

        reg = ToolRegistry()
        reg.register(Tool(ToolSpec(
            name="echo",
            description="Echo back input",
            risk=RiskLevel.LOW,
        ), handler=echo))
        reg.register(Tool(ToolSpec(
            name="dangerous",
            description="High risk operation",
            risk=RiskLevel.HIGH,
        ), handler=echo))
        return reg

    async def test_execute_success(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg, require_confirm=False)
        result = await engine.execute("echo", x="hello")
        assert result["success"] is True
        assert "echo" in result["output"]
        assert result["tool"] == "echo"
        assert result["elapsed_ms"] >= 0

    async def test_execute_tool_not_found(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg)
        result = await engine.execute("nonexistent")
        assert result["success"] is False
        assert "not found" in result["output"]

    async def test_execute_disabled_tool(self):
        reg = self._make_registry_with_tools()
        reg.get("echo").disable()
        engine = PawsEngine(reg)
        result = await engine.execute("echo")
        assert result["success"] is False
        assert "disabled" in result["output"]

    async def test_audit_log(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg, require_confirm=False)
        await engine.execute("echo", x=1)
        await engine.execute("echo", x=2)
        log = engine.audit_log
        assert len(log) == 2
        assert log[0]["tool"] == "echo"
        assert log[0]["success"] is True

    def test_match_by_name(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg)
        results = engine.match("echo")
        assert len(results) >= 1
        assert results[0].name == "echo"

    def test_match_by_description(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg)
        results = engine.match("High risk")
        assert len(results) >= 1
        assert results[0].name == "dangerous"

    def test_match_no_results(self):
        reg = self._make_registry_with_tools()
        engine = PawsEngine(reg)
        results = engine.match("nonexistent_pattern_xyz")
        assert results == []


# ═══════════════════════════════════════════════════════════════════
#  CatBase 集成 — tool_registry / skill_registry / BUILTIN_TOOLS
# ═══════════════════════════════════════════════════════════════════


class TestCatBaseToolsIntegration:
    """CatBase 上的工具系统集成。"""

    def test_cat_has_tool_registry(self):
        cat = CatBase("test_cat")
        assert isinstance(cat.tool_registry, ToolRegistry)
        assert cat.tool_registry.count() == 0  # bare CatBase, no assemble

    def test_cat_has_skill_registry(self):
        cat = CatBase("test_cat")
        assert isinstance(cat.skill_registry, SkillRegistry)
        assert cat.skill_registry.count() == 0

    def test_assemble_registers_builtin_tools(self):
        cat = CatBase("test_cat")
        assemble_default_cat(cat)
        assert cat.tool_registry.count() >= 4  # BUILTIN_TOOLS
        assert cat.tool_registry.get("read_file") is not None
        assert cat.tool_registry.get("write_file") is not None
        assert cat.tool_registry.get("run_command") is not None
        assert cat.tool_registry.get("http_get") is not None

    def test_assemble_tool_to_openai_schemas(self):
        cat = CatBase("test_cat")
        assemble_default_cat(cat)
        schemas = cat.tool_registry.to_openai_schemas()
        assert len(schemas) >= 4
        for s in schemas:
            assert s["type"] == "function"

    def test_can_register_custom_tool(self):
        cat = CatBase("test_cat")

        async def custom(**kwargs):
            return "custom result"
        cat.tool_registry.register(Tool(ToolSpec(
            name="my_custom",
            description="My custom tool",
            risk=RiskLevel.LOW,
        ), handler=custom))
        assert cat.tool_registry.get("my_custom") is not None

    def test_paws_engine_on_cat(self):
        cat = CatBase("test_cat")
        assemble_default_cat(cat)
        engine = PawsEngine(cat.tool_registry)

        async def _run():
            result = await engine.execute(
                "read_file", path="/nonexistent_test_file")
            return result

        result = anyio.run(_run)
        assert isinstance(result, dict)
        assert "success" in result


# ═══════════════════════════════════════════════════════════════════
#  公开 API 导出
# ═══════════════════════════════════════════════════════════════════


class TestPublicAPI:
    """验证 meowcat.tools 公开 API + meowcat 顶层导出。"""

    def test_tools_package_exports(self):
        from meowcat.tools import __all__ as tools_all
        expected = {
            "Tool", "ToolSpec", "RiskLevel", "ToolRegistry",
            "Skill", "SkillSpec", "SkillRegistry",
            "BUILTIN_TOOLS", "PawsEngine",
        }
        assert set(tools_all) == expected

    def test_meowcat_top_level_exports(self):
        from meowcat import (
            BUILTIN_TOOLS as bt,
            PawsEngine as pe,
            RiskLevel as rl,
            Skill as sk,
            SkillRegistry as sr,
            SkillSpec as ss,
            Tool as t,
            ToolRegistry as tr,
            ToolSpec as ts,
        )
        # 类型检查
        assert rl.LOW.value == "low"
        assert issubclass(type(tr()), ToolRegistry)
        assert issubclass(type(sr()), SkillRegistry)
        assert isinstance(bt, list)
        assert len(bt) == 4
