# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""
v1.0.1 — CatBase 权限控制（替代 KittenBase 的 wiring 裁剪 + 方法黑名单）
========================================================================

验证 CatBase 新参数:
    1. TestParentId        — parent_id 只是字符串，无父猫对象引用
    2. TestAllowedOrgans   — allowed_organs 拒绝禁止器官名的直接访问
    3. TestForbiddenMethods — forbidden_methods 阻止主猫专属方法调用
    4. TestDefaultCatBase   — 默认 CatBase 行为不变（无限制）
"""

from __future__ import annotations

import pytest

from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.biology import CEREBRUM, HIPPOCAMPUS, THALAMUS
from meowcat.errors import IllegalNeuralPathError


# -- 1. parent_id 只是字符串 ----------------------------------------

class TestParentId:
    """parent_id 不持有父猫对象引用。"""

    def test_parent_id_none_by_default(self) -> None:
        cat = make_cat("cat1")
        assert cat.parent_id is None

    def test_parent_id_is_string(self) -> None:
        cat = make_cat("cat1", parent_id="main-cat")
        assert cat.parent_id == "main-cat"
        # parent_id 只是字符串，不是对象引用
        assert isinstance(cat.parent_id, str)


# -- 2. allowed_organs 器官属性拦截 --------------------------------

class TestAllowedOrgans:
    """allowed_organs 限制 CatBase 的直接属性访问。"""

    def test_none_allows_all(self) -> None:
        """allowed_organs=None（默认）全部放行。"""
        cat = make_cat("cat1")
        # 非器官属性正常访问
        assert cat.name == "cat1"
        # 不存在的属性抛普通 AttributeError
        with pytest.raises(AttributeError):
            _ = cat.hippocampus

    def test_allowed_organs_blocks_forbidden(self) -> None:
        """allowed_organs 有值时拦截禁止器官名。"""
        cat = make_cat(
            "cat1",
            allowed_organs=frozenset({"cerebellum", "cerebrum", "paws"}),
        )
        with pytest.raises(IllegalNeuralPathError, match="hippocampus"):
            _ = cat.hippocampus

    def test_allowed_organs_passes_allowed(self) -> None:
        """allowed_organs 集合内的属性不抛 IllegalNeuralPathError。"""
        cat = make_cat(
            "cat1",
            allowed_organs=frozenset({"cerebrum"}),
        )
        # cerebrum 在允许列表中，未挂载 → AttributeError（不是 Illegal）
        try:
            _ = cat.cerebrum
        except AttributeError:
            pass  # 预期：未设置所以不存在
        except IllegalNeuralPathError:
            pytest.fail("cerebrum 在 allowed_organs 中，不应被拦截")

    def test_underscore_prefix_skips_check(self) -> None:
        """_ 前缀私有属性零开销跳过 allowed_organs 检查。"""
        cat = make_cat(
            "cat1",
            allowed_organs=frozenset({"cerebrum"}),
        )
        # _host 等私有属性不经过拦截
        assert cat._host is not None
        assert cat._events is not None

    def test_cat_id_always_accessible(self) -> None:
        """cat_uid（property）不受 allowed_organs 影响。"""
        cat = make_cat(
            "cat1",
            allowed_organs=frozenset({"cerebrum"}),
        )
        assert cat.name == "cat1"  # cat_uid/name 始终可访问


# -- 3. forbidden_methods 方法黑名单 --------------------------------

class _DummyOrgan:
    def __init__(self, name: str = "dummy") -> None:
        self.name = name

    def spawn_kitten(self, *args, **kwargs):
        return "spawned"

    def absorb_merge(self, *args, **kwargs):
        return "absorbed"

    def regular_method(self, *args, **kwargs):
        return "ok"


class TestForbiddenMethods:
    """CatBase.forbidden_methods 阻止指定方法名调用。"""

    @pytest.fixture
    def cat(self) -> CatBase:
        c = make_cat(
            "k1",
            forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
        )
        c.wire_default_nervous_system()
        c.mount("brain", "test_organ", _DummyOrgan())
        c.wiring.connect(THALAMUS, ("brain", "test_organ"))
        c.freeze_nervous_system()
        return c

    @pytest.mark.anyio
    async def test_spawn_kitten_forbidden(self, cat) -> None:
        with pytest.raises(IllegalNeuralPathError, match="spawn_kitten"):
            await cat.signal(
                THALAMUS, ("brain", "test_organ"), "spawn_kitten",
            )

    @pytest.mark.anyio
    async def test_absorb_merge_forbidden(self, cat) -> None:
        with pytest.raises(IllegalNeuralPathError, match="absorb_merge"):
            await cat.signal(
                THALAMUS, ("brain", "test_organ"), "absorb_merge",
            )

    @pytest.mark.anyio
    async def test_regular_method_allowed(self, cat) -> None:
        result = await cat.signal(
            THALAMUS, ("brain", "test_organ"), "regular_method",
        )
        assert result == "ok"


# -- 4. 默认 CatBase 行为不变 ---------------------------------------

class TestDefaultCatBase:
    """默认 CatBase（无参数）行为与 v1.0.0 一致。"""

    def test_default_parent_id_is_none(self) -> None:
        cat = make_cat("cat1")
        assert cat.parent_id is None

    def test_default_no_forbidden_methods(self) -> None:
        """不传 forbidden_methods 时方法调用不受限。"""
        cat = make_cat("cat1")
        cat.wire_default_nervous_system()
        cat.mount("brain", "test", _DummyOrgan())
        cat.wiring.connect(THALAMUS, ("brain", "test"))
        cat.freeze_nervous_system()
        # 不做 async 调用，只验证 wiring 正常
        assert cat.wiring.is_allowed(THALAMUS, ("brain", "test"))

    def test_default_allowed_organs_is_none(self) -> None:
        """不传 allowed_organs 时所有属性均可访问。"""
        cat = make_cat("cat1")
        # 不存在的属性抛 AttributeError，非 IllegalNeuralPathError
        try:
            _ = cat.hippocampus
        except AttributeError:
            pass  # 预期
        assert cat.name == "cat1"
