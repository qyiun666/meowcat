# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.0.1 — CatBase 分身猫隔离（替代 KittenBase + _KittenParentProxy）
===================================================================

验证:
    1. TestNoParentObjectRef  — 分身猫 parent_id 只是字符串，不持有父猫对象
    2. TestAllowedOrgansIsolation — allowed_organs 实现器官裁剪
    3. TestNoParentProxy      — 无 parent proxy（_KittenParentProxy 已删除）
"""

from __future__ import annotations

from meowcat.assembly import CatBase
from meowcat.errors import IllegalNeuralPathError
from meowcat.testing import make_cat

# -- 1. 无父猫对象引用 ----------------------------------------------

class TestNoParentObjectRef:
    """分身猫通过 parent_id 追踪，不持有父猫 CatBase 对象。"""

    def test_kitten_parent_id_no_object_ref(self) -> None:
        """创建分身猫：parent_id 只是字符串，不会存储父猫对象。"""
        main_cat = make_cat("main")
        kitten = make_cat("kit", parent_id=main_cat.cat_uid)
        assert kitten.parent_id == main_cat.cat_uid
        # parent_id 不是父猫对象
        assert not isinstance(kitten.parent_id, CatBase)

    def test_kitten_parent_id_is_string(self) -> None:
        """parent_id 类型就是 str。"""
        kitten = make_cat("kit", parent_id="main")
        assert isinstance(kitten.parent_id, str)
        assert kitten.parent_id == "main"

    def test_default_cat_parent_id_none(self) -> None:
        """默认 CatBase（非分身猫）parent_id 为 None。"""
        cat = make_cat("main")
        assert cat.parent_id is None

    def test_kitten_does_not_hold_parent_object(self) -> None:
        """分身猫无法通过任何属性访问父猫对象。"""
        main_cat = make_cat("main")
        kitten = make_cat("kit", parent_id=main_cat.cat_uid)
        # 确认没有 parent 对象引用
        assert not hasattr(type(kitten), "parent")
        # parent_id 只是字符串标识
        assert kitten.parent_id == main_cat.cat_uid


# -- 2. allowed_organs 器官裁剪 ------------------------------------

class TestAllowedOrgansIsolation:
    """allowed_organs 实现分身猫器官裁剪，隔离通过"根本没给"。"""

    def test_kitten_allowed_organs_blocks_brain_organs(self) -> None:
        """分身猫禁止访问 hippocampus 等脑区器官。"""
        kitten = make_cat(
            "kit", parent_id="main",
            allowed_organs=frozenset({
                "cerebellum", "cerebrum", "paws", "whiskers", "amygdala",
            }),
        )
        # 禁止的器官
        for name in ("hippocampus", "thalamus", "frontal", "hypothalamus",
                     "cortex", "brainstem", "ears", "eyes", "mouth", "purr", "tail"):
            try:
                getattr(kitten, name)
                pytest.fail(f"{name} 应被 allowed_organs 拦截")
            except IllegalNeuralPathError:
                pass  # 预期

    def test_kitten_allowed_organs_passes_permitted(self) -> None:
        """分身猫允许的器官名不抛 IllegalNeuralPathError。"""
        kitten = make_cat(
            "kit", parent_id="main",
            allowed_organs=frozenset({
                "cerebellum", "cerebrum", "paws", "whiskers", "amygdala",
            }),
        )
        for name in ("cerebellum", "cerebrum", "paws", "whiskers", "amygdala"):
            try:
                _ = getattr(kitten, name)
            except AttributeError:
                pass  # 未挂载，AttributeError 正常
            except IllegalNeuralPathError:
                pytest.fail(f"{name} 在 allowed_organs 中，不应被拦截")

    def test_kitten_can_access_own_properties(self) -> None:
        """分身猫可访问自身属性（cat_uid、parent_id 等）。"""
        kitten = make_cat(
            "kit", parent_id="main",
            allowed_organs=frozenset({"cerebrum"}),
        )
        assert kitten.name == "kit"
        assert kitten.cat_uid is not None  # auto-generated
        assert kitten.parent_id == "main"

    def test_kitten_private_attrs_accessible(self) -> None:
        """_ 前缀属性不受 allowed_organs 限制。"""
        kitten = make_cat(
            "kit", parent_id="main",
            allowed_organs=frozenset({"cerebrum"}),
        )
        assert kitten._host is not None
        assert kitten._events is not None
        assert kitten._nervous is not None


# -- 3. 无 parent proxy --------------------------------------------

class TestNoParentProxy:
    """_KittenParentProxy 已删除，分身猫无 parent 属性。"""

    def test_catbase_has_no_parent_property(self) -> None:
        """CatBase 不存在 parent property（替代 KittenBase.parent）。"""
        cat = make_cat("main")
        assert not hasattr(type(cat), "parent")

    def test_kitten_has_no_parent_proxy(self) -> None:
        """分身猫没有 parent proxy，parent_id 只是字符串。"""
        kitten = make_cat("kit", parent_id="main")
        assert not hasattr(type(kitten), "parent")
        assert kitten.parent_id == "main"


# helpers -----------------------------------------------------------

import pytest  # noqa: E402

