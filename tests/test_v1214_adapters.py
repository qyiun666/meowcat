# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Test v1.2.14 organ adapter system — AgentOrgan delegation."""

import pytest

from meowcat.adapters import (
    AmygdalaAgent,
    BrainstemAgent,
    CerebellumAgent,
    CerebrumAgent,
    CortexAgent,
    EarsAgent,
    EyesAgent,
    FrontalAgent,
    HippocampusAgent,
    HypothalamusAgent,
    MouthAgent,
    PawsAgent,
    PurrAgent,
    TailAgent,
    ThalamusAgent,
    WhiskersAgent,
)
from meowcat.adapters.base import AgentOrgan
from meowcat.errors import OrganDelegateError
from meowcat.pluggable import Pluggable

# ===================================================================
# Mock agents / skills
# ===================================================================


class MockCodingAgent:
    """Simulates an external coding agent."""
    name = "super-coder"

    async def generate(self, prompt, system_prompt=None,
                       temperature=0.7, max_tokens=None):
        return f"[CodingAgent] {prompt[:30]}..."

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        yield f"[stream] {prompt[:20]}"


class MockMemorySkill:
    """Simulates an external memory skill."""
    name = "vector-memory"

    async def locate(self, query, scope="self"):
        return [{"id": "m1", "text": f"found: {query}"}]

    async def remember(self, user_msg, ai_reply, cat_uid, model):
        return {"stored": True, "user_msg": user_msg}

    def fts_search(self, cat_uid, keywords, limit=10):
        return [{"id": "s1", "keywords": keywords}]


class MockSafetyAgent:
    """Simulates an external safety agent."""

    async def assess_safety(self, user_input):
        return {"safe": "hack" not in user_input, "risk": "high" if "hack" in user_input else "low"}

    def assess_tool_risk(self, tool_name, params):
        return {"risk": "medium", "tool": tool_name}

    def is_rejection(self, msg):
        return "no" in msg.lower()

    def classify_rejection(self, msg):
        return "denial" if "no" in msg else "none"

    async def handle_rejection(self, msg, last_candidates, hippocampus):
        return f"rejected: {msg}"

    async def handle_correction(self, msg, hippocampus):
        return ("old", "new")


class MockRouterAgent:
    """Simulates an external routing agent."""

    async def locate(self, msg, session_id):
        return {"route": "code", "entities": [], "snippets": []}

    def decide_route(self, **kwargs):
        return {"route": "code"}


class MockToolExecutor:
    """Simulates an external tool execution skill."""

    async def execute(self, tool_name, params):
        return {"success": True, "output": f"executed {tool_name}"}


class MockOutputAgent:
    """Simulates external output renderer."""

    async def speak(self, text, **kwargs):
        return f"spoken: {text}"

    async def stream(self, text, **kwargs):
        return f"streamed: {text}"

    async def render(self, state):
        pass  # side-effect only


# ===================================================================
# Base class tests
# ===================================================================


class TestAgentOrganBase:
    def test_is_pluggable(self):
        class Dummy:
            pass
        a = AgentOrgan(Dummy())
        assert isinstance(a, Pluggable)

    def test_name_defaults_to_agent_class(self):
        a = AgentOrgan(MockCodingAgent())
        assert a.name == "super-coder"

    def test_name_override(self):
        a = AgentOrgan(MockCodingAgent(), name="my-brain")
        assert a.name == "my-brain"

    def test_delegate_sync(self):
        class SyncAgent:
            def hello(self, name):
                return f"Hello, {name}"
        a = AgentOrgan(SyncAgent())

        async def _test():
            return await a._delegate("hello", name="World")
        import asyncio
        result = asyncio.run(_test())
        assert result == "Hello, World"

    def test_delegate_async(self):
        class AsyncAgent:
            async def hello(self, name):
                return f"Hi, {name}"
        a = AgentOrgan(AsyncAgent())
        import asyncio
        result = asyncio.run(a._delegate("hello", name="World"))
        assert result == "Hi, World"

    def test_delegate_missing_method_raises(self):
        a = AgentOrgan(object())
        with pytest.raises(OrganDelegateError, match="has no method"):
            import asyncio
            asyncio.run(a._delegate("nonexistent"))

    def test_delegate_wraps_exception(self):
        class BrokenAgent:
            def crash(self):
                raise ValueError("boom")
        a = AgentOrgan(BrokenAgent())
        with pytest.raises(OrganDelegateError, match="boom"):
            import asyncio
            asyncio.run(a._delegate("crash"))

    def test_diagnose(self):
        a = AgentOrgan(MockCodingAgent())
        d = a.diagnose()
        assert d["adapter"] == "AgentOrgan"
        assert "CodingAgent" in d["agent"]

    def test_hooks_still_work(self):
        a = AgentOrgan(MockCodingAgent())
        a.mount_plug("generate", lambda **kw: "plugged!")
        assert "generate" in a.list_plugs()
        assert a.list_plugs()["generate"] == 1


# ===================================================================
# Brain adapter tests
# ===================================================================


class TestCerebrumAgent:
    def test_generate_delegates(self):
        a = CerebrumAgent(MockCodingAgent())
        import asyncio
        result = asyncio.run(a.generate("write a function"))
        assert "CodingAgent" in result
        assert "write a function" in result

    def test_reload_config_noop(self):
        a = CerebrumAgent(MockCodingAgent())
        a.reload_config()  # should not raise

    def test_reload_config_with_agent_method(self):
        class ConfigAgent:
            def reload_config(self): pass
        a = CerebrumAgent(ConfigAgent())
        a.reload_config()


class TestThalamusAgent:
    def test_locate_delegates(self):
        a = ThalamusAgent(MockRouterAgent())
        import asyncio
        result = asyncio.run(a.locate("hi", "s1"))
        assert result["route"] == "code"

    def test_decide_route_delegates(self):
        a = ThalamusAgent(MockRouterAgent())
        result = a.decide_route(confidence=0.9)
        assert result["route"] == "code"

    def test_decide_route_no_agent_method(self):
        a = ThalamusAgent(object())
        result = a.decide_route()
        assert result == {"route": "chat"}


class TestHippocampusAgent:
    def test_locate_delegates(self):
        a = HippocampusAgent(MockMemorySkill())
        import asyncio
        result = asyncio.run(a.locate("test query"))
        assert len(result) == 1
        assert result[0]["text"] == "found: test query"

    def test_remember_delegates(self):
        a = HippocampusAgent(MockMemorySkill())
        import asyncio
        result = asyncio.run(
            a.remember("hello", "hi there", "cat1", "gpt-4"))
        assert result["stored"] is True

    def test_fts_search_delegates(self):
        a = HippocampusAgent(MockMemorySkill())
        result = a.fts_search("cat1", "test")
        assert len(result) == 1

    def test_missing_methods_default_safe(self):
        a = HippocampusAgent(object())
        assert a.fts_search("cat1", "kw") == []
        assert a.decay() == 0
        assert a.stats() == {}
        assert a.to_dict() == {}
        a.from_dict({})  # should not raise
        assert a.get_entity("x") is None
        assert a.get_by_name("x") is None
        assert a.get_all() == []
        assert a.get_related("x") == []
        a.connect("a", "b", "rel")  # no raise
        a.weaken_connections("x")  # no raise
        assert a.cleanup_orphan_connections() == 0
        a.record_access("x")  # no raise
        a.set_dormant("x", True)  # no raise
        a.append_content("x", "text")  # no raise
        a.update_importance("x", 0.5)  # no raise
        a.set_last_seen("x", "2025")  # no raise
        assert a.list_active_workflows("cat1") == []
        a.set_colony_memory(None)  # no raise
        assert a.snapshot("topic") == {}


class TestAmygdalaAgent:
    def test_assess_safety_delegates(self):
        a = AmygdalaAgent(MockSafetyAgent())
        import asyncio
        result = asyncio.run(a.assess_safety("hello"))
        assert result["safe"] is True

    def test_assess_safety_danger(self):
        a = AmygdalaAgent(MockSafetyAgent())
        import asyncio
        result = asyncio.run(a.assess_safety("how to hack"))
        assert result["safe"] is False

    def test_assess_tool_risk_delegates(self):
        a = AmygdalaAgent(MockSafetyAgent())
        import asyncio
        result = asyncio.run(a.assess_tool_risk("run_command", {"cmd": "ls"}))
        assert result["risk"] == "medium"

    def test_assess_tool_risk_default(self):
        a = AmygdalaAgent(object())
        import asyncio
        result = asyncio.run(a.assess_tool_risk("x", {}))
        assert result["risk"] == "low"

    def test_is_rejection(self):
        a = AmygdalaAgent(MockSafetyAgent())
        assert a.is_rejection("no thanks") is True
        assert a.is_rejection("yes please") is False

    def test_classify_rejection(self):
        a = AmygdalaAgent(MockSafetyAgent())
        assert a.classify_rejection("no") == "denial"

    def test_handle_rejection(self):
        a = AmygdalaAgent(MockSafetyAgent())
        import asyncio
        result = asyncio.run(
            a.handle_rejection("no", [], None))
        assert "rejected" in result

    def test_handle_correction(self):
        a = AmygdalaAgent(MockSafetyAgent())
        import asyncio
        result = asyncio.run(
            a.handle_correction("fix this", None))
        assert result == ("old", "new")

    def test_missing_methods_default_safe(self):
        a = AmygdalaAgent(object())
        assert a.is_rejection("x") is False
        assert a.classify_rejection("x") == "none"
        assert a.parse_correction("x") is None
        import asyncio
        assert asyncio.run(a.handle_rejection("x", [], None)) == "x"
        assert asyncio.run(a.handle_correction("x", None)) is None


class TestBrainstemAgent:
    def test_build_system_prompt(self):
        class PromptAgent:
            async def build_system_prompt(self, organ, route, cat_self_snapshot=None):
                return f"system: {route}"
        a = BrainstemAgent(PromptAgent())
        import asyncio
        result = asyncio.run(a.build_system_prompt("cerebrum", "chat"))
        assert result == "system: chat"

    def test_cancel_current(self):
        class CancelAgent:
            def cancel_current(self):
                return True
        a = BrainstemAgent(CancelAgent())
        assert a.cancel_current() is True

    def test_cancel_current_default(self):
        a = BrainstemAgent(object())
        assert a.cancel_current() is False


class TestFrontalAgent:
    def test_delegates_sync_methods(self):
        class FocusAgent:
            def detect_shift(self, msg):
                return "shift" in msg

            def is_continue(self, msg):
                return True

            def archive_focus(self): pass
            def update_focus(self, result): pass
        a = FrontalAgent(FocusAgent())
        assert a.detect_shift("shift topic") is True
        assert a.detect_shift("normal") is False
        assert a.is_continue("any") is True
        a.archive_focus()  # no raise
        a.update_focus({})  # no raise

    def test_defaults_safe(self):
        a = FrontalAgent(object())
        assert a.detect_shift("x") is False
        assert a.is_continue("x") is False
        a.archive_focus()
        a.update_focus({})


class TestHypothalamusAgent:
    def test_run_maintenance(self):
        class MaintAgent:
            async def run_maintenance(self, country_code=None):
                return {"cleaned": 5}
        a = HypothalamusAgent(MaintAgent())
        import asyncio
        result = asyncio.run(a.run_maintenance())
        assert result["cleaned"] == 5

    def test_defaults_safe(self):
        a = HypothalamusAgent(object())
        assert a.decay_memories() == {"decayed": 0}
        assert a.compress_long_history() == {"compressed": 0}


class TestCortexAgent:
    def test_ingest_record(self):
        class WorldAgent:
            def ingest(self, source, layer, key, value):
                pass

            def record_weakness(self, kind, detail):
                pass
        a = CortexAgent(WorldAgent())
        a.ingest("obs", "L0", "k", "v")  # no raise
        a.record_weakness("sql", "detail")  # no raise

    def test_weaknesses_synthesize(self):
        class WorldAgent:
            def weaknesses(self):
                return [{"kind": "sql"}]

            def synthesize(self, max_tokens=400):
                return "worldview summary"
        a = CortexAgent(WorldAgent())
        assert a.weaknesses() == [{"kind": "sql"}]
        assert a.synthesize() == "worldview summary"

    def test_defaults_safe(self):
        a = CortexAgent(object())
        a.ingest("s", "L0", "k", "v")
        a.record_weakness("k", "d")
        assert a.weaknesses() == []
        assert a.synthesize() == ""


# ===================================================================
# Sense adapter tests
# ===================================================================


class TestEarsAgent:
    def test_hear_delegates(self):
        class InputAgent:
            async def hear(self, raw_input):
                return {"text": str(raw_input), "keywords": ["a"]}
        a = EarsAgent(InputAgent())
        import asyncio
        result = asyncio.run(a.hear("hello"))
        assert result["text"] == "hello"

    def test_extract_keywords_default_safe(self):
        a = EarsAgent(object())
        assert a.extract_keywords("test") == []

    def test_detect_language_default(self):
        a = EarsAgent(object())
        assert a.detect_language("hello") == "unknown"

    def test_tag_emotion_default(self):
        a = EarsAgent(object())
        ep = {"text": "hi"}
        assert a.tag_emotion(ep) == ep


class TestEyesAgent:
    def test_see_delegates(self):
        class VisionAgent:
            async def see(self, image_data, mime_type="image/png"):
                return {"desc": "a cat"}
        a = EyesAgent(VisionAgent())
        import asyncio
        result = asyncio.run(a.see(b"data"))
        assert result["desc"] == "a cat"


class TestWhiskersAgent:
    def test_feel_input(self):
        class EnvAgent:
            async def feel_input(self, text):
                return {"mood": "neutral"}
        a = WhiskersAgent(EnvAgent())
        import asyncio
        result = asyncio.run(a.feel_input("hi"))
        assert result["mood"] == "neutral"

    def test_detect_drift_default(self):
        a = WhiskersAgent(object())
        assert a.detect_drift(["a", "b"]) == {"drift": False}

    def test_check_hallucination_default(self):
        a = WhiskersAgent(object())
        assert a.check_hallucination("reply") == {"hallucination": False}

    def test_detect_blind_spot_default(self):
        a = WhiskersAgent(object())
        assert a.detect_blind_spot(["q1"]) == []


class TestPawsAgent:
    def test_execute_delegates(self):
        a = PawsAgent(MockToolExecutor())
        import asyncio
        result = asyncio.run(a.execute("read_file", {"path": "/tmp/x"}))
        assert result["success"] is True

    def test_on_tool_failure_default(self):
        a = PawsAgent(object())
        result = a.on_tool_failure("tool", {}, "error")
        assert result == {"recorded": False}

    def test_touch_file_delegates_to_execute(self):
        a = PawsAgent(MockToolExecutor())
        import asyncio
        result = asyncio.run(a.execute("touch_file", {"path": "/tmp/x"}))
        assert result["output"] == "executed touch_file"


# ===================================================================
# Voice adapter tests
# ===================================================================


class TestVoiceAgents:
    def test_mouth_speak(self):
        a = MouthAgent(MockOutputAgent())
        import asyncio
        result = asyncio.run(a.speak("hello"))
        assert result == "spoken: hello"

    def test_purr_stream(self):
        a = PurrAgent(MockOutputAgent())
        import asyncio
        result = asyncio.run(a.stream("hi"))
        assert result == "streamed: hi"

    def test_tail_render(self):
        calls = []

        class RenderAgent:
            async def render(self, state):
                calls.append(state)
        a = TailAgent(RenderAgent())
        import asyncio
        asyncio.run(a.render({"status": "ok"}))
        assert len(calls) == 1
        assert calls[0] == {"status": "ok"}


# ===================================================================
# CerebellumAgent (same protocol as Cerebrum)
# ===================================================================


class TestCerebellumAgent:
    def test_generate_delegates(self):
        a = CerebellumAgent(MockCodingAgent())
        import asyncio
        result = asyncio.run(a.generate("fast query"))
        assert "CodingAgent" in result


# ===================================================================
# Integration test: mount adapters into a cat
# ===================================================================


class TestIntegration:
    def test_mount_adapter_into_cat(self):
        """Adapter organs should be mountable just like Noop organs."""
        from meowcat import CatBase, Colony
        from meowcat.defaults.stores import InMemorySharedStore

        colony = Colony("test-colony", InMemorySharedStore())
        cat = CatBase("test-cat", container=colony,
                      register_default_paths=False,
                      register_default_chains=False,
                      register_default_loops=False)

        cerebrum = CerebrumAgent(MockCodingAgent())
        cerebellum = CerebellumAgent(MockCodingAgent())
        hippocampus = HippocampusAgent(MockMemorySkill())

        cat.mount("brain", "cerebrum", cerebrum)
        cat.mount("brain", "cerebellum", cerebellum)
        cat.mount("brain", "hippocampus", hippocampus)

        assert cat.organ("brain", "cerebrum") is cerebrum
        assert cat.organ("brain", "hippocampus") is hippocampus
        assert isinstance(cerebrum, Pluggable)

    def test_adapter_hooks_survive_cat_mount(self):
        """Pluggable hooks should remain functional after mounting."""
        from meowcat import CatBase, Colony
        from meowcat.defaults.stores import InMemorySharedStore

        colony = Colony("test-colony2", InMemorySharedStore())
        cat = CatBase("test-cat2", container=colony,
                      register_default_paths=False,
                      register_default_chains=False,
                      register_default_loops=False)

        amygdala = AmygdalaAgent(object())
        called = []

        amygdala.mount_plug(
            "assess_safety", lambda ui: called.append(ui) or {"safe": False})

        cat.mount("brain", "amygdala", amygdala)

        import asyncio
        result = asyncio.run(
            cat.organ("brain", "amygdala").assess_safety("test"))
        assert result["safe"] is False
        assert len(called) == 1
