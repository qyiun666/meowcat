"""v1.1.20 Vector Store + Shared Memory — VectorStore + SharedMemoryPool tests."""

import pytest

from meowcat.protocols_storage import VectorStorageProtocol
from meowcat.storage.vector_store import VectorStore
from meowcat.colony import Colony
from meowcat.colony.memory import SharedMemoryPool
from meowcat.defaults.stores import InMemorySharedStore


# -- VectorStore ----------------------------------------------------------

class TestVectorStore:
    """VectorStore — lightweight keyword-based vector store."""

    def test_implements_protocol(self):
        store = VectorStore()
        assert isinstance(store, VectorStorageProtocol)

    def test_add_returns_id(self):
        store = VectorStore()
        doc_id = store.add("Cats are great", {"source": "test"})
        assert isinstance(doc_id, str)
        assert len(doc_id) == 12

    def test_search_empty_returns_list(self):
        store = VectorStore()
        assert store.search("anything") == []

    def test_keyword_search_finds_match(self):
        store = VectorStore()
        store.add("Cats make wonderful pets", {})
        store.add("Dogs are loyal companions", {})
        store.add("Programming in Python is fun", {})
        results = store.search("feline animals and cats", k=2)
        assert len(results) >= 1
        assert "Cats" in results[0]["text"]

    def test_keyword_search_no_match(self):
        store = VectorStore()
        store.add("apple banana cherry", {})
        results = store.search("xylophone zebra quantum")
        assert results == []

    def test_delete_existing(self):
        store = VectorStore()
        doc_id = store.add("test", {})
        assert store.delete(doc_id) is True
        assert store.count() == 0

    def test_delete_nonexistent(self):
        store = VectorStore()
        assert store.delete("no-such-id") is False

    def test_count(self):
        store = VectorStore()
        assert store.count() == 0
        store.add("a", {})
        store.add("b", {})
        assert store.count() == 2

    def test_diagnose(self):
        store = VectorStore()
        diag = store.diagnose()
        assert diag["count"] == 0
        assert diag["persist_path"] == "in-memory"
        assert diag["has_embedding"] is False

    def test_persist_survives_reload(self, tmp_path):
        p = tmp_path / "vec.jsonl"
        s1 = VectorStore(persist_path=p)
        s1.add("hello world", {"tag": "greeting"})
        s1.add("goodbye world", {"tag": "farewell"})

        s2 = VectorStore(persist_path=p)
        assert s2.count() == 2
        results = s2.search("hello", k=1)
        assert len(results) == 1
        assert "hello" in results[0]["text"]

    def test_persist_delete_rewrites(self, tmp_path):
        p = tmp_path / "vec.jsonl"
        s1 = VectorStore(persist_path=p)
        doc_id = s1.add("temp data", {})
        s1.add("keep data", {})
        s1.delete(doc_id)

        s2 = VectorStore(persist_path=p)
        assert s2.count() == 1
        assert s2.search("keep")[0]["text"] == "keep data"

    def test_unicode_text(self):
        store = VectorStore()
        store.add("你好世界", {"lang": "zh"})
        store.add("こんにちは世界", {"lang": "ja"})
        results = store.search("你好")
        assert len(results) == 1
        assert results[0]["text"] == "你好世界"

    def test_jaccard_partial_overlap(self):
        store = VectorStore()
        store.add("Python async programming guide", {})
        store.add("Java spring boot tutorial", {})
        results = store.search("async await tutorial Python", k=1)
        assert len(results) >= 1
        assert "Python" in results[0]["text"]


# -- SharedMemoryPool -----------------------------------------------------

class TestSharedMemoryPool:
    """SharedMemoryPool — colony-level shared memory."""

    @pytest.fixture
    def colony(self):
        return Colony("test-mem", storage=InMemorySharedStore())

    @pytest.mark.anyio
    async def test_colony_memory_lazy_init(self, colony):
        assert colony._memory_pool is None
        mem = colony.memory
        assert colony._memory_pool is mem
        assert isinstance(mem, SharedMemoryPool)

    @pytest.mark.anyio
    async def test_remember_and_recall(self, colony):
        await colony.memory.remember("用户喜欢 Python 3.12", {"cat": "planner"})
        await colony.memory.remember("用户使用 macOS", {"cat": "planner"})
        await colony.memory.remember("项目使用 PostgreSQL", {"cat": "executor"})

        results = await colony.memory.recall("Python 版本", k=2)
        assert len(results) >= 1
        assert any("Python" in r["text"] for r in results)

    @pytest.mark.anyio
    async def test_recall_empty(self, colony):
        results = await colony.memory.recall("nothing here", k=3)
        assert results == []

    @pytest.mark.anyio
    async def test_forget(self, colony):
        doc_id = await colony.memory.remember("test memory", {})
        assert await colony.memory.count() == 1

        deleted = await colony.memory.forget(doc_id)
        assert deleted is True
        assert await colony.memory.count() == 0

        # Double delete is safe
        assert await colony.memory.forget(doc_id) is False

    @pytest.mark.anyio
    async def test_forget_nonexistent(self, colony):
        assert await colony.memory.forget("no-such") is False

    @pytest.mark.anyio
    async def test_count(self, colony):
        assert await colony.memory.count() == 0
        await colony.memory.remember("a", {})
        await colony.memory.remember("b", {})
        assert await colony.memory.count() == 2

    @pytest.mark.anyio
    async def test_list_all(self, colony):
        await colony.memory.remember("memory one", {"n": 1})
        await colony.memory.remember("memory two", {"n": 2})

        all_mem = await colony.memory.list_all()
        assert len(all_mem) == 2
        texts = {m["text"] for m in all_mem}
        assert texts == {"memory one", "memory two"}

    @pytest.mark.anyio
    async def test_list_all_empty(self, colony):
        assert await colony.memory.list_all() == []

    @pytest.mark.anyio
    async def test_remember_persists_in_storage(self, colony):
        doc_id = await colony.memory.remember("persist me", {"tag": "test"})
        # Verify stored in colony namespace
        raw = await colony.ns_get("knowledge", f"mem:{doc_id}")
        import json
        record = json.loads(raw)
        assert record["text"] == "persist me"
        assert record["metadata"]["tag"] == "test"


# -- Import smoke test ----------------------------------------------------

class TestImportSmoke:
    """Verify v1.1.20 exports are reachable from meowcat."""

    def test_vector_store_import(self):
        from meowcat import VectorStore as VS  # noqa: F811
        assert VS is VectorStore

    def test_shared_memory_pool_import(self):
        from meowcat import SharedMemoryPool as SMP  # noqa: F811
        assert SMP is SharedMemoryPool
