# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for TaskOrchestrator DAG execution (T-26 / v1.3.6)."""

from __future__ import annotations

import asyncio

import pytest

from meowcat.task_orchestrator import (
    TaskNode,
    TaskOrchestrator,
    TaskResult,
    TaskStatus,
)


# ── TaskStatus ────────────────────────────────────────────────────────


class TestTaskStatus:
    """TaskStatus enum values."""

    def test_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.READY.value == "ready"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_count(self):
        assert len(TaskStatus) == 6


# ── TaskResult ────────────────────────────────────────────────────────


class TestTaskResult:
    """TaskResult dataclass."""

    def test_defaults(self):
        r = TaskResult(task_id="t1")
        assert r.task_id == "t1"
        assert r.status == TaskStatus.PENDING
        assert r.output is None
        assert r.error == ""
        assert r.duration == 0.0

    def test_completed(self):
        r = TaskResult(
            task_id="done",
            status=TaskStatus.COMPLETED,
            output="result",
            duration=1.5,
        )
        assert r.status == TaskStatus.COMPLETED
        assert r.output == "result"
        assert r.duration == 1.5

    def test_failed(self):
        r = TaskResult(
            task_id="fail",
            status=TaskStatus.FAILED,
            error="boom",
            duration=0.1,
        )
        assert r.status == TaskStatus.FAILED
        assert r.error == "boom"


# ── TaskNode ──────────────────────────────────────────────────────────


class TestTaskNode:
    """TaskNode dataclass."""

    def test_defaults(self):
        n = TaskNode(task_id="t1")
        assert n.task_id == "t1"
        assert n.name == ""
        assert n.payload == {}
        assert n.depends_on == []
        assert n.status == TaskStatus.PENDING

    def test_custom(self):
        n = TaskNode(
            task_id="build",
            name="Build project",
            payload={"cmd": "make"},
            depends_on=["lint", "test"],
        )
        assert n.task_id == "build"
        assert n.name == "Build project"
        assert n.payload == {"cmd": "make"}
        assert n.depends_on == ["lint", "test"]


# ── TaskOrchestrator: constructor / registration ─────────────────────


class TestTaskOrchestratorConstruct:
    """Constructor and initial state."""

    def test_defaults(self):
        orch = TaskOrchestrator()
        assert orch.max_concurrent == 5
        assert orch.abort_on_failure is True
        assert orch.nodes == {}

    def test_custom(self):
        orch = TaskOrchestrator(max_concurrent=10, abort_on_failure=False)
        assert orch.max_concurrent == 10
        assert orch.abort_on_failure is False


class TestTaskOrchestratorAddTask:
    """add_task and basic registration."""

    def test_add_task(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        assert "a" in orch.nodes

    def test_add_task_returns_node(self):
        orch = TaskOrchestrator()
        n = orch.add_task(TaskNode(task_id="x"))
        assert n.task_id == "x"

    def test_add_task_overwrites(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a", name="first"))
        orch.add_task(TaskNode(task_id="a", name="second"))
        assert orch.nodes["a"].name == "second"

    def test_add_task_empty_id_raises(self):
        orch = TaskOrchestrator()
        with pytest.raises(ValueError, match="must not be empty"):
            orch.add_task(TaskNode(task_id=""))


class TestTaskOrchestratorAddDependency:
    """add_dependency."""

    def test_add_dependency(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_dependency("b", "a")
        assert orch.nodes["b"].depends_on == ["a"]

    def test_add_dependency_idempotent(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_dependency("b", "a")
        orch.add_dependency("b", "a")
        assert orch.nodes["b"].depends_on == ["a"]

    def test_add_dependency_missing_task_raises(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        with pytest.raises(KeyError, match="not found"):
            orch.add_dependency("a", "ghost")

    def test_add_dependency_missing_dep_raises(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        with pytest.raises(KeyError, match="not found"):
            orch.add_dependency("ghost", "a")


class TestTaskOrchestratorRemoveTask:
    """remove_task and cleanup."""

    def test_remove_existing(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        removed = orch.remove_task("a")
        assert removed is not None
        assert removed.task_id == "a"
        assert "a" not in orch.nodes

    def test_remove_missing(self):
        orch = TaskOrchestrator()
        assert orch.remove_task("ghost") is None

    def test_remove_cleans_up_dependencies(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.remove_task("a")
        assert "a" not in orch.nodes
        assert orch.nodes["b"].depends_on == []

    def test_clear(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.clear()
        assert orch.nodes == {}


# ── TaskOrchestrator: topological_sort ───────────────────────────────


class TestTaskOrchestratorTopoSort:
    """topological_sort."""

    def test_empty(self):
        orch = TaskOrchestrator()
        assert orch.topological_sort() == []

    def test_single_node(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        levels = orch.topological_sort()
        assert levels == [["a"]]

    def test_linear_chain(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="c", depends_on=["b"]))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="a"))
        levels = orch.topological_sort()
        assert levels == [["a"], ["b"], ["c"]]

    def test_diamond(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="d", depends_on=["b", "c"]))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="a"))
        levels = orch.topological_sort()
        assert levels[0] == ["a"]
        # b and c are independent → same level
        assert set(levels[1]) == {"b", "c"}
        assert levels[2] == ["d"]

    def test_independent_nodes_same_level(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_task(TaskNode(task_id="c"))
        levels = orch.topological_sort()
        assert set(levels[0]) == {"a", "b", "c"}

    def test_cycle_detection(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a", depends_on=["b"]))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        with pytest.raises(ValueError, match="Cycle detected"):
            orch.topological_sort()

    def test_missing_dependency_raises(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a", depends_on=["ghost"]))
        with pytest.raises(ValueError, match="not registered"):
            orch.topological_sort()

    def test_complex_graph(self):
        orch = TaskOrchestrator()
        # a → b, c → d, b → d, e (independent)
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="d", depends_on=["b", "c"]))
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="e"))
        levels = orch.topological_sort()
        assert levels[0] == ["a", "e"]
        assert set(levels[1]) == {"b", "c"}
        assert levels[2] == ["d"]


# ── TaskOrchestrator: execute ────────────────────────────────────────


class TestTaskOrchestratorExecute:
    """execute with various DAG shapes."""

    @staticmethod
    async def _echo(node: TaskNode) -> str:
        return f"done:{node.task_id}"

    @pytest.mark.asyncio
    async def test_execute_single(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        results = await orch.execute(self._echo)
        assert results["a"].status == TaskStatus.COMPLETED
        assert results["a"].output == "done:a"
        assert results["a"].duration > 0

    @pytest.mark.asyncio
    async def test_execute_empty(self):
        orch = TaskOrchestrator()
        results = await orch.execute(self._echo)
        assert results == {}

    @pytest.mark.asyncio
    async def test_execute_linear(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["b"]))
        results = await orch.execute(self._echo)
        assert all(r.status == TaskStatus.COMPLETED for r in results.values())
        assert results["c"].output == "done:c"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_task(TaskNode(task_id="c"))
        results = await orch.execute(self._echo)
        assert all(r.status == TaskStatus.COMPLETED for r in results.values())
        # All three should have completed
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_execute_diamond(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="d", depends_on=["b", "c"]))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="a"))
        results = await orch.execute(self._echo)
        assert all(r.status == TaskStatus.COMPLETED for r in results.values())
        assert results["d"].output == "done:d"

    @pytest.mark.asyncio
    async def test_execute_subset(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_task(TaskNode(task_id="c"))
        results = await orch.execute(self._echo, tasks=["a", "c"])
        assert set(results.keys()) == {"a", "c"}
        assert "b" not in results

    @pytest.mark.asyncio
    async def test_execute_subset_missing_raises(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        with pytest.raises(KeyError, match="not registered"):
            await orch.execute(self._echo, tasks=["ghost"])

    @pytest.mark.asyncio
    async def test_execute_subset_preserves_internal_deps(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["b"]))
        # Execute only a and c → c's dep on b is filtered out (b not in subset)
        results = await orch.execute(self._echo, tasks=["a", "c"])
        assert results["a"].status == TaskStatus.COMPLETED
        assert results["c"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_abort_on_failure(self):
        orch = TaskOrchestrator(abort_on_failure=True)

        async def _fail_b(node: TaskNode) -> str:
            if node.task_id == "b":
                raise RuntimeError("b failed")
            return f"ok:{node.task_id}"

        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["b"]))
        results = await orch.execute(_fail_b)
        assert results["a"].status == TaskStatus.COMPLETED
        assert results["b"].status == TaskStatus.FAILED
        assert results["c"].status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_execute_no_abort_continues(self):
        orch = TaskOrchestrator(abort_on_failure=False)

        async def _fail_b(node: TaskNode) -> str:
            if node.task_id == "b":
                raise RuntimeError("b failed")
            return f"ok:{node.task_id}"

        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        orch.add_task(TaskNode(task_id="c", depends_on=["b"]))
        results = await orch.execute(_fail_b)
        assert results["a"].status == TaskStatus.COMPLETED
        assert results["b"].status == TaskStatus.FAILED
        # c still runs (abort_on_failure=False)
        assert results["c"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_concurrent_within_level(self):
        orch = TaskOrchestrator(max_concurrent=2)
        started: list[str] = []
        lock = asyncio.Lock()

        async def _track(node: TaskNode) -> str:
            async with lock:
                started.append(node.task_id)
            return f"ok:{node.task_id}"

        # 3 independent tasks, max_concurrent=2
        orch.add_task(TaskNode(task_id="a"))
        orch.add_task(TaskNode(task_id="b"))
        orch.add_task(TaskNode(task_id="c"))
        results = await orch.execute(_track)
        assert len(results) == 3
        assert all(r.status == TaskStatus.COMPLETED for r in results.values())

    @pytest.mark.asyncio
    async def test_execute_result_status(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a"))
        results = await orch.execute(self._echo)
        assert results["a"].status == TaskStatus.COMPLETED
        assert results["a"].duration > 0


# ── TaskOrchestrator: diagnose ────────────────────────────────────────


class TestTaskOrchestratorDiagnose:
    """Diagnose snapshot."""

    def test_diagnose_empty(self):
        orch = TaskOrchestrator(max_concurrent=3, abort_on_failure=False)
        diag = orch.diagnose()
        assert diag["max_concurrent"] == 3
        assert diag["abort_on_failure"] is False
        assert diag["task_count"] == 0

    def test_diagnose_with_tasks(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a", name="Task A"))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        diag = orch.diagnose()
        assert diag["task_count"] == 2
        assert diag["topology"]["level_count"] == 2
        assert len(diag["tasks"]) == 2

    def test_diagnose_cycle(self):
        orch = TaskOrchestrator()
        orch.add_task(TaskNode(task_id="a", depends_on=["b"]))
        orch.add_task(TaskNode(task_id="b", depends_on=["a"]))
        diag = orch.diagnose()
        assert "error" in diag["topology"]
