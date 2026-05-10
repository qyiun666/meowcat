# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat worker — spawn_worker Mixin (v2.3.0: extracted from assembly.py).

Provides :class:`SpawnWorkerMixin` which implements ``cat.spawn_worker(...)``
for summoning independent worker cats. Split from assembly.py per H-06 remediation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meowcat.assembly import CatBase


class SpawnWorkerMixin:
    """Mixin that provides the spawn_worker method for CatBase.

    Requires: ``self._container``, ``self._events``, ``self.cat_uid``
    (provided by CatBase).
    """

    def spawn_worker(
        self,
        name: str,
        task: str,
        *,
        allowed_organs: frozenset[str] | None = None,
    ) -> "CatBase":
        """Summon a worker cat and stick a task on its TaskPad.

        The worker cat is a normal :class:`CatBase` instance with
        ``parent_id = self.cat_uid``. It gets a fresh :class:`TaskPad`
        with the task already posted.

        Args:
            name: Worker cat display name.
            task: Task description (auto-posted to worker's TaskPad).
            allowed_organs: Organ access restriction (security sandbox).
                ``None`` = all organs allowed.

        Returns:
            Worker :class:`CatBase` instance with task_pad and parent_id set.

        Emits:
            ``kitten.spawned`` event with ``{parent_id, kitten_id, task}``.
        """
        from meowcat.biology.task_pad import TaskPad

        worker = self._container.create_cat(
            name=name,
            parent_id=self.cat_uid,
            allowed_organs=allowed_organs,
        )
        worker.task_pad = TaskPad()
        worker.task_pad.post(task)

        self._events.emit_nowait("kitten.spawned", {
            "parent_id": self.cat_uid,
            "kitten_id": worker.cat_uid,
            "task": task,
        })
        return worker
