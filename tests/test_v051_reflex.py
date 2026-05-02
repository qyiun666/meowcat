"""
v0.5.1 Task 1.9b — Reflex 反射弧 + ReflexRegistry 契约测试
============================================================

契约类别：
    1. TestReflex            — hops / path 长度校验 / priority 排序
    2. TestReflexRegistry    — register / 同名替换 / unregister / get / match / all
    3. TestReflexValidate    — validate 校验 wiring 合法性

参考：docs/v0.5.1/design.md
"""

from __future__ import annotations

import pytest

from meowcat.errors import ReflexPathInvalidError
from meowcat.reflex import Reflex, ReflexRegistry
from meowcat.wiring import Wiring


def _always_trigger(_input: object) -> bool:
    return True


def _never_trigger(_input: object) -> bool:
    return False


def _text_trigger(input: object) -> bool:
    return isinstance(input, str)


# -- 1. Reflex -----------------------------------------------------

class TestReflex:
    """Reflex model: hops / path 校验 / priority。"""

    def test_hops_two_hops(self) -> None:
        r = Reflex(
            name="test",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y"), ("c", "z")),
        )
        assert r.hops() == [
            (("a", "x"), ("b", "y")),
            (("b", "y"), ("c", "z")),
        ]

    def test_hops_single_hop(self) -> None:
        r = Reflex(
            name="min",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        assert r.hops() == [(("a", "x"), ("b", "y"))]

    def test_default_stages_empty(self) -> None:
        r = Reflex(
            name="bare",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        assert r.stages == []

    def test_default_priority_zero(self) -> None:
        r = Reflex(
            name="def",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        assert r.priority == 0


# -- 2. ReflexRegistry ---------------------------------------------

class TestReflexRegistry:
    """register / 同名替换 / unregister / get / match / all。"""

    def test_register_and_get(self) -> None:
        reg = ReflexRegistry()
        r = Reflex(
            name="hello",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        reg.register(r)
        assert reg.get("hello") is r

    def test_register_rejects_one_hop_path(self) -> None:
        reg = ReflexRegistry()
        r = Reflex(
            name="bad",
            trigger=_always_trigger,
            path=(("a", "x"),),  # 只有 1 个器官，凑不出 hop
        )
        with pytest.raises(ValueError, match="at least 2 hops"):
            reg.register(r)

    def test_register_same_name_replaces(self) -> None:
        reg = ReflexRegistry()
        r1 = Reflex(
            name="dup",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=1,
        )
        r2 = Reflex(
            name="dup",
            trigger=_never_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=10,
        )
        reg.register(r1)
        reg.register(r2)
        assert reg.get("dup") is r2  # 后注册替换

    def test_unregister_existing(self) -> None:
        reg = ReflexRegistry()
        r = Reflex(
            name="tmp",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        reg.register(r)
        assert reg.unregister("tmp") is True
        assert reg.get("tmp") is None

    def test_unregister_nonexistent(self) -> None:
        reg = ReflexRegistry()
        assert reg.unregister("never") is False

    def test_match_returns_none_on_empty(self) -> None:
        reg = ReflexRegistry()
        assert reg.match("hello") is None

    def test_match_returns_first_trigger(self) -> None:
        reg = ReflexRegistry()
        r_text = Reflex(
            name="text",
            trigger=_text_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=10,
        )
        r_always = Reflex(
            name="fallback",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=1,
        )
        reg.register(r_always)
        reg.register(r_text)  # higher priority → 先被 try
        # text 输入 → 命中 text
        assert reg.match("hello world") is r_text
        # int 输入 → text 不命中，fallback 中
        assert reg.match(42) is r_always

    def test_match_sort_by_priority(self) -> None:
        """高 priority 的先被尝试。"""
        reg = ReflexRegistry()
        low = Reflex(
            name="low",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=1,
        )
        high = Reflex(
            name="high",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=100,
        )
        reg.register(low)
        reg.register(high)
        assert reg.match("anything") is high

    def test_match_trigger_exception_is_skipped(self) -> None:
        def boom(_input: object) -> bool:
            raise RuntimeError("trigger fail")

        reg = ReflexRegistry()
        r_bad = Reflex(
            name="bad",
            trigger=boom,
            path=(("a", "x"), ("b", "y")),
            priority=10,
        )
        r_ok = Reflex(
            name="ok",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
            priority=1,
        )
        reg.register(r_ok)
        reg.register(r_bad)
        assert reg.match("test") is r_ok

    def test_all_returns_copy(self) -> None:
        reg = ReflexRegistry()
        r1 = Reflex(
            name="r1",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        r2 = Reflex(
            name="r2",
            trigger=_never_trigger,
            path=(("a", "x"), ("b", "y")),
        )
        reg.register(r1)
        reg.register(r2)
        items = reg.all()
        assert len(items) == 2
        # 按 priority 倒序；默认 0 所以 r1 和 r2 都 priority=0，顺序是注册序
        names = [r.name for r in items]
        assert "r1" in names
        assert "r2" in names


# -- 3. validate ---------------------------------------------------

class TestReflexValidate:
    """ReflexRegistry.validate 校验 wiring 合法性。"""

    def test_validate_all_hops_valid(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.connect(("b", "y"), ("c", "z"))

        reg = ReflexRegistry()
        reg.register(Reflex(
            name="good",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y"), ("c", "z")),
        ))
        reg.validate(w)  # 不应抛

    def test_validate_invalid_hop_raises(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        # ("b","y") → ("c","z") 没 connect

        reg = ReflexRegistry()
        reg.register(Reflex(
            name="bad_hop",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y"), ("c", "z")),
        ))
        with pytest.raises(ReflexPathInvalidError, match="bad_hop"):
            reg.validate(w)

    def test_validate_forbidden_hop_raises(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("b", "y"))

        reg = ReflexRegistry()
        reg.register(Reflex(
            name="forbidden_hop",
            trigger=_always_trigger,
            path=(("a", "x"), ("b", "y")),
        ))
        with pytest.raises(ReflexPathInvalidError, match="forbidden_hop"):
            reg.validate(w)
