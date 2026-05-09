# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.2.35 框架级修复回归测试。

覆盖 T1~T6:
  T1: CatBase container 类型标注修复
  T2: loops.py 误导入保护
  T3: 存储协议统一 SharedStorageProtocol → SharedStore
  T4: InMemoryVectorStore.add() 抛 NotImplementedError
  T5: VectorStore._make_id MD5 → SHA256
  T6: tools/__init__ 懒加载委托 _LAZY_MAP
"""

from __future__ import annotations

import pytest

from meowcat.defaults import InMemoryVectorStore
from meowcat.errors import StandaloneCatError
from meowcat.storage import VectorStore
from meowcat.testing import make_cat, make_test_colony

# ──────────────────────────────────────────────────────────────────────
# T1: CatBase container 类型标注修复
# ──────────────────────────────────────────────────────────────────────


class Test_T1_CatBaseContainer:
    """T1: CatBase("01") 抛 StandaloneCatError; 带 container 正常工作。"""

    def test_catbase_no_container_raises_standalone(self):
        from meowcat.assembly import CatBase
        with pytest.raises(StandaloneCatError):
            CatBase("01")

    def test_catbase_with_container_works(self):
        cat = make_cat("t1-test")
        assert cat.cat_uid == "01"
        assert cat.container is not None
        assert cat.cat_address == "test_01"


# ──────────────────────────────────────────────────────────────────────
# T2: loops.py 误导入保护
# ──────────────────────────────────────────────────────────────────────

class Test_T2_LoopsImportProtection:
    """T2: loops.py __getattr__ 拦截误导入并给出迁移提示。

    ``from module import X`` 不触发 ``__getattr__``（Python 语言限制），
    因此用 ``import module; module.X`` 形式验证。
    """

    def test_attr_access_locate_event_raises_helpful_error(self):
        """loops.LocateEvent → AttributeError with migration hint."""
        import meowcat.loops as _loops
        with pytest.raises(AttributeError) as exc:
            _ = _loops.LocateEvent
        assert "meowcat.events" in str(exc.value)

    def test_attr_access_eventbus_raises_helpful_error(self):
        """loops.EventBus → AttributeError with migration hint."""
        import meowcat.loops as _loops
        with pytest.raises(AttributeError) as exc:
            _ = _loops.EventBus
        assert "meowcat.events" in str(exc.value)

    def test_import_locate_event_from_events_works(self):
        from meowcat.events import LocateEvent  # noqa: F401

    def test_import_eventbus_from_events_works(self):
        from meowcat.events import EventBus  # noqa: F401

    def test_import_normal_from_loops_works(self):
        """正常导入 loops 模块的正确定义不应被影响。"""
        from meowcat.loops import BUILTIN_LOOPS, Loop  # noqa: F401

    def test_unknown_attr_still_raises(self):
        """非事件类的未知属性仍抛出 AttributeError。"""
        import meowcat.loops as _loops
        with pytest.raises(AttributeError):
            _ = _loops.NonExistent


# ──────────────────────────────────────────────────────────────────────
# T3: 存储协议统一 — SharedStorageProtocol → SharedStore
# ──────────────────────────────────────────────────────────────────────

class Test_T3_StorageProtocolMigration:
    """T3: Colony 接受 SharedStore; SharedStorageProtocol 保留兼容。"""

    def test_colony_with_inmemory_shared_store_works(self):
        colony = make_test_colony("t3-colony")
        assert colony._storage is not None
        # _ensure_storage 返回 SharedStore 类型
        store = colony._ensure_storage()
        from meowcat.storage import SharedStore
        assert isinstance(store, SharedStore)

    def test_colony_default_auto_creates_shared_store(self):
        from meowcat.colony import Colony
        colony = Colony.default("t3-default")
        store = colony._ensure_storage()
        assert store is not None

    def test_shared_storage_protocol_still_exists(self):
        from meowcat.protocols_storage import SharedStorageProtocol

        class _CompatImpl(SharedStorageProtocol):
            def load(self): return {}
            def save(self, data): pass
            def merge(self, delta): return {}
        assert isinstance(_CompatImpl(), SharedStorageProtocol)


# ──────────────────────────────────────────────────────────────────────
# T4: InMemoryVectorStore.add() 抛 NotImplementedError
# ──────────────────────────────────────────────────────────────────────

class Test_T4_InMemoryVectorStore:
    """T4: InMemoryVectorStore.add() 抛 NotImplementedError。"""

    @pytest.mark.anyio
    async def test_add_raises_not_implemented(self):
        vs = InMemoryVectorStore()
        with pytest.raises(NotImplementedError) as exc:
            await vs.add("hello", {})
        assert "InMemoryVectorStore.add()" in str(exc.value)

    @pytest.mark.anyio
    async def test_store_and_search_still_works(self):
        """store/search/delete 正常功能不受影响。"""
        vs = InMemoryVectorStore()
        await vs.store("e1", [1.0, 0.0])
        await vs.store("e2", [0.0, 1.0])
        results = await vs.search([1.0, 0.0], top_k=1)
        assert results == ["e1"]

    @pytest.mark.anyio
    async def test_delete_returns_true_for_existing(self):
        vs = InMemoryVectorStore()
        await vs.store("e1", [1.0, 0.0])
        assert await vs.delete("e1") is True
        assert await vs.delete("e1") is False


# ──────────────────────────────────────────────────────────────────────
# T5: VectorStore._make_id MD5 → SHA256
# ──────────────────────────────────────────────────────────────────────

class Test_T5_VectorStoreMakeId:
    """T5: VectorStore.add() 产生 SHA256-based id。"""

    def test_add_generates_valid_id(self):
        vs = VectorStore()
        doc_id = vs.add("hello world", {"source": "test"})
        assert isinstance(doc_id, str)
        assert len(doc_id) == 12  # hexdigest[:12]

    def test_add_generates_deterministic_id(self):
        vs = VectorStore()
        id1 = vs.add("hello world", {"source": "test"})
        vs2 = VectorStore()
        id2 = vs2.add("hello world", {"source": "test"})
        assert id1 == id2  # same input = same id

    def test_add_generates_different_ids(self):
        vs = VectorStore()
        id1 = vs.add("hello world", {"k": "a"})
        id2 = vs.add("hello world", {"k": "b"})
        assert id1 != id2

    def test_search_and_delete_by_id(self):
        vs = VectorStore()
        doc_id = vs.add("cats are great", {})
        results = vs.search("cats", k=1)
        assert len(results) == 1
        assert results[0]["id"] == doc_id
        assert vs.delete(doc_id) is True
        assert vs.delete(doc_id) is False


# ──────────────────────────────────────────────────────────────────────
# T6: tools/__init__ 懒加载委托 _LAZY_MAP
# ──────────────────────────────────────────────────────────────────────

class Test_T6_ToolsLazyDelegation:
    """T6: tools/__init__ 的 plus 懒加载委托到顶层 _LAZY_MAP。

    v2.0: BUILTIN_TOOLS 和 BrowserTool 已移出框架，懒加载
    只对保留符号 (ChromaStore, Crystallizer, SkillLoader 等) 有效。"""

    def test_unknown_attr_raises(self):
        """tools 模块未知属性通过 __getattr__ 抛出 AttributeError。"""
        import meowcat.tools as _tools
        with pytest.raises(AttributeError):
            _ = _tools.NonExistent
