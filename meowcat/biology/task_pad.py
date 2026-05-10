# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""TaskPad — cat's private task list (room furniture #5).

插座式设计: framework provides storage + slots, app-layer decides
WHEN to post tasks, WHAT to execute, and HOW to decompose.

Usage::

    from meowcat.biology.task_pad import TaskPad, TaskItem

    pad = TaskPad()
    pad.post("写一个用户登录函数")
    item = pad.pick()  # FIFO
    pad.mark_done(item.task_id, result="已完成")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from meowcat.log import MeowLog
from meowcat.pluggable import Pluggable

_log = MeowLog.get("meowcat.task_pad")


class TaskStatus(str, Enum):
    """Task lifecycle states."""

    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskItem:
    """A single sticky note on the TaskPad.

    Args:
        task_id: Auto-generated unique identifier.
        content: Task description — what needs to be done.
        status: Current lifecycle state.
        result: Execution result text (appended on completion).
        created_at: When the task was posted.
        done_at: When the task was completed or failed.
    """

    task_id: str
    content: str
    status: TaskStatus = TaskStatus.TODO
    result: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    done_at: datetime | None = None


class TaskPad(Pluggable):
    """Room furniture #5 — the cat's to-do list.

    Framework layer responsibilities:
    - ``post()`` / ``pick()`` / ``mark_done()`` / ``mark_failed()`` storage
    - capacity management
    - plugin slots for custom logic (on_post, on_done, on_failed)

    App layer responsibilities:
    - When to call ``post()`` (every message? manual?)
    - What format (plain text? structured JSON?)
    - How to decompose complex tasks into subtasks

    Args:
        max_tasks: Max tasks before ``post()`` starts rejecting. Default 20.
    """

    HOOKS: dict[str, dict[str, str]] = {
        "on_post": {"in": "item: TaskItem", "out": "Any | None"},
        "on_done": {"in": "item: TaskItem", "out": "Any | None"},
        "on_failed": {"in": "item: TaskItem", "out": "Any | None"},
        "post_filter": {"in": "item: TaskItem", "out": "bool | None"},
    }

    __slots__ = ("_tasks", "_max_tasks")

    def __init__(self, max_tasks: int = 20) -> None:
        super().__init__()
        if max_tasks < 1:
            raise ValueError(f"max_tasks must be >= 1, got {max_tasks}")
        self._max_tasks = max_tasks
        self._tasks: list[TaskItem] = []

    # -- Core API ------------------------------------------------------

    def post(self, content: str) -> TaskItem:
        """Stick a task note onto the pad.

        Args:
            content: Task description.

        Returns:
            The created TaskItem.

        Raises:
            ValueError: If ``max_tasks`` reached and this is an enforced
                capacity pad (future extension for strict mode).
        """
        if len(self._tasks) >= self._max_tasks:
            _log.warning("post rejected (pad full)", max_tasks=self._max_tasks)
            raise ValueError(
                f"TaskPad is full ({self._max_tasks} tasks). Drain or complete some first."
            )

        task_id = uuid.uuid4().hex[:12]
        item = TaskItem(task_id=task_id, content=content)

        # post_filter chain — any False vetoes
        for _name, ok in self._run_plugs_sync("post_filter", item):
            if ok is False:
                _log.debug("task post filtered", task_id=task_id)
                return item  # item created but not added to list

        self._tasks.append(item)

        # on_post hook (fire-and-forget)
        for _name, _r in self._run_plugs_sync("on_post", item):
            pass

        _log.debug("task posted", task_id=task_id, content=content[:80])
        return item

    def pick(self) -> TaskItem | None:
        """Take the next TODO task off the pad (FIFO).

        Returns:
            The next TaskItem with status TODO, or None if empty.
        """
        for item in self._tasks:
            if item.status == TaskStatus.TODO:
                return item
        return None

    def mark_doing(self, task_id: str) -> None:
        """Mark a task as in-progress.

        Args:
            task_id: The task to update.

        Raises:
            ValueError: If task_id not found.
        """
        item = self._find(task_id)
        item.status = TaskStatus.DOING

    def mark_done(self, task_id: str, result: str = "") -> None:
        """Mark a task as completed.

        Args:
            task_id: The task to complete.
            result: Execution result text (appended to TaskItem.result).

        Raises:
            ValueError: If task_id not found.
        """
        item = self._find(task_id)
        item.status = TaskStatus.DONE
        item.result = result
        item.done_at = datetime.now(timezone.utc)

        for _name, _r in self._run_plugs_sync("on_done", item):
            pass

        _log.debug("task done", task_id=task_id)

    def mark_failed(self, task_id: str, error: str = "") -> None:
        """Mark a task as failed.

        Args:
            task_id: The task that failed.
            error: Error description (written to TaskItem.result).

        Raises:
            ValueError: If task_id not found.
        """
        item = self._find(task_id)
        item.status = TaskStatus.FAILED
        item.result = error
        item.done_at = datetime.now(timezone.utc)

        for _name, _r in self._run_plugs_sync("on_failed", item):
            pass

        _log.debug("task failed", task_id=task_id, error=error[:120])

    # -- Query ---------------------------------------------------------

    def list_todo(self) -> list[TaskItem]:
        """List all TODO tasks."""
        return [t for t in self._tasks if t.status == TaskStatus.TODO]

    def list_all(self) -> list[TaskItem]:
        """List all tasks (shallow copy)."""
        return list(self._tasks)

    def is_empty(self) -> bool:
        """Whether the pad has any tasks."""
        return len(self._tasks) == 0

    def count(self) -> int:
        """Total task count."""
        return len(self._tasks)

    def count_by_status(self) -> dict[str, int]:
        """Count tasks grouped by status."""
        counts: dict[str, int] = {s.value: 0 for s in TaskStatus}
        for t in self._tasks:
            counts[t.status.value] += 1
        return counts

    def diagnose(self) -> dict[str, Any]:
        """Return a diagnostic snapshot."""
        return {
            "count": self.count(),
            "max_tasks": self._max_tasks,
            "by_status": self.count_by_status(),
            "plugs": self.list_plugs(),
        }

    # -- Internal ------------------------------------------------------

    def _find(self, task_id: str) -> TaskItem:
        """Find a task by id. Raises ValueError if not found."""
        for item in self._tasks:
            if item.task_id == task_id:
                return item
        raise ValueError(f"Task {task_id!r} not found on TaskPad")


__all__ = [
    "TaskPad",
    "TaskItem",
    "TaskStatus",
]
