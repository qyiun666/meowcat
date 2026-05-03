"""meowcat standalone tests: v0.5.28b Loop + LoopRegistry + self-loop Path.

Validates:
- Loop dataclass immutability + defaults
- BUILTIN_LOOPS 5 built-in loops
- Loop Registry register / get / list_all
- LoopRegistry.run() trigger event -> run chain -> exit event
- Self-loop Path (from == to) calls local method directly
- CatBase auto-registers 5 built-in loops
- cat.run_loop() facade method
"""
from __future__ import annotations

import anyio
import pytest

from meowcat.testing import make_cat
from meowcat import CatBase
from meowcat.chain import Chain
from meowcat.loop import Lifecycle
from meowcat.loops import (
    BUILTIN_LOOPS,
    Loop,
    LoopRegistry,
    register_default_loops,
)
from meowcat.path import Path, PathRegistry, register_builtin_paths


# -- Loop dataclass -----------------------------------------------


class TestLoopDataclass:
    """Loop immutable dataclass."""

    def test_loop_creation(self):
        c = Chain("test_chain", ("a",))
        lp = Loop("test", "desc", chain=c, trigger="t", exit_event="e")
        assert lp.name == "test"
        assert lp.description == "desc"
        assert lp.chain is c
        assert lp.trigger == "t"
        assert lp.exit_event == "e"

    def test_loop_defaults(self):
        c = Chain("test_chain")
        lp = Loop("minimal", "", chain=c)
        assert lp.trigger is None
        assert lp.exit_event is None

    def test_loop_frozen(self):
        c = Chain("test_chain")
        lp = Loop("frozen", "", chain=c)
        with pytest.raises(Exception):
            lp.name = "changed"  # type: ignore[misc]

    def test_loop_eq(self):
        c = Chain("same")
        lp1 = Loop("x", "d", chain=c, trigger="t")
        lp2 = Loop("x", "d", chain=c, trigger="t")
        assert lp1 == lp2

    def test_loop_ne(self):
        c = Chain("a")
        lp1 = Loop("x", "", chain=c)
        lp2 = Loop("y", "", chain=c)
        assert lp1 != lp2


# -- BUILTIN_LOOPS -------------------------------------------------


class TestBuiltinLoops:
    """Built-in loop table."""

    def test_not_empty(self):
        assert len(BUILTIN_LOOPS) == 5

    def test_no_duplicate_names(self):
        names = [lp.name for lp in BUILTIN_LOOPS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_known_loops_exist(self):
        names = {lp.name for lp in BUILTIN_LOOPS}
        expected = {
            "conversation", "tool_execution",
            "danger_response", "maintenance", "diagnostic",
        }
        assert names == expected

    def test_conversation_loop_has_trigger(self):
        lp = next(lp for lp in BUILTIN_LOOPS if lp.name == "conversation")
        assert lp.trigger == Lifecycle.PERCEIVE_START
        assert lp.chain.name == "conversation_chain"
        assert "hear" in lp.chain.path_names
        assert "speak" in lp.chain.path_names
        assert "remember" in lp.chain.path_names

    def test_diagnostic_loop_no_trigger(self):
        lp = next(lp for lp in BUILTIN_LOOPS if lp.name == "diagnostic")
        assert lp.trigger is None
        assert lp.chain.path_names == ()  # empty chain

    def test_maintenance_loop_reuses_builtin_chain(self):
        lp = next(lp for lp in BUILTIN_LOOPS if lp.name == "maintenance")
        assert lp.chain.name == "maintenance"
        assert lp.chain.path_names == ("decay", "cleanup_orphans")
        assert lp.trigger == "heartbeat.tick"

    def test_danger_loop(self):
        lp = next(lp for lp in BUILTIN_LOOPS if lp.name == "danger_response")
        assert lp.trigger == "amygdala.alert"
        assert lp.chain.name == "danger_chain"
        assert "assess_safety" in lp.chain.path_names


# -- LoopRegistry register / get / list_all -----------------------


class TestLoopRegistryBasic:
    """LoopRegistry basic CRUD."""

    def test_register_and_get(self):
        reg = LoopRegistry()
        c = Chain("c")
        lp = Loop("test", "", chain=c)
        reg.register(lp)
        assert reg.get("test") is lp

    def test_get_missing(self):
        reg = LoopRegistry()
        assert reg.get("nonexistent") is None

    def test_list_all_empty(self):
        reg = LoopRegistry()
        assert reg.list_all() == []

    def test_list_all_order(self):
        reg = LoopRegistry()
        c1 = Chain("c1")
        c2 = Chain("c2")
        lp1 = Loop("first", "", chain=c1)
        lp2 = Loop("second", "", chain=c2)
        reg.register(lp1)
        reg.register(lp2)
        result = reg.list_all()
        assert len(result) == 2
        assert result[0] is lp1
        assert result[1] is lp2

    def test_register_overwrite(self):
        reg = LoopRegistry()
        c1 = Chain("c1")
        c2 = Chain("c2")
        lp1 = Loop("dup", "", chain=c1)
        lp2 = Loop("dup", "", chain=c2)
        reg.register(lp1)
        reg.register(lp2)
        assert reg.get("dup") is lp2
        assert len(reg.list_all()) == 1

    def test_register_invalid_type(self):
        reg = LoopRegistry()
        with pytest.raises(TypeError, match="Expected Loop instance"):
            reg.register("not a loop")  # type: ignore[arg-type]

    def test_register_default_loops(self):
        from meowcat.chain import ChainRegistry, register_builtin_chains

        chain_reg = ChainRegistry()
        register_builtin_chains(chain_reg)

        loop_reg = LoopRegistry()
        register_default_loops(loop_reg, chain_reg)

        all_loops = loop_reg.list_all()
        assert len(all_loops) == len(BUILTIN_LOOPS)

        # Inline chains get registered too
        conv_chain = chain_reg.get("conversation_chain")
        assert conv_chain is not None
        assert "hear" in conv_chain.path_names


# -- LoopRegistry.run() -------------------------------------------


class TestLoopRegistryRun:
    """LoopRegistry.run() trigger event -> run chain -> exit event."""

    def _setup_cat(self):
        """Create CatBase with fake organs + event tracking."""
        cat = make_cat("test")
        TH = ("brain", "_thalamus")
        HC = ("brain", "_hippocampus")
        CB = ("brain", "_cerebrum")
        CL = ("brain", "_cerebellum")
        MH = ("voice", "_mouth")
        AM = ("brain", "_amygdala")

        trace: list[tuple[str, object]] = []

        class FakeThalamus:
            name = "thalamus"

            async def decide_route(self, **kw):
                trace.append(("decide_route", kw))
                return {"route": "brain"}

        class FakeHippocampus:
            name = "hippo"

            async def locate(self, query=None, **kw):
                trace.append(("locate", query))
                return {"found": f"mem:{query}"}

            async def remember(self, **kw):
                trace.append(("remember", kw))
                return {"stored": True}

        class FakeCerebrum:
            name = "cerebrum"

            async def generate(self, prompt=None, **kw):
                trace.append(("generate", prompt))
                return {"text": f"reply:{prompt}"}

        class FakeCerebellum:
            name = "cerebellum"

        class FakeMouth:
            name = "mouth"

            async def speak(self, text=None, **kw):
                trace.append(("speak", text))
                return {"spoken": text}

        class FakeAmygdala:
            name = "amygdala"

            async def assess_safety(self, **kw):
                trace.append(("assess_safety", kw))
                return {"risk": "safe"}

        cat.mount(*TH, FakeThalamus())
        cat.mount(*HC, FakeHippocampus())
        cat.mount(*CB, FakeCerebrum())
        cat.mount(*CL, FakeCerebellum())
        cat.mount(*MH, FakeMouth())
        cat.mount(*AM, FakeAmygdala())

        cat.wiring.connect(TH, HC)
        cat.wiring.connect(TH, CB)
        cat.wiring.connect(CL, MH)

        # Register paths (including self-loop paths)
        cat.path_registry.register(Path("hear", TH, TH, "hear", "read"))
        cat.path_registry.register(
            Path("decide_route", TH, TH, "decide_route", "read"),
        )
        cat.path_registry.register(Path("locate", TH, TH, "locate", "read"))
        cat.path_registry.register(
            Path("deep_reason", TH, CB, "generate", "read"),
        )
        cat.path_registry.register(Path("speak", CL, MH, "speak", "write"))
        cat.path_registry.register(
            Path("assess_safety", AM, AM, "assess_safety", "read"),
        )

        return cat, trace

    def test_run_loop_with_trigger_and_exit(self):
        """Loop with trigger and exit_event."""
        cat, trace = self._setup_cat()

        # Register event tracking
        events_fired: list[str] = []

        @cat.on("test.trigger")
        def on_trigger(payload):
            events_fired.append(f"trigger:{payload}")

        @cat.on("test.exit")
        def on_exit(payload):
            events_fired.append(f"exit:{payload}")

        # Register chains and loops
        c = Chain("test_chain", ("assess_safety",))
        cat.chain_registry.register(c)
        lp = Loop("test", "", chain=c, trigger="test.trigger",
                  exit_event="test.exit")
        cat.loop_registry.register(lp)

        async def _run():
            result = await cat.loop_registry.run(
                cat, "test", msg="alert!",
            )
            assert result == {"risk": "safe"}
            assert len(events_fired) == 2
            assert events_fired[0].startswith("trigger:")
            assert events_fired[1].startswith("exit:")

        anyio.run(_run)

    def test_run_loop_no_trigger(self):
        """Loop without trigger (manual trigger)."""
        cat, trace = self._setup_cat()

        c = Chain("no_trigger_chain", ("assess_safety",))
        cat.chain_registry.register(c)
        lp = Loop("manual", "", chain=c, trigger=None, exit_event=None)
        cat.loop_registry.register(lp)

        async def _run():
            result = await cat.loop_registry.run(cat, "manual")
            assert result == {"risk": "safe"}

        anyio.run(_run)

    def test_run_missing_loop(self):
        """Missing loop -> KeyError."""
        cat, _ = self._setup_cat()

        async def _run():
            with pytest.raises(KeyError, match="not found"):
                await cat.loop_registry.run(cat, "nonexistent")

        anyio.run(_run)

    def test_run_diagnostic_loop_empty_chain(self):
        """Diagnostic loop (empty chain) returns initial input."""
        cat, _ = self._setup_cat()

        async def _run():
            result = await cat.loop_registry.run(
                cat, "diagnostic", status="ok",
            )
            assert result == {"status": "ok"}

        anyio.run(_run)


# -- Self-loop Path execution -----------------------------------------------


class TestSelfLoopPath:
    """Self-loop Path (from == to) calls local method directly."""

    def test_self_loop_path_run(self):
        """Self-loop path bypasses wiring signal, calls local method directly."""
        cat = make_cat("test")
        TH = ("brain", "_thalamus")

        called: list[dict] = []

        class FakeThalamus:
            name = "thalamus"

            async def decide_route(self, msg=None, **kw):
                called.append({"method": "decide_route", "msg": msg})
                return {"route": "cerebrum"}

        cat.mount(*TH, FakeThalamus())
        cat.path_registry.register(
            Path("decide_route", TH, TH, "decide_route", "read"),
        )

        async def _run():
            result = await cat.path_registry.run(
                cat, "decide_route", msg="hello",
            )
            assert result == {"route": "cerebrum"}
            assert len(called) == 1
            assert called[0]["msg"] == "hello"

        anyio.run(_run)

    def test_self_loop_builtin_path_exists(self):
        """Built-in self-loop Paths exist."""
        cat = make_cat("test")
        path = cat.path_registry.get("decide_route")
        assert path is not None
        assert path.from_organ == path.to_organ
        assert path.method == "decide_route"

        path2 = cat.path_registry.get("assess_safety")
        assert path2 is not None
        assert path2.from_organ == path2.to_organ


# -- CatBase integration ---------------------------------------------------


class TestCatBaseLoopIntegration:
    """CatBase auto-registers 5 built-in loops + run_loop() facade."""

    def test_cat_has_loop_registry(self):
        cat = make_cat("test")
        assert hasattr(cat, "loop_registry")
        loops = cat.loop_registry.list_all()
        assert len(loops) == 5

    def test_cat_has_builtin_loops(self):
        cat = make_cat("test")
        for name in ("conversation", "tool_execution", "danger_response",
                     "maintenance", "diagnostic"):
            lp = cat.loop_registry.get(name)
            assert lp is not None, f"Missing loop: {name}"
            assert lp.name == name

    def test_cat_has_run_loop_method(self):
        cat = make_cat("test")
        assert hasattr(cat, "run_loop")
        assert callable(cat.run_loop)

    def test_cat_run_loop_diagnostic(self):
        """cat.run_loop("diagnostic") executes correctly."""
        cat = make_cat("test")

        async def _run():
            result = await cat.run_loop("diagnostic", x=1)
            assert result == {"x": 1}

        anyio.run(_run)

    def test_conversation_loop_chain_registered(self):
        """Built-in loops' inline Chains are in chain_registry."""
        cat = make_cat("test")
        conv_chain = cat.chain_registry.get("conversation_chain")
        assert conv_chain is not None
        assert "hear" in conv_chain.path_names
        assert "speak" in conv_chain.path_names

    def test_tool_loop_chain_registered(self):
        cat = make_cat("test")
        tool_chain = cat.chain_registry.get("tool_loop_chain")
        assert tool_chain is not None
        assert "execute_tool" in tool_chain.path_names

    def test_danger_chain_registered(self):
        cat = make_cat("test")
        danger_chain = cat.chain_registry.get("danger_chain")
        assert danger_chain is not None
        assert "assess_safety" in danger_chain.path_names

    def test_from_meowcat_import_loops(self):
        """Externally importable via from meowcat import Loop/LoopRegistry/BUILTIN_LOOPS."""
        from meowcat import BUILTIN_LOOPS as L, Loop as LP, LoopRegistry as LR
        assert len(L) == 5
        assert hasattr(LP, "__dataclass_fields__")
        assert hasattr(LR, "register")


# -- New Path coverage -------------------------------------------------


class TestNewPathsForLoop:
    """v0.5.28b new Paths exist and are correct."""

    def test_execute_tool_path(self):
        cat = make_cat("test")
        p = cat.path_registry.get("execute_tool")
        assert p is not None
        assert p.mode == "write"

    def test_decide_route_is_self_loop(self):
        cat = make_cat("test")
        p = cat.path_registry.get("decide_route")
        assert p.from_organ == p.to_organ
        assert p.mode == "read"

    def test_check_danger_is_self_loop(self):
        cat = make_cat("test")
        p = cat.path_registry.get("assess_safety")
        assert p.from_organ == p.to_organ

    def test_assess_risk_is_self_loop(self):
        cat = make_cat("test")
        p = cat.path_registry.get("assess_safety")
        assert p.from_organ == p.to_organ

    def test_total_path_count(self):
        """BUILTIN_PATHS currently 26 (v1.0.15 added 3 orchestration domain paths)."""
        cat = make_cat("test")
        all_paths = cat.path_registry.list_all()
        assert len(all_paths) == 26
