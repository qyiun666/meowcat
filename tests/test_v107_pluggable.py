"""v1.0.7 Pluggable + Noop 全补齐 + Voice Protocols 测试。

覆盖:
- Pluggable mixin 的 mount/unmount/_run_plugs/list_plugs
- 15 个 Noop 器官的三模式插件执行 (A/B/C)
- NoopThalamus / NoopHippocampus 功能
- Voice Protocols (Mouth/Purr/Tail)
- create_cat() 默认使用 NoopThalamus/NoopHippocampus
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from meowcat import (
    MouthProtocol,
    NoopAmygdala,
    NoopBrainstem,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
    NoopThalamus,
    NoopWhiskers,
    Pluggable,
    PurrProtocol,
    TailProtocol,
)
from meowcat.biology import ORGAN_PROTOCOLS
from meowcat.defaults import create_cat


# ===================================================================
# Pluggable mixin
# ===================================================================


class _FakePluggable(Pluggable):
    """最小 Pluggable 实现，用于测试 mixin 行为。"""
    HOOKS: dict[str, dict[str, str]] = {"test_hook": {"in": "x", "out": "y"}}


def test_pluggable_init():
    p = _FakePluggable()
    assert p.list_plugs() == {}
    assert p.HOOKS == {"test_hook": {"in": "x", "out": "y"}}


def test_pluggable_mount_unmount():
    p = _FakePluggable()

    def fn1(x):
        return x * 2

    def fn2(x):
        return x * 3

    p.mount_plug("test_hook", fn1)
    p.mount_plug("test_hook", fn2)
    assert p.list_plugs() == {"test_hook": 2}

    # 按注册顺序执行
    results = list(p._run_plugs_sync("test_hook", 5))
    assert results == [("test_hook", 10), ("test_hook", 15)]

    # 卸载单个
    p.unmount_plug("test_hook", fn1)
    assert p.list_plugs() == {"test_hook": 1}

    # 卸载全部
    p.unmount_plug("test_hook")
    assert p.list_plugs() == {}


def test_pluggable_unmount_nonexistent():
    p = _FakePluggable()
    p.unmount_plug("nonexistent")  # 不应抛异常


def test_pluggable_run_plugs_no_plugs():
    p = _FakePluggable()
    results = list(p._run_plugs_sync("test_hook", "x"))
    assert results == []


# ===================================================================
# 模式 A — 首命中覆盖
# ===================================================================


@pytest.mark.asyncio
async def test_amygdala_mode_a_default():
    a = NoopAmygdala()
    r = await a.assess_safety("hi")
    assert r == {"safe": True, "risk": "none"}


@pytest.mark.asyncio
async def test_amygdala_mode_a_plug_block():
    a = NoopAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False, "risk": "block"})
    r = await a.assess_safety("malicious input")
    assert r == {"safe": False, "risk": "block"}


@pytest.mark.asyncio
async def test_amygdala_mode_a_plug_first_wins():
    a = NoopAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False, "risk": "block"})
    a.mount_plug("assess_safety", lambda x: {
                 "safe": False, "risk": "override"})
    r = await a.assess_safety("test")
    # 第一个返回非安全即返回
    assert r == {"safe": False, "risk": "block"}


@pytest.mark.asyncio
async def test_amygdala_mode_a_plug_safe_passes():
    a = NoopAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": True, "risk": "none"})
    r = await a.assess_safety("hello")
    assert r == {"safe": True, "risk": "none"}  # 默认


@pytest.mark.asyncio
async def test_frontal_mode_a():
    f = NoopFrontal()
    assert await f.is_continue("msg") is False
    f.mount_plug("is_continue", lambda _: True)
    assert await f.is_continue("msg") is True


@pytest.mark.asyncio
async def test_frontal_mode_a_detect_shift():
    f = NoopFrontal()
    assert await f.detect_shift("msg") is False
    f.mount_plug("detect_shift", lambda _: True)
    assert await f.detect_shift("msg") is True


# ===================================================================
# 模式 B — 合并增强
# ===================================================================


@pytest.mark.asyncio
async def test_ears_mode_b_hear():
    e = NoopEars()
    r = await e.hear("hello")
    assert r == {"text": "hello", "keywords": [], "language": "unknown"}

    e.mount_plug("hear", lambda raw: {"language": "zh", "keywords": ["hello"]})
    r = await e.hear("hello")
    assert r == {"text": "hello", "keywords": ["hello"], "language": "zh"}


@pytest.mark.asyncio
async def test_ears_mode_b_extract_keywords():
    e = NoopEars()
    r = await e.extract_keywords("test")
    assert r == []

    e.mount_plug("extract_keywords", lambda text, top_k: ["a", "b"])
    r = await e.extract_keywords("test")
    assert r == ["a", "b"]


@pytest.mark.asyncio
async def test_whiskers_mode_b():
    w = NoopWhiskers()
    r = await w.feel_input("test")
    assert r == {}
    w.mount_plug("feel_input", lambda t: {"injection": True})
    r = await w.feel_input("test")
    assert r == {"injection": True}


@pytest.mark.asyncio
async def test_whiskers_mode_b_hallucination():
    w = NoopWhiskers()
    r = await w.check_hallucination("reply", "s1")
    assert r == {"hallucination": False}
    w.mount_plug("check_hallucination", lambda reply,
                 sid: {"hallucination": True})
    r = await w.check_hallucination("reply", "s1")
    assert r == {"hallucination": True}


@pytest.mark.asyncio
async def test_hypothalamus_mode_b():
    h = NoopHypothalamus()
    r = await h.run_maintenance()
    assert r == {"decayed": 0, "orphans_cleaned": 0,
                 "woke": 0, "suggestions": []}
    h.mount_plug("run_maintenance", lambda cc: {"decayed": 5})
    r = await h.run_maintenance()
    assert r["decayed"] == 5
    assert r["orphans_cleaned"] == 0  # 保留默认


@pytest.mark.asyncio
async def test_cortex_mode_b():
    c = NoopCortex()
    r = await c.synthesize(100)
    assert r == ""
    c.mount_plug("synthesize", lambda mt: "worldview snippet")
    r = await c.synthesize(100)
    assert r == "worldview snippet"


@pytest.mark.asyncio
async def test_brainstem_mode_b():
    b = NoopBrainstem()
    r = await b.build_system_prompt("chat")
    assert r == ""
    b.mount_plug("build_system_prompt", lambda route: f"prompt for {route}")
    r = await b.build_system_prompt("chat")
    assert r == "prompt for chat"


@pytest.mark.asyncio
async def test_thalamus_mode_b():
    t = NoopThalamus()
    r = await t.locate("hello", "s1")
    assert r["route"] == "chat"
    t.mount_plug("locate", lambda msg, sid: {"route": "danger"})
    r = await t.locate("hello", "s1")
    assert r["route"] == "danger"


@pytest.mark.asyncio
async def test_hippocampus_mode_b_remember():
    h = NoopHippocampus()
    r = await h.remember("hi", "hello", "cat1", "gpt-4")
    assert r["user_msg"] == "hi"
    assert r["ai_reply"] == "hello"


# ===================================================================
# 模式 C — 完全替代
# ===================================================================


@pytest.mark.asyncio
async def test_mouth_mode_c():
    m = NoopMouth()
    r = await m.speak("hello")
    assert r == ""  # 默认
    m.mount_plug("speak", lambda text, **kw: f"[[{text}]]")
    r = await m.speak("hello")
    assert r == "[[hello]]"


@pytest.mark.asyncio
async def test_purr_mode_c():
    p = NoopPurr()
    r = await p.stream("hello")
    assert r is None
    p.mount_plug("stream", lambda text, **kw: text.upper())
    r = await p.stream("hello")
    assert r == "HELLO"


@pytest.mark.asyncio
async def test_tail_mode_c():
    t = NoopTail()
    await t.render({"status": "ok"})  # 默认 no-op
    rendered: list[dict[str, Any]] = []
    t.mount_plug("render", lambda s: rendered.append(s))
    await t.render({"status": "testing"})
    assert rendered == [{"status": "testing"}]


@pytest.mark.asyncio
async def test_eyes_mode_c():
    e = NoopEyes()
    r = await e.see(b"img", "image/png")
    assert r == {}
    e.mount_plug("see", lambda data, mime: {"caption": "a cat"})
    r = await e.see(b"img", "image/png")
    assert r == {"caption": "a cat"}


@pytest.mark.asyncio
async def test_paws_mode_c():
    p = NoopPaws()
    r = await p.execute("tool1", {"arg": 1})
    assert r == {"ok": False, "reason": "noop_paws: execute disabled"}
    p.mount_plug("execute", lambda name, params: {
                 "ok": True, "result": "done"})
    r = await p.execute("tool1", {"arg": 1})
    assert r == {"ok": True, "result": "done"}


# ===================================================================
# NoopThalamus 完整功能
# ===================================================================


@pytest.mark.asyncio
async def test_thalamus_locate_default():
    t = NoopThalamus()
    r = await t.locate("hello world", "session_1")
    assert r["route"] == "chat"
    assert r["entities"] == []
    assert r["snippets"] == []


def test_thalamus_decide_route():
    t = NoopThalamus()
    r = t.decide_route()
    assert r == {"route": "chat"}


def test_thalamus_hooks():
    t = NoopThalamus()
    assert "locate" in t.HOOKS
    assert "locate" in NoopThalamus.HOOKS


# ===================================================================
# NoopHippocampus 完整功能
# ===================================================================


def test_hippocampus_add_and_get_entity():
    h = NoopHippocampus()
    h.add_entity({"id": "e1", "name": "test_entity", "importance": 0.8})
    e = h.get_entity("e1")
    assert e is not None
    assert e["name"] == "test_entity"


def test_hippocampus_get_by_name():
    h = NoopHippocampus()
    h.add_entity({"id": "e1", "name": "alice"})
    h.add_entity({"id": "e2", "name": "bob"})
    assert h.get_by_name("alice") is not None
    assert h.get_by_name("charlie") is None


def test_hippocampus_get_all():
    h = NoopHippocampus()
    h.add_entity({"id": "e1"})
    h.add_entity({"id": "e2"})
    assert len(h.get_all()) == 2


def test_hippocampus_connect_and_get_related():
    h = NoopHippocampus()
    h.add_entity({"id": "e1", "name": "parent"})
    h.add_entity({"id": "e2", "name": "child"})
    h.connect("e1", "e2", "has_child", 0.9)
    related = h.get_related("e1")
    assert len(related) == 1
    assert related[0]["name"] == "child"


def test_hippocampus_fts_search():
    h = NoopHippocampus()
    h.add_episode({"user_msg": "what is python",
                  "ai_reply": "a programming language"})
    h.add_episode({"user_msg": "what is java", "ai_reply": "also a language"})
    results = h.fts_search("cat1", "python")
    assert len(results) == 1
    assert results[0]["user_msg"] == "what is python"


def test_hippocampus_stats():
    h = NoopHippocampus()
    h.add_entity({"id": "e1"})
    h.add_episode({"user_msg": "hi", "ai_reply": "hello"})
    stats = h.stats()
    assert stats["entities"] == 1
    assert stats["episodes"] == 1


def test_hippocampus_decay():
    h = NoopHippocampus()
    h.add_entity({"id": "e1", "importance": 0.5})
    count = h.decay()
    assert count == 1
    assert h.entities["e1"]["importance"] < 0.5


def test_hippocampus_serialize():
    h = NoopHippocampus()
    h.add_entity({"id": "e1", "name": "test"})
    d = h.to_dict()
    assert "entities" in d
    assert len(d["entities"]) == 1

    h2 = NoopHippocampus()
    h2.from_dict(d)
    assert h2.get_entity("e1") is not None


def test_hippocampus_dormant_access():
    h = NoopHippocampus()
    h.add_entity({"id": "e1"})
    h.record_access("e1")
    assert h.entities["e1"].get("_last_accessed", 0) > 0
    h.set_dormant("e1", True)
    assert h.entities["e1"]["dormant"] is True


def test_hippocampus_hooks():
    h = NoopHippocampus()
    assert "remember" in h.HOOKS
    assert "recall" in h.HOOKS


# ===================================================================
# Voice Protocols — isinstance 检查
# ===================================================================


def test_noop_mouth_is_mouth_protocol():
    m = NoopMouth()
    assert isinstance(m, MouthProtocol)


def test_noop_purr_is_purr_protocol():
    p = NoopPurr()
    assert isinstance(p, PurrProtocol)


def test_noop_tail_is_tail_protocol():
    t = NoopTail()
    assert isinstance(t, TailProtocol)


# ===================================================================
# create_cat 默认 Thalamus/Hippocampus
# ===================================================================


@pytest.mark.asyncio
async def test_create_cat_default_thalamus_hippocampus():
    """create_cat 不传 thalamus/hippocampus 时自动使用 Noop 实现。"""

    class FakeLLM:
        name = "fake"

        async def generate(self, prompt, **kw):
            return "ok"

        async def stream_generate(self, prompt, **kw):
            yield "ok"

        def reload_config(self):
            pass

    llm = FakeLLM()
    from meowcat.testing import make_test_colony
    colony = make_test_colony()
    cat = create_cat(container=colony, cerebrum=llm, name="test-cat")
    assert isinstance(cat.thalamus, NoopThalamus)
    assert isinstance(cat.hippocampus, NoopHippocampus)


# ===================================================================
# ORGAN_PROTOCOLS 包含 voice protocols
# ===================================================================


def test_organ_protocols_includes_voice():
    assert ("voice", "mouth") in ORGAN_PROTOCOLS
    assert ("voice", "purr") in ORGAN_PROTOCOLS
    assert ("voice", "tail") in ORGAN_PROTOCOLS
    assert ORGAN_PROTOCOLS[("voice", "mouth")] is MouthProtocol
    assert ORGAN_PROTOCOLS[("voice", "purr")] is PurrProtocol
    assert ORGAN_PROTOCOLS[("voice", "tail")] is TailProtocol


# ===================================================================
# Pluggable list_plugs 多 hook
# ===================================================================


def test_pluggable_multi_hook_list():
    a = NoopAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False})
    a.mount_plug("assess_tool_risk", lambda n, p: {"risk": "high"})
    lst = a.list_plugs()
    assert lst == {"assess_safety": 1, "assess_tool_risk": 1}
