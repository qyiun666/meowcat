"""
v0.5.1 Task 1.9a — Wiring 神经通路图契约测试
================================================

契约类别：
    1. TestWiringConnect     — connect / connect_many / 幂等 / organ 校验
    2. TestWiringForbid      — forbid / forbid_many / 黑名单优先
    3. TestWiringFreeze      — freeze 后禁止写 / 冻结幂等
    4. TestWiringQuery       — is_allowed / assert_allowed / edges / forbids
    5. TestWiringSnapshot    — 不可变快照

参考：docs/v0.5.1/design.md
"""

from __future__ import annotations

import pytest

from meowcat.errors import IllegalNeuralPathError, MeowCatError
from meowcat.wiring import Edge, Organ, Wiring, WiringSnapshot


# -- 1. connect ---------------------------------------------------

class TestWiringConnect:
    """connect / connect_many / 幂等 / 参数校验。"""

    def test_connect_basic(self) -> None:
        w = Wiring()
        w.connect(("brain", "cerebellum"), ("sense", "paws"))
        assert w.is_allowed(("brain", "cerebellum"), ("sense", "paws"))

    def test_connect_idempotent(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.connect(("a", "x"), ("b", "y"))
        assert w.is_allowed(("a", "x"), ("b", "y"))

    def test_connect_many(self) -> None:
        w = Wiring()
        edges: list[Edge] = [
            (("a", "x"), ("b", "y")),
            (("b", "y"), ("c", "z")),
        ]
        w.connect_many(edges)
        assert w.is_allowed(("a", "x"), ("b", "y"))
        assert w.is_allowed(("b", "y"), ("c", "z"))

    def test_connect_rejects_invalid_organ_type(self) -> None:
        w = Wiring()
        with pytest.raises(ValueError, match="must be .*str.*str"):
            w.connect(("x", "y"), "not-a-tuple")  # type: ignore[arg-type]

    def test_connect_rejects_empty_string_category(self) -> None:
        w = Wiring()
        with pytest.raises(ValueError, match="must be .*str.*str"):
            w.connect(("", "y"), ("b", "z"))

    def test_connect_rejects_wrong_length_tuple(self) -> None:
        w = Wiring()
        with pytest.raises(ValueError, match="must be .*str.*str"):
            w.connect(("x", "y", "z"), ("a", "b"))  # type: ignore[arg-type]


# -- 2. forbid ----------------------------------------------------

class TestWiringForbid:
    """forbid / forbid_many / 黑名单优先。"""

    def test_forbid_basic(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("b", "y"))
        assert not w.is_allowed(("a", "x"), ("b", "y"))

    def test_forbid_many(self) -> None:
        w = Wiring()
        w.forbid_many([
            (("a", "x"), ("b", "y")),
            (("b", "y"), ("c", "z")),
        ])
        assert not w.is_allowed(("a", "x"), ("b", "y"))
        assert not w.is_allowed(("b", "y"), ("c", "z"))

    def test_forbid_priority_over_connect(self) -> None:
        """黑名单优先级高于白名单——即使 connect 过也报非法。"""
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        assert not w.is_allowed(("brain", "cerebrum"), ("sense", "paws"))

    def test_forbid_idempotent(self) -> None:
        w = Wiring()
        w.forbid(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("b", "y"))
        assert not w.is_allowed(("a", "x"), ("b", "y"))


# -- 3. freeze ----------------------------------------------------

class TestWiringFreeze:
    """freeze 后禁止写 / 冻结幂等。"""

    def test_freeze_blocks_connect(self) -> None:
        w = Wiring()
        w.freeze()
        with pytest.raises(MeowCatError, match="frozen"):
            w.connect(("a", "x"), ("b", "y"))

    def test_freeze_blocks_forbid(self) -> None:
        w = Wiring()
        w.freeze()
        with pytest.raises(MeowCatError, match="frozen"):
            w.forbid(("a", "x"), ("b", "y"))

    def test_freeze_idempotent(self) -> None:
        w = Wiring()
        w.freeze()
        w.freeze()  # 不应抛
        assert w.frozen

    def test_frozen_property(self) -> None:
        w = Wiring()
        assert not w.frozen
        w.freeze()
        assert w.frozen


# -- 4. 查询 ------------------------------------------------------

class TestWiringQuery:
    """is_allowed / assert_allowed / edges / forbids。"""

    def test_is_allowed_unknown_edge_returns_false(self) -> None:
        w = Wiring()
        assert not w.is_allowed(("a", "x"), ("b", "y"))

    def test_assert_allowed_raises_on_forbidden(self) -> None:
        w = Wiring()
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        with pytest.raises(IllegalNeuralPathError, match="Illegal neural path"):
            w.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))

    def test_assert_allowed_raises_on_unconnected(self) -> None:
        w = Wiring()
        with pytest.raises(IllegalNeuralPathError):
            w.assert_allowed(("a", "x"), ("b", "y"))

    def test_assert_allowed_passes_on_connected(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.assert_allowed(("a", "x"), ("b", "y"))  # 不抛即通过

    def test_edges_returns_frozenset(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        assert isinstance(w.edges(), frozenset)
        assert ((("a", "x"), ("b", "y"))) in w.edges()

    def test_forbids_returns_frozenset(self) -> None:
        w = Wiring()
        w.forbid(("a", "x"), ("b", "y"))
        assert isinstance(w.forbids(), frozenset)
        assert ((("a", "x"), ("b", "y"))) in w.forbids()


# -- 5. WiringSnapshot ---------------------------------------------

class TestWiringSnapshot:
    """不可变快照：is_allowed / allowed / forbidden 属性。"""

    def test_snapshot_is_allowed(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("c", "z"))
        snap = w.snapshot()
        assert snap.is_allowed(("a", "x"), ("b", "y"))
        assert not snap.is_allowed(("a", "x"), ("c", "z"))
        assert not snap.is_allowed(("a", "x"), ("unknown", "z"))

    def test_snapshot_allowed_forbidden_props(self) -> None:
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("c", "z"))
        snap = w.snapshot()
        assert isinstance(snap.allowed, frozenset)
        assert isinstance(snap.forbidden, frozenset)
        assert ((("a", "x"), ("b", "y"))) in snap.allowed
        assert ((("a", "x"), ("c", "z"))) in snap.forbidden

    def test_snapshot_is_immutable(self) -> None:
        """快照的 frozenset 不可变。"""
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        snap = w.snapshot()
        with pytest.raises(AttributeError):
            # type: ignore[union-attr]
            snap.allowed.add((("x", "y"), ("z", "w")))
