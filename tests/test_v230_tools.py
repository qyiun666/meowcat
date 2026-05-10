# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for v2.3.0: tools/ layer coverage (tool, paws, matcher).

Covers H-10 remediation targets:
- tool.py: Tool/ToolSpec/ToolRegistry (register, execute, enable/disable, cascade)
- paws.py: PawsEngine (execute flow, match, audit log)
- matcher.py: KeywordToolMatcher (keyword scoring, plug/unplug, filters)
"""

from __future__ import annotations

import asyncio

import pytest

from meowcat.tools.matcher import KeywordToolMatcher, _tokenize
from meowcat.tools.paws import PawsEngine
from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec


# ── ToolSpec & RiskLevel tests ──────────────────────────────────────


class TestRiskLevel:
    def test_enum_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


class TestToolSpec:
    def test_creation_minimal(self):
        spec = ToolSpec(name="test", description="A test tool")
        assert spec.name == "test"
        assert spec.description == "A test tool"
        assert spec.parameters == {}
        assert spec.risk == RiskLevel.MEDIUM
        assert spec.category == "general"

    def test_creation_full(self):
        spec = ToolSpec(
            name="read",
            description="Read file",
            parameters={"path": {"type": "string",
                                 "description": "File path"}},
            risk=RiskLevel.HIGH,
            category="file",
        )
        assert spec.name == "read"
        assert spec.parameters["path"]["type"] == "string"
        assert spec.risk == RiskLevel.HIGH
        assert spec.category == "file"


# ── Tool tests ──────────────────────────────────────────────────────


class TestTool:
    @pytest.fixture
    def tool(self):
        return Tool(
            ToolSpec(name="echo", description="Echo back input",
                     category="util"),
            handler=None,
        )

    def test_creation(self, tool):
        assert tool.name == "echo"
        assert tool.description == "Echo back input"
        assert tool.enabled is True

    def test_enable_disable(self, tool):
        tool.disable()
        assert tool.enabled is False
        tool.enable()
        assert tool.enabled is True

    def test_enabled_setter(self, tool):
        tool.enabled = False
        assert tool.enabled is False
        tool.enabled = True
        assert tool.enabled is True

    @pytest.mark.anyio
    async def test_execute_sync_handler(self):
        def handler(x: int) -> int:
            return x * 2

        tool = Tool(
            ToolSpec(name="double", description="Double a number"),
            handler=handler,
        )
        result = await tool.execute(x=3)
        assert result == "6"

    @pytest.mark.anyio
    async def test_execute_async_handler(self):
        async def handler(x: int) -> str:
            await asyncio.sleep(0.001)
            return f"got {x}"

        tool = Tool(
            ToolSpec(name="async_echo", description="Async echo"),
            handler=handler,
        )
        result = await tool.execute(x=42)
        assert result == "got 42"

    @pytest.mark.anyio
    async def test_execute_no_handler_raises(self):
        tool = Tool(ToolSpec(name="noop", description="No handler"))
        with pytest.raises(RuntimeError, match="has no handler"):
            await tool.execute()

    @pytest.mark.anyio
    async def test_execute_handler_raises(self):
        def handler(**kwargs):
            raise ValueError("bad input")

        tool = Tool(
            ToolSpec(name="bomb", description="Always fails"),
            handler=handler,
        )
        result = await tool.execute()
        assert result.startswith("Error executing 'bomb':")

    def test_to_openai_schema_basic(self):
        tool = Tool(
            ToolSpec(
                name="read_file",
                description="Read file contents",
                parameters={"path": {"type": "string",
                                     "description": "File path"}},
            ),
        )
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "read_file"
        assert schema["function"]["description"] == "Read file contents"
        assert schema["function"]["parameters"]["type"] == "object"
        assert "path" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["path"]

    def test_to_openai_schema_array_items(self):
        tool = Tool(
            ToolSpec(
                name="search",
                description="Search",
                parameters={
                    "keywords": {
                        "type": "array",
                        "description": "Keywords",
                        "items": {"type": "string"},
                    }
                },
            ),
        )
        schema = tool.to_openai_schema()
        props = schema["function"]["parameters"]["properties"]
        assert props["keywords"]["type"] == "array"
        assert props["keywords"]["items"] == {"type": "string"}


# ── ToolRegistry tests ──────────────────────────────────────────────


class TestToolRegistry:
    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    @pytest.fixture
    def echo_tool(self):
        return Tool(
            ToolSpec(
                name="echo",
                description="Echo back input",
                category="util",
                risk=RiskLevel.LOW,
            ),
        )

    @pytest.fixture
    def read_tool(self):
        return Tool(
            ToolSpec(
                name="read",
                description="Read file",
                category="file",
                risk=RiskLevel.MEDIUM,
            ),
        )

    def test_register_and_get(self, registry, echo_tool):
        registry.register(echo_tool)
        assert registry.get("echo") is echo_tool
        assert registry.count() == 1

    def test_register_duplicate(self, registry, echo_tool):
        registry.register(echo_tool)
        tool2 = Tool(
            ToolSpec(name="echo", description="New echo", category="new"),
        )
        registry.register(tool2)  # overwrites
        assert registry.get("echo") is tool2

    def test_unregister(self, registry, echo_tool):
        registry.register(echo_tool)
        assert registry.unregister("echo") is True
        assert registry.get("echo") is None
        assert registry.count() == 0

    def test_unregister_missing(self, registry):
        assert registry.unregister("nope") is False

    def test_resolve_private_only(self, registry, echo_tool):
        registry.register(echo_tool)
        assert registry.resolve("echo") is echo_tool
        assert registry.resolve("nope") is None

    def test_resolve_cascade_shared(self, registry, echo_tool):
        shared = ToolRegistry()
        shared.register(echo_tool)
        registry.set_shared(shared)
        # resolve should find in shared when not in private
        assert registry.resolve("echo") is echo_tool

    def test_resolve_private_first(self, registry, echo_tool, read_tool):
        # private shadows shared
        shared = ToolRegistry()
        shared_tool = Tool(
            ToolSpec(name="echo", description="Shared echo", category="shared"),
        )
        shared.register(shared_tool)
        registry.register(echo_tool)
        registry.set_shared(shared)
        assert registry.resolve("echo") is echo_tool  # private wins

    def test_list_all_with_disabled(self, registry, echo_tool, read_tool):
        registry.register(echo_tool)
        registry.register(read_tool)
        read_tool.disable()
        # enabled_only=True (default)
        enabled = registry.list_all()
        assert len(enabled) == 1
        assert enabled[0] is echo_tool
        # enabled_only=False
        all_tools = registry.list_all(enabled_only=False)
        assert len(all_tools) == 2

    def test_list_by_category(self, registry, echo_tool, read_tool):
        registry.register(echo_tool)
        registry.register(read_tool)
        util_tools = registry.list_by_category("util")
        assert len(util_tools) == 1
        assert util_tools[0] is echo_tool

    def test_list_by_category_empty(self, registry):
        assert registry.list_by_category("nope") == []

    def test_count(self, registry, echo_tool, read_tool):
        assert registry.count() == 0
        registry.register(echo_tool)
        assert registry.count() == 1
        registry.register(read_tool)
        assert registry.count() == 2

    def test_enable_disable_by_name(self, registry, echo_tool):
        registry.register(echo_tool)
        assert registry.disable("echo") is True
        assert echo_tool.enabled is False
        assert registry.enable("echo") is True
        assert echo_tool.enabled is True

    def test_enable_disable_missing(self, registry):
        assert registry.enable("nope") is False
        assert registry.disable("nope") is False

    def test_to_openai_schemas(self, registry, echo_tool, read_tool):
        registry.register(echo_tool)
        registry.register(read_tool)
        schemas = registry.to_openai_schemas()
        assert len(schemas) == 2
        names = {s["function"]["name"] for s in schemas}
        assert names == {"echo", "read"}

    def test_to_openai_schemas_excludes_disabled(self, registry, echo_tool, read_tool):
        registry.register(echo_tool)
        registry.register(read_tool)
        read_tool.disable()
        schemas = registry.to_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "echo"


# ── PawsEngine tests ────────────────────────────────────────────────


class TestPawsEngine:
    @pytest.fixture
    def registry(self):
        reg = ToolRegistry()
        # register a simple echo tool
        reg.register(
            Tool(
                ToolSpec(
                    name="echo",
                    description="Echo back input",
                    category="util",
                    risk=RiskLevel.LOW,
                ),
                handler=lambda x: f"echo: {x}",
            )
        )
        # register a slow tool
        reg.register(
            Tool(
                ToolSpec(
                    name="slow",
                    description="A slow tool",
                    category="util",
                    risk=RiskLevel.LOW,
                ),
                handler=lambda: asyncio.sleep(10),
            )
        )
        # register a bomb tool
        reg.register(
            Tool(
                ToolSpec(
                    name="bomb",
                    description="Always fails",
                    category="test",
                    risk=RiskLevel.HIGH,
                ),
                handler=lambda: (_ for _ in ()).throw(ValueError("kaboom")),
            )
        )
        return reg

    @pytest.fixture
    def engine(self, registry):
        return PawsEngine(registry)

    @pytest.mark.anyio
    async def test_execute_success(self, engine):
        result = await engine.execute("echo", x="hello")
        assert result["success"] is True
        assert result["output"] == "echo: hello"
        assert result["tool"] == "echo"
        assert "elapsed_ms" in result

    @pytest.mark.anyio
    async def test_execute_not_found(self, engine):
        result = await engine.execute("nope")
        assert result["success"] is False
        assert "not found" in result["output"]
        assert result["tool"] == "nope"

    @pytest.mark.anyio
    async def test_execute_disabled(self, engine, registry):
        registry.disable("echo")
        result = await engine.execute("echo", x="hello")
        assert result["success"] is False
        assert "disabled" in result["output"]

    @pytest.mark.anyio
    async def test_execute_low_risk_no_confirm(self, engine):
        result = await engine.execute("echo", x="hi")
        assert result["success"] is True
        assert result.get("confirmed") is True  # LOW risk: no confirm needed

    @pytest.mark.anyio
    async def test_execute_high_risk_needs_confirm(self, engine):
        def handler():
            return "ok"

        engine.tool_registry.register(
            Tool(
                ToolSpec(
                    name="risky",
                    description="High risk op",
                    category="admin",
                    risk=RiskLevel.HIGH,
                ),
                handler=handler,
            )
        )
        result = await engine.execute("risky")
        assert result["success"] is True
        assert result.get("confirmed") is False  # HIGH risk needs confirm

    @pytest.mark.anyio
    async def test_execute_no_require_confirm(self, registry):
        def handler():
            return "ok"

        registry.register(
            Tool(
                ToolSpec(
                    name="risky",
                    description="High risk op",
                    category="admin",
                    risk=RiskLevel.HIGH,
                ),
                handler=handler,
            )
        )
        engine = PawsEngine(registry, require_confirm=False)
        result = await engine.execute("risky")
        assert result["success"] is True
        assert result.get("confirmed") is True

    @pytest.mark.anyio
    async def test_execute_timeout(self, registry):
        engine = PawsEngine(registry, timeout_s=0.01)
        result = await engine.execute("slow")
        assert result["success"] is False
        assert "timed out" in result["output"]

    @pytest.mark.anyio
    async def test_execute_handler_error(self, engine):
        # Tool.execute() catches handler errors and returns error string,
        # so PawsEngine sees it as success with error in output.
        result = await engine.execute("bomb")
        assert result["success"] is True
        assert "kaboom" in result["output"]

    def test_match_keyword(self, engine, registry):
        registry.register(
            Tool(
                ToolSpec(
                    name="read_file",
                    description="Read file contents from disk",
                    category="file",
                ),
            )
        )
        results = engine.match("read file")
        assert len(results) > 0
        assert results[0].name == "read_file"

    def test_match_no_results(self, engine):
        results = engine.match("zzz_nonexistent_zzz")
        assert results == []

    def test_audit_log(self, engine):
        # Audit log initially empty
        assert engine.audit_log == []
        # Audit log is a copy (mutating copy doesn't affect internal)
        log = engine.audit_log
        log.append({"fake": True})
        assert engine.audit_log == []

    @pytest.mark.anyio
    async def test_audit_log_records_execution(self, engine):
        await engine.execute("echo", x="test")
        log = engine.audit_log
        assert len(log) == 1
        assert log[0]["tool"] == "echo"
        assert log[0]["success"] is True

    def test_init_defaults(self, registry):
        engine = PawsEngine(registry)
        assert engine.require_confirm is True
        assert engine.timeout_s == 30.0


# ── KeywordToolMatcher tests ────────────────────────────────────────


class TestKeywordToolMatcher:
    @pytest.fixture
    def registry(self):
        reg = ToolRegistry()
        reg.register(
            Tool(
                ToolSpec(
                    name="read_file",
                    description="Read file contents from disk",
                    category="file",
                ),
            )
        )
        reg.register(
            Tool(
                ToolSpec(
                    name="write_file",
                    description="Write data to a file on disk",
                    category="file",
                ),
            )
        )
        reg.register(
            Tool(
                ToolSpec(
                    name="list_dir",
                    description="List directory contents",
                    category="file",
                ),
            )
        )
        reg.register(
            Tool(
                ToolSpec(
                    name="search_db",
                    description="Search database records",
                    category="database",
                ),
            )
        )
        return reg

    @pytest.fixture
    def matcher(self, registry):
        return KeywordToolMatcher(registry)

    def test_no_registry(self):
        matcher = KeywordToolMatcher(None)
        assert matcher.match("read file") == []
        assert matcher.best_match("read file") is None

    def test_match_by_name(self, matcher):
        results = matcher.match("read file")
        assert len(results) > 0
        # read_file should come first (name match)
        assert results[0][0].name == "read_file"

    def test_match_by_description(self, matcher):
        results = matcher.match("disk")
        names = [r[0].name for r in results]
        assert "read_file" in names
        assert "write_file" in names

    def test_match_by_category(self, matcher):
        # "database" keyword appears in category of search_db
        results = matcher.match("database")
        assert len(results) > 0
        names = [r[0].name for r in results]
        assert "search_db" in names

    def test_best_match(self, matcher):
        best = matcher.best_match("read file")
        assert best is not None
        assert best.name == "read_file"

    def test_best_match_none(self, matcher):
        best = matcher.best_match("zzz_nonexistent_zzz")
        assert best is None

    def test_top_n_limit(self, matcher):
        results = matcher.match("file", top_n=2)
        assert len(results) <= 2

    def test_min_score(self, matcher):
        # "file" matches name tokens in read_file/write_file (score ~18 each),
        # so use min_score=19 to filter all out
        results = matcher.match("file", min_score=19)
        assert len(results) == 0

    def test_disabled_tools_excluded(self, matcher, registry):
        registry.disable("read_file")
        results = matcher.match("read file")
        names = [r[0].name for r in results]
        assert "read_file" not in names

    def test_plug_custom_scorer(self, matcher):
        def custom_scorer(tool, keywords):
            # always return 100 for write_file
            return 100 if tool.name == "write_file" else 0

        matcher.plug("scorer", custom_scorer)
        results = matcher.match("anything")
        assert len(results) > 0
        assert results[0][0].name == "write_file"

    def test_plug_filter(self, matcher):
        def filter_fn(tool):
            return tool.name == "read_file"  # exclude read_file

        matcher.plug("filter", filter_fn)
        results = matcher.match("file")
        names = [r[0].name for r in results]
        assert "read_file" not in names

    def test_unplug_specific_fn(self, matcher):
        def scorer_fn(tool, keywords):
            return 50

        matcher.plug("scorer", scorer_fn)
        results = matcher.match("file")
        assert len(results) > 0
        matcher.unplug("scorer", scorer_fn)
        # after unplug, should go back to default scoring
        results2 = matcher.match("file")
        assert len(results2) > 0

    def test_unplug_whole_hook(self, matcher):
        def filter_fn(tool):
            return True

        matcher.plug("filter", filter_fn)
        results_before = matcher.match("file")
        assert results_before == []
        matcher.unplug("filter")
        results_after = matcher.match("file")
        assert len(results_after) > 0

    def test_unplug_nonexistent_hook(self, matcher):
        matcher.unplug("nonexistent")  # should not raise

    def test_returns_score_tuples(self, matcher):
        results = matcher.match("read file")
        for r in results:
            assert isinstance(r[0], Tool)
            assert isinstance(r[1], int)
            assert r[1] >= 1


# ── _tokenize tests ─────────────────────────────────────────────────


class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("hello world")
        assert tokens == ["hello", "world"]

    def test_filters_short(self):
        tokens = _tokenize("a b c de fg hi")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens
        assert "de" in tokens
        assert "fg" in tokens
        assert "hi" in tokens

    def test_lowercase(self):
        tokens = _tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_split_on_special(self):
        tokens = _tokenize("hello_world foo-bar baz.qux")
        assert tokens == ["hello", "world", "foo", "bar", "baz", "qux"]

    def test_numbers(self):
        tokens = _tokenize("file123 name42")
        assert tokens == ["file123", "name42"]

    def test_empty(self):
        tokens = _tokenize("")
        assert tokens == []

    def test_only_short(self):
        tokens = _tokenize("a b c")
        assert tokens == []
