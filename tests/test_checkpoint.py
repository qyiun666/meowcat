# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for general-purpose checkpoint store (T-24 / v1.3.6)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from meowcat.checkpoint import CheckpointConfig, CheckpointStore, JsonCheckpointStore


# ── CheckpointConfig ──────────────────────────────────────────────────


class TestCheckpointConfig:
    """CheckpointConfig default values."""

    def test_defaults(self):
        cfg = CheckpointConfig()
        assert cfg.data_dir == "./data/checkpoints"
        assert cfg.autosave is True

    def test_custom(self):
        cfg = CheckpointConfig(data_dir="/tmp/ckpt", autosave=False)
        assert cfg.data_dir == "/tmp/ckpt"
        assert cfg.autosave is False


# ── CheckpointStore base ──────────────────────────────────────────────


class TestCheckpointStoreBase:
    """Abstract base — cannot instantiate directly, subclass must implement."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError, match="abstract"):
            CheckpointStore()  # type: ignore[abstract]

    @pytest.mark.anyio
    async def test_concrete_subclass_works(self):
        class MinimalStore(CheckpointStore):
            async def save(self, key, data): pass
            async def load(self, key): return None
            async def delete(self, key): pass
            async def list_keys(self): return []
        store = MinimalStore()
        assert await store.load("any") is None


# ── JsonCheckpointStore ───────────────────────────────────────────────


class TestJsonCheckpointStore:
    """JsonCheckpointStore CRUD and lifecycle tests."""

    @pytest.fixture
    def store(self) -> JsonCheckpointStore:
        with tempfile.TemporaryDirectory() as tmp:
            yield JsonCheckpointStore(tmp)

    @pytest.mark.anyio
    async def test_save_and_load(self, store: JsonCheckpointStore):
        data = {"step": 3, "results": [1, 2, 3], "meta": {"status": "running"}}
        await store.save("task-001", data)
        loaded = await store.load("task-001")
        assert loaded == data

    @pytest.mark.anyio
    async def test_load_missing_returns_none(self, store: JsonCheckpointStore):
        assert await store.load("no-such-key") is None

    @pytest.mark.anyio
    async def test_delete(self, store: JsonCheckpointStore):
        await store.save("del-me", {"x": 1})
        assert await store.load("del-me") is not None
        await store.delete("del-me")
        assert await store.load("del-me") is None

    @pytest.mark.anyio
    async def test_delete_missing_no_error(self, store: JsonCheckpointStore):
        # Should not raise
        await store.delete("ghost")

    @pytest.mark.anyio
    async def test_list_keys(self, store: JsonCheckpointStore):
        await store.save("alpha", {"n": 1})
        await store.save("beta", {"n": 2})
        await store.save("gamma", {"n": 3})
        keys = await store.list_keys()
        assert keys == ["alpha", "beta", "gamma"]

    @pytest.mark.anyio
    async def test_list_keys_empty(self, store: JsonCheckpointStore):
        assert await store.list_keys() == []

    @pytest.mark.anyio
    async def test_overwrite(self, store: JsonCheckpointStore):
        await store.save("key", {"v": 1})
        await store.save("key", {"v": 99})
        loaded = await store.load("key")
        assert loaded == {"v": 99}

    @pytest.mark.anyio
    async def test_load_all(self, store: JsonCheckpointStore):
        await store.save("a", {"x": 1})
        await store.save("b", {"y": 2})
        all_data = await store.load_all()
        assert all_data == {"a": {"x": 1}, "b": {"y": 2}}

    @pytest.mark.anyio
    async def test_load_all_empty(self, store: JsonCheckpointStore):
        assert await store.load_all() == {}

    @pytest.mark.anyio
    async def test_complex_data_types(self, store: JsonCheckpointStore):
        """Int, float, bool, None, list, nested dict round-trip."""
        data = {
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, "two", 3.0],
            "nested": {"a": {"b": [1, 2]}},
        }
        await store.save("complex", data)
        loaded = await store.load("complex")
        assert loaded == data

    @pytest.mark.anyio
    async def test_config_property(self, store: JsonCheckpointStore):
        cfg = store.config
        assert isinstance(cfg, CheckpointConfig)
        assert cfg.autosave is True

    @pytest.mark.anyio
    async def test_diagnose(self, store: JsonCheckpointStore):
        diag = store.diagnose()
        assert "data_dir" in diag
        assert "autosave" in diag
        assert diag["autosave"] is True

    @pytest.mark.anyio
    async def test_atomic_write_no_partial_file(self, store: JsonCheckpointStore):
        """Verify no .tmp files leak after save."""
        await store.save("atomic", {"ok": True})
        dir_path = Path(store.config.data_dir)
        tmp_files = list(dir_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    @pytest.mark.anyio
    async def test_key_with_special_chars(self, store: JsonCheckpointStore):
        """Keys with dashes, underscores, dots."""
        await store.save("task/sub-1.v2", {"p": 1})
        loaded = await store.load("task/sub-1.v2")
        assert loaded == {"p": 1}
        keys = await store.list_keys()
        assert "task/sub-1.v2" in keys

    @pytest.mark.anyio
    async def test_unicode_data(self, store: JsonCheckpointStore):
        data = {"message": "你好世界 🌍", "author": "猫"}
        await store.save("unicode", data)
        loaded = await store.load("unicode")
        assert loaded == data

    @pytest.mark.anyio
    async def test_empty_dict(self, store: JsonCheckpointStore):
        await store.save("empty", {})
        assert await store.load("empty") == {}
