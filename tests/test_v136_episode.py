# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.3.6 T-11: episode CRUD + 批量查询 + 持久化恢复全覆盖测试.

覆盖:
- NoopHippocampus add_episode / get_episode / get_episodes
- RenovatedHippocampus add_episode with write-through persistence
- JsonlEpisodeStore append / get / get_batch / load_all / get_stats
- Hippocampus lifecycle: _load_from_store / _flush_to_store
- 持久化恢复: 构造新 store 实例读取之前写入的数据
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import anyio
import pytest

from meowcat import NoopHippocampus
from meowcat.defaults.renovated import RenovatedHippocampus
from meowcat.storage import JsonlEpisodeStore

# ===================================================================
# 1. NoopHippocampus episode CRUD
# ===================================================================

class TestNoopHippocampusEpisode:
    """NoopHippocampus add_episode / get_episode / get_episodes."""

    def test_add_episode_with_id(self) -> None:
        h = NoopHippocampus()
        eid = h.add_episode(
            {"id": "ep1", "user_msg": "hi", "ai_reply": "hello"})
        assert eid == "ep1"
        assert len(h.episodes) == 1
        assert h.episodes[0]["user_msg"] == "hi"

    def test_add_episode_auto_id(self) -> None:
        h = NoopHippocampus()
        eid = h.add_episode({"user_msg": "q", "ai_reply": "a"})
        assert eid.startswith("ep_")
        assert h.episodes[0]["id"] == eid

    def test_add_episode_sequential_auto_id(self) -> None:
        h = NoopHippocampus()
        eid1 = h.add_episode({"user_msg": "q1"})
        eid2 = h.add_episode({"user_msg": "q2"})
        assert eid1 == "ep_0"
        assert eid2 == "ep_1"

    def test_get_episode_found(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1", "user_msg": "hi"})
        h.add_episode({"id": "ep2", "user_msg": "hello"})
        ep = h.get_episode("ep2")
        assert ep is not None
        assert ep["user_msg"] == "hello"

    def test_get_episode_not_found(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1", "user_msg": "hi"})
        assert h.get_episode("nonexistent") is None

    def test_get_episode_empty_store(self) -> None:
        h = NoopHippocampus()
        assert h.get_episode("any") is None

    def test_get_episodes_batch_found(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1", "user_msg": "a"})
        h.add_episode({"id": "ep2", "user_msg": "b"})
        h.add_episode({"id": "ep3", "user_msg": "c"})
        results = h.get_episodes(["ep1", "ep3"])
        assert len(results) == 2
        msgs = {r["user_msg"] for r in results}
        assert msgs == {"a", "c"}

    def test_get_episodes_batch_partial(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1", "user_msg": "a"})
        results = h.get_episodes(["ep1", "ep_missing"])
        assert len(results) == 1
        assert results[0]["user_msg"] == "a"

    def test_get_episodes_batch_empty_ids(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1", "user_msg": "a"})
        assert h.get_episodes([]) == []

    def test_get_episodes_batch_all_missing(self) -> None:
        h = NoopHippocampus()
        h.add_episode({"id": "ep1"})
        assert h.get_episodes(["x", "y", "z"]) == []

    def test_add_episode_preserves_all_fields(self) -> None:
        h = NoopHippocampus()
        ep = {"id": "ep_x", "user_msg": "q", "ai_reply": "a",
              "cat_uid": "cat1", "model": "gpt-4", "ts": 1234567890}
        h.add_episode(ep)
        got = h.get_episode("ep_x")
        assert got is not None
        assert got["user_msg"] == "q"
        assert got["ai_reply"] == "a"
        assert got["cat_uid"] == "cat1"


# ===================================================================
# 2. JsonlEpisodeStore
# ===================================================================

class TestJsonlEpisodeStore:
    """JsonlEpisodeStore append / get / get_batch / load_all / get_stats."""

    @pytest.fixture
    def tmp_dir(self) -> str:
        with tempfile.TemporaryDirectory() as d:
            yield d

    def _store(self, tmp_dir: str) -> JsonlEpisodeStore:
        return JsonlEpisodeStore(tmp_dir)

    def test_append_with_id(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        eid = store.append("cat1", {"id": "ep1", "user_msg": "hi"})
        assert eid == "ep1"

    def test_append_auto_id(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        eid = store.append("cat1", {"user_msg": "hello"})
        assert eid.startswith("ep_")
        assert len(eid) > 3

    def test_get_found(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append(
            "cat1", {"id": "ep1", "user_msg": "hi", "ai_reply": "hello"})
        ep = store.get("cat1", "ep1")
        assert ep is not None
        assert ep["user_msg"] == "hi"
        assert ep["ai_reply"] == "hello"

    def test_get_not_found(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "hi"})
        assert store.get("cat1", "nonexistent") is None

    def test_get_empty_store(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        assert store.get("cat1", "any") is None

    def test_get_unknown_cat(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "hi"})
        assert store.get("cat2", "ep1") is None

    def test_get_batch_found(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "a", "user_msg": "1"})
        store.append("cat1", {"id": "b", "user_msg": "2"})
        store.append("cat1", {"id": "c", "user_msg": "3"})
        results = store.get_batch("cat1", ["a", "c"])
        assert len(results) == 2
        msgs = {r["user_msg"] for r in results}
        assert msgs == {"1", "3"}

    def test_get_batch_partial(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "a", "user_msg": "1"})
        results = store.get_batch("cat1", ["a", "z"])
        assert len(results) == 1

    def test_get_batch_empty_ids(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "a", "user_msg": "1"})
        assert store.get_batch("cat1", []) == []

    def test_get_batch_empty_cat(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        assert store.get_batch("unknown", ["a"]) == []

    def test_load_all(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "a"})
        store.append("cat1", {"id": "ep2", "user_msg": "b"})
        store.append("cat1", {"id": "ep3", "user_msg": "c"})
        all_eps = store.load_all("cat1")
        assert len(all_eps) == 3
        assert all_eps[0]["user_msg"] == "a"
        assert all_eps[2]["user_msg"] == "c"

    def test_load_all_empty_cat(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        assert store.load_all("unknown") == []

    def test_get_stats(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        assert store.get_stats("cat1") == {"total_episodes": 0}
        store.append("cat1", {"id": "a"})
        store.append("cat1", {"id": "b"})
        assert store.get_stats("cat1") == {"total_episodes": 2}

    def test_persists_across_instances(self, tmp_dir: str) -> None:
        """同一 data_dir 下新建 store 实例可以读取之前写入的数据。"""
        store1 = self._store(tmp_dir)
        store1.append("cat1", {"id": "ep1", "user_msg": "persisted"})
        store1.append("cat1", {"id": "ep2", "user_msg": "also persisted"})

        # 新实例，相同目录
        store2 = JsonlEpisodeStore(tmp_dir)
        assert store2.get("cat1", "ep1") is not None
        assert store2.get("cat1", "ep1")[
            "user_msg"] == "persisted"  # type: ignore[index]
        assert len(store2.load_all("cat1")) == 2
        assert store2.get_stats("cat1") == {"total_episodes": 2}

    def test_multi_cat_isolation(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "a", "user_msg": "cat1-msg"})
        store.append("cat2", {"id": "b", "user_msg": "cat2-msg"})

        # type: ignore[index]
        assert store.get("cat1", "a")["user_msg"] == "cat1-msg"
        # type: ignore[index]
        assert store.get("cat2", "b")["user_msg"] == "cat2-msg"
        assert store.get("cat1", "b") is None  # cat1 看不到 cat2 的

        assert len(store.load_all("cat1")) == 1
        assert len(store.load_all("cat2")) == 1
        assert store.get_stats("cat1") == {"total_episodes": 1}
        assert store.get_stats("cat2") == {"total_episodes": 1}

    def test_complex_data_types(self, tmp_dir: str) -> None:
        store = self._store(tmp_dir)
        ep = {
            "id": "complex",
            "user_msg": "test",
            "ai_reply": "reply",
            "metadata": {"tokens": 42, "model": "gpt-4"},
            "tags": ["important", "python"],
            "nested": {"a": {"b": [1, 2, 3]}},
        }
        store.append("cat1", ep)
        got = store.get("cat1", "complex")
        assert got is not None
        assert got["metadata"]["tokens"] == 42  # type: ignore[index]
        assert got["tags"] == ["important", "python"]  # type: ignore[index]
        assert got["nested"]["a"]["b"] == [1, 2, 3]  # type: ignore[index]

    def test_partial_index_recovery(self, tmp_dir: str) -> None:
        """如果 index 文件丢失但 jsonl 还在，load_all 仍可用。"""
        store = self._store(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "a"})
        store.append("cat1", {"id": "ep2", "user_msg": "b"})

        # 删除 index 文件
        idx_path = Path(tmp_dir) / "cat1.episodes.idx.json"
        idx_path.unlink()

        # get 会返回 None（索引丢失）
        assert store.get("cat1", "ep1") is None

        # load_all 仍能读取所有数据
        all_eps = store.load_all("cat1")
        assert len(all_eps) == 2
        msgs = {ep["user_msg"] for ep in all_eps}
        assert msgs == {"a", "b"}

        # stats 返回 0（依赖索引）
        assert store.get_stats("cat1") == {"total_episodes": 0}


# ===================================================================
# 3. RenovatedHippocampus episode CRUD with store
# ===================================================================

class TestRenovatedHippocampusEpisode:
    """RenovatedHippocampus add_episode with JsonlEpisodeStore write-through."""

    @pytest.fixture
    def tmp_dir(self) -> str:
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_add_episode_without_store(self) -> None:
        h = RenovatedHippocampus()  # no episode_store
        eid = h.add_episode({"id": "ep1", "user_msg": "hi"})
        assert eid == "ep1"
        assert h.get_episode("ep1") is not None

    def test_add_episode_with_store_write_through(self, tmp_dir: str) -> None:
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "cat1"
        eid = h.add_episode({"id": "ep1", "user_msg": "hi"})
        assert eid == "ep1"
        # 确认已持久化到 store
        assert store.get("cat1", "ep1") is not None
        assert store.get("cat1", "ep1")[
            "user_msg"] == "hi"  # type: ignore[index]

    def test_add_episode_store_never_crashes(self) -> None:
        """即使 store 不可写，add_episode 也不应该抛异常。"""

        class _BadStore:
            def append(self, cat_uid: str, episode: dict) -> str:
                raise OSError("disk full")

        h = RenovatedHippocampus(episode_store=_BadStore())
        h.cat_uid = "cat1"
        # 不应抛异常
        eid = h.add_episode({"id": "ep1", "user_msg": "hi"})
        assert eid == "ep1"
        assert h.get_episode("ep1") is not None  # 内存中仍在

    def test_get_episode_in_memory(self, tmp_dir: str) -> None:
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "cat1"
        h.add_episode({"id": "ep1", "user_msg": "in-memory"})
        # 内存获取成功
        assert h.get_episode("ep1") is not None

    def test_get_episode_not_found(self, tmp_dir: str) -> None:
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        assert h.get_episode("nonexistent") is None

    def test_get_episodes_batch(self) -> None:
        h = RenovatedHippocampus()
        h.add_episode({"id": "a", "user_msg": "1"})
        h.add_episode({"id": "b", "user_msg": "2"})
        h.add_episode({"id": "c", "user_msg": "3"})
        results = h.get_episodes(["a", "c"])
        assert len(results) == 2
        msgs = {r["user_msg"] for r in results}
        assert msgs == {"1", "3"}

    def test_add_episode_uses_cat_uid_for_store(self, tmp_dir: str) -> None:
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "my-custom-cat"
        eid = h.add_episode({"id": "ep1", "user_msg": "x"})
        assert eid == "ep1"
        # store 使用 cat_uid
        assert store.get("my-custom-cat", "ep1") is not None
        # 其他 cat 看不到
        assert store.get("other-cat", "ep1") is None

    def test_add_episode_uses_episode_cat_uid_fallback(self, tmp_dir: str) -> None:
        """cat_uid 为空时回退到 episode 中的 cat_uid。"""
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = ""  # 未设置
        eid = h.add_episode(
            {"id": "ep1", "cat_uid": "fallback-cat", "user_msg": "x"})
        assert eid == "ep1"
        assert store.get("fallback-cat", "ep1") is not None

    def test_add_episode_uses_unknown_fallback(self, tmp_dir: str) -> None:
        """cat_uid 和 episode cat_uid 都为空时回退到 'unknown'。"""
        store = JsonlEpisodeStore(tmp_dir)
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = ""
        eid = h.add_episode({"id": "ep1", "user_msg": "x"})
        assert eid == "ep1"
        assert store.get("unknown", "ep1") is not None


# ===================================================================
# 4. Hippocampus lifecycle (_load_from_store / _flush_to_store)
# ===================================================================

class TestHippocampusLifecycle:
    """_load_from_store / _flush_to_store + 持玖化恢复."""

    @pytest.fixture
    def tmp_dir(self) -> str:
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_load_from_store_no_store(self) -> None:
        h = RenovatedHippocampus()  # no store

        async def _run() -> None:
            await h._load_from_store()  # 不应抛异常
        anyio.run(_run)

    def test_load_from_store_no_cat_uid(self) -> None:
        store = JsonlEpisodeStore(tempfile.mkdtemp())
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = ""  # 未设置

        async def _run() -> None:
            await h._load_from_store()  # 不应抛异常
        anyio.run(_run)

    def test_flush_to_store_no_store(self) -> None:
        h = RenovatedHippocampus()

        async def _run() -> None:
            await h._flush_to_store()  # no-op
        anyio.run(_run)

    def test_load_from_store_restores_episodes(self, tmp_dir: str) -> None:
        """写入 store → 新建 hippocampus → _load_from_store 恢复。"""
        # 先写数据
        store = JsonlEpisodeStore(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "persisted-a"})
        store.append("cat1", {"id": "ep2", "user_msg": "persisted-b"})

        # 新 hippocampus
        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "cat1"

        async def _run() -> None:
            await h._load_from_store()
        anyio.run(_run)

        assert len(h.episodes) == 2
        msgs = {ep["user_msg"] for ep in h.episodes}
        assert msgs == {"persisted-a", "persisted-b"}

    def test_load_from_store_dedup(self, tmp_dir: str) -> None:
        """已存在内存中的 episode 不会被重复加载。"""
        store = JsonlEpisodeStore(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "stored"})

        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "cat1"
        # 已在内存中
        h.add_episode({"id": "ep1", "user_msg": "in-memory"})

        async def _run() -> None:
            await h._load_from_store()
        anyio.run(_run)

        assert len(h.episodes) == 1  # 不重复
        assert h.episodes[0]["user_msg"] == "in-memory"  # 内存版本保留

    def test_load_from_store_handles_io_error(self, tmp_dir: str) -> None:
        """IO 错误不抛异常，内存保持为空。"""

        class _BadStore:
            def load_all(self, cat_uid: str) -> list:
                raise OSError("cannot read")

        h = RenovatedHippocampus(episode_store=_BadStore())
        h.cat_uid = "cat1"

        async def _run() -> None:
            await h._load_from_store()
        anyio.run(_run)
        assert len(h.episodes) == 0  # 不崩溃

    def test_lifecycle_integration_start_shutdown(self, tmp_dir: str) -> None:
        """通过 cat lifecycle 验证 start → load, shutdown → no crash。"""
        store = JsonlEpisodeStore(tmp_dir)
        store.append("cat1", {"id": "ep1", "user_msg": "pre-populated"})

        h = RenovatedHippocampus(episode_store=store)
        h.cat_uid = "cat1"

        async def _run() -> None:
            await h._load_from_store()
        anyio.run(_run)

        assert len(h.episodes) == 1
        assert h.episodes[0]["user_msg"] == "pre-populated"

        # shutdown 不抛异常
        async def _shutdown() -> None:
            await h._flush_to_store()
        anyio.run(_shutdown)

    def test_full_roundtrip_write_read(self, tmp_dir: str) -> None:
        """写 → 新建 hippocampus → restore → 验证数据完整。"""
        store = JsonlEpisodeStore(tmp_dir)

        # 第一轮：写
        h1 = RenovatedHippocampus(episode_store=store)
        h1.cat_uid = "cat1"
        h1.add_episode({"id": "a", "user_msg": "q1", "ai_reply": "a1"})
        h1.add_episode({"id": "b", "user_msg": "q2", "ai_reply": "a2"})

        # 第二轮：新建
        h2 = RenovatedHippocampus(episode_store=store)
        h2.cat_uid = "cat1"

        async def _run() -> None:
            await h2._load_from_store()
        anyio.run(_run)

        assert len(h2.episodes) == 2
        assert h2.get_episode("a") is not None
        assert h2.get_episode("a")["ai_reply"] == "a1"  # type: ignore[index]
        assert h2.get_episodes(["a", "b"])  # batch 也能用
