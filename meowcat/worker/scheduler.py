# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat worker scheduler — priority + dependency-aware worker orchestration (v1.2.22).

Schedules :class:`BaseWorker` instances by priority (higher first), respecting
``depends_on`` chains. Handles retry via ``max_retries`` already baked into
:class:`BaseWorker.run`.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from typing import Any

from meowcat.worker import BaseWorker, WorkerState, WorkerStatus

logger = logging.getLogger(__name__)


class WorkerScheduler:
    """Priority + dependency-aware worker scheduler.

    Each worker runs independently after its dependencies complete.
    Workers with the same readiness are dispatched by priority DESC.

    Usage::

        scheduler = WorkerScheduler()
        scheduler.submit(worker_a)  # returns job_id
        scheduler.submit(worker_b)
        results = await scheduler.run_all()
        # results: {worker_id: WorkerState}
    """

    def __init__(self, *, max_concurrency: int = 1) -> None:
        self._workers: dict[str, BaseWorker] = {}
        self._job_ids: dict[str, str] = {}  # job_id → worker_id
        self._results: dict[str, WorkerState] = {}
        self._max_concurrency = max_concurrency

    # -- Registration -----------------------------------------------------------

    def submit(
        self,
        worker: BaseWorker,
        *,
        task_id: str = "",
        steps: list[dict[str, Any]] | None = None,
        resume: bool = False,
    ) -> str:
        """Register a worker for scheduled execution.

        Args:
            worker: The worker instance to schedule.
            task_id: Task identifier passed to worker.run().
            steps: Steps passed to worker.run().
            resume: Whether to resume from checkpoint.

        Returns:
            Job identifier string.
        """
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self._job_ids[job_id] = worker.worker_id
        self._workers[worker.worker_id] = worker

        # Store execution config on the worker for later retrieval
        worker._sched_task_id = task_id or f"task-{worker.worker_id}"
        worker._sched_steps = steps or []
        worker._sched_resume = resume

        logger.debug(
            "Scheduler: submitted %s (job=%s, priority=%d)",
            worker.worker_id,
            job_id,
            worker.priority,
        )
        return job_id

    # -- Execution ---------------------------------------------------------------

    async def run_all(self) -> dict[str, WorkerState]:
        """Execute all submitted workers respecting dependencies and priorities.

        Returns:
            Mapping of worker_id → final WorkerState.

        Execution order:
        1. Build dependency graph from each worker's ``depends_on``.
        2. Dispatch ready workers (all dependencies satisfied) by priority DESC.
        3. As each worker completes, check if blocked workers become ready.
        4. Cycle detection: if no worker is ready and some remain blocked, raise.
        """
        if not self._workers:
            return {}

        # Build dependency tracking
        pending_deps: dict[str, set[str]] = {}
        dependents: dict[str, set[str]] = defaultdict(set)  # w_id → who depends on me

        for w_id, worker in self._workers.items():
            deps = set(worker.depends_on) & set(self._workers.keys())
            pending_deps[w_id] = deps
            for dep_id in deps:
                dependents[dep_id].add(w_id)

        # Workers sorted by (ready, -priority)
        def _sort_key(w_id: str) -> tuple[bool, int]:
            worker = self._workers[w_id]
            ready = not pending_deps.get(w_id, set())
            return (not ready, -worker.priority)

        remaining = set(self._workers.keys())
        sem = asyncio.Semaphore(self._max_concurrency)

        async def _run_worker(w_id: str) -> None:
            async with sem:
                worker = self._workers[w_id]
                try:
                    state = await worker.run(
                        worker._sched_task_id,
                        worker._sched_steps,
                        resume=worker._sched_resume,
                    )
                except Exception as exc:
                    state = worker.state
                    state.status = WorkerStatus.FAILED
                    state.error = str(exc)
                self._results[w_id] = state
                remaining.discard(w_id)

                # Unblock dependents
                for dep_id in dependents.get(w_id, set()):
                    pending_deps[dep_id].discard(w_id)

        # Main scheduling loop
        while remaining:
            ready = [w_id for w_id in remaining if not pending_deps.get(w_id, set())]
            if not ready:
                # Cycle or missing dependency
                blocked_info = {w_id: list(deps) for w_id, deps in pending_deps.items() if deps}
                raise RuntimeError(
                    f"Scheduler: deadlock detected — workers blocked by "
                    f"unresolved dependencies: {blocked_info}"
                )

            ready.sort(key=_sort_key)

            tasks = [asyncio.create_task(_run_worker(w_id)) for w_id in ready]
            await asyncio.gather(*tasks)

        return dict(self._results)

    # -- Inspection --------------------------------------------------------------

    def status(self, worker_id: str) -> WorkerStatus | None:
        """Get current status of a submitted worker, or None if not found."""
        if worker_id in self._results:
            return self._results[worker_id].status
        if worker_id in self._workers:
            return self._workers[worker_id].state.status
        return None

    def list_workers(self) -> list[dict[str, Any]]:
        """List all submitted workers with metadata."""
        result = []
        for w_id, worker in self._workers.items():
            result.append(
                {
                    "worker_id": w_id,
                    "priority": worker.priority,
                    "depends_on": worker.depends_on,
                    "max_retries": worker.max_retries,
                    "status": self.status(w_id).value if self.status(w_id) else "unknown",
                }
            )
        return result


__all__ = ["WorkerScheduler"]
