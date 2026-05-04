"""
v1.1.8 — 统一对外入口 + 搜索边界测试
=====================================

验证:
    1. TestReceiveExternal           — receive_external 地址路由
    2. TestListCatCapabilities       — list_cat_capabilities 能力列表
    3. TestSearchScopeGuard          — search_scope_guard 范围守卫
    4. TestHippocampusLocate         — NoopHippocampus.locate 搜索边界
"""

from __future__ import annotations

import pytest

from meowcat.colony import Colony
from meowcat.defaults.organs import NoopHippocampus
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.testing import make_cat


# -- 辅助工厂 -------------------------------------------------------

def _colony_with_cats(*cat_ids: str) -> Colony:
    """Create a colony with the given cats (no organs mounted)."""
    colony = Colony("test-colony", storage=InMemorySharedStore())
    for cid in cat_ids:
        colony.create_cat(cid)
    return colony


# -- 1. receive_external 统一入口 ----------------------------------

class TestReceiveExternal:
    """receive_external 统一对外入口 — 地址路由。"""

    @pytest.mark.asyncio
    async def test_valid_address_delivers(self) -> None:
        """有效地址路由消息到目标猫。"""
        colony = _colony_with_cats("planner")

        result = await colony.receive_external(
            "test-colony/planner", message="查询表结构"
        )
        assert result["status"] == "delivered"
        assert result["cat_id"] == "planner"
        assert result["cats_count"] == 1

    @pytest.mark.asyncio
    async def test_event_emitted_on_cat(self) -> None:
        """消息以事件形式发送到目标猫。"""
        colony = _colony_with_cats("planner")
        cat = colony.get_cat("planner")

        received: list[dict] = []

        async def _handler(data: dict) -> None:
            received.append(data)

        cat.on("external_message", _handler)

        await colony.receive_external(
            "test-colony/planner", message="hello", priority="high"
        )
        assert len(received) == 1
        assert received[0]["message"] == "hello"
        assert received[0]["priority"] == "high"
        assert received[0]["address"] == "test-colony/planner"

    @pytest.mark.asyncio
    async def test_invalid_address_format(self) -> None:
        """无效地址格式抛出 ValueError。"""
        colony = _colony_with_cats("planner")

        with pytest.raises(ValueError, match="Invalid address"):
            await colony.receive_external("no-slash", message="hi")

        with pytest.raises(ValueError, match="Invalid address"):
            await colony.receive_external("/only_cat", message="hi")

        with pytest.raises(ValueError, match="Invalid address"):
            await colony.receive_external("colony/", message="hi")

    @pytest.mark.asyncio
    async def test_colony_mismatch(self) -> None:
        """地址中的 colony_id 不匹配抛出 ValueError。"""
        colony = _colony_with_cats("planner")

        with pytest.raises(ValueError, match="does not match"):
            await colony.receive_external(
                "other-colony/planner", message="hi"
            )

    @pytest.mark.asyncio
    async def test_cat_not_found(self) -> None:
        """目标猫不存在抛出 KeyError。"""
        colony = _colony_with_cats("planner")

        with pytest.raises(KeyError):
            await colony.receive_external(
                "test-colony/nonexistent", message="hi"
            )

    @pytest.mark.asyncio
    async def test_empty_colony(self) -> None:
        """空猫群中路由抛出 KeyError。"""
        colony = Colony("test-colony", storage=InMemorySharedStore())

        with pytest.raises(KeyError):
            await colony.receive_external(
                "test-colony/anyone", message="hi"
            )


# -- 2. list_cat_capabilities 能力列表 -----------------------------

class TestListCatCapabilities:
    """list_cat_capabilities 列出猫舍所有猫的能力。"""

    def test_empty_colony(self) -> None:
        """空猫群返回空字典。"""
        colony = Colony("test-colony", storage=InMemorySharedStore())
        assert colony.list_cat_capabilities() == {}

    def test_cats_without_organs(self) -> None:
        """猫没有挂载器官时返回空列表。"""
        colony = _colony_with_cats("planner", "executor")
        caps = colony.list_cat_capabilities()

        assert set(caps.keys()) == {"planner", "executor"}
        assert caps["planner"] == []
        assert caps["executor"] == []

    def test_cats_with_organs(self) -> None:
        """猫挂载器官后返回器官坐标。"""
        colony = _colony_with_cats("planner", "executor")
        colony.get_cat("planner").mount("brain", "cerebrum", object())
        colony.get_cat("planner").mount("brain", "amygdala", object())
        colony.get_cat("executor").mount("sense", "ears", object())

        caps = colony.list_cat_capabilities()

        planner = {tuple(o.items()) for o in caps["planner"]}
        assert (("category", "brain"), ("name", "cerebrum")) in planner
        assert (("category", "brain"), ("name", "amygdala")) in planner
        assert caps["executor"] == [{"category": "sense", "name": "ears"}]

    def test_structure_has_category_and_name(self) -> None:
        """返回结构中每个条目包含 category 和 name。"""
        colony = _colony_with_cats("cat-a")
        colony.get_cat("cat-a").mount("brain", "hippocampus", object())

        caps = colony.list_cat_capabilities()
        entry = caps["cat-a"][0]

        assert "category" in entry
        assert "name" in entry
        assert entry["category"] == "brain"
        assert entry["name"] == "hippocampus"


# -- 3. search_scope_guard 搜索边界守卫 ----------------------------

class TestSearchScopeGuard:
    """search_scope_guard 验证搜索范围边界。"""

    def test_valid_scope_self(self) -> None:
        """scope='self' 通过验证。"""
        colony = _colony_with_cats("planner")
        colony.search_scope_guard("planner", "self")  # 不抛异常

    def test_valid_scope_colony(self) -> None:
        """scope='colony' 通过验证。"""
        colony = _colony_with_cats("planner")
        colony.search_scope_guard("planner", "colony")  # 不抛异常

    def test_invalid_scope(self) -> None:
        """无效 scope 值抛出 ValueError。"""
        colony = _colony_with_cats("planner")

        with pytest.raises(ValueError, match="Invalid search scope"):
            colony.search_scope_guard("planner", "global")

        with pytest.raises(ValueError, match="Invalid search scope"):
            colony.search_scope_guard("planner", "")

        with pytest.raises(ValueError, match="Invalid search scope"):
            colony.search_scope_guard("planner", "all")

    def test_cat_not_found(self) -> None:
        """猫不存在抛出 KeyError。"""
        colony = _colony_with_cats("planner")

        with pytest.raises(KeyError, match="not found"):
            colony.search_scope_guard("nonexistent", "self")


# -- 4. NoopHippocampus.locate 搜索边界 ----------------------------

class TestHippocampusLocate:
    """NoopHippocampus.locate 带 scope 的搜索。"""

    def test_scope_self_searches_own(self) -> None:
        """scope='self' 搜索自身海马体。"""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "users 表结构是什么",
                          "ai_reply": "users 表有 id, name, email 列"})

        results = hippo.locate("表结构", scope="self")
        assert len(results) >= 1
        assert any("users" in str(r) for r in results)

    def test_scope_colony_returns_empty(self) -> None:
        """scope='colony' 框架存根返回空（应用层实现）。"""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "users 表", "ai_reply": "id, name"})

        results = hippo.locate("users", scope="colony")
        assert results == []

    def test_invalid_scope_raises(self) -> None:
        """无效 scope 抛出 ValueError。"""
        hippo = NoopHippocampus()

        with pytest.raises(ValueError, match="Invalid search scope"):
            hippo.locate("test", scope="global")

        with pytest.raises(ValueError, match="Invalid search scope"):
            hippo.locate("test", scope="")

    def test_scope_self_no_results(self) -> None:
        """scope='self' 无匹配时返回空列表。"""
        hippo = NoopHippocampus()

        results = hippo.locate("nothing", scope="self")
        assert results == []

    def test_default_scope_is_self(self) -> None:
        """默认 scope='self'。"""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "hello world", "ai_reply": "hi"})

        results_default = hippo.locate("hello")
        results_explicit = hippo.locate("hello", scope="self")
        assert results_default == results_explicit
