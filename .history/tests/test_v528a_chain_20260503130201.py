"""meowcat standalone tests: v0.5.28a Chain + ChainRegistry.

Validates:
- Chain dataclass immutability + defaults
- ChainRegistry register / get / list_all
- ChainRegistry.run() sequential path execution with result passing
- Empty chain, single-step chain, multi-step chain
- Missing chain -> KeyError
- CatBase auto-registers 6 built-in chains
"""

from __future__ import annotations

import anyio
import pytest

from meowcat import CatBase
from meowcat.chain import BUILTIN_CHAINS, Chain, ChainRegistry, register_builtin_chains
from meowcat.path import Path


# -- Chain dataclass -----------------------------------------------


class TestChainDataclass:
    """Chain immutable dataclass."""

    def test_chain_creation(self):
        c = Chain("test", ("a", "b", "c"), "desc")
        assert c.name == "test"
        assert c.path_names == ("a", "b", "c")
        assert c.description == "desc"

    def test_chain_defaults(self):
        c = Chain("minimal")
        assert c.path_names == ()
        assert c.description == ""

    def test_chain_frozen(self):
        c = Chain("frozen", ("a",))
        with pytest.raises(Exception):
            c.name = "changed"  # type: ignore[misc]

    def test_chain_eq(self):
        c1 = Chain("same", ("a", "b"), "desc")
        c2 = Chain("same", ("a", "b"), "desc")
        assert c1 == c2

    def test_chain_ne(self):
        c1 = Chain("a", ("x",))
        c2 = Chain("b", ("x",))
        assert c1 != c2

    def test_chain_path_names_is_tuple(self):
        c = Chain("test", ("a", "b"))
        assert isinstance(c.path_names, tuple)


# -- BUILTIN_CHAINS -------------------------------------------------


class TestBuiltinChains:
    """Built-in chain table."""

    def test_not_empty(self):
        assert len(BUILTIN_CHAINS) == 6

    def test_no_duplicate_names(self):
        names = [c.name for c in BUILTIN_CHAINS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_known_chains_exist(self):
        names = {c.name for c in BUILTIN_CHAINS}
        expected = {
            "memory_search", "full_reasoning",
            "tool_exec", "maintenance", "diagnostic",
            "workflow_chain",
        }
        assert names == expected

    def test_diagnostic_is_empty(self):
        diag = [c for c in BUILTIN_CHAINS if c.name == "diagnostic"][0]
        assert diag.path_names == ()

    def test_memory_search_is_single(self):
        ms = [c for c in BUILTIN_CHAINS if c.name == "memory_search"][0]
        assert ms.path_names == ("locate",)

    def test_full_reasoning_has_two(self):
        fr = [c for c in BUILTIN_CHAINS if c.name == "full_reasoning"][0]
        assert len(fr.path_names) == 2
        assert "deep_reason" in fr.path_names
        assert "speak" in fr.path_names


# -- ChainRegistry register / get / list_all -----------------------


class TestChainRegistryBasic:
    """ChainRegistry basic CRUD."""

    def test_register_and_get(self):
        reg = ChainRegistry()
        c = Chain("test", ("a", "b"))
        reg.register(c)
        assert reg.get("test") is c

    def test_get_missing(self):
        reg = ChainRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all_empty(self):
        reg = ChainRegistry()
        assert reg.list_all() == []

    def test_list_all_order(self):
        reg = ChainRegistry()
        c1 = Chain("first", ("a",))
        c2 = Chain("second", ("b",))
        reg.register(c1)
        reg.register(c2)
        result = reg.list_all()
        assert len(result) == 2
        assert result[0] is c1
        assert result[1] is c2

    def test_register_overwrite(self):
        reg = ChainRegistry()
        c1 = Chain("dup", ("a",))
        c2 = Chain("dup", ("b",))
        reg.register(c1)
        reg.register(c2)
        assert reg.get("dup") is c2
        assert len(reg.list_all()) == 1

    def test_register_invalid_type(self):
        reg = ChainRegistry()
        with pytest.raises(TypeError, match="Expected Chain instance"):
            reg.register("not a chain")  # type: ignore[arg-type]

    def test_register_builtin_chains(self):
        reg = ChainRegistry()
        register_builtin_chains(reg)
        all_chains = reg.list_all()
        assert len(all_chains) == len(BUILTIN_CHAINS)
        c = reg.get("memory_search")
        assert c is not None
        assert c.name == "memory_search"


# -- ChainRegistry.run() -------------------------------------------


class TestChainRegistryRun:
    """ChainRegistry.run() sequential path execution with result passing."""

    def _setup_cat(self):
        """Create CatBase with fake organs."""
        cat = CatBase("test")

        TH = ("brain", "_thalamus")
        HC = ("brain", "_hippocampus")
        CB = ("bra", "_cerebrum")
        CL = ("brain", "_cerebellum")
        MH = ("voice", "_mouth")

        called: dict = {}

        class FakeHippocampus:
            name = "hippo"

            async def locate(self, query=None, **kw):
                called["locate"] = query
                return {"found": f"memory:{query}"}

        class FakeCerebrum:
            name = "cerebrum"

            async def generate(self, prompt=None, **kw):
                called["generate"] = prompt
                return {"text": f"reply_to:{prompt}"}

        class FakeMouth:
            name = "mouth"

            async def say(self, text=None, **kw):
                called["say"] = text
                return {"spoken": text}

        cat.mount(*TH, object())
        cat.mount(*HC, FakeHippocampus())
        cat.mount(*CB, FakeCerebrum())
        cat.mount(*CL, object())
        cat.mount(*MH, FakeMouth())

        cat.wiring.connect(TH, HC)
        cat.wiring.connect(TH, CB)
        cat.wiring.connect(CL, MH)

        # Register paths with custom coords (unmapped to avoid Protocol contract checks)
        cat.path_registry.register(Path("locate", TH, HC, "locate", "read"))
        cat.path_registry.register(
            Path("deep_reason", TH, CB, "generate", "read"))
        cat.path_registry.register(Path("say", CL, MH, "say", "write"))

        return cat, called

    def test_run_single_step_chain(self):
        """Single-step chain: memory_search = ('locate',)."""
        cat, called = self._setup_cat()

        async def _run():
            result = await cat.chain_registry.run(
                cat, "memory_search", query="hello",
            )
            assert result == {"found": "memory:hello"}
            assert called["locate"] == "hello"

        anyio.run(_run)

    def test_run_multi_step_chain(self):
        """Multi-step chain: manual full_reasoning = ('deep_reason', 'say').
        
        Previous step's return value flows as kwargs to the next step:
        generate returns {"text":...} -> say receives text=...
        (key name must align with downstream parameter name).
        """
        cat, called = self._setup_cat()

        # 用自定义坐标注册链路
        cat.chain_registry.register(
            Chain("test_reasoning", ("deep_reason", "say"), "test"),
        )

        async def _run():
            result = await cat.chain_registry.run(
                cat, "test_reasoning", prompt="你好",
            )
            # generate 返回 {"text": "reply_to:你好"}
            # say 收到 text="reply_to:你好"
            assert result == {"spoken": "reply_to:你好"}
            assert called["generate"] == "你好"
            assert called["say"] == "reply_to:你好"

        anyio.run(_run)

    def test_run_empty_chain(self):
        """空链路 diagnostic 返回初始输入。"""
        cat, _ = self._setup_cat()

        async def _run():
            result = await cat.chain_registry.run(
                cat, "diagnostic", status="ok",
            )
            assert result == {"status": "ok"}

        anyio.run(_run)

    def test_run_missing_chain(self):
        """不存在的链路 → KeyError。"""
        cat, _ = self._setup_cat()

        async def _run():
            with pytest.raises(KeyError, match="not found"):
                await cat.chain_registry.run(cat, "nonexistent")

        anyio.run(_run)

    def test_run_missing_path_in_chain(self):
        """链路中引用的 path 不存在 → PathRegistry.run 抛 KeyError。"""
        cat, _ = self._setup_cat()

        # 注册一条引用不存在 path 的链
        cat.chain_registry.register(
            Chain("bad_chain", ("nonexistent_path",)),
        )

        async def _run():
            with pytest.raises(KeyError, match="nonexistent_path"):
                await cat.chain_registry.run(cat, "bad_chain")

        anyio.run(_run)

    def test_run_result_pass_through(self):
        """非 dict 返回值包装为 {"_result": ...}。"""
        cat = CatBase("test")
        TH = ("brain", "_thalamus")
        HC = ("brain", "_hippocampus")

        class FakeHippocampus:
            name = "hippo"

            async def locate(self, query=None, **kw):
                return f"string_result:{query}"

        cat.mount(*TH, object())
        cat.mount(*HC, FakeHippocampus())
        cat.wiring.connect(TH, HC)
        cat.path_registry.register(Path("locate", TH, HC, "locate", "read"))

        async def _run():
            result = await cat.chain_registry.run(
                cat, "memory_search", query="test",
            )
            assert result == {"_result": "string_result:test"}

        anyio.run(_run)


# -- CatBase 自动注册 -----------------------------------------------


class TestCatBaseChainIntegration:
    """CatBase auto-registers 6 built-in chains."""

    def test_cat_has_chain_registry(self):
        cat = CatBase("test")
        assert hasattr(cat, "chain_registry")
        chains = cat.chain_registry.list_all()
        # v0.5.28b: +3 inline chains from register_default_loops (conversation_chain,
        # tool_loop_chain, danger_chain)
        assert len(chains) == 9

    def test_cat_has_builtin_chains(self):
        cat = CatBase("test")
        for name in ("memory_search", "full_reasoning", "tool_exec",
                     "maintenance", "diagnostic"):
            chain = cat.chain_registry.get(name)
            assert chain is not None, f"Missing chain: {name}"
            assert chain.name == name
