# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.0.7 Pluggable + Default 全补齐 + Voice Protocols 测试。

覆盖:
- Pluggable mixin 的 mount/unmount/_run_plugs/list_plugs
- 15 个 Default 器官的三模式插件执行 (A/B/C)
- DefaultThalamus / DefaultHippocampus 功能
- Voice Protocols (Mouth/Purr/Tail)
- create_cat() 默认使用 DefaultThalamus/DefaultHippocampus
"""

from __future__ import annotations

from typing import Any

import pytest

from meowcat import (
    MouthProtocol,
    DefaultAmygdala,
    DefaultBrainstem,
    DefaultCortex,
    DefaultEars,
    DefaultEyes,
    DefaultFrontal,
    DefaultHippocampus,
    DefaultHypothalamus,
    DefaultMouth,
    DefaultPaws,
    DefaultPurr,
    DefaultTail,
    DefaultThalamus,
    DefaultWhiskers,
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


@pytest.mark.anyio
async def test_amygdala_mode_a_default():
    a = DefaultAmygdala()
    r = await a.assess_safety("hi")
    assert r == {"safe": True, "risk": "low"}


@pytest.mark.anyio
async def test_amygdala_mode_a_plug_block():
    a = DefaultAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False, "risk": "block"})
    r = await a.assess_safety("malicious input")
    assert r == {"safe": False, "risk": "block"}


@pytest.mark.anyio
async def test_amygdala_mode_a_plug_first_wins():
    a = DefaultAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False, "risk": "block"})
    a.mount_plug("assess_safety", lambda x: {
                 "safe": False, "risk": "override"})
    r = await a.assess_safety("test")
    # 第一个返回非安全即返回
    assert r == {"safe": False, "risk": "block"}


@pytest.mark.anyio
async def test_amygdala_mode_a_plug_safe_passes():
    a = DefaultAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": True, "risk": "none"})
    r = await a.assess_safety("hello")
    assert r == {"safe": True, "risk": "low"}  # 默认（插件 safe 穿透后落回 Default）


@pytest.mark.anyio
async def test_frontal_mode_a():
    f = DefaultFrontal()
    assert f.is_continue("msg") is False
    f.mount_plug("is_continue", lambda _: True)
    assert f.is_continue("msg") is True


@pytest.mark.anyio
async def test_frontal_mode_a_detect_shift():
    f = DefaultFrontal()
    assert f.detect_shift("msg") is True  # 无已知关键词时默认视为转移
    f.mount_plug("detect_shift", lambda _: False)
    assert f.detect_shift("msg") is False


# ===================================================================
# 模式 B — 合并增强
# ===================================================================


@pytest.mark.anyio
async def test_ears_mode_b_hear():
    e = DefaultEars()
    r = await e.hear("hello")
    assert r == {"text": "hello", "keywords": ["hello"], "language": "en"}

    e.mount_plug("hear", lambda raw: {"language": "zh", "keywords": ["hello"]})
    r = await e.hear("hello")
    assert r == {"text": "hello", "keywords": ["hello"], "language": "zh"}


@pytest.mark.anyio
async def test_ears_mode_b_extract_keywords():
    e = DefaultEars()
    r = e.extract_keywords("test")
    assert r == ["test"]

    e.mount_plug("extract_keywords", lambda text, top_k: ["a", "b"])
    r = e.extract_keywords("test")
    assert r == ["test", "a", "b"]


@pytest.mark.anyio
async def test_whiskers_mode_b():
    w = DefaultWhiskers()
    r = await w.feel_input("test")
    assert r.get("length") == 4
    assert r.get("has_code") is False
    w.mount_plug("feel_input", lambda t: {"injection": True})
    r = await w.feel_input("test")
    assert r["injection"] is True


@pytest.mark.anyio
async def test_whiskers_mode_b_hallucination():
    w = DefaultWhiskers()
    r = w.check_hallucination("reply", "s1")
    assert r == {"hallucination": False}
    w.mount_plug("check_hallucination", lambda reply,
                 sid: {"hallucination": True})
    r = w.check_hallucination("reply", "s1")
    assert r == {"hallucination": True}


@pytest.mark.anyio
async def test_hypothalamus_mode_b():
    h = DefaultHypothalamus()
    r = await h.run_maintenance()
    assert r == {"decayed": 0, "orphans_cleaned": 0,
                 "woke": 0, "suggestions": []}
    h.mount_plug("run_maintenance", lambda cc: {"decayed": 5})
    r = await h.run_maintenance()
    assert r["decayed"] == 5
    assert r["orphans_cleaned"] == 0  # 保留默认


@pytest.mark.anyio
async def test_cortex_mode_b():
    c = DefaultCortex()
    r = c.synthesize(100)
    assert r == ""
    c.mount_plug("synthesize", lambda mt: "worldview snippet")
    r = c.synthesize(100)
    assert r == "worldview snippet"


@pytest.mark.anyio
async def test_brainstem_mode_b():
    b = DefaultBrainstem()
    r = await b.build_system_prompt("cerebrum", "chat")
    assert r != ""
    # default prompt contains the cat name
    assert "MeowCat" in r
    b.mount_plug("build_system_prompt", lambda organ, route,
                 snapshot=None: f"prompt for {route}")
    r = await b.build_system_prompt("cerebrum", "chat")
    assert r == "prompt for chat"


@pytest.mark.anyio
async def test_thalamus_mode_b():
    t = DefaultThalamus()
    r = await t.locate("hello", "s1")
    assert r["route"] == "chat"
    t.mount_plug("locate", lambda msg, sid: {"route": "danger"})
    r = await t.locate("hello", "s1")
    assert r["route"] == "danger"


@pytest.mark.anyio
async def test_hippocampus_mode_b_remember():
    h = DefaultHippocampus()
    r = await h.remember("hi", "hello", "cat1", "gpt-4")
    assert r["user_msg"] == "hi"
    assert r["ai_reply"] == "hello"


# ===================================================================
# 模式 C — 完全替代
# ===================================================================


@pytest.mark.anyio
async def test_mouth_mode_c():
    m = DefaultMouth()
    r = await m.speak("hello")
    assert r == "hello"  # 默认返回传入文本
    m.mount_plug("speak", lambda text, **kw: f"[[{text}]]")
    r = await m.speak("hello")
    assert r == "[[hello]]"


@pytest.mark.anyio
async def test_purr_mode_c():
    p = DefaultPurr()
    r = await p.stream("hello")
    assert r is None
    p.mount_plug("stream", lambda text, **kw: text.upper())
    r = await p.stream("hello")
    assert r == "HELLO"


@pytest.mark.anyio
async def test_tail_mode_c():
    t = DefaultTail()
    await t.render({"status": "ok"})  # 默认 no-op
    rendered: list[dict[str, Any]] = []
    t.mount_plug("render", lambda s: rendered.append(s))
    await t.render({"status": "testing"})
    assert rendered == [{"status": "testing"}]


@pytest.mark.anyio
async def test_eyes_mode_c():
    e = DefaultEyes()
    r = await e.see(b"img", "image/png")
    assert r == {"format": "image/png", "size_bytes": 3,
                 "width_hint": "unknown", "height_hint": "unknown"}
    e.mount_plug("see", lambda data, mime: {"caption": "a cat"})
    r = await e.see(b"img", "image/png")
    assert r == {"caption": "a cat"}


@pytest.mark.anyio
async def test_paws_mode_c():
    p = DefaultPaws()
    r = await p.execute("tool1", {"arg": 1})
    assert r == {"ok": False, "reason": "no tool_registry mounted"}
    p.mount_plug("execute", lambda name, params: {
                 "ok": True, "result": "done"})
    r = await p.execute("tool1", {"arg": 1})
    assert r == {"ok": True, "result": "done"}


# ===================================================================
# DefaultThalamus 完整功能
# ===================================================================


@pytest.mark.anyio
async def test_thalamus_locate_default():
    t = DefaultThalamus()
    r = await t.locate("hello world", "session_1")
    assert r["route"] == "chat"
    assert r["entities"] == []
    assert r["snippets"] == []


def test_thalamus_decide_route():
    t = DefaultThalamus()
    r = t.decide_route()
    assert r["route"] == "chat"
    assert r["keywords"] == []  # 无输入时关键词为空


def test_thalamus_hooks():
    t = DefaultThalamus()
    assert "locate" in t.HOOKS
    assert "locate" in DefaultThalamus.HOOKS


# ===================================================================
# DefaultHippocampus 完整功能
# ===================================================================


def test_hippocampus_add_and_get_entity():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1", "name": "test_entity", "importance": 0.8})
    e = h.get_entity("e1")
    assert e is not None
    assert e["name"] == "test_entity"


def test_hippocampus_get_by_name():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1", "name": "alice"})
    h.add_entity({"id": "e2", "name": "bob"})
    assert h.get_by_name("alice") is not None
    assert h.get_by_name("charlie") is None


def test_hippocampus_get_all():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1"})
    h.add_entity({"id": "e2"})
    assert len(h.get_all()) == 2


def test_hippocampus_connect_and_get_related():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1", "name": "parent"})
    h.add_entity({"id": "e2", "name": "child"})
    h.connect("e1", "e2", "has_child", 0.9)
    related = h.get_related("e1")
    assert len(related) == 1
    assert related[0]["name"] == "child"


def test_hippocampus_fts_search():
    h = DefaultHippocampus()
    h.add_episode({"user_msg": "what is python",
                  "ai_reply": "a programming language"})
    h.add_episode({"user_msg": "what is java", "ai_reply": "also a language"})
    results = h.fts_search("cat1", "python")
    assert len(results) == 1
    assert results[0]["user_msg"] == "what is python"


def test_hippocampus_stats():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1"})
    h.add_episode({"user_msg": "hi", "ai_reply": "hello"})
    stats = h.stats()
    assert stats["entities"] == 1
    assert stats["episodes"] == 1


def test_hippocampus_decay():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1", "importance": 0.5})
    count = h.decay()
    assert count == 1
    assert h.entities["e1"]["importance"] < 0.5


def test_hippocampus_serialize():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1", "name": "test"})
    d = h.to_dict()
    assert "entities" in d
    assert len(d["entities"]) == 1

    h2 = DefaultHippocampus()
    h2.from_dict(d)
    assert h2.get_entity("e1") is not None


def test_hippocampus_dormant_access():
    h = DefaultHippocampus()
    h.add_entity({"id": "e1"})
    h.record_access("e1")
    assert h.entities["e1"].get("_last_accessed", 0) > 0
    h.set_dormant("e1", True)
    assert h.entities["e1"]["dormant"] is True


def test_hippocampus_hooks():
    h = DefaultHippocampus()
    assert "remember" in h.HOOKS
    assert "recall" in h.HOOKS


# ===================================================================
# Voice Protocols — isinstance 检查
# ===================================================================


def test_noop_mouth_is_mouth_protocol():
    m = DefaultMouth()
    assert isinstance(m, MouthProtocol)


def test_noop_purr_is_purr_protocol():
    p = DefaultPurr()
    assert isinstance(p, PurrProtocol)


def test_noop_tail_is_tail_protocol():
    t = DefaultTail()
    assert isinstance(t, TailProtocol)


# ===================================================================
# create_cat 默认 Thalamus/Hippocampus
# ===================================================================


@pytest.mark.anyio
async def test_create_cat_default_thalamus_hippocampus():
    """create_cat 不传 thalamus/hippocampus 时自动使用 Default 实现。"""

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
    assert isinstance(cat.thalamus, DefaultThalamus)
    assert isinstance(cat.hippocampus, DefaultHippocampus)


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
    a = DefaultAmygdala()
    a.mount_plug("assess_safety", lambda x: {"safe": False})
    a.mount_plug("assess_tool_risk", lambda n, p: {"risk": "high"})
    lst = a.list_plugs()
    assert lst == {"assess_safety": 1, "assess_tool_risk": 1}
