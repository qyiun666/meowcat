# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""v1.1.18 SharedStore + Log — shared storage interface + structured logging tests."""

import pytest

from meowcat.storage import SharedStore
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.log import MeowLog


# -- SharedStore ABC -------------------------------------------------------

class TestSharedStoreABC:
    """SharedStore cannot be instantiated directly."""

    def test_abstract(self) -> None:
        with pytest.raises(TypeError):
            SharedStore()  # type: ignore[abstract]


class TestInMemorySharedStore:
    """InMemorySharedStore as concrete SharedStore."""

    def test_is_shared_store(self) -> None:
        store = InMemorySharedStore()
        assert isinstance(store, SharedStore)

    @pytest.mark.anyio
    async def test_get_set_delete(self) -> None:
        store = InMemorySharedStore()
        await store.set("k1", "v1")
        assert await store.get("k1") == "v1"
        await store.delete("k1")
        assert await store.get("k1") is None

    @pytest.mark.anyio
    async def test_list_keys(self) -> None:
        store = InMemorySharedStore()
        await store.set("a", 1)
        await store.set("b", 2)
        keys = await store.list_keys()
        assert sorted(keys) == ["a", "b"]

    @pytest.mark.anyio
    async def test_load_save_merge(self) -> None:
        store = InMemorySharedStore()
        await store.save({"x": 1, "y": 2})
        assert await store.load() == {"x": 1, "y": 2}

        result = await store.merge({"z": 3})
        assert result == {"x": 1, "y": 2, "z": 3}

    @pytest.mark.anyio
    async def test_watch(self) -> None:
        import asyncio
        store = InMemorySharedStore()
        watcher = store.watch("ns/")
        # Start watcher first, then trigger change
        task = asyncio.ensure_future(watcher.__anext__())
        await asyncio.sleep(0)  # let watcher start waiting
        await store.set("ns/key1", "val1")
        item = await asyncio.wait_for(task, timeout=1.0)
        assert item == ("ns/key1", "val1")

    @pytest.mark.anyio
    async def test_set_overwrite(self) -> None:
        store = InMemorySharedStore()
        await store.set("k", 1)
        await store.set("k", 2)
        assert await store.get("k") == 2


# -- MeowLog ---------------------------------------------------------------

class TestMeowLog:
    """Structured logger with pluggable handlers."""

    def test_get_singleton(self) -> None:
        a = MeowLog.get("test.a")
        b = MeowLog.get("test.a")
        assert a is b

    def test_get_different_names(self) -> None:
        a = MeowLog.get("test.x")
        b = MeowLog.get("test.y")
        assert a is not b

    def test_debug_info_warning_error_no_crash(self) -> None:
        log = MeowLog.get("test.level")
        # Should not raise
        log.debug("debug msg", key="val")
        log.info("info msg", key="val")
        log.warning("warn msg", key="val")
        log.error("error msg", key="val")

    def test_plug_handler_called(self) -> None:
        captured: list[dict] = []

        def capture(entry: dict) -> None:
            captured.append(entry)

        MeowLog.plug_handler(capture)
        log = MeowLog.get("test.handler")
        log.info("handler_test", extra="data")

        assert len(captured) == 1
        entry = captured[0]
        assert entry["level"] == "INFO"
        assert entry["message"] == "handler_test"
        assert entry["data"] == {"extra": "data"}
        assert entry["logger"] == "test.handler"
        assert "timestamp" in entry

        MeowLog.clear_handlers()

    def test_clear_handlers(self) -> None:
        captured: list[dict] = []

        def capture(entry: dict) -> None:
            captured.append(entry)

        MeowLog.plug_handler(capture)
        MeowLog.clear_handlers()
        log = MeowLog.get("test.clear")
        log.info("should_not_capture")
        assert len(captured) == 0

    def test_handler_exception_does_not_crash(self) -> None:
        def bad_handler(entry: dict) -> None:
            raise RuntimeError("boom")

        MeowLog.plug_handler(bad_handler)
        log = MeowLog.get("test.bad")
        # Should not raise despite handler failure
        log.info("survives")
        MeowLog.clear_handlers()

    def test_structured_data(self) -> None:
        log = MeowLog.get("test.struct")
        log.info("user_action", user="alice", action="login", count=42)


# -- Import smoke test -----------------------------------------------------

class TestImportSmoke:
    """Verify v1.1.18 exports are reachable from meowcat."""

    def test_shared_store_import(self) -> None:
        from meowcat import SharedStore as S  # noqa: F811
        assert S is SharedStore

    def test_meow_log_import(self) -> None:
        from meowcat import MeowLog as M  # noqa: F811
        assert M is MeowLog

