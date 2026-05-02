"""meowcat 框架独立测试 — 零 meowagent 依赖。

验证: Protocol 可 import、Wiring 连通/禁止/冻结、CatBase 装配、
默认实现可创建完整猫。
"""

from __future__ import annotations

import pytest

from meowcat import (
    CatBase,
    EventBus,
    Pipeline,
    Wiring,
)
from meowcat.defaults import create_cat
from meowcat.defaults.organs import NoopAmygdala, NoopEars
from meowcat.protocols import (
    AmygdalaProtocol,
    CatProtocol,
    EarsProtocol,
    KittenProtocol,
)
from meowcat.models import EntityShape, PipelineContext


class TestProtocols:
    """所有 Protocol 可 import + isinstance 校验。"""

    def test_cat_protocol_has_new_api(self) -> None:
        import typing
        hints = typing.get_type_hints(CatProtocol)
        assert "turn" in hints, "CatProtocol missing 'turn' type hint"
        # 方法可用 dir 检查
        members = {n for n, _ in __import__("inspect").getmembers(CatProtocol)}
        for name in ("process_message", "perceive_stream",
                     "start", "shutdown"):
            assert name in members, f"CatProtocol missing '{name}'"

    def test_noop_satisfies_amygdala(self) -> None:
        a = NoopAmygdala()
        assert isinstance(a, AmygdalaProtocol)
        assert a.is_rejection("hello") is False

    def test_noop_satisfies_ears(self) -> None:
        e = NoopEars()
        assert isinstance(e, EarsProtocol)
        assert e.extract_keywords("hello") == []


class TestWiring:
    """Wiring 连通/禁止/冻结。"""

    def test_connect_and_is_allowed(self) -> None:
        w = Wiring()
        w.connect(("brain", "thalamus"), ("brain", "cerebrum"))
        assert w.is_allowed(("brain", "thalamus"), ("brain", "cerebrum"))
        assert not w.is_allowed(("brain", "thalamus"), ("sense", "paws"))

    def test_forbid_and_freeze(self) -> None:
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("brain", "hippocampus"))
        assert w.is_allowed(("brain", "cerebrum"), ("brain", "hippocampus"))
        w.forbid(("brain", "cerebrum"), ("brain", "hippocampus"))
        assert not w.is_allowed(("brain", "cerebrum"),
                                ("brain", "hippocampus"))
        w.freeze()
        assert w._frozen is True
        with pytest.raises(Exception):
            w.connect(("brain", "a"), ("brain", "b"))


class TestCatBase:
    """CatBase mount/signal 基础流程。"""

    def test_mount_and_organ(self) -> None:
        cat = CatBase("test")
        obj = object()
        cat.mount("brain", "hippocampus", obj)
        assert cat.organ("brain", "hippocampus") is obj
        with pytest.raises(Exception):
            cat.organ("brain", "nonexistent")

    def test_signal_blocked_by_wiring(self) -> None:
        cat = CatBase("test")
        a = object()
        b = object()
        cat.mount("brain", "cerebrum", a)
        cat.mount("sense", "paws", b)
        # cerebrum→paws 默认不在 wiring 表里，应被拦截
        with pytest.raises(Exception):
            import anyio
            anyio.run(cat.signal, ("brain", "cerebrum"),
                      ("sense", "paws"), "generate")


class TestCreateCat:
    """create_cat 一行建猫。"""

    class MockCerebrum:
        name = "mock"

        async def generate(self, prompt, system_prompt=None,
                           temperature=0.7, max_tokens=None) -> str:
            return "meow"

        async def stream_generate(self, prompt, system_prompt=None,
                                  temperature=0.7, max_tokens=None):
            yield "meow"
            return

        def reload_config(self) -> None:
            pass

    def test_create_minimal_cat(self) -> None:
        cat = create_cat("test-cat", cerebrum=self.MockCerebrum())
        assert cat.cat_id == "test-cat"
        assert cat.organs("brain")
        assert cat.organs("sense")
        assert cat.organs("voice")
        assert cat.wiring._frozen is True

    def test_create_cat_with_custom_organs(self) -> None:
        custom_ears = NoopEars()
        cat = create_cat("test-cat", cerebrum=self.MockCerebrum(),
                         ears=custom_ears)
        assert cat.ears is custom_ears
        # amygdalla 未提供，应为 Noop
        assert isinstance(cat.amygdala, NoopAmygdala)


class TestModels:
    """所有 Shape 构造 + 序列化。"""

    def test_entity_shape(self) -> None:
        e = EntityShape(id="e1", session_id="s1", name="test")
        d = e.model_dump()
        assert d["id"] == "e1"
        assert d["type"] == "topic"

    def test_pipeline_context_with_brainstem(self) -> None:
        class FakeBS:
            async def process(self, msg: str) -> str: return msg

            async def process_stream(self, msg: str):
                yield {"content": msg}
                return

            def build_system_prompt(self, route: str) -> str: return ""
            def cancel_current(self) -> bool: return False

        bs = FakeBS()
        ctx = PipelineContext(msg="hi", brainstem=bs)
        assert ctx.msg == "hi"
        assert ctx.brainstem is bs
