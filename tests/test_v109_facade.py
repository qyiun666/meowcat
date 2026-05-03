"""
v1.0.9 — CLI 门面方法 + Colony 别名 + wiring 新边集成测试
==========================================================

验证:
    1. TestSearchMemory        — CatBase.search_memory 门面方法
    2. TestMemoryStats          — CatBase.memory_stats 门面方法
    3. TestRunMaintenance       — CatBase.run_maintenance 门面方法
    4. TestColonyAliases        — Colony.adopt / Colony.release 别名
    5. TestNewWiringEdges       — v1.0.8 新增 wiring 边集成测试
"""

from __future__ import annotations

import pytest

from meowcat.anatomy import (
    AMYGDALA, ANOMALY_GROWTH, BRAINSTEM, CORRECTION_GROWTH,
    EARS, EYES, HIPPOCAMPUS, THALAMUS, WHISKERS,
)
from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.colony import Colony
from meowcat.defaults.organs import (
    NoopAmygdala, NoopBrainstem, NoopEars, NoopEyes,
    NoopHippocampus, NoopHypothalamus, NoopThalamus,
    NoopWhiskers,
)
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.errors import IllegalNeuralPathError
from meowcat.loops import DAILY_MAINTENANCE_SEQ


# -- 辅助 ---------------------------------------------------------

class _MockGrowth:
    """模拟生长器官 — 实现 record + diagnose 用于 wiring 边测试。"""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def record(self, **kwargs: object) -> dict:
        self.records.append(dict(kwargs))
        return {"recorded": True}

    def diagnose(self) -> dict:
        return {"records": len(self.records)}


def _make_wired_cat(cat_id: str = "wired-cat") -> CatBase:
    """创建装配了关键 Noop 器官的猫。"""
    cat = make_cat(cat_id)
    cat.mount("brain", "thalamus", NoopThalamus())
    cat.mount("brain", "hippocampus", NoopHippocampus())
    cat.mount("brain", "amygdala", NoopAmygdala())
    cat.mount("brain", "hypothalamus", NoopHypothalamus())
    cat.mount("brain", "brainstem", NoopBrainstem())
    cat.mount("sense", "ears", NoopEars())
    cat.mount("sense", "eyes", NoopEyes())
    cat.mount("sense", "whiskers", NoopWhiskers())
    cat.wire_default_nervous_system()
    return cat


class _MaintenanceMockHippocampus:
    """维护测试用海马体 — 方法接受 **kwargs（兼容链的 kwargs 传递）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def decay(self, **kwargs: object) -> dict:
        self.calls.append("decay")
        return {"decayed": 1}

    def cleanup_orphan_connections(self, **kwargs: object) -> dict:
        self.calls.append("cleanup")
        return {"orphans_cleaned": 0}

    def diagnose(self) -> dict:
        return {"calls": len(self.calls)}

    def stats(self, **kwargs: object) -> dict:
        return {"entities": 0, "episodes": 0}


def _make_maintenance_cat(cat_id: str = "maint-cat") -> CatBase:
    """创建维护专用猫 — 挂载维护链需要的 hypothalamus + brainstem + hippocampus。"""
    cat = make_cat(cat_id)
    cat.mount("brain", "hippocampus", _MaintenanceMockHippocampus())
    cat.mount("brain", "hypothalamus", NoopHypothalamus())
    cat.mount("brain", "brainstem", NoopBrainstem())
    cat.wire_default_nervous_system()
    return cat


# -- 1. search_memory 门面 -----------------------------------------

class TestSearchMemory:
    """CatBase.search_memory() — 搜索记忆门面。

    执行 ``memory_search`` Chain（内含 "locate" Path，丘脑自环），
    调用 Thalamus.locate(msg, session_id)。
    """

    @pytest.mark.asyncio
    async def test_search_memory_empty(self) -> None:
        """空记忆搜索返回 dict。"""
        cat = _make_wired_cat()
        result = await cat.search_memory("hello")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_search_memory_with_limit(self) -> None:
        """limit 参数传递。"""
        cat = _make_wired_cat()
        result = await cat.search_memory("test", limit=10)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_search_memory_returns_dict(self) -> None:
        """返回值是 dict。"""
        cat = _make_wired_cat()
        result = await cat.search_memory("anything")
        assert isinstance(result, dict)


# -- 2. memory_stats 门面 ------------------------------------------

class TestMemoryStats:
    """CatBase.memory_stats() — 记忆统计门面。

    通过 signal(BRAINSTEM, HIPPOCAMPUS, "stats") 调用海马体统计。
    """

    @pytest.mark.asyncio
    async def test_memory_stats_empty(self) -> None:
        """空记忆统计。"""
        cat = _make_wired_cat()
        result = await cat.memory_stats()
        assert isinstance(result, dict)
        assert result["entities"] == 0
        assert result["episodes"] == 0

    @pytest.mark.asyncio
    async def test_memory_stats_after_episode(self) -> None:
        """记忆后统计反映变化。"""
        cat = _make_wired_cat()
        hippo = cat.organ("brain", "hippocampus")
        hippo.add_episode({"user_msg": "hello", "ai_reply": "hi"})

        result = await cat.memory_stats()
        assert result["episodes"] == 1

    @pytest.mark.asyncio
    async def test_memory_stats_returns_dict(self) -> None:
        """返回值是 dict。"""
        cat = _make_wired_cat()
        result = await cat.memory_stats()
        assert isinstance(result, dict)


# -- 3. run_maintenance 门面 ---------------------------------------

class TestRunMaintenance:
    """CatBase.run_maintenance() — 维护门面。

    执行 ``daily_maintenance`` 元闭环。
    维护链会将前一步结果作为 kwargs 传给下一步（如 decay→cleanup），
    因此 mock 器官方法需接受 **kwargs。
    """

    @pytest.mark.asyncio
    async def test_run_maintenance_no_country(self) -> None:
        """不带 country_code 运行维护。"""
        cat = _make_maintenance_cat()
        cat.loopseq_registry.register(DAILY_MAINTENANCE_SEQ)
        result = await cat.run_maintenance()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_maintenance_with_country(self) -> None:
        """带 country_code 运行维护（参数被 facade 忽略，不影响执行）。"""
        cat = _make_maintenance_cat()
        cat.loopseq_registry.register(DAILY_MAINTENANCE_SEQ)
        result = await cat.run_maintenance(country_code="CN")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_maintenance_missing_seq(self) -> None:
        """未注册 DAILY_MAINTENANCE_SEQ 时抛 KeyError。"""
        cat = _make_maintenance_cat()
        with pytest.raises(KeyError, match="not found"):
            await cat.run_maintenance()


# -- 4. Colony 别名 -------------------------------------------------

class TestColonyAliases:
    """Colony.adopt() / Colony.release() 别名方法。"""

    def test_adopt_registers_cat(self) -> None:
        """adopt(cat) 等价于 register(cat)。"""
        colony = Colony("test", storage=InMemorySharedStore())
        cat = make_cat("cat-1")
        colony.adopt(cat)
        assert colony.list_cats() == ["cat-1"]
        assert colony.get_cat("cat-1") is cat

    def test_release_removes_cat(self) -> None:
        """release(cat_id) 等价于 unregister(cat_id)。"""
        colony = Colony("test", storage=InMemorySharedStore())
        cat = make_cat("cat-1")
        colony.register(cat)
        assert colony.list_cats() == ["cat-1"]

        colony.release("cat-1")
        assert colony.list_cats() == []

    def test_release_nonexistent_raises(self) -> None:
        """release 不存在的猫抛 KeyError。"""
        colony = Colony("test", storage=InMemorySharedStore())
        with pytest.raises(KeyError):
            colony.release("nonexistent")

    def test_adopt_multiple_cats(self) -> None:
        """收养多只猫。"""
        colony = Colony("test", storage=InMemorySharedStore())
        cat_a = make_cat("a")
        cat_b = make_cat("b")
        colony.adopt(cat_a)
        colony.adopt(cat_b)
        assert sorted(colony.list_cats()) == ["a", "b"]

    def test_adopt_and_release_workflow(self) -> None:
        """收养→释放完整流程。"""
        colony = Colony("test", storage=InMemorySharedStore())
        cat = make_cat("whiskers")
        colony.adopt(cat)
        assert colony.cat_count == 1

        colony.release("whiskers")
        assert colony.cat_count == 0

    def test_adopt_sets_colony_storage(self) -> None:
        """adopt 注入共享存储引用。"""
        store = InMemorySharedStore()
        colony = Colony("test", storage=store)
        cat = make_cat("cat-1")
        colony.adopt(cat)

        assert hasattr(cat, "_colony_storage")
        assert cat._colony_storage is store  # type: ignore[attr-defined]


# -- 5. v1.0.8 wiring 新边集成测试 ---------------------------------

class TestNewWiringEdges:
    """验证 v1.0.8 新增的 6 条允许边 + 2 条禁止边。"""

    def _make_full_cat(self) -> CatBase:
        """创建挂载了生长器官的猫。"""
        cat = _make_wired_cat("full-cat")
        cat.mount("growth", "anomaly_growth", _MockGrowth())
        cat.mount("growth", "correction_growth", _MockGrowth())
        # 重新 wiring 以包含 growth 的边
        cat.wire_default_nervous_system()
        return cat

    # -- 新增允许边 --------------------------------------------------

    @pytest.mark.asyncio
    async def test_ears_to_amygdala_allowed(self) -> None:
        """EARS → AMYGDALA 应激反射边允许。"""
        cat = _make_wired_cat()
        result = await cat.signal(EARS, AMYGDALA, "assess_safety",
                                  user_input="hello")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_eyes_to_amygdala_allowed(self) -> None:
        """EYES → AMYGDALA 应激反射边允许。"""
        cat = _make_wired_cat()
        result = await cat.signal(EYES, AMYGDALA, "assess_safety",
                                  user_input="test")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_whiskers_to_amygdala_allowed(self) -> None:
        """WHISKERS → AMYGDALA 注入检测边允许。"""
        cat = _make_wired_cat()
        result = await cat.signal(WHISKERS, AMYGDALA, "assess_safety",
                                  user_input="test injection")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_amygdala_to_anomaly_allowed(self) -> None:
        """AMYGDALA → ANOMALY_GROWTH 安全事件记录边允许。"""
        cat = self._make_full_cat()
        result = await cat.signal(AMYGDALA, ANOMALY_GROWTH, "record",
                                  reason="test", snippet="snippet")
        assert isinstance(result, dict)
        assert result["recorded"] is True

    @pytest.mark.asyncio
    async def test_amygdala_to_correction_allowed(self) -> None:
        """AMYGDALA → CORRECTION_GROWTH 纠正记录边允许。"""
        cat = self._make_full_cat()
        result = await cat.signal(AMYGDALA, CORRECTION_GROWTH, "record",
                                  wrong="bad", correct="good")
        assert isinstance(result, dict)
        assert result["recorded"] is True

    @pytest.mark.asyncio
    async def test_whiskers_to_anomaly_allowed(self) -> None:
        """WHISKERS → ANOMALY_GROWTH 异常检测记录边允许。"""
        cat = self._make_full_cat()
        result = await cat.signal(WHISKERS, ANOMALY_GROWTH, "record",
                                  reason="drift", snippet="test")
        assert isinstance(result, dict)
        assert result["recorded"] is True

    # -- 新增禁止边 --------------------------------------------------

    @pytest.mark.asyncio
    async def test_cerebrum_to_anomaly_forbidden(self) -> None:
        """CEREBRUM → ANOMALY_GROWTH 禁止边生效。"""
        from meowcat.anatomy import CEREBRUM

        cat = self._make_full_cat()
        # mount cerebrum（用一个简单的 mock）

        class _MockCerebrum:
            def generate(self, prompt: str) -> str:
                return prompt

            def diagnose(self) -> dict:
                return {}
        cat.mount("brain", "cerebrum", _MockCerebrum())
        cat.wire_default_nervous_system()

        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            await cat.signal(CEREBRUM, ANOMALY_GROWTH, "record",
                             reason="test", snippet="test")

    @pytest.mark.asyncio
    async def test_cerebrum_to_correction_forbidden(self) -> None:
        """CEREBRUM → CORRECTION_GROWTH 禁止边生效。"""
        from meowcat.anatomy import CEREBRUM

        cat = self._make_full_cat()

        class _MockCerebrum:
            def generate(self, prompt: str) -> str:
                return prompt

            def diagnose(self) -> dict:
                return {}
        cat.mount("brain", "cerebrum", _MockCerebrum())
        cat.wire_default_nervous_system()

        with pytest.raises(IllegalNeuralPathError, match="forbidden"):
            await cat.signal(CEREBRUM, CORRECTION_GROWTH, "record",
                             wrong="bad", correct="good")

    # -- 已有边不受影响 ----------------------------------------------

    @pytest.mark.asyncio
    async def test_ears_to_thalamus_hearing_edge(self) -> None:
        """EARS → THALAMUS wiring edge exists (hearing through Path system)."""
        from meowcat.path import PathRegistry, Path as PathObj
        cat = _make_wired_cat()
        # 通过 Path 系统验证: hear 路径是 EARS → THALAMUS
        hear_path = cat.path_registry.get("hear")
        assert hear_path is not None
        assert hear_path.from_organ == EARS
        assert hear_path.to_organ == THALAMUS

    @pytest.mark.asyncio
    async def test_brainstem_to_hippocampus_stats_works(self) -> None:
        """BrainStem → Hippocampus stats 不受影响。"""
        cat = _make_wired_cat()
        result = await cat.signal(BRAINSTEM, HIPPOCAMPUS, "stats")
        assert isinstance(result, dict)
        assert "entities" in result
