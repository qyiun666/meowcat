"""
v1.0.2 — Colony 猫群容器测试
==============================

验证:
    1. TestCreateCat           — create_cat 自动注册
    2. TestRegisterUnregister  — register/unregister/list_cats/get_cat
    3. TestDeliverResult       — deliver_result 回传父猫
    4. TestBroadcast           — broadcast 所有猫响应
    5. TestSignalBetween       — signal_between 跨猫通信
    6. TestCrossWiring         — wiring 跨猫隔离
    7. TestSharedStorage       — SharedStorage 命名空间隔离
    8. TestCatCount            — cat_count 属性
"""

from __future__ import annotations

import asyncio

import pytest

from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.errors import IllegalNeuralPathError


# -- 辅助 ---------------------------------------------------------

class _MockHippocampus:
    """模拟海马体，实现 locate / remember 方法。"""

    def __init__(self) -> None:
        self.memories: list[str] = []

    def locate(self, query: str) -> dict:
        return {"results": self.memories, "query": query}

    def remember(self, content: str) -> dict:
        self.memories.append(content)
        return {"stored": content}

    def diagnose(self) -> dict:
        return {"memories": len(self.memories)}


class _MockCerebrum:
    """模拟大脑。"""

    def generate(self, prompt: str) -> str:
        return f"echo: {prompt}"


class _Helper:
    """测试辅助: 创建一个带海马体的猫。"""

    @staticmethod
    def make_cat(cat_uid: str) -> CatBase:
        cat = make_cat(cat_uid)
        cat.mount("brain", "hippocampus", _MockHippocampus())
        cat.mount("brain", "cerebrum", _MockCerebrum())
        return cat


# -- 1. create_cat 自动注册 ----------------------------------------

class TestCreateCat:
    """create_cat 创建的猫自动注册到 colony。"""

    def test_create_cat_registers(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat = colony.create_cat(name="cat-1")
        assert cat.name == "cat-1"
        assert colony.list_cats() == [cat.cat_uid]
        assert colony.get_cat(cat.cat_uid) is cat

    def test_create_cat_with_parent_id(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat = colony.create_cat(name="kitten", parent_id="main-cat")
        assert cat.parent_id == "main-cat"
        # parent_id 只是字符串，不是对象引用
        assert isinstance(cat.parent_id, str)

    def test_create_cat_with_allowed_organs(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat = colony.create_cat(
            name="cat-1",
            allowed_organs=frozenset({"cerebrum", "paws"}),
        )
        # 允许的属性正常
        assert cat.name == "cat-1"
        # 禁止的属性抛异常
        with pytest.raises(IllegalNeuralPathError, match="hippocampus"):
            _ = cat.hippocampus

    def test_create_cat_multiple(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat_a = colony.create_cat(name="a")
        cat_b = colony.create_cat(name="b")
        assert sorted(colony.list_cats()) == sorted(
            [cat_a.cat_uid, cat_b.cat_uid])


# -- 2. register / unregister --------------------------------------

class TestRegisterUnregister:
    """手动注册/移除猫。"""

    def test_register_unregister(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat = _Helper.make_cat("cat-1")
        colony.register(cat)
        assert colony.list_cats() == [cat.cat_uid]

        colony.unregister(cat.cat_uid)
        assert colony.list_cats() == []

    def test_unregister_nonexistent(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        with pytest.raises(KeyError):
            colony.unregister("nonexistent")

    def test_get_cat_nonexistent(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        with pytest.raises(KeyError):
            colony.get_cat("nonexistent")

    def test_list_cats_empty(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        assert colony.list_cats() == []

    def test_register_overwrite(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat1 = colony.create_cat(name="cat-1")
        cat2 = colony.create_cat(name="cat-1")  # 同名不同 uid
        assert colony.get_cat(cat1.cat_uid) is cat1
        # 注册同名但 uid 不同的猫，不会覆盖
        assert len(colony._cats) == 2
        assert colony.get_cat(cat2.cat_uid) is cat2


# -- 3. deliver_result 回传 ----------------------------------------

class TestDeliverResult:
    """deliver_result 分身旁回传结果给父猫。"""

    @pytest.mark.asyncio
    async def test_deliver_result(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)
        cat = colony.create_cat(name="main-cat")
        kitten = colony.create_cat(name="kitten", parent_id=cat.cat_uid)

        await colony.deliver_result(cat.cat_uid, kitten.cat_uid, {"done": True})

        val = await colony.storage_get(cat.cat_uid, f"kitten:{kitten.cat_uid}/result")
        assert val == {"done": True}

    @pytest.mark.asyncio
    async def test_deliver_result_multiple_kittens(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)
        cat = colony.create_cat(name="main-cat")

        await colony.deliver_result(cat.cat_uid, "k1", {"task": "A"})
        await colony.deliver_result(cat.cat_uid, "k2", {"task": "B"})

        v1 = await colony.storage_get(cat.cat_uid, "kitten:k1/result")
        v2 = await colony.storage_get(cat.cat_uid, "kitten:k2/result")
        assert v1 == {"task": "A"}
        assert v2 == {"task": "B"}


# -- 4. broadcast --------------------------------------------------

class TestBroadcast:
    """broadcast 向所有猫广播事件。"""

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat_a = colony.create_cat(name="a")
        cat_b = colony.create_cat(name="b")

        received: list[str] = []

        async def handler(payload: dict) -> None:
            received.append(payload["msg"])

        cat_a.on("hello", handler)
        cat_b.on("hello", handler)

        await colony.broadcast("hello", msg="world")
        assert received == ["world", "world"]


# -- 5. signal_between 跨猫通信 ------------------------------------

class TestSignalBetween:
    """signal_between 猫间通信。"""

    @pytest.mark.asyncio
    async def test_signal_between(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat_a = _Helper.make_cat("a")
        cat_b = _Helper.make_cat("b")
        colony.register(cat_a)
        colony.register(cat_b)

        # cat_a → cat_b.hippocampus.locate()
        result = await colony.signal_between(
            cat_a.cat_uid, cat_b.cat_uid, "brain", "hippocampus", "locate",
            query="hello",
        )
        assert result == {"results": [], "query": "hello"}

    @pytest.mark.asyncio
    async def test_signal_between_cat_not_found(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat = colony.create_cat(name="a")

        with pytest.raises(KeyError):
            await colony.signal_between(
                cat.cat_uid, "nonexistent", "brain", "hippocampus", "locate",
            )


# -- 6. 跨猫 wiring 隔离 -------------------------------------------

class TestCrossWiring:
    """跨猫 wiring 白名单/黑名单校验。"""

    def test_no_cross_wiring_allows_all(self) -> None:
        """未设置 cross_wiring → 全部放行。"""
        colony = Colony("test", storage=InMemorySharedStore())
        # 不抛异常
        colony._assert_cross_allowed("a", "b")

    def test_cross_forbidden_blocks(self) -> None:
        colony = Colony(
            "test", storage=InMemorySharedStore(),
            cross_wiring_forbidden={("a", "b")},
        )
        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            colony._assert_cross_allowed("a", "b")

    def test_cross_allowed_only_blocks_unknown(self) -> None:
        colony = Colony(
            "test", storage=InMemorySharedStore(),
            cross_wiring_allowed={("a", "b"), ("b", "c")},
        )
        # 白名单中有 → 通过
        colony._assert_cross_allowed("a", "b")
        colony._assert_cross_allowed("b", "c")
        # 不在白名单 → 拒绝
        with pytest.raises(IllegalNeuralPathError, match="not allowed"):
            colony._assert_cross_allowed("a", "c")

    def test_allow_cross_forbid_cross_methods(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        colony.allow_cross("a", "b")
        colony.forbid_cross("c", "d")

        # 白名单边通过
        colony._assert_cross_allowed("a", "b")
        # 未设置白名单的边... 因为 _has_cross_wiring=True 且有白名单，
        # 不在白名单中的应被拒绝
        with pytest.raises(IllegalNeuralPathError):
            colony._assert_cross_allowed("a", "c")
        # 黑名单边拒绝
        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            colony._assert_cross_allowed("c", "d")

    @pytest.mark.asyncio
    async def test_signal_between_rejected_by_cross_wiring(self) -> None:
        cat_a = _Helper.make_cat("a")
        cat_b = _Helper.make_cat("b")
        colony = Colony(
            "test", storage=InMemorySharedStore(),
            cross_wiring_forbidden={(cat_a.cat_uid, cat_b.cat_uid)},
        )
        colony.register(cat_a)
        colony.register(cat_b)

        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            await colony.signal_between(
                cat_a.cat_uid, cat_b.cat_uid, "brain", "hippocampus", "locate",
            )


# -- 7. SharedStorage 命名空间隔离 ----------------------------------

class TestSharedStorage:
    """共享存储的命名空间隔离。"""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)

        await colony.storage_set("cat-a", "memories/hello", "world")
        await colony.storage_set("cat-b", "memories/hello", "bonjour")

        # 各自独立
        assert await colony.storage_get("cat-a", "memories/hello") == "world"
        assert await colony.storage_get("cat-b", "memories/hello") == "bonjour"

    @pytest.mark.asyncio
    async def test_storage_delete(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)

        await colony.storage_set("cat-a", "temp", "data")
        await colony.storage_delete("cat-a", "temp")
        assert await colony.storage_get("cat-a", "temp") is None

    @pytest.mark.asyncio
    async def test_storage_list_keys(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)

        await colony.storage_set("cat-a", "key1", "v1")
        await colony.storage_set("cat-a", "key2", "v2")
        await colony.storage_set("cat-b", "key3", "v3")

        keys_a = await colony.storage_list_keys("cat-a")
        assert sorted(keys_a) == ["key1", "key2"]

        keys_b = await colony.storage_list_keys("cat-b")
        assert keys_b == ["key3"]

    @pytest.mark.asyncio
    async def test_storage_watch(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)

        # 启动 watch
        watch_iter = colony.storage_watch("cat-a", "events/")

        # 设定计时器在事件循环中写入
        async def _write() -> None:
            await asyncio.sleep(0.01)
            await colony.storage_set("cat-a", "events/msg1", "hello")

        task = asyncio.create_task(_write())

        # 读取 watch 结果
        items: list = []
        async for item in watch_iter:  # type: ignore[attr-defined]
            items.append(item)
            break  # 只取第一条

        await task
        assert len(items) == 1
        key, val = items[0]
        assert key.endswith("events/msg1")
        assert val == "hello"


# -- 8. 其他 -------------------------------------------------------

class TestCatCount:
    """cat_count 属性。"""

    def test_cat_count(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        assert colony.cat_count == 0

        colony.create_cat(name="a")
        assert colony.cat_count == 1

        colony.create_cat(name="b")
        assert colony.cat_count == 2


class TestHealthCheckAll:
    """health_check_all 全猫体检。"""

    @pytest.mark.asyncio
    async def test_health_check_all(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        cat_a = _Helper.make_cat("a")
        cat_b = _Helper.make_cat("b")
        colony.register(cat_a)
        colony.register(cat_b)

        results = await colony.health_check_all()
        assert set(results.keys()) == {cat_a.cat_uid, cat_b.cat_uid}
        # 每只猫的 hippocampus 都在
        assert "brain:hippocampus" in results[cat_a.cat_uid]
        assert "brain:hippocampus" in results[cat_b.cat_uid]
