"""v1.1.19 Persistent Storage — SqliteGraphStore + JsonlL6Store tests."""

import pytest

from meowcat.protocols_storage import GraphStorageProtocol, L6StorageProtocol
from meowcat.storage.sqlite_graph_store import SqliteGraphStore
from meowcat.storage.jsonl_l6_store import JsonlL6Store


# -- SqliteGraphStore ---------------------------------------------------

class TestSqliteGraphStore:
    """SqliteGraphStore — SQLite-backed persistent graph storage."""

    @pytest.fixture
    def store(self, tmp_path):
        return SqliteGraphStore(tmp_path / "graphs.db")

    def test_implements_protocol(self, store):
        assert isinstance(store, GraphStorageProtocol)

    @pytest.mark.anyio
    async def test_load_empty_returns_dict(self, store):
        data = await store.load("no-such-cat")
        assert data == {}

    @pytest.mark.anyio
    async def test_save_and_load(self, store):
        graph = {"entities": [{"id": "e1"}],
                 "connections": [{"from": "e1", "to": "e2"}]}
        await store.save("cat-a", graph)
        loaded = await store.load("cat-a")
        assert loaded == graph

    @pytest.mark.anyio
    async def test_save_overwrites(self, store):
        await store.save("cat-b", {"v": 1})
        await store.save("cat-b", {"v": 2})
        assert await store.load("cat-b") == {"v": 2}

    @pytest.mark.anyio
    async def test_multiple_cats_isolated(self, store):
        await store.save("c1", {"n": "one"})
        await store.save("c2", {"n": "two"})
        assert await store.load("c1") == {"n": "one"}
        assert await store.load("c2") == {"n": "two"}

    @pytest.mark.anyio
    async def test_save_complex_data(self, store):
        complex_graph = {
            "entities": [{"id": "e1", "props": {"name": "test", "count": 42}}],
            "connections": [{"from": "e1", "to": None, "weight": 0.95}],
            "meta": {"version": 1, "tags": ["a", "b"]},
        }
        await store.save("complex", complex_graph)
        assert await store.load("complex") == complex_graph

    @pytest.mark.anyio
    async def test_save_unicode(self, store):
        graph = {"name": "猫猫", "desc": "日本語テスト"}
        await store.save("unicode", graph)
        assert await store.load("unicode") == graph


# -- JsonlL6Store -------------------------------------------------------

class TestJsonlL6Store:
    """JsonlL6Store — JSONL-based persistent conversation storage."""

    @pytest.fixture
    def store(self, tmp_path):
        return JsonlL6Store(tmp_path / "convos")

    def test_implements_protocol(self, store):
        assert isinstance(store, L6StorageProtocol)

    def test_load_all_empty(self, store):
        assert store.load_all("no-cat") == []

    def test_append_and_load_all(self, store):
        store.append("cat-x", 1, "Hello", "Hi!")
        store.append("cat-x", 2, "How are you?", "Good")
        records = store.load_all("cat-x")
        assert len(records) == 2
        assert records[0] == {"turn": 1, "user": "Hello", "ai": "Hi!"}
        assert records[1] == {"turn": 2, "user": "How are you?", "ai": "Good"}

    def test_load_recent(self, store):
        for i in range(5):
            store.append("cat-r", i + 1, f"u{i}", f"a{i}")
        recent = store.load_recent("cat-r", n=2)
        assert len(recent) == 2
        assert recent[0]["turn"] == 4
        assert recent[1]["turn"] == 5

    def test_load_recent_more_than_available(self, store):
        store.append("cat-s", 1, "u", "a")
        recent = store.load_recent("cat-s", n=10)
        assert len(recent) == 1

    def test_total_chars(self, store):
        store.append("cat-c", 1, "ab", "cd")
        store.append("cat-c", 2, "efg", "h")
        # user: 2+3=5, ai: 2+1=3, total=8
        assert store.total_chars("cat-c") == 8

    def test_get_stats(self, store):
        store.append("cat-st", 1, "hello", "world")
        store.append("cat-st", 2, "foo", "bar")
        stats = store.get_stats("cat-st")
        assert stats == {"total_turns": 2, "total_chars": 16}

    def test_cats_isolated(self, store):
        store.append("a", 1, "ua", "aa")
        store.append("b", 1, "ub", "ab")
        assert len(store.load_all("a")) == 1
        assert len(store.load_all("b")) == 1
        assert store.load_all("a")[0]["user"] == "ua"

    def test_unicode(self, store):
        store.append("猫", 1, "你好", "こんにちは")
        records = store.load_all("猫")
        assert records[0]["user"] == "你好"
        assert records[0]["ai"] == "こんにちは"

    def test_empty_stats(self, store):
        stats = store.get_stats("nobody")
        assert stats == {"total_turns": 0, "total_chars": 0}

    def test_load_recent_empty(self, store):
        assert store.load_recent("nonexist", n=5) == []


# -- Import smoke test --------------------------------------------------

class TestImportSmoke:
    """Verify v1.1.19 exports are reachable from meowcat."""

    def test_sqlite_graph_store_import(self):
        from meowcat import SqliteGraphStore as S  # noqa: F811
        assert S is SqliteGraphStore

    def test_jsonl_l6_store_import(self):
        from meowcat import JsonlL6Store as J  # noqa: F811
        assert J is JsonlL6Store
