# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat worker subsystem — resumable worker abstraction (v1.1.29).

Provides :class:`BaseWorker` and :class:`CheckpointStore` for long-running,
restartable task execution. Workers represent individual units of work
that can be paused, checkpointed, and resumed across process restarts.

Framework-layer: defines the worker lifecycle + checkpoint interface.
App-layer: implements concrete task logic and persistence backends.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# -- Worker status -----------------------------------------------------------

class WorkerStatus(Enum):
    """Worker lifecycle status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkerState:
    """Serializable worker state for checkpoint/restore."""
    worker_id: str
    status: WorkerStatus = WorkerStatus.IDLE
    task_id: str = ""
    progress: float = 0.0
    checkpoint: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0


# -- Checkpoint store ---------------------------------------------------------

class CheckpointStore(ABC):
    """Abstract checkpoint persistence for workers.

    Framework-layer: defines the interface.
    App-layer: plugs in concrete storage (file, SQLite, Redis, etc.).
    """

    @abstractmethod
    async def save(self, state: WorkerState) -> None:
        """Persist worker state as a checkpoint."""

    @abstractmethod
    async def load(self, worker_id: str) -> WorkerState | None:
        """Load last checkpoint for a worker, or None."""

    @abstractmethod
    async def delete(self, worker_id: str) -> None:
        """Remove checkpoint for a worker."""

    @abstractmethod
    async def list_all(self) -> list[str]:
        """List all checkpointed worker IDs."""


class InMemoryCheckpointStore(CheckpointStore):
    """In-memory checkpoint store — default for development/testing."""

    def __init__(self) -> None:
        self._store: dict[str, WorkerState] = {}

    async def save(self, state: WorkerState) -> None:
        state.updated_at = time.time()
        self._store[state.worker_id] = state

    async def load(self, worker_id: str) -> WorkerState | None:
        return self._store.get(worker_id)

    async def delete(self, worker_id: str) -> None:
        self._store.pop(worker_id, None)

    async def list_all(self) -> list[str]:
        return list(self._store.keys())


# -- Base worker --------------------------------------------------------------

class BaseWorker(ABC):
    """Abstract resumable worker.

    Workers execute tasks with checkpoint support. If a task fails or the
    process restarts, the worker can resume from the last checkpoint.

    v1.2.22: Added priority, depends_on, max_retries for scheduler support.

    .. note:: (v1.2.33)

        Maintains its own ``_hooks`` / ``register_hook()`` / lifecycle hook
        pattern that duplicates :class:`meowcat.pluggable.Pluggable`.
        Migration tracked in roadmap B31.

    Usage::

        class MyWorker(BaseWorker):
            async def execute_step(self, step: dict) -> Any:
                # do work, return result
                return {"done": True}

        worker = MyWorker(worker_id="w1", store=InMemoryCheckpointStore())
        await worker.run(task_id="t1", steps=[{"n": 1}, {"n": 2}])
    """

    def __init__(
        self,
        worker_id: str = "",
        *,
        store: CheckpointStore | None = None,
        priority: int = 0,
        depends_on: list[str] | None = None,
        max_retries: int = 0,
    ) -> None:
        self.worker_id = worker_id or _new_worker_id()
        self.store = store or InMemoryCheckpointStore()
        self.state = WorkerState(worker_id=self.worker_id)
        self.priority = priority
        self.depends_on = depends_on or []
        self.max_retries = max_retries

        # Pluggable hooks
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    # -- Plugin system ---------------------------------------------------

    def plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """Register a lifecycle hook."""
        self._hooks.setdefault(hook, []).append(fn)

    def unplug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """Unregister lifecycle hook(s)."""
        if hook not in self._hooks:
            return
        if fn is None:
            self._hooks.pop(hook, None)
        else:
            self._hooks[hook] = [f for f in self._hooks[hook] if f is not fn]

    # -- Subclass interface -----------------------------------------------

    @abstractmethod
    async def execute_step(self, step: dict[str, Any]) -> Any:
        """Execute one step. Subclass implements concrete logic."""

    # -- Lifecycle --------------------------------------------------------

    async def run(
        self,
        task_id: str,
        steps: list[dict[str, Any]],
        *,
        resume: bool = False,
    ) -> WorkerState:
        """Run all steps, checkpointing after each.

        Args:
            task_id: Unique task identifier.
            steps: Ordered list of step payloads.
            resume: If True, try to resume from last checkpoint.

        Returns:
            Final worker state.

        If max_retries > 0 and the task fails, it will be retried up to
        max_retries times before finally failing.
        """
        remaining_retries = self.max_retries

        while True:
            try:
                return await self._run_once(task_id, steps, resume=resume)
            except Exception:
                if remaining_retries <= 0:
                    raise
                remaining_retries -= 1
                logger.warning(
                    "Worker %s task %s failed, retrying (%d left)",
                    self.worker_id, task_id, remaining_retries,
                )
                # Reset state for retry
                self.state.checkpoint.clear()
                self.state.progress = 0.0
                self.state.error = ""

    async def _run_once(
        self,
        task_id: str,
        steps: list[dict[str, Any]],
        *,
        resume: bool = False,
    ) -> WorkerState:
        # Try resume
        if resume:
            saved = await self.store.load(self.worker_id)
            if saved is not None and saved.status in (
                WorkerStatus.PAUSED, WorkerStatus.RUNNING,
            ):
                self.state = saved
                completed_steps = int(self.state.progress)
                steps = steps[completed_steps:]
                logger.info("Worker %s resumed at step %d",
                            self.worker_id, completed_steps)

        self.state.task_id = task_id
        self.state.status = WorkerStatus.RUNNING
        self.state.started_at = time.time()
        self._fire("on_start", self.state)

        total = len(steps)
        try:
            for i, step in enumerate(steps):
                self.state.checkpoint["current_step"] = step
                result = await self.execute_step(step)
                self.state.checkpoint[f"step_{i}"] = result
                self.state.progress = float(i + 1)
                await self.store.save(self.state)
                self._fire("on_step", self.state, step, result)

            self.state.status = WorkerStatus.COMPLETED
            self.state.progress = float(total)
            self._fire("on_complete", self.state)

        except Exception as exc:
            self.state.status = WorkerStatus.FAILED
            self.state.error = str(exc)
            await self.store.save(self.state)
            self._fire("on_error", self.state, exc)
            logger.exception("Worker %s failed at step %d",
                             self.worker_id, int(self.state.progress))

        finally:
            self.state.updated_at = time.time()
            await self.store.save(self.state)

        return self.state

    async def pause(self) -> None:
        """Pause the worker, saving state for later resume."""
        self.state.status = WorkerStatus.PAUSED
        self.state.updated_at = time.time()
        await self.store.save(self.state)
        self._fire("on_pause", self.state)

    # -- Internal ---------------------------------------------------------

    def _fire(self, hook: str, *args: Any, **kwargs: Any) -> None:
        for fn in self._hooks.get(hook, ()):
            try:
                fn(*args, **kwargs)
            except Exception:
                logger.exception("Worker hook '%s' failed", hook)


def _new_worker_id() -> str:
    return f"w-{uuid.uuid4().hex[:8]}"


# -- Deferred import (avoids circular import with worker.scheduler) -----------
from meowcat.worker.scheduler import WorkerScheduler  # noqa: E402,F811


# -- Re-exports --------------------------------------------------------------
__all__ = [
    "WorkerStatus",
    "WorkerState",
    "CheckpointStore",
    "InMemoryCheckpointStore",
    "BaseWorker",
    "WorkerScheduler",
]

