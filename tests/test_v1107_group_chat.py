"""
v1.1.7 — 群聊通信测试
=====================

验证:
    1. TestBroadcastRequest          — broadcast_request 请求所有猫并收集结果
    2. TestBroadcastRequestCustom    — 自定义 to_category/to_name
    3. TestBroadcastRequestErrors    — 错误处理 (ignore_errors=True/False)
    4. TestBroadcastRequestEmpty     — 空猫群
    5. TestGroupChatIntegration      — 群聊+私聊打通 (broadcast_request → signal_between)
"""

from __future__ import annotations

import pytest

from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.colony import Colony
from meowcat.defaults.stores import InMemorySharedStore


# -- 辅助器官 -------------------------------------------------------

class _MockAmygdala:
    """模拟杏仁核 — 安全评估。"""

    def __init__(self, safe: bool = True) -> None:
        self.safe = safe

    def assess_safety(self, **kw: object) -> dict:
        return {"safe": self.safe, "input": kw}

    def diagnose(self) -> dict:
        return {"safe": self.safe}


class _MockCerebrum:
    """模拟大脑 — 推理。"""

    def __init__(self, prefix: str = "echo") -> None:
        self.prefix = prefix

    def generate(self, prompt: str) -> str:
        return f"{self.prefix}: {prompt}"

    async def generate_async(self, prompt: str) -> str:
        return f"async_{self.prefix}: {prompt}"

    def diagnose(self) -> dict:
        return {"prefix": self.prefix}


class _ErrorOrgan:
    """故意抛异常的器官。"""

    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc or RuntimeError("boom")

    def boom(self, **kw: object) -> None:
        raise self._exc

    def assess_safety(self, **kw: object) -> dict:
        raise self._exc

    def diagnose(self) -> dict:
        return {"status": "broken"}


# -- 辅助工厂 -------------------------------------------------------

def _make_cat_with_brain(cat_id: str, safe: bool = True, prefix: str = "echo") -> CatBase:
    """创建带 amygdale + cerebrum 的测试猫。"""
    cat = make_cat(cat_id)
    cat.mount("brain", "amygdala", _MockAmygdala(safe=safe))
    cat.mount("brain", "cerebrum", _MockCerebrum(prefix=prefix))
    return cat


# -- 1. broadcast_request 基础 -----------------------------------

class TestBroadcastRequest:
    """broadcast_request 向所有猫广播请求并收集结果。"""

    @pytest.mark.asyncio
    async def test_broadcast_single_cat(self) -> None:
        """单猫 broadcast_request 返回单结果。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("planner")
        colony.get_cat("planner").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))

        results = await colony.broadcast_request(
            "assess_safety", sql="DROP TABLE users")
        assert results == {"planner": {"safe": True,
                                       "input": {"sql": "DROP TABLE users"}}}

    @pytest.mark.asyncio
    async def test_broadcast_multiple_cats(self) -> None:
        """多猫 broadcast_request 返回所有猫的结果。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("planner")
        colony.create_cat("executor")
        colony.create_cat("reviewer")
        colony.get_cat("planner").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))
        colony.get_cat("executor").mount(
            "brain", "amygdala", _MockAmygdala(safe=False))
        colony.get_cat("reviewer").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))

        results = await colony.broadcast_request(
            "assess_safety", sql="DROP TABLE")
        assert set(results.keys()) == {"planner", "executor", "reviewer"}
        assert results["planner"]["safe"] is True
        assert results["executor"]["safe"] is False
        assert results["reviewer"]["safe"] is True

    @pytest.mark.asyncio
    async def test_broadcast_returns_cat_id_keys(self) -> None:
        """确保键是 cat_id 字符串。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("alpha")
        colony.get_cat("alpha").mount(
            "brain", "amygdala", _MockAmygdala())

        results = await colony.broadcast_request("assess_safety")
        assert "alpha" in results
        assert isinstance(list(results.keys())[0], str)


# -- 2. 自定义 organ 目标 -----------------------------------------

class TestBroadcastRequestCustom:
    """broadcast_request 支持自定义 to_category/to_name。"""

    @pytest.mark.asyncio
    async def test_custom_organ_target(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("cat-a")
        colony.get_cat("cat-a").mount(
            "brain", "cerebrum", _MockCerebrum(prefix="cat-a"))
        colony.create_cat("cat-b")
        colony.get_cat("cat-b").mount(
            "brain", "cerebrum", _MockCerebrum(prefix="cat-b"))

        results = await colony.broadcast_request(
            "generate",
            to_category="brain",
            to_name="cerebrum",
            prompt="hello",
        )
        assert results == {
            "cat-a": "cat-a: hello",
            "cat-b": "cat-b: hello",
        }

    @pytest.mark.asyncio
    async def test_async_method_support(self) -> None:
        """broadcast_request 支持异步方法。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("cat-a")
        colony.get_cat("cat-a").mount(
            "brain", "cerebrum", _MockCerebrum(prefix="cat-a"))

        results = await colony.broadcast_request(
            "generate_async",
            to_category="brain",
            to_name="cerebrum",
            prompt="hi",
        )
        assert results == {"cat-a": "async_cat-a: hi"}


# -- 3. 错误处理 ---------------------------------------------------

class TestBroadcastRequestErrors:
    """broadcast_request 错误处理。"""

    @pytest.mark.asyncio
    async def test_ignore_errors_default(self) -> None:
        """默认 ignore_errors=True，猫异常变成错误字典。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("planner")
        colony.get_cat("planner").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))
        colony.create_cat("broken")
        colony.get_cat("broken").mount(
            "brain", "amygdala", _ErrorOrgan(RuntimeError("oops")))

        # assess_safety: planner 正常返回，broken 抛异常
        results = await colony.broadcast_request("assess_safety")
        assert results["planner"] == {"safe": True, "input": {}}
        assert "error" in results["broken"]
        assert "oops" in results["broken"]["error"]

    @pytest.mark.asyncio
    async def test_ignore_errors_false(self) -> None:
        """ignore_errors=False 时第一只猫异常即抛出。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("broken")
        colony.get_cat("broken").mount(
            "brain", "amygdala", _ErrorOrgan(RuntimeError("boom")))

        with pytest.raises(RuntimeError, match="boom"):
            await colony.broadcast_request("boom", ignore_errors=False)

    @pytest.mark.asyncio
    async def test_organ_not_mounted(self) -> None:
        """器官未挂载时返回错误。"""
        colony = Colony("test", storage=InMemorySharedStore())
        # cat 没有挂载 amygdale
        colony.create_cat("bare")

        results = await colony.broadcast_request("assess_safety")
        assert "error" in results["bare"]


# -- 4. 空猫群 -----------------------------------------------------

class TestBroadcastRequestEmpty:
    """broadcast_request 空猫群行为。"""

    @pytest.mark.asyncio
    async def test_empty_colony(self) -> None:
        colony = Colony("test", storage=InMemorySharedStore())
        results = await colony.broadcast_request("assess_safety")
        assert results == {}


# -- 5. 群聊+私聊打通 -----------------------------------------------

class TestGroupChatIntegration:
    """broadcast_request (群聊) + signal_between (私聊) 打通。"""

    @pytest.mark.asyncio
    async def test_broadcast_then_private(self) -> None:
        """群聊获取全局视图 → 私聊对特定猫深入追问。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("master")
        colony.create_cat("worker-1")
        colony.create_cat("worker-2")

        colony.get_cat("master").mount(
            "brain", "cerebrum", _MockCerebrum(prefix="master"))
        colony.get_cat("worker-1").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))
        colony.get_cat("worker-2").mount(
            "brain", "amygdala", _MockAmygdala(safe=False))

        # Step 1: 群聊 — 所有猫评估安全性
        results = await colony.broadcast_request(
            "assess_safety", action="delete_db")
        assert results["worker-1"]["safe"] is True
        assert results["worker-2"]["safe"] is False

        # Step 2: 私聊 — 对不安全的猫深入追问
        worker2_result = await colony.signal_between(
            "master", "worker-2", "brain", "amygdala",
            "assess_safety", action="explain_why",
        )
        assert worker2_result["safe"] is False

    @pytest.mark.asyncio
    async def test_private_then_broadcast(self) -> None:
        """私聊确认某猫状态 → 群聊广播最新结论。"""
        colony = Colony("test", storage=InMemorySharedStore())
        colony.create_cat("coordinator")
        colony.create_cat("alice")
        colony.create_cat("bob")

        colony.get_cat("coordinator").mount(
            "brain", "cerebrum", _MockCerebrum(prefix="coord"))
        colony.get_cat("alice").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))
        colony.get_cat("bob").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))

        # Step 1: 私聊 — 先问 alice
        alice_result = await colony.signal_between(
            "coordinator", "alice", "brain", "amygdala",
            "assess_safety", proposal="new_policy",
        )
        assert alice_result["safe"] is True

        # Step 2: 群聊 — 广播给所有人
        results = await colony.broadcast_request(
            "assess_safety", proposal="new_policy")
        assert results["alice"]["safe"] is True
        assert results["bob"]["safe"] is True

    @pytest.mark.asyncio
    async def test_broadcast_bypasses_cross_wiring(self) -> None:
        """broadcast_request 绕过 cross_wiring (colony 级操作)。"""
        colony = Colony(
            "test", storage=InMemorySharedStore(),
            cross_wiring_forbidden={("a", "b")},  # 阻止 a→b 私聊
        )
        colony.create_cat("a")
        colony.create_cat("b")
        colony.get_cat("a").mount(
            "brain", "amygdala", _MockAmygdala(safe=True))
        colony.get_cat("b").mount(
            "brain", "amygdala", _MockAmygdala(safe=False))

        # broadcast_request 不应受 cross_wiring 影响
        results = await colony.broadcast_request("assess_safety")
        assert results["a"]["safe"] is True
        assert results["b"]["safe"] is False
