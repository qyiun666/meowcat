# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for FocusStore persistence (T-22 / v1.3.6)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from meowcat.focus import FocusState, FocusStore, JsonFocusStore


# ── FocusState ────────────────────────────────────────────────────────


class TestFocusState:
    """FocusState dataclass default values and construction."""

    def test_defaults(self):
        state = FocusState()
        assert state.topics == []
        assert state.current_keywords == []
        assert state.threshold == 0.3

    def test_custom(self):
        state = FocusState(
            topics=["db design", "sql"],
            current_keywords=["schema", "migration"],
            threshold=0.5,
        )
        assert state.topics == ["db design", "sql"]
        assert state.current_keywords == ["schema", "migration"]
        assert state.threshold == 0.5

    def test_threshold_range(self):
        state = FocusState(threshold=0.0)
        assert state.threshold == 0.0
        state = FocusState(threshold=1.0)
        assert state.threshold == 1.0


# ── FocusStore (abstract base) ────────────────────────────────────────


class _PartialFocusStore(FocusStore):
    """Concrete subclass that doesn't implement abstract methods — for testing."""


class TestFocusStoreBase:
    """FocusStore abstract base cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            FocusStore()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_methods(self):
        with pytest.raises(TypeError):
            _PartialFocusStore()  # type: ignore[abstract]


# ── JsonFocusStore ────────────────────────────────────────────────────


class TestJsonFocusStore:
    """JsonFocusStore save/load/delete/diagnose."""

    @pytest.fixture
    def tmp_path(self) -> Path:
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp) / "focus.json"

    @pytest.fixture
    def store(self, tmp_path: Path) -> JsonFocusStore:
        return JsonFocusStore(tmp_path)

    # ── save / load round-trip ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_save_and_load(self, store: JsonFocusStore):
        state = FocusState(
            topics=["db", "api"],
            current_keywords=["postgres", "fastapi"],
            threshold=0.4,
        )
        await store.save(state)
        loaded = await store.load()
        assert loaded is not None
        assert loaded.topics == ["db", "api"]
        assert loaded.current_keywords == ["postgres", "fastapi"]
        assert loaded.threshold == 0.4

    @pytest.mark.asyncio
    async def test_load_missing_returns_none(self, store: JsonFocusStore):
        assert await store.load() is None

    @pytest.mark.asyncio
    async def test_overwrite(self, store: JsonFocusStore):
        await store.save(FocusState(topics=["v1"]))
        await store.save(FocusState(topics=["v2"], threshold=0.7))
        loaded = await store.load()
        assert loaded is not None
        assert loaded.topics == ["v2"]
        assert loaded.threshold == 0.7

    @pytest.mark.asyncio
    async def test_empty_state(self, store: JsonFocusStore):
        await store.save(FocusState())
        loaded = await store.load()
        assert loaded is not None
        assert loaded.topics == []
        assert loaded.current_keywords == []
        assert loaded.threshold == 0.3

    # ── delete ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete(self, store: JsonFocusStore):
        await store.save(FocusState(topics=["x"]))
        assert await store.load() is not None
        await store.delete()
        assert await store.load() is None

    @pytest.mark.asyncio
    async def test_delete_missing_no_error(self, store: JsonFocusStore):
        # Should not raise when no file exists
        await store.delete()

    # ── properties ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_file_path_property(self, store: JsonFocusStore, tmp_path: Path):
        assert store.file_path == tmp_path

    # ── diagnose ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_diagnose_no_file(self, store: JsonFocusStore):
        diag = store.diagnose()
        assert diag["file_path"] == str(store.file_path)
        assert diag["exists"] is False
        assert diag["file_size"] == 0

    @pytest.mark.asyncio
    async def test_diagnose_with_file(self, store: JsonFocusStore):
        await store.save(FocusState(topics=["hello"]))
        diag = store.diagnose()
        assert diag["exists"] is True
        assert diag["file_size"] > 0

    # ── atomic write ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_atomic_write_no_temp_leak(self, store: JsonFocusStore):
        await store.save(FocusState(topics=["atomic"]))
        parent = store.file_path.parent
        # No .focus_*.json temp files should remain
        tmp_files = list(parent.glob(".focus_*.json"))
        assert len(tmp_files) == 0

    # ── unicode ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_unicode_data(self, store: JsonFocusStore):
        state = FocusState(
            topics=["中文话题", "日本語"],
            current_keywords=["关键词", "データ"],
        )
        await store.save(state)
        loaded = await store.load()
        assert loaded is not None
        assert loaded.topics == state.topics
        assert loaded.current_keywords == state.current_keywords

    # ── corrupted file ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_corrupted_json_returns_none(self, store: JsonFocusStore):
        store.file_path.parent.mkdir(parents=True, exist_ok=True)
        store.file_path.write_text("not json {{{", encoding="utf-8")
        assert await store.load() is None

    # ── parent directory auto-created ─────────────────────────────

    @pytest.mark.asyncio
    async def test_auto_creates_parent_dir(self, tmp_path: Path):
        nested = tmp_path / "sub" / "deep" / "focus.json"
        store = JsonFocusStore(nested)
        await store.save(FocusState(topics=["deep"]))
        assert nested.exists()
        loaded = await store.load()
        assert loaded is not None
        assert loaded.topics == ["deep"]
