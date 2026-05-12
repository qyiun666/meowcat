# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: Wiring 连通/禁止/冻结/快照。

验证:
- connect / forbid / is_allowed / assert_allowed
- 黑名单优先级高于白名单
- freeze 后写操作抛异常
- snapshot / edges / forbids 只读视图
- connect_many / forbid_many 批量操作
- 非法 Organ 参数校验
"""

from __future__ import annotations

import pytest

from meowcat.errors import IllegalNeuralPathError, MeowCatError
from meowcat.wiring import Edge, Organ, Wiring


class TestWiringConnectAndForbid:
    """connect / forbid / is_allowed / assert_allowed 基础契约。"""

    def test_connect_then_allowed(self) -> None:
        w = Wiring()
        w.connect(("brain", "thalamus"), ("brain", "cerebrum"))
        assert w.is_allowed(("brain", "thalamus"), ("brain", "cerebrum"))

    def test_not_connected_returns_false(self) -> None:
        w = Wiring()
        assert not w.is_allowed(("brain", "x"), ("sense", "y"))

    def test_forbid_overrides_connect(self) -> None:
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        assert not w.is_allowed(("brain", "cerebrum"), ("sense", "paws"))

    def test_assert_allowed_raises_on_forbidden(self) -> None:
        w = Wiring()
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        with pytest.raises(IllegalNeuralPathError) as exc:
            w.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))
        assert "forbidden" in str(exc.value)

    def test_assert_allowed_raises_on_not_connected(self) -> None:
        w = Wiring()
        with pytest.raises(IllegalNeuralPathError) as exc:
            w.assert_allowed(("brain", "a"), ("brain", "b"))
        assert "not connected" in str(exc.value)

    def test_assert_allowed_passes_on_connected(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        w.assert_allowed(("brain", "a"), ("brain", "b"))  # 不抛


class TestWiringFreeze:
    """freeze 后写操作抛 MeowCatError。"""

    def test_freeze_sets_frozen(self) -> None:
        w = Wiring()
        assert not w.frozen
        w.freeze()
        assert w.frozen

    def test_connect_after_freeze_raises(self) -> None:
        w = Wiring()
        w.freeze()
        with pytest.raises(MeowCatError):
            w.connect(("brain", "a"), ("brain", "b"))

    def test_forbid_after_freeze_raises(self) -> None:
        w = Wiring()
        w.freeze()
        with pytest.raises(MeowCatError):
            w.forbid(("brain", "a"), ("brain", "b"))

    def test_is_allowed_still_works_after_freeze(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        w.freeze()
        assert w.is_allowed(("brain", "a"), ("brain", "b"))

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


class TestWiringSnapshot:
    """WiringSnapshot 不可变快照。"""

    def test_snapshot_reflects_current_state(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        w.forbid(("brain", "x"), ("brain", "y"))
        snap = w.snapshot()
        assert snap.is_allowed(("brain", "a"), ("brain", "b"))
        assert not snap.is_allowed(("brain", "x"), ("brain", "y"))
        assert len(snap.allowed) == 1
        assert len(snap.forbidden) == 1

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
        w = Wiring()
        w.connect(("a", "x"), ("b", "y"))
        snap = w.snapshot()
        with pytest.raises(AttributeError):
            # type: ignore[union-attr]
            snap.allowed.add((("x", "y"), ("z", "w")))


class TestWiringIntrospection:
    """edges / forbids 只读视图。"""

    def test_edges_returns_allowed(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        assert (("brain", "a"), ("brain", "b")) in w.edges()

    def test_forbids_returns_forbidden(self) -> None:
        w = Wiring()
        w.forbid(("brain", "x"), ("brain", "y"))
        assert (("brain", "x"), ("brain", "y")) in w.forbids()

    def test_edges_and_forbids_are_frozenset(self) -> None:
        w = Wiring()
        assert isinstance(w.edges(), frozenset)
        assert isinstance(w.forbids(), frozenset)


class TestWiringBulk:
    """connect_many / forbid_many 批量操作。"""

    def test_connect_many(self) -> None:
        w = Wiring()
        w.connect_many([
            (("brain", "a"), ("brain", "b")),
            (("brain", "b"), ("brain", "c")),
        ])
        assert w.is_allowed(("brain", "a"), ("brain", "b"))
        assert w.is_allowed(("brain", "b"), ("brain", "c"))

    def test_forbid_many(self) -> None:
        w = Wiring()
        w.connect(("brain", "a"), ("brain", "b"))
        w.forbid_many([
            (("brain", "a"), ("brain", "b")),
            (("brain", "x"), ("brain", "y")),
        ])
        assert not w.is_allowed(("brain", "a"), ("brain", "b"))
        assert not w.is_allowed(("brain", "x"), ("brain", "y"))


class TestOrganValidation:
    """Organ 参数校验。"""

    def test_invalid_organ_raises_value_error(self) -> None:
        w = Wiring()
        with pytest.raises(ValueError):
            w.connect(("brain",), ("brain", "a"))  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            w.connect(("brain", ""), ("brain", "a"))
        with pytest.raises(ValueError):
            w.connect(("brain", "a"), (123, "b"))  # type: ignore[arg-type]

    def test_empty_string_name_raises(self) -> None:
        w = Wiring()
        with pytest.raises(ValueError):
            w.connect(("brain", ""), ("brain", "a"))


class TestWiringEdgeTypes:
    """Edge / Organ 类型别名可用。"""

    def test_edge_type(self) -> None:
        edge: Edge = (("brain", "a"), ("brain", "b"))
        assert len(edge) == 2

    def test_organ_type(self) -> None:
        organ: Organ = ("brain", "cerebrum")
        assert organ[0] == "brain"
        assert organ[1] == "cerebrum"


# -- from v0.5.1: 补充契约测试 ----------------------------------


class TestWiringConnect:
    """v0.5.1: connect / connect_many / 幂等 / 参数校验。"""

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


class TestWiringForbid:
    """v0.5.1: forbid / forbid_many / 黑名单优先。"""

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
        w = Wiring()
        w.connect(("brain", "cerebrum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        assert not w.is_allowed(("brain", "cerebrum"), ("sense", "paws"))

    def test_forbid_idempotent(self) -> None:
        w = Wiring()
        w.forbid(("a", "x"), ("b", "y"))
        w.forbid(("a", "x"), ("b", "y"))
        assert not w.is_allowed(("a", "x"), ("b", "y"))


class TestWiringQuery:
    """v0.5.1: is_allowed / assert_allowed / edges / forbids。"""

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
