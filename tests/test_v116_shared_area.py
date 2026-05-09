# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""
v1.1.6 — 猫舍共享区测试
========================

验证:
    1. TestColonyOwner         — ColonyOwner 创建和字段 (默认/自定义/extra)
    2. TestColonyRules         — ColonyRules 创建/check/on_check 插件
    3. TestColonyOwnerRules    — Colony 接受 owner/rules 参数和属性
    4. TestNamespaceStorage    — 命名空间存储 (ns_get/set/delete/list)
    5. TestCustomNamespace     — storage_plug 自定义命名空间
    6. TestNamespaceIsolation  — 命名空间隔离验证
"""

from __future__ import annotations

import pytest

from meowcat.colony import Colony, ColonyOwner, ColonyRules
from meowcat.defaults.stores import InMemorySharedStore

# -- 1. ColonyOwner -------------------------------------------------------


class TestColonyOwner:
    """ColonyOwner 基础构造和字段。"""

    def test_defaults(self) -> None:
        o = ColonyOwner()
        assert o.name == ""
        assert o.email == ""
        assert o.language == "en"
        assert o.extra == {}

    def test_custom(self) -> None:
        o = ColonyOwner(name="张三", email="zhang@corp.com", language="zh")
        assert o.name == "张三"
        assert o.email == "zhang@corp.com"
        assert o.language == "zh"

    def test_extra_fields(self) -> None:
        o = ColonyOwner(name="Li Si", extra={
                        "slack_id": "U123", "role": "admin"})
        assert o.name == "Li Si"
        assert o.extra["slack_id"] == "U123"
        assert o.extra["role"] == "admin"

    def test_is_dataclass(self) -> None:
        o1 = ColonyOwner(name="a")
        o2 = ColonyOwner(name="a")
        assert o1 == o2
        assert o1 != ColonyOwner(name="b")


# -- 2. ColonyRules -------------------------------------------------------

class TestColonyRules:
    """ColonyRules 创建、check、on_check 插件。"""

    def test_defaults(self) -> None:
        r = ColonyRules()
        assert r.safety_policy == "normal"
        assert r.approval_required is False
        assert r.rate_limit_per_min == 60
        assert r.extra == {}

    def test_custom(self) -> None:
        r = ColonyRules(safety_policy="strict",
                        approval_required=True, rate_limit_per_min=20)
        assert r.safety_policy == "strict"
        assert r.approval_required is True
        assert r.rate_limit_per_min == 20

    def test_extra_fields(self) -> None:
        r = ColonyRules(extra={"custom_policy": "block_external_domains"})
        assert r.extra["custom_policy"] == "block_external_domains"

    def test_pluggable_inheritance(self) -> None:
        r = ColonyRules()
        assert hasattr(r, "plug")
        assert hasattr(r, "unplug")
        assert hasattr(r, "list_plugs")


# -- 3. Colony owner/rules 参数和属性 -------------------------------------

class TestColonyOwnerRules:
    """Colony 接受 owner/rules 构造参数并通过属性暴露。"""

    def test_default_owner(self) -> None:
        c = Colony("test")
        assert c.owner == ColonyOwner()
        assert c.owner.name == ""

    def test_default_rules(self) -> None:
        c = Colony("test")
        assert c.rules.safety_policy == "normal"

    def test_custom_owner(self) -> None:
        o = ColonyOwner(name="张三", email="zhang@corp.com", language="zh")
        c = Colony("test", owner=o)
        assert c.owner is o
        assert c.owner.name == "张三"

    def test_custom_rules(self) -> None:
        r = ColonyRules(safety_policy="strict", rate_limit_per_min=10)
        c = Colony("test", rules=r)
        assert c.rules is r
        assert c.rules.safety_policy == "strict"

    def test_owner_setter(self) -> None:
        c = Colony("test")
        o = ColonyOwner(name="new owner")
        c.owner = o
        assert c.owner is o

    def test_owner_rules_independent(self) -> None:
        """owner 和 rules 是独立对象，修改不影响别处。"""
        o = ColonyOwner(name="A")
        r = ColonyRules(safety_policy="strict")
        c = Colony("test", owner=o, rules=r)

        o.name = "B"
        assert c.owner.name == "B"  # 同一个引用


# -- 4. 命名空间存储 ------------------------------------------------------

class TestNamespaceStorage:
    """ns_get/set/delete/list_keys 基本操作。"""

    @pytest.fixture
    def colony(self) -> Colony:
        return Colony("test", storage=InMemorySharedStore())

    @pytest.mark.anyio
    async def test_ns_set_get(self, colony: Colony) -> None:
        await colony.ns_set("owner", "name", "张三")
        result = await colony.ns_get("owner", "name")
        assert result == "张三"

    @pytest.mark.anyio
    async def test_ns_set_get_multiple(self, colony: Colony) -> None:
        await colony.ns_set("knowledge", "faq_001", "如何部署?")
        await colony.ns_set("knowledge", "faq_002", "如何回滚?")

        assert await colony.ns_get("knowledge", "faq_001") == "如何部署?"
        assert await colony.ns_get("knowledge", "faq_002") == "如何回滚?"

    @pytest.mark.anyio
    async def test_ns_delete(self, colony: Colony) -> None:
        await colony.ns_set("knowledge", "temp", "value")
        await colony.ns_delete("knowledge", "temp")
        assert await colony.ns_get("knowledge", "temp") is None

    @pytest.mark.anyio
    async def test_ns_list_keys(self, colony: Colony) -> None:
        await colony.ns_set("knowledge", "k1", 1)
        await colony.ns_set("knowledge", "k2", 2)
        await colony.ns_set("growth", "g1", 3)

        keys = await colony.ns_list_keys("knowledge")
        assert set(keys) == {"k1", "k2"}

    @pytest.mark.anyio
    async def test_ns_list_keys_empty(self, colony: Colony) -> None:
        keys = await colony.ns_list_keys("growth")
        assert keys == []

    @pytest.mark.anyio
    async def test_ns_namespace_isolation(self, colony: Colony) -> None:
        """不同命名空间之间不相互污染。"""
        await colony.ns_set("owner", "name", "admin")
        await colony.ns_set("knowledge", "key", 10)

        assert await colony.ns_get("owner", "key") is None
        assert await colony.ns_get("knowledge", "name") is None

    @pytest.mark.anyio
    async def test_ns_all_builtin_namespaces(self, colony: Colony) -> None:
        """所有 3 个内置命名空间都可以正常读写。"""
        namespaces = ["owner", "knowledge", "cats"]
        for ns in namespaces:
            await colony.ns_set(ns, "test_key", f"{ns}_value")
            assert await colony.ns_get(ns, "test_key") == f"{ns}_value"

    @pytest.mark.anyio
    async def test_ns_cats_profile(self, colony: Colony) -> None:
        """cats/{cat_uid}/ 命名空间存储猫公开简介。"""
        await colony.ns_set("cats", "planner/profile", {"role": "planner", "model": "gpt-4o"})
        profile = await colony.ns_get("cats", "planner/profile")
        assert profile["role"] == "planner"

    @pytest.mark.anyio
    async def test_ns_not_affect_cat_storage(self, colony: Colony) -> None:
        """命名空间存储不影响猫级别存储。"""
        await colony.ns_set("knowledge", "key1", "ns_value")
        await colony.storage_set("cat_x", "key1", "cat_value")

        assert await colony.ns_get("knowledge", "key1") == "ns_value"
        assert await colony.storage_get("cat_x", "key1") == "cat_value"


# -- 5. 自定义命名空间 ----------------------------------------------------

class TestCustomNamespace:
    """storage_plug 注册自定义命名空间。"""

    @pytest.fixture
    def colony(self) -> Colony:
        return Colony("test", storage=InMemorySharedStore())

    def test_registered_namespaces_default(self) -> None:
        c = Colony("test")
        assert c.registered_namespaces == frozenset(
            {"owner", "knowledge", "cats"})

    def test_register_custom_namespace(self) -> None:
        c = Colony("test")
        c.storage_plug("namespace", "audit")
        assert "audit" in c.registered_namespaces
        assert c.registered_namespaces == frozenset(
            {"owner", "knowledge", "cats", "audit"})

    def test_register_multiple_custom(self) -> None:
        c = Colony("test")
        c.storage_plug("namespace", "audit")
        c.storage_plug("namespace", "metrics")
        assert "audit" in c.registered_namespaces
        assert "metrics" in c.registered_namespaces

    def test_ns_registered_namespaces_is_frozen(self) -> None:
        c = Colony("test")
        ns = c.registered_namespaces
        assert isinstance(ns, frozenset)

    @pytest.mark.anyio
    async def test_custom_namespace_works(self, colony: Colony) -> None:
        colony.storage_plug("namespace", "audit")
        await colony.ns_set("audit", "event_001", "user_login")
        assert await colony.ns_get("audit", "event_001") == "user_login"

    @pytest.mark.anyio
    async def test_unregistered_namespace_still_works(self, colony: Colony) -> None:
        """未注册的命名空间仍然可以写入（注册只是跟踪，不是权限控制）。"""
        await colony.ns_set("unreg", "k", "v")
        assert await colony.ns_get("unreg", "k") == "v"


# -- 6. 命名空间隔离验证 --------------------------------------------------

class TestNamespaceIsolation:
    """全面验证命名空间隔离和猫级存储互不干扰。"""

    @pytest.fixture
    def colony(self) -> Colony:
        return Colony("test", storage=InMemorySharedStore())

    @pytest.mark.anyio
    async def test_full_isolation(self, colony: Colony) -> None:
        """三个维度的键完全不冲突。"""
        # 猫级存储
        await colony.storage_set("cat_a", "mem", "cat_a_memory")
        # 命名空间存储
        await colony.ns_set("knowledge", "mem", "colony_knowledge")

        # 各自独立
        assert await colony.storage_get("cat_a", "mem") == "cat_a_memory"
        assert await colony.ns_get("knowledge", "mem") == "colony_knowledge"

    @pytest.mark.anyio
    async def test_list_only_current_namespace(self, colony: Colony) -> None:
        await colony.ns_set("owner", "k1", 1)
        await colony.ns_set("knowledge", "k2", 2)
        await colony.ns_set("cats", "k3", 3)

        assert await colony.ns_list_keys("owner") == ["k1"]
        assert await colony.ns_list_keys("knowledge") == ["k2"]
        assert await colony.ns_list_keys("cats") == ["k3"]
