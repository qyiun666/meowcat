# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""
v1.3.6 — PeriodicScheduler 全覆盖测试
======================================

验证:
    1. TestPeriodicConfig              — PeriodicConfig dataclass 字段
    2. TestPeriodicTaskInit            — PeriodicTask 构造 + 默认值
    3. TestPeriodicSchedulerInit       — PeriodicScheduler 构造 + 默认值
    4. TestTaskRegister                — register() 注册任务
    5. TestTaskUnregister              — unregister() 移除
    6. TestTaskRegisterValidation      — register() 参数校验
    7. TestTaskGetList                 — get() / list_tasks()
    8. TestIsDueInterval               — _is_due() interval 判定
    9. TestIsDueFirstRun               — _is_due() 首次执行
   10. TestIsDueCronDisabled           — _is_due() cron 默认返回 False
   11. TestSchedulerLifecycle          — start() / stop() 生命周期
   12. TestSchedulerIdempotent         — start/stop 幂等
   13. TestTaskExecution               — 任务实际执行
   14. TestTaskDisabled                — 禁用的任务不执行
   15. TestTaskErrorHandling           — 异常处理不崩溃
   16. TestConcurrencyLimit            — max_concurrent 并发限制
   17. TestRunCountIncrement           — run_count 递增
   18. TestDiagnose                    — diagnose() 快照
   19. TestOverrideIsDue               — 子类覆盖 _is_due()
   20. TestOverrideExecute             — 子类覆盖 _execute()
"""

from __future__ import annotations

import asyncio
import time

import pytest

from meowcat.scheduler import PeriodicConfig, PeriodicScheduler, PeriodicTask

# ── 1. PeriodicConfig ───────────────────────────────────────────────────

class TestPeriodicConfig:
    """PeriodicConfig dataclass 字段。"""

    def test_default_fields(self) -> None:
        cfg = PeriodicConfig()
        assert cfg.tick_interval == 1.0
        assert cfg.max_concurrent == 5

    def test_custom_fields(self) -> None:
        cfg = PeriodicConfig(tick_interval=0.5, max_concurrent=10)
        assert cfg.tick_interval == 0.5
        assert cfg.max_concurrent == 10


# ── 2. PeriodicTask ─────────────────────────────────────────────────────

class TestPeriodicTaskInit:
    """PeriodicTask 构造 + 默认值。"""

    def test_default_fields(self) -> None:
        t = PeriodicTask(name="test", loop_name="maintenance", interval=60.0)
        assert t.name == "test"
        assert t.loop_name == "maintenance"
        assert t.interval == 60.0
        assert t.cron is None
        assert t.enabled is True
        assert t.last_run is None
        assert t.run_count == 0

    def test_cron_task(self) -> None:
        t = PeriodicTask(name="daily", loop_name="diagnostic",
                         cron="0 3 * * *")
        assert t.interval is None
        assert t.cron == "0 3 * * *"

    def test_disabled_task(self) -> None:
        t = PeriodicTask(
            name="off", loop_name="x", interval=10.0, enabled=False,
        )
        assert t.enabled is False

    def test_with_last_run(self) -> None:
        t = PeriodicTask(
            name="x", loop_name="y", interval=5.0, last_run=100.0,
            run_count=3,
        )
        assert t.last_run == 100.0
        assert t.run_count == 3


# ── 3. PeriodicScheduler Init ───────────────────────────────────────────

class TestPeriodicSchedulerInit:
    """PeriodicScheduler 构造 + 默认值。"""

    def test_default_construction(self) -> None:
        s = PeriodicScheduler()
        assert s.config.tick_interval == 1.0
        assert s.config.max_concurrent == 5
        assert s.running is False
        assert s.list_tasks() == []

    def test_custom_construction(self) -> None:
        s = PeriodicScheduler(tick_interval=0.5, max_concurrent=3)
        assert s.config.tick_interval == 0.5
        assert s.config.max_concurrent == 3

    def test_config_is_readonly_copy(self) -> None:
        s = PeriodicScheduler(tick_interval=2.0)
        cfg = s.config
        cfg.tick_interval = 99.0  # type: ignore[misc]
        assert s.config.tick_interval == 2.0


# ── 4. Register ─────────────────────────────────────────────────────────

class TestTaskRegister:
    """register() 注册任务。"""

    def test_register_interval(self) -> None:
        s = PeriodicScheduler()
        t = s.register("cleanup", "maintenance", interval=300.0)
        assert t.name == "cleanup"
        assert t.loop_name == "maintenance"
        assert t.interval == 300.0
        assert s.get("cleanup") is t

    def test_register_cron(self) -> None:
        s = PeriodicScheduler()
        t = s.register("daily", "diagnostic", cron="0 3 * * *")
        assert t.cron == "0 3 * * *"
        assert t.interval is None

    def test_register_disabled(self) -> None:
        s = PeriodicScheduler()
        t = s.register("off", "x", interval=10.0, enabled=False)
        assert t.enabled is False

    def test_register_overwrite(self) -> None:
        s = PeriodicScheduler()
        s.register("a", "loop1", interval=60.0)
        s.register("a", "loop2", interval=120.0)
        assert s.get("a").loop_name == "loop2"  # type: ignore[union-attr]
        assert s.get("a").interval == 120.0  # type: ignore[union-attr]

    def test_list_after_register(self) -> None:
        s = PeriodicScheduler()
        s.register("a", "l1", interval=10.0)
        s.register("b", "l2", interval=20.0)
        tasks = s.list_tasks()
        assert len(tasks) == 2
        names = {t.name for t in tasks}
        assert names == {"a", "b"}


# ── 5. Unregister ───────────────────────────────────────────────────────

class TestTaskUnregister:
    """unregister() 移除。"""

    def test_unregister_existing(self) -> None:
        s = PeriodicScheduler()
        s.register("a", "l1", interval=10.0)
        removed = s.unregister("a")
        assert removed is not None
        assert removed.name == "a"
        assert s.get("a") is None
        assert s.list_tasks() == []

    def test_unregister_non_existent(self) -> None:
        s = PeriodicScheduler()
        assert s.unregister("nx") is None


# ── 6. Register Validation ──────────────────────────────────────────────

class TestTaskRegisterValidation:
    """register() 参数校验。"""

    def test_neither_interval_nor_cron(self) -> None:
        s = PeriodicScheduler()
        with pytest.raises(ValueError, match="must provide either"):
            s.register("bad", "loop")

    def test_both_interval_and_cron(self) -> None:
        s = PeriodicScheduler()
        with pytest.raises(ValueError, match="mutually exclusive"):
            s.register("bad", "loop", interval=10.0, cron="* * * * *")


# ── 7. Get / List ───────────────────────────────────────────────────────

class TestTaskGetList:
    """get() / list_tasks()。"""

    def test_get_existing(self) -> None:
        s = PeriodicScheduler()
        s.register("a", "l1", interval=10.0)
        assert s.get("a") is not None

    def test_get_non_existent(self) -> None:
        s = PeriodicScheduler()
        assert s.get("nx") is None

    def test_list_empty(self) -> None:
        s = PeriodicScheduler()
        assert s.list_tasks() == []

    def test_list_preserves_order_hint(self) -> None:
        s = PeriodicScheduler()
        s.register("z", "lz", interval=1.0)
        s.register("a", "la", interval=2.0)
        names = [t.name for t in s.list_tasks()]
        assert names == ["z", "a"]


# ── 8. _is_due — interval ──────────────────────────────────────────────

class TestIsDueInterval:
    """_is_due() interval 判定。"""

    def test_due_when_elapsed(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", interval=5.0,
                         last_run=0.0)
        assert s._is_due(t, now=6.0) is True

    def test_not_due_when_within_interval(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", interval=5.0,
                         last_run=0.0)
        assert s._is_due(t, now=4.0) is False

    def test_exactly_at_boundary(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", interval=5.0,
                         last_run=0.0)
        assert s._is_due(t, now=5.0) is True

    def test_zero_interval(self) -> None:
        """Zero interval → always due (every tick)."""
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", interval=0.0,
                         last_run=100.0)
        assert s._is_due(t, now=100.0) is True


# ── 9. _is_due — first run ─────────────────────────────────────────────

class TestIsDueFirstRun:
    """_is_due() 首次执行（last_run=None）。"""

    def test_first_run_is_due(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", interval=60.0)
        assert s._is_due(t, now=0.0) is True

    def test_first_run_cron_still_false(self) -> None:
        """Cron tasks are NOT automatically due (no parser)."""
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", cron="* * * * *")
        assert s._is_due(t, now=0.0) is False


# ── 10. _is_due — cron disabled ────────────────────────────────────────

class TestIsDueCronDisabled:
    """_is_due() cron 默认返回 False。"""

    def test_cron_default_never_due(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", cron="0 * * * *")
        assert s._is_due(t, now=0.0) is False
        assert s._is_due(t, now=9999.0) is False

    def test_parse_cron_raises(self) -> None:
        s = PeriodicScheduler()
        with pytest.raises(NotImplementedError):
            s._parse_cron("* * * * *")

    def test_cron_not_due_after_first_run(self) -> None:
        s = PeriodicScheduler()
        t = PeriodicTask(name="x", loop_name="l", cron="* * * * *",
                         last_run=0.0, run_count=1)
        assert s._is_due(t, now=99999.0) is False


# ── 11. Lifecycle ──────────────────────────────────────────────────────

class TestSchedulerLifecycle:
    """start() / stop() 生命周期。"""

    @pytest.mark.anyio
    async def test_start_sets_running(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()

        await s.start(cat)
        assert s.running is True

        await s.stop()
        assert s.running is False

    @pytest.mark.anyio
    async def test_stop_when_not_running(self) -> None:
        s = PeriodicScheduler()
        await s.stop()  # Should not raise
        assert s.running is False

    @pytest.mark.anyio
    async def test_start_idempotent(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()
        await s.start(cat)
        await s.start(cat)  # second start should be no-op
        assert s.running is True
        await s.stop()


# ── 12. Scheduler Idempotent ───────────────────────────────────────────

class TestSchedulerIdempotent:
    """start/stop 幂等。"""

    @pytest.mark.anyio
    async def test_multiple_stop_safe(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()
        await s.start(cat)
        await s.stop()
        await s.stop()  # Should be safe
        await s.stop()
        assert s.running is False

    @pytest.mark.anyio
    async def test_start_stop_start(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()
        await s.start(cat)
        await s.stop()
        await s.start(cat)
        assert s.running is True
        await s.stop()


# ── 13. Task Execution ─────────────────────────────────────────────────

class TestTaskExecution:
    """任务实际执行。"""

    @pytest.mark.anyio
    async def test_task_runs(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FakeCat()
        s.register("test", "maintenance", interval=0.05)

        await s.start(cat)
        await cat.wait_for_runs(1, timeout=1.0)
        await s.stop()

        assert cat.call_count >= 1

    @pytest.mark.anyio
    async def test_task_runs_multiple_times(self) -> None:
        s = PeriodicScheduler(tick_interval=0.02)
        cat = _FakeCat()
        s.register("t", "loop", interval=0.04)

        await s.start(cat)
        await cat.wait_for_runs(2, timeout=1.0)
        await s.stop()

        # Should have run at least 2 times
        assert cat.call_count >= 2

    @pytest.mark.anyio
    async def test_correct_loop_called(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FakeCat()
        s.register("cleanup", "maintenance", interval=0.05)
        s.register("diag", "diagnostic", interval=0.06)

        await s.start(cat)
        await cat.wait_for_runs(2, timeout=1.0)
        await s.stop()

        assert "maintenance" in cat.called_loops
        assert "diagnostic" in cat.called_loops


# ── 14. Disabled Task ──────────────────────────────────────────────────

class TestTaskDisabled:
    """禁用的任务不执行。"""

    @pytest.mark.anyio
    async def test_disabled_task_not_run(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FakeCat()
        s.register("off", "loop", interval=0.05, enabled=False)

        await s.start(cat)
        for _ in range(3):
            await asyncio.sleep(0)  # yield control, let scheduler tick
        await s.stop()

        assert cat.call_count == 0

    @pytest.mark.anyio
    async def test_enable_after_registration(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FakeCat()
        t = s.register("t", "loop", interval=0.05, enabled=False)

        # Enable and start
        t.enabled = True
        await s.start(cat)
        await cat.wait_for_runs(1, timeout=1.0)
        await s.stop()

        assert cat.call_count >= 1


# ── 15. Error Handling ─────────────────────────────────────────────────

class TestTaskErrorHandling:
    """异常处理不崩溃。"""

    @pytest.mark.anyio
    async def test_failing_task_does_not_crash_scheduler(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FailingCat()
        s.register("bad", "loop", interval=0.05)

        await s.start(cat)
        await asyncio.sleep(0.2)  # brief wait for scheduler cycles
        # Scheduler should still be running
        assert s.running is True
        await s.stop()

    @pytest.mark.anyio
    async def test_one_failing_does_not_block_others(self) -> None:
        """One task failing should not prevent other tasks from running."""
        s = PeriodicScheduler(tick_interval=0.03)
        exec_count = 0
        event = asyncio.Event()

        class MixedCat:
            async def run_loop(self, name):
                nonlocal exec_count
                if name == "bad":
                    raise RuntimeError("boom")
                exec_count += 1
                event.set()

        cat = MixedCat()
        s.register("bad", "bad", interval=0.03)
        s.register("good", "good", interval=0.03)

        await s.start(cat)
        try:
            await asyncio.wait_for(event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        await s.stop()

        assert exec_count >= 1  # good task ran despite bad task errors


# ── 16. Concurrency Limit ──────────────────────────────────────────────

class TestConcurrencyLimit:
    """max_concurrent 并发限制。"""

    @pytest.mark.anyio
    async def test_semaphore_limits_concurrency(self) -> None:
        s = PeriodicScheduler(tick_interval=0.02, max_concurrent=2)
        concurrent = 0
        max_seen = 0

        class SlowCat:
            async def run_loop(self, name):
                nonlocal concurrent, max_seen
                concurrent += 1
                max_seen = max(max_seen, concurrent)
                await asyncio.sleep(0.05)
                concurrent -= 1

        cat = SlowCat()
        # Register many fast tasks to trigger concurrency
        for i in range(8):
            s.register(f"t{i}", "loop", interval=0.01)

        await s.start(cat)
        await asyncio.sleep(0.2)
        await s.stop()

        # With max_concurrent=2, should never exceed 2
        assert max_seen <= 2


# ── 17. Run Count ──────────────────────────────────────────────────────

class TestRunCountIncrement:
    """run_count 递增。"""

    @pytest.mark.anyio
    async def test_run_count_increments(self) -> None:
        s = PeriodicScheduler(tick_interval=0.02)
        cat = _FakeCat()
        s.register("t", "loop", interval=0.03)

        await s.start(cat)
        await cat.wait_for_runs(2, timeout=1.0)
        await s.stop()

        task = s.get("t")
        assert task is not None
        assert task.run_count >= 2

    @pytest.mark.anyio
    async def test_last_run_updated(self) -> None:
        s = PeriodicScheduler(tick_interval=0.05)
        cat = _FakeCat()
        s.register("t", "loop", interval=0.05)

        await s.start(cat)
        await cat.wait_for_runs(1, timeout=1.0)
        await s.stop()

        task = s.get("t")
        assert task is not None
        assert task.last_run is not None
        assert task.last_run > 0.0


# ── 18. Diagnose ───────────────────────────────────────────────────────

class TestDiagnose:
    """diagnose() 快照。"""

    def test_initial_diagnose(self) -> None:
        s = PeriodicScheduler(tick_interval=0.5, max_concurrent=3)
        d = s.diagnose()
        assert d["tick_interval"] == 0.5
        assert d["max_concurrent"] == 3
        assert d["running"] is False
        assert d["task_count"] == 0
        assert d["tasks"] == []

    def test_diagnose_with_tasks(self) -> None:
        s = PeriodicScheduler()
        s.register("a", "l1", interval=60.0)
        s.register("b", "l2", cron="0 * * * *")
        d = s.diagnose()
        assert d["task_count"] == 2
        assert len(d["tasks"]) == 2
        names = {t["name"] for t in d["tasks"]}
        assert names == {"a", "b"}

    @pytest.mark.anyio
    async def test_diagnose_shows_running(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()
        await s.start(cat)
        d = s.diagnose()
        assert d["running"] is True
        await s.stop()

    @pytest.mark.anyio
    async def test_diagnose_task_fields(self) -> None:
        s = PeriodicScheduler()
        cat = _FakeCat()
        s.register("t", "loop", interval=0.03)
        await s.start(cat)
        await cat.wait_for_runs(1, timeout=1.0)
        await s.stop()

        d = s.diagnose()
        tinfo = d["tasks"][0]
        assert tinfo["name"] == "t"
        assert tinfo["loop_name"] == "loop"
        assert tinfo["interval"] == 0.03
        assert tinfo["cron"] is None
        assert tinfo["enabled"] is True
        assert tinfo["last_run"] is not None
        assert tinfo["run_count"] >= 1


# ── 19. Override _is_due ───────────────────────────────────────────────

class TestOverrideIsDue:
    """子类覆盖 _is_due()。"""

    @pytest.mark.anyio
    async def test_custom_is_due(self) -> None:
        call_log: list[str] = []

        class CustomScheduler(PeriodicScheduler):
            def _is_due(self, task, now):
                call_log.append(task.name)
                # Every 3rd tick
                return task.run_count < 3

        s = CustomScheduler(tick_interval=0.02)
        cat = _FakeCat()
        s.register("t", "loop", interval=0.0)  # interval ignored

        await s.start(cat)
        await cat.wait_for_runs(3, timeout=1.0)
        await s.stop()

        # _is_due was called (at least a few times)
        assert len(call_log) >= 3
        # Task ran exactly 3 times (run_count < 3)
        task = s.get("t")
        assert task is not None
        assert task.run_count == 3


# ── 20. Override _execute ──────────────────────────────────────────────

class TestOverrideExecute:
    """子类覆盖 _execute()。"""

    @pytest.mark.anyio
    async def test_custom_execute(self) -> None:
        exec_log: list[str] = []

        class CustomScheduler(PeriodicScheduler):
            async def _execute(self, task, cat):
                exec_log.append(f"{task.name}:{task.loop_name}")

        s = CustomScheduler(tick_interval=0.03)
        cat = _FakeCat()
        s.register("test", "maintenance", interval=0.03)

        await s.start(cat)
        await asyncio.sleep(0.1)  # brief wait for scheduler tick
        await s.stop()

        assert len(exec_log) >= 1
        assert exec_log[0] == "test:maintenance"
        # FakeCat should NOT have been called (we overrode _execute)
        assert cat.call_count == 0


# ── Helpers ─────────────────────────────────────────────────────────────


class _FakeCat:
    """Minimal cat stub for scheduler testing."""

    def __init__(self) -> None:
        self.call_count = 0
        self.called_loops: list[str] = []
        self.event: asyncio.Event = asyncio.Event()

    async def run_loop(self, name: str, **kwargs: object) -> dict[str, object]:
        self.call_count += 1
        self.called_loops.append(name)
        self.event.set()
        return {"ok": True}

    async def wait_for_runs(self, n: int = 1, *, timeout: float = 1.0) -> None:
        """Wait for at least n run_loop calls, with timeout."""
        deadline = time.monotonic() + timeout
        while self.call_count < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return  # timeout — test assertions will catch insufficient calls
            self.event.clear()
            try:
                await asyncio.wait_for(self.event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                return


class _FailingCat:
    """Cat stub that always raises."""

    async def run_loop(self, name: str, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("simulated failure")
