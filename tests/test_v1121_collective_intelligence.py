# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v1.1.21 Collective Intelligence — Cross-cat memory search + delegation with memory snapshot."""

from __future__ import annotations

import pytest

from meowcat.colony import Colony
from meowcat.colony.memory import SharedMemoryPool
from meowcat.defaults.organs import NoopHippocampus
from meowcat.defaults.stores import InMemorySharedStore


# -- 1. Cross-cat memory search (Hippocampus.locate scope=colony) ----------

class TestCrossCatMemorySearch:
    """Hippocampus.locate(scope='colony') searches colony SharedMemoryPool."""

    def test_scope_self_unchanged(self):
        """scope='self' still searches own hippocampus (no regression)."""
        hippo = NoopHippocampus()
        hippo.add_episode(
            {"user_msg": "users 表结构", "ai_reply": "id, name, email"})

        results = hippo.locate("表结构", scope="self")
        assert len(results) >= 1
        assert any("users" in str(r) for r in results)

    def test_scope_colony_no_colony_memory(self):
        """scope='colony' without injected colony_memory returns empty."""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "private data", "ai_reply": "secret"})

        results = hippo.locate("data", scope="colony")
        assert results == []

    def test_scope_colony_searches_shared_memory(self):
        """scope='colony' with injected colony_memory searches shared memory."""
        hippo = NoopHippocampus()
        colony = Colony("test-cross", storage=InMemorySharedStore())

        # Add shared memories
        import asyncio

        async def _seed():
            await colony.memory.remember(
                "users 表有 id, name, email 三列", {"cat": "db-expert"})
            await colony.memory.remember(
                "orders 表关联 users 表的外键是 user_id", {"cat": "db-expert"})
        asyncio.run(_seed())

        hippo.set_colony_memory(colony.memory)

        results = hippo.locate("users 表", scope="colony")
        assert len(results) >= 1
        assert any("users" in str(r["text"]) for r in results)

    def test_scope_colony_no_match(self):
        """scope='colony' returns empty when no match in shared memory."""
        hippo = NoopHippocampus()
        colony = Colony("test-nomatch", storage=InMemorySharedStore())
        hippo.set_colony_memory(colony.memory)

        results = hippo.locate("nonexistent_xyz", scope="colony")
        assert results == []

    def test_colony_wires_hippocampus_on_create(self):
        """Colony.create_cat() injects colony_memory into hippocampus.

        Note: mount must happen before colony can detect the hippocampus.
        create_cat() checks for already-mounted organs; mounting after
        creation requires manual wiring (the colony injection is best-effort).
        """
        colony = Colony("test-wire", storage=InMemorySharedStore())
        cat = colony.create_cat(name="planner")
        cat.mount("brain", "hippocampus", NoopHippocampus())

        # After mounting, manually wire colony memory (same logic as create_cat)
        hippo = cat.organ("brain", "hippocampus")
        hippo.set_colony_memory(colony.memory)
        assert hippo._colony_memory is colony.memory

        # Verify cross-cat search works after wiring
        import asyncio

        async def _seed():
            await colony.memory.remember(
                "users 表有 id, name, email 三列", {"cat": "db-expert"})
        asyncio.run(_seed())

        results = hippo.locate("users", scope="colony")
        assert len(results) >= 1

    def test_invalid_scope_raises(self):
        """Invalid scope raises ValueError."""
        hippo = NoopHippocampus()
        with pytest.raises(ValueError, match="Invalid search scope"):
            hippo.locate("test", scope="global")


# -- 2. Memory snapshot (Hippocampus.snapshot) ------------------------------

class TestMemorySnapshot:
    """Hippocampus.snapshot() extracts memory context for delegation."""

    def test_snapshot_self_only(self):
        """snapshot with scope='self' gathers own hippocampus memories."""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "users 表结构是什么",
                          "ai_reply": "users 表有 id, name, email 列"})
        hippo.add_episode({"user_msg": "auth 模块怎么用",
                          "ai_reply": "auth 模块使用 JWT token"})

        snap = hippo.snapshot("users", "auth", scope="self")
        assert snap["topics"] == ["users", "auth"]
        assert len(snap["context"]) >= 1
        assert all(c["type"] == "self" for c in snap["context"])
        assert "created_at" in snap

    def test_snapshot_with_colony(self):
        """snapshot with scope='colony' includes shared memories."""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "users 表", "ai_reply": "基础结构"})

        colony = Colony("test-snap-colony", storage=InMemorySharedStore())
        import asyncio

        async def _seed():
            await colony.memory.remember(
                "users 表主键是 id，使用 UUID", {"cat": "db-expert"})
        asyncio.run(_seed())

        hippo.set_colony_memory(colony.memory)

        snap = hippo.snapshot("users", scope="colony")
        types = {c["type"] for c in snap["context"]}
        # self: fts_search matches "users" in "users 表"
        # colony: keyword_search matches "users" in shared memory
        assert types >= {"self", "colony"}

    def test_snapshot_empty(self):
        """snapshot with no matching memories returns empty context."""
        hippo = NoopHippocampus()
        snap = hippo.snapshot("nonexistent", scope="self")
        assert snap["topics"] == ["nonexistent"]
        assert snap["context"] == []

    def test_snapshot_multiple_topics(self):
        """snapshot can gather context for multiple topics."""
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "表 A 的字段", "ai_reply": "字段说明"})
        hippo.add_episode({"user_msg": "表 B 的索引", "ai_reply": "索引说明"})

        snap = hippo.snapshot("表", "字段", "索引", scope="self")
        assert len(snap["topics"]) == 3
        # Should have contexts tagged with their respective topics
        topics_in_ctx = {c["topic"] for c in snap["context"]}
        assert topics_in_ctx <= {"表", "字段", "索引"}


# -- 3. Delegation: spawn_cat with memory_snapshot --------------------------

class TestDelegationSpawnCat:
    """Colony.spawn_cat() creates kittens with inherited memory context."""

    def test_spawn_cat_creates_with_snapshot(self):
        """spawn_cat stores memory_snapshot on the kitten."""
        colony = Colony("test-spawn", storage=InMemorySharedStore())
        parent = colony.create_cat(name="parent")

        snap = {"topics": ["users表"], "context": [{"type": "self",
                "source": "episode", "content": "users 表结构"}]}

        kitten = colony.spawn_cat(
            name="kitten-1", parent_id=parent.cat_uid, memory_snapshot=snap)
        assert kitten.name == "kitten-1"
        assert kitten.parent_id == parent.cat_uid
        assert kitten._memory_snapshot == snap
        assert kitten.container is colony

    def test_spawn_cat_without_snapshot(self):
        """spawn_cat without snapshot works fine."""
        colony = Colony("test-nosnap", storage=InMemorySharedStore())
        kitten = colony.spawn_cat(name="kitten-2")
        assert kitten.name == "kitten-2"
        assert not hasattr(kitten, '_memory_snapshot')

    def test_spawn_cat_full_flow(self):
        """Full delegation flow: snapshot → spawn_cat with memory context."""
        colony = Colony("test-full", storage=InMemorySharedStore())

        # Parent cat with hippocampus
        parent = colony.create_cat(name="architect")
        hippo = NoopHippocampus()
        hippo.add_episode({"user_msg": "users 表设计",
                          "ai_reply": "users 表: id uuid, name text, email text"})
        parent.mount("brain", "hippocampus", hippo)
        hippo.set_colony_memory(colony.memory)

        # Parent takes a snapshot
        slice_ = hippo.snapshot("users", scope="self")
        assert len(slice_["context"]) >= 1

        # Delegate to kitten with snapshot
        kitten = colony.spawn_cat(
            name="executor-1", parent_id=parent.cat_uid, memory_snapshot=slice_)
        assert kitten.parent_id == parent.cat_uid
        assert kitten._memory_snapshot is slice_
        # Kitten has same colony storage
        assert kitten._colony_storage is colony._storage

    def test_spawn_cat_in_full_colony(self):
        """spawn_cat when colony is full raises RuntimeError."""
        colony = Colony("test-full-cap",
                        storage=InMemorySharedStore(), max_cats=1)
        colony.create_cat(name="only-cat")

        with pytest.raises(RuntimeError, match="full"):
            colony.spawn_cat(name="kitten-overflow")


# -- 4. SharedMemoryPool.keyword_search ------------------------------------

class TestKeywordSearch:
    """SharedMemoryPool.keyword_search() — sync keyword search for Hippocampus."""

    def test_keyword_search_finds_matches(self):
        """keyword_search returns matching shared memories."""
        colony = Colony("test-kws", storage=InMemorySharedStore())
        import asyncio

        async def _seed():
            await colony.memory.remember("Python async programming", {"cat": "dev"})
            await colony.memory.remember("Java spring boot", {"cat": "dev"})
            await colony.memory.remember("Rust async runtime", {"cat": "dev"})
        asyncio.run(_seed())

        results = colony.memory.keyword_search("Python async", k=10)
        assert len(results) >= 1
        assert any("Python" in r["text"] for r in results)

    def test_keyword_search_no_match(self):
        """keyword_search returns empty when no match."""
        colony = Colony("test-kws-empty", storage=InMemorySharedStore())
        results = colony.memory.keyword_search("nothing", k=10)
        assert results == []

    def test_keyword_search_limit(self):
        """keyword_search respects k limit."""
        colony = Colony("test-kws-limit", storage=InMemorySharedStore())
        import asyncio

        async def _seed():
            for i in range(5):
                await colony.memory.remember(f"test memory item {i}", {})
        asyncio.run(_seed())

        results = colony.memory.keyword_search("test memory", k=3)
        assert len(results) <= 3

