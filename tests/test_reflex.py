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
            trigger=lambda x: (_ for _ in ()).throw(ValueError("boom")),  # type: ignore[arg-type]
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
