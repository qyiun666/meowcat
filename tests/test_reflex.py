# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: ReflexRegistry 注册/匹配/校验。

验证:
- register 注册 / 同名替换 / priority 排序
- match 从高到低命中 / 无命中返回 None / trigger 异常不崩
- validate 校验 path 在 wiring 里合法 / 不合法抛异常
- unregister / get / all 查询
- hops 相邻跳序列
"""

from __future__ import annotations

import pytest

from meowcat.errors import ReflexPathInvalidError
from meowcat.reflex import Reflex, ReflexRegistry
from meowcat.wiring import Wiring


class TestReflexBasics:
    """Reflex 构造与 hops。"""

    def test_reflex_hops(self) -> None:
        r = Reflex(
            name="test",
            trigger=lambda x: True,
            path=(
                ("brain", "a"),
                ("brain", "b"),
                ("brain", "c"),
            ),
        )
        assert r.hops() == [
            (("brain", "a"), ("brain", "b")),
            (("brain", "b"), ("brain", "c")),
        ]

    def test_reflex_default_priority_zero(self) -> None:
        r = Reflex(
            name="test",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b")),
        )
        assert r.priority == 0

    def test_reflex_default_stages_empty(self) -> None:
        r = Reflex(
            name="test",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b")),
        )
        assert r.stages == []

    def test_reflex_single_hop_minimum(self) -> None:
        r = Reflex(
            name="test",
            trigger=lambda x: False,
            path=(("brain", "a"), ("sense", "ears")),
        )
        assert r.hops() == [(("brain", "a"), ("sense", "ears"))]


class TestReflexRegistryRegister:
    """ReflexRegistry 注册与排序。"""

    def test_register_and_get(self) -> None:
        reg = ReflexRegistry()
        r = Reflex(
            name="text",
            trigger=lambda x: "hello" in str(x),
            path=(("brain", "a"), ("brain", "b")),
        )
        reg.register(r)
        assert reg.get("text") is r

    def test_register_same_name_replaces(self) -> None:
        reg = ReflexRegistry()
        r1 = Reflex(name="x", trigger=lambda x: True,
                    path=(("brain", "a"), ("brain", "b")))
        r2 = Reflex(name="x", trigger=lambda x: False,
                    path=(("brain", "a"), ("brain", "b")))
        reg.register(r1)
        reg.register(r2)
        assert reg.get("x") is r2
        assert len(reg.all()) == 1

    def test_register_sorted_by_priority_desc(self) -> None:
        reg = ReflexRegistry()
        r_low = Reflex(name="low", trigger=lambda x: True,
                       path=(("brain", "a"), ("brain", "b")), priority=1)
        r_high = Reflex(name="high", trigger=lambda x: True,
                        path=(("brain", "a"), ("brain", "b")), priority=10)
        r_mid = Reflex(name="mid", trigger=lambda x: True,
                       path=(("brain", "a"), ("brain", "b")), priority=5)
        reg.register(r_low)
        reg.register(r_high)
        reg.register(r_mid)
        assert [r.name for r in reg.all()] == ["high", "mid", "low"]


class TestReflexRegistryMatch:
    """ReflexRegistry match 按优先级命中。"""

    def test_match_returns_highest_priority(self) -> None:
        reg = ReflexRegistry()
        hits: list[str] = []

        def make_trigger(name: str):
            def t(_x: str) -> bool:
                hits.append(name)
                return True
            return t

        reg.register(Reflex(name="low", trigger=make_trigger("low"),
                            path=(("brain", "a"), ("brain", "b")), priority=1))
        reg.register(Reflex(name="high", trigger=make_trigger("high"),
                            path=(("brain", "a"), ("brain", "b")), priority=10))
        result = reg.match("hello")
        assert result is not None
        assert result.name == "high"

    def test_match_no_match_returns_none(self) -> None:
        reg = ReflexRegistry()
        reg.register(Reflex(
            name="never", trigger=lambda x: False,
            path=(("brain", "a"), ("brain", "b")),
        ))
        assert reg.match("hello") is None

    def test_match_trigger_exception_is_silent(self) -> None:
        reg = ReflexRegistry()
        reg.register(Reflex(
            name="crash",
            trigger=lambda x: (_ for _ in ()).throw(
                ValueError("boom")),  # type: ignore[arg-type]
            path=(("brain", "a"), ("brain", "b")),
        ))
        reg.register(Reflex(
            name="fallback",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b")),
        ))
        result = reg.match("hello")
        assert result is not None
        assert result.name == "fallback"


class TestReflexRegistryValidate:
    """ReflexRegistry validate 校验 path 合法性。"""

    def test_validate_all_legal_passes(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        w.connect(("brain", "b"), ("brain", "c"))
        reg = ReflexRegistry()
        reg.register(Reflex(
            name="ok",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b"), ("brain", "c")),
        ))
        reg.validate(w)  # 不抛

    def test_validate_illegal_hop_raises(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        # brain,b → brain,c 不在 wiring 里
        reg = ReflexRegistry()
        reg.register(Reflex(
            name="bad",
            trigger=lambda x: True,
            path=(("brain", "a"), ("brain", "b"), ("brain", "c")),
        ))
        with pytest.raises(ReflexPathInvalidError) as exc:
            reg.validate(w)
        assert exc.value.reflex_name == "bad"


class TestReflexRegistryUnregister:
    """unregister 移除。"""

    def test_unregister_existing(self) -> None:
        reg = ReflexRegistry()
        r = Reflex(name="x", trigger=lambda x: True,
                   path=(("brain", "a"), ("brain", "b")))
        reg.register(r)
        assert reg.unregister("x") is True
        assert reg.get("x") is None

    def test_unregister_nonexistent(self) -> None:
        reg = ReflexRegistry()
        assert reg.unregister("no-such") is False


# -- from v0.5.1: 补充反射弧契约测试 -----------------------------


def _always_trigger(_input: object) -> bool:
    return True


def _never_trigger(_input: object) -> bool:
    return False


def _text_trigger(input: object) -> bool:
    return isinstance(input, str)


class TestReflex:
    """v0.5.1: Reflex model: hops / path 校验 / priority。"""

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


class TestReflexRegistry:
    """v0.5.1: register / 同名替换 / unregister / get / match / all。"""

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


class TestReflexValidate:
    """v0.5.1: ReflexRegistry.validate 校验 wiring 合法性。"""

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
