# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""PeriodicScheduler — interval/cron-based background task scheduler.

T-21 (v1.3.6): Framework-level base class for periodic maintenance tasks.
Any Agent needs background upkeep (memory decay, index rebuild, etc.).
The scheduler supports interval-based and cron-based task registration
with start/stop lifecycle integration.

Usage::

    scheduler = PeriodicScheduler(tick_interval=1.0)

    # Register interval-based tasks
    scheduler.register("decay", "maintenance", interval=300)   # every 5 min
    scheduler.register("cleanup", "maintenance", interval=3600) # every hour

    # Register cron-based tasks (app layer provides cron parser)
    scheduler.register("daily", "diagnostic", cron="0 3 * * *")

    # Lifecycle: start/stop
    await scheduler.start(cat)
    ...
    await scheduler.stop()

Cron expressions are stored as opaque strings by default.  App layer can
override ``_parse_cron()`` to provide cron parsing (e.g. via ``croniter``).
If cron parsing is not available, cron-based tasks are skipped with a
debug log.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class PeriodicConfig:
    """Periodic scheduler configuration.

    Attributes:
        tick_interval:   How often (seconds) the scheduler checks
                         whether any task is due.
        max_concurrent:  Maximum number of tasks that may execute
                         concurrently.
    """

    tick_interval: float = 1.0
    max_concurrent: int = 5


# ── PeriodicTask ───────────────────────────────────────────────────────


@dataclass
class PeriodicTask:
    """A single scheduled task definition.

    Attributes:
        name:       Unique task name within the scheduler.
        loop_name:  Name of the loop to execute (via ``cat.run_loop()``).
        interval:   Interval in seconds (mutually exclusive with *cron*).
        cron:       Cron expression string (mutually exclusive with
                    *interval*).  Parsing is delegated to the app layer
                    via ``_parse_cron()``.
        enabled:    Whether this task is currently active.
        last_run:   Monotonic timestamp of last execution (internal,
                    set by the scheduler).
        run_count:  Total number of times this task has been executed
                    (internal counter).
    """

    name: str
    loop_name: str
    interval: float | None = None
    cron: str | None = None
    enabled: bool = True
    last_run: float | None = None
    run_count: int = 0


# ── PeriodicScheduler ──────────────────────────────────────────────────


class PeriodicScheduler:
    """Background periodic task scheduler base class.

    Manages a collection of :class:`PeriodicTask` entries and runs a
    background tick loop that dispatches due tasks to the cat's loop
    registry.

    Lifecycle::

        register()  →  start(cat)  →  [tick loop runs]  →  stop()

    Tasks are dispatched **asynchronously** — multiple tasks may run
    concurrently, capped by ``max_concurrent``.  If a task raises an
    exception it is logged and the scheduler continues.

    App layer can override:

    - ``_parse_cron(expr)`` for cron expression support.
    - ``_is_due(task, now)`` for custom scheduling logic.
    - ``_execute(task, cat)`` for custom dispatch behaviour.
    - ``_on_error(task, exc)`` for custom error handling.
    """

    def __init__(
        self,
        tick_interval: float = 1.0,
        max_concurrent: int = 5,
    ) -> None:
        self._config = PeriodicConfig(
            tick_interval=tick_interval,
            max_concurrent=max_concurrent,
        )
        self._tasks: dict[str, PeriodicTask] = {}
        self._running: bool = False
        self._task: asyncio.Task[Any] | None = None
        self._sem: asyncio.Semaphore | None = None
        self._inflight: set[asyncio.Task[Any]] = set()

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> PeriodicConfig:
        """Current scheduler configuration (read-only copy)."""
        return PeriodicConfig(
            tick_interval=self._config.tick_interval,
            max_concurrent=self._config.max_concurrent,
        )

    @property
    def running(self) -> bool:
        """Whether the scheduler background loop is active."""
        return self._running

    # ── Task registration ──────────────────────────────────────────

    def register(
        self,
        name: str,
        loop_name: str,
        *,
        interval: float | None = None,
        cron: str | None = None,
        enabled: bool = True,
    ) -> PeriodicTask:
        """Register a periodic task.

        Args:
            name:       Unique task name.
            loop_name:  Name of the loop to execute via
                        ``cat.run_loop(loop_name)``.
            interval:   Interval in seconds.  Mutually exclusive
                        with *cron*.
            cron:       Cron expression string.  Mutually exclusive
                        with *interval*.
            enabled:    Whether the task starts active.

        Returns:
            The registered :class:`PeriodicTask`.

        Raises:
            ValueError: Both *interval* and *cron* are ``None``, or
                        both are provided.
        """
        if interval is None and cron is None:
            raise ValueError(
                f"Task '{name}': must provide either interval or cron"
            )
        if interval is not None and cron is not None:
            raise ValueError(
                f"Task '{name}': interval and cron are mutually exclusive"
            )

        task = PeriodicTask(
            name=name,
            loop_name=loop_name,
            interval=interval,
            cron=cron,
            enabled=enabled,
        )
        self._tasks[name] = task
        return task

    def unregister(self, name: str) -> PeriodicTask | None:
        """Remove a task from the scheduler.

        Args:
            name:  Task name.

        Returns:
            The removed :class:`PeriodicTask`, or ``None`` if not found.
        """
        return self._tasks.pop(name, None)

    def get(self, name: str) -> PeriodicTask | None:
        """Look up a registered task by name."""
        return self._tasks.get(name)

    def list_tasks(self) -> list[PeriodicTask]:
        """Return all registered tasks."""
        return list(self._tasks.values())

    # ── Lifecycle ──────────────────────────────────────────────────

    async def start(self, cat: Any) -> None:
        """Start the background scheduling loop.

        Must be called after all tasks are registered.  The scheduler
        begins checking tasks at *tick_interval* and dispatching due
        tasks via ``cat.run_loop()``.

        Safe to call multiple times (idempotent).

        Args:
            cat:  A CatBase instance providing ``run_loop(name)``.
        """
        if self._running:
            return

        self._running = True
        self._sem = asyncio.Semaphore(self._config.max_concurrent)
        self._task = asyncio.ensure_future(self._run_loop(cat))

    async def stop(self) -> None:
        """Stop the scheduler background loop.

        Cancels the tick loop and waits for in-flight tasks to drain.
        Safe to call multiple times (idempotent).
        """
        if not self._running:
            return

        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Wait for all in-flight dispatches to complete
        if self._inflight:
            await asyncio.gather(*self._inflight, return_exceptions=True)
            self._inflight.clear()

        self._sem = None

    # ── Background tick loop ───────────────────────────────────────

    async def _run_loop(self, cat: Any) -> None:
        """Background loop: tick and dispatch due tasks."""
        while self._running:
            try:
                now = time.monotonic()
                for task in list(self._tasks.values()):
                    if not task.enabled:
                        continue
                    if self._is_due(task, now):
                        task.last_run = now
                        task.run_count += 1
                        # Dispatch asynchronously (fire-and-forget
                        # with concurrency limit); keep reference
                        # for clean shutdown
                        t = asyncio.ensure_future(
                            self._dispatch(task, cat)
                        )
                        self._inflight.add(t)
                        t.add_done_callback(self._inflight.discard)
            except Exception:
                _log.debug(
                    "PeriodicScheduler tick error", exc_info=True,
                )

            await asyncio.sleep(self._config.tick_interval)

    async def _dispatch(self, task: PeriodicTask, cat: Any) -> None:
        """Dispatch a single task (runs under semaphore for concurrency
        control).
        """
        if self._sem is None:
            return
        async with self._sem:
            try:
                await self._execute(task, cat)
            except Exception as exc:
                self._on_error(task, exc)

    # ── Due-check (overridable) ────────────────────────────────────

    def _is_due(self, task: PeriodicTask, now: float) -> bool:
        """Check whether a task is due for execution.

        Framework default supports:

        - **interval**:  ``now - last_run >= interval`` (or *last_run*
          is ``None`` → execute immediately on first tick).
        - **cron**:      Delegates to ``_parse_cron()``.

        Override for custom scheduling logic.
        """
        if task.interval is not None:
            if task.last_run is None:
                return True
            return (now - task.last_run) >= task.interval

        if task.cron is not None:
            return self._check_cron(task, now)

        return False

    # ── Cron support (overridable) ─────────────────────────────────

    def _check_cron(self, task: PeriodicTask, now: float) -> bool:
        """Check whether a cron-based task is due.

        Framework default returns ``False`` (cron not supported without
        app-layer parser).  Override ``_parse_cron()`` and this method
        for cron support::

            class MyScheduler(PeriodicScheduler):
                def _parse_cron(self, expr):
                    import croniter
                    return croniter.croniter(expr)

                def _check_cron(self, task, now):
                    it = self._parse_cron(task.cron)
                    ...
        """
        return False

    def _parse_cron(self, expr: str) -> Any:
        """Parse a cron expression.  Override to provide cron parsing.

        Framework default raises :exc:`NotImplementedError`.
        App layer can use ``croniter`` or any cron library.
        """
        raise NotImplementedError(
            "Cron support requires a cron parser. "
            "Install 'croniter' and override _parse_cron()."
        )

    # ── Execution (overridable) ────────────────────────────────────

    async def _execute(self, task: PeriodicTask, cat: Any) -> None:
        """Execute a due task via ``cat.run_loop()``.

        Override to customise dispatch behaviour (e.g. pass extra
        kwargs, use a different execution method).
        """
        await cat.run_loop(task.loop_name)

    # ── Error handling (overridable) ───────────────────────────────

    def _on_error(self, task: PeriodicTask, exc: Exception) -> None:
        """Handle a task execution error.

        Framework default logs at warning level.  Override for
        custom error handling (circuit-breaker, alerts, etc.).
        """
        _log.warning(
            "PeriodicScheduler task '%s' (loop=%s) failed: %s",
            task.name, task.loop_name, exc,
        )

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "tick_interval": self._config.tick_interval,
            "max_concurrent": self._config.max_concurrent,
            "running": self._running,
            "task_count": len(self._tasks),
            "tasks": [
                {
                    "name": t.name,
                    "loop_name": t.loop_name,
                    "interval": t.interval,
                    "cron": t.cron,
                    "enabled": t.enabled,
                    "last_run": t.last_run,
                    "run_count": t.run_count,
                }
                for t in self._tasks.values()
            ],
        }
