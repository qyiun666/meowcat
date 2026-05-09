# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""TaskOrchestrator — DAG-based task orchestration with topological sort and parallel dispatch.

The orchestrator topologically sorts tasks into levels and dispatches each level concurrently.
Framework provides DAG infrastructure; SubTask/Kitten/task-semantics are app-layer concerns.

Usage::

    orch = TaskOrchestrator(max_concurrent=5)
    orch.add_task(TaskNode(task_id="fetch", name="Fetch"))
    orch.add_task(TaskNode(task_id="parse", name="Parse", depends_on=["fetch"]))
    results = await orch.execute(run_task)
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_log = logging.getLogger(__name__)


# ── Status & Result ────────────────────────────────────────────────────


class TaskStatus(Enum):
    """Task node lifecycle status."""

    PENDING = "pending"
    """Task is registered but not yet ready to run (dependencies not met)."""

    READY = "ready"
    """All dependencies satisfied, task is queued for execution."""

    RUNNING = "running"
    """Task is currently being executed."""

    COMPLETED = "completed"
    """Task finished successfully."""

    FAILED = "failed"
    """Task execution raised an exception."""

    CANCELLED = "cancelled"
    """Task was cancelled due to a dependency failure or explicit cancellation."""


@dataclass
class TaskResult:
    """Outcome of a single task node execution.

    Attributes:
        task_id:    The task's unique identifier.
        status:     Final status (:attr:`TaskStatus.COMPLETED` or
                    :attr:`TaskStatus.FAILED`).
        output:     Return value from the executor (if completed), or
                    ``None``.
        error:      Exception message (if failed), or ``""``.
        duration:   Wall-clock duration of execution in seconds.
    """

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    output: Any = None
    error: str = ""
    duration: float = 0.0


# ── TaskNode ────────────────────────────────────────────────────────────


@dataclass
class TaskNode:
    """A single node in the task DAG.

    Attributes:
        task_id:    Unique identifier for this task.
        name:       Human-readable task name (for logging / diagnostics).
        payload:    Arbitrary app-layer data attached to the task
                    (the executor receives this).
        depends_on: List of ``task_id`` strings that must complete
                    before this task can start.
        status:     Current lifecycle status (managed by orchestrator
                    during execution).
    """

    task_id: str
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


# ── Executor type ──────────────────────────────────────────────────────

TaskExecutor = Callable[[TaskNode], Awaitable[Any]]
"""App-layer async callback: receives a :class:`TaskNode`, returns arbitrary result.

The orchestrator calls this once per task when the task is dispatched.
Return value is stored in :attr:`TaskResult.output`.
"""


# ── TaskOrchestrator ───────────────────────────────────────────────────


class TaskOrchestrator:
    """DAG-based task orchestrator with topological sort and parallel dispatch.

    Tasks are registered via :meth:`add_task`. Dependencies declared via
    :meth:`add_dependency` or ``TaskNode.depends_on``.
    :meth:`topological_sort` produces concurrent-safe levels.
    :meth:`execute` dispatches level-by-level with bounded concurrency.

    Design decisions:
    - **Cycle detection**: :meth:`topological_sort` raises :exc:`ValueError` on cycles.
    - **Failure policy**: by default, a failed task cancels downstream dependents.
      Set ``abort_on_failure=False`` to continue independent branches.
    - **Framework only provides infrastructure**: task semantics are app-layer concerns.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        abort_on_failure: bool = True,
    ) -> None:
        self._max_concurrent = max_concurrent
        self._abort_on_failure = abort_on_failure
        self._nodes: dict[str, TaskNode] = {}
        self._sem: asyncio.Semaphore | None = None

    # ── Properties ─────────────────────────────────────────────────

    @property
    def max_concurrent(self) -> int:
        """Maximum number of tasks that may run concurrently within a level."""
        return self._max_concurrent

    @property
    def abort_on_failure(self) -> bool:
        """Whether a failed task should cancel all downstream dependents."""
        return self._abort_on_failure

    @property
    def nodes(self) -> dict[str, TaskNode]:
        """All registered task nodes (read-only copy)."""
        return dict(self._nodes)

    # ── Registration ───────────────────────────────────────────────

    def add_task(self, node: TaskNode) -> TaskNode:
        """Register a task node.

        If a node with the same ``task_id`` already exists it is replaced.

        Args:
            node:  The :class:`TaskNode` to register.

        Returns:
            The registered node (same instance).

        Raises:
            ValueError: ``task_id`` is empty.
        """
        if not node.task_id:
            raise ValueError("TaskNode.task_id must not be empty")
        self._nodes[node.task_id] = node
        return node

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Declare that *task_id* depends on *depends_on*.

        Convenience method — equivalent to appending to
        :attr:`TaskNode.depends_on` on the node.

        Args:
            task_id:    The dependent task.
            depends_on: The prerequisite task.

        Raises:
            KeyError: Either *task_id* or *depends_on* is not registered.
        """
        if task_id not in self._nodes:
            raise KeyError(
                f"Task '{task_id}' not found. Register it via add_task() first.")
        if depends_on not in self._nodes:
            raise KeyError(
                f"Task '{depends_on}' not found. Register it via add_task() first.")
        node = self._nodes[task_id]
        if depends_on not in node.depends_on:
            node.depends_on.append(depends_on)

    def remove_task(self, task_id: str) -> TaskNode | None:
        """Remove a task and all inbound dependencies referencing it.

        Args:
            task_id:  Task identifier.

        Returns:
            The removed :class:`TaskNode`, or ``None`` if not found.
        """
        node = self._nodes.pop(task_id, None)
        if node is not None:
            # Clean up dependencies that reference this task
            for other in self._nodes.values():
                if task_id in other.depends_on:
                    other.depends_on.remove(task_id)
        return node

    def clear(self) -> None:
        """Remove all registered tasks."""
        self._nodes.clear()

    # ── Topological sort ───────────────────────────────────────────

    @staticmethod
    def _kahn_sort(nodes: dict[str, TaskNode]) -> list[list[str]]:
        """Kahn's algorithm: topological sort into execution levels.

        Single source of truth for topological sort, called by both
        :meth:`topological_sort` (public) and :meth:`_execute_levels` (private).

        Args:
            nodes: Task nodes keyed by task_id.

        Returns:
            A list of levels, each being a list of ``task_id`` strings.

        Raises:
            ValueError: The task graph contains a cycle or missing dependency.
        """
        in_degree: dict[str, int] = {}
        adj: dict[str, list[str]] = defaultdict(list)

        for tid in nodes:
            in_degree.setdefault(tid, 0)

        for tid, node in nodes.items():
            for dep in node.depends_on:
                if dep not in nodes:
                    raise ValueError(
                        f"Task '{tid}' depends on '{dep}', which is not registered.")
                adj[dep].append(tid)
                in_degree[tid] = in_degree.get(tid, 0) + 1

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0)
        levels: list[list[str]] = []
        visited_count = 0

        while queue:
            level: list[str] = []
            for _ in range(len(queue)):
                tid = queue.popleft()
                level.append(tid)
                visited_count += 1
                for neighbour in adj.get(tid, []):
                    in_degree[neighbour] -= 1
                    if in_degree[neighbour] == 0:
                        queue.append(neighbour)
            levels.append(level)

        if visited_count != len(nodes):
            remaining = [tid for tid, deg in in_degree.items() if deg > 0]
            raise ValueError(
                f"Cycle detected in task graph. Nodes still with incoming edges: {remaining}"
            )

        return levels

    def topological_sort(self) -> list[list[str]]:
        """Topologically sort registered tasks into execution levels.

        **Public inspection API** — callers use this to preview the
        execution plan before running :meth:`execute`.  It always
        operates on the full ``self._nodes`` set.

        Each level is a list of ``task_id`` strings that can run
        concurrently (no mutual dependencies).  Levels are ordered:
        level 0 has no dependencies, level 1 depends only on level 0, etc.

        .. note::

           :meth:`_execute_levels` does **not** call this method.
           It calls :meth:`_kahn_sort` directly because it sorts a
           *filtered subgraph* (when ``execute(tasks=[...])`` is used),
           which may differ from ``self._nodes``.

        Returns:
            A list of levels, each being a list of ``task_id`` strings.

        Raises:
            ValueError: The task graph contains a cycle, or references
                        a missing dependency.
        """
        if not self._nodes:
            return []

        return self._kahn_sort(self._nodes)

    # ── Execution ──────────────────────────────────────────────────

    async def execute(
        self,
        executor: TaskExecutor,
        *,
        tasks: Sequence[str] | None = None,
    ) -> dict[str, TaskResult]:
        """Execute the task DAG level-by-level.

        Args:
            executor: Async callable ``(TaskNode) -> Any`` per task.
            tasks: Optional subset of task_ids; None = all registered.

        Returns:
            Dict ``task_id`` → :class:`TaskResult` for all scheduled tasks
            (including cancelled).

        Raises:
            ValueError: DAG contains a cycle or missing dependency.
            KeyError: A task in *tasks* is not registered.
        """
        if tasks is not None:
            subset_ids = set(tasks)
            # Validate all tasks exist
            for tid in subset_ids:
                if tid not in self._nodes:
                    raise KeyError(f"Task '{tid}' not registered")
        else:
            subset_ids = set(self._nodes.keys())

        if not subset_ids:
            return {}

        # Build subgraph — only keep internal dependencies
        sub_nodes: dict[str, TaskNode] = {}
        for tid in subset_ids:
            node = self._nodes[tid]
            filtered_deps = [d for d in node.depends_on if d in subset_ids]
            sub_nodes[tid] = TaskNode(
                task_id=node.task_id,
                name=node.name,
                payload=node.payload.copy(),
                depends_on=list(filtered_deps),
            )

        return await self._execute_levels(sub_nodes, executor)

    async def _execute_levels(
        self,
        nodes: dict[str, TaskNode],
        executor: TaskExecutor,
    ) -> dict[str, TaskResult]:
        """Execute tasks level-by-level with topological ordering.

        Delegates to :meth:`_kahn_sort` for sort, dispatches each level
        concurrently with semaphore-bounded concurrency, tracks status,
        and propagates failures.

        Args:
            nodes: Subgraph of TaskNodes to execute.
            executor: Async callback ``(TaskNode) -> Any``.

        Returns:
            Dict mapping ``task_id`` → :class:`TaskResult` for all scheduled tasks.
        """
        results: dict[str, TaskResult] = {}
        failed_ids: set[str] = set()

        # Use shared Kahn's algorithm for topological sort
        levels = self._kahn_sort(nodes)
        for level in levels:
            if failed_ids and self._abort_on_failure:
                # Cancel all remaining tasks in this and subsequent levels
                for tid in level:
                    if tid not in results:
                        results[tid] = TaskResult(
                            task_id=tid,
                            status=TaskStatus.CANCELLED,
                            error="Cancelled due to upstream failure",
                        )
                        nodes[tid].status = TaskStatus.CANCELLED
                continue

            # Filter out already-failed dependents of failed tasks
            ready: list[str] = []
            for tid in level:
                if tid in failed_ids:
                    results[tid] = TaskResult(
                        task_id=tid,
                        status=TaskStatus.FAILED,
                        error=results.get(tid, TaskResult(tid)).error,
                    )
                    continue
                ready.append(tid)

            if not ready:
                continue

            # Dispatch level concurrently with semaphore
            sem = asyncio.Semaphore(self._max_concurrent)

            async def _run_one(tid: str, _sem: asyncio.Semaphore = sem) -> None:
                async with _sem:
                    node = nodes[tid]
                    node.status = TaskStatus.RUNNING
                    loop = asyncio.get_running_loop()
                    t0 = loop.time()
                    try:
                        output = await executor(node)
                        dt = loop.time() - t0
                        results[tid] = TaskResult(
                            task_id=tid,
                            status=TaskStatus.COMPLETED,
                            output=output,
                            duration=dt,
                        )
                        node.status = TaskStatus.COMPLETED
                    except Exception as exc:
                        dt = loop.time() - t0
                        results[tid] = TaskResult(
                            task_id=tid,
                            status=TaskStatus.FAILED,
                            error=str(exc),
                            duration=dt,
                        )
                        node.status = TaskStatus.FAILED
                        failed_ids.add(tid)

            await asyncio.gather(*(_run_one(tid) for tid in ready))

        return results

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state.

        Includes the DAG topology if valid, or cycle information if
        a cycle is present.
        """
        info: dict[str, Any] = {
            "max_concurrent": self._max_concurrent,
            "abort_on_failure": self._abort_on_failure,
            "task_count": len(self._nodes),
        }

        try:
            levels = self.topological_sort()
            info["topology"] = {
                "levels": levels,
                "level_count": len(levels),
            }
        except ValueError as exc:
            info["topology"] = {"error": str(exc)}

        info["tasks"] = [
            {
                "task_id": n.task_id,
                "name": n.name,
                "depends_on": n.depends_on,
                "status": n.status.value,
            }
            for n in self._nodes.values()
        ]
        return info
