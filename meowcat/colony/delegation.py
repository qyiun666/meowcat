# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Task delegation Mixin (v1.3.8: extracted from colony/__init__.py)."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any


class _DelegationMixin:
    """Task delegation methods extracted from Colony.

    Provides fire-and-forget task delegation (delegate_async), status polling
    (task_status/await_task), and cat health checking (check_cat).

    Requires the host class to provide:
        - ``self._cats`` (dict of cat_uid -> CatBase)
        - ``self._task_results`` (dict of task_id -> result)
        - ``self.ns_set()`` / ``self.ns_get()`` (from _NamespaceMixin)
        - ``self.signal_between()`` (Colony inter-cat communication)
    """

    _TASKS_NS = "__tasks__"

    async def delegate_async(
        self,
        from_id: str,
        to_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        timeout: float = 60.0,
        **kw: Any,
    ) -> str:
        """Fire-and-forget task delegation to a kitten. Returns task_id immediately.

        The task runs in background as an :class:`asyncio.Task`.  The main
        cat's conversation loop is NOT blocked — the main cat can keep
        talking to the user while the kitten works.  Use :meth:`await_task`
        to poll for results.

        Status is tracked in colony shared storage (``__tasks__/task_id``).

        Usage::

            # Main cat delegates, continues talking to user
            task_id = await colony.delegate_async(
                "01", "02", "brain", "cerebrum", "generate",
                prompt="检查数据库表结构", timeout=120.0,
            )
            reply = f"已派发任务（{task_id}），后台执行中..."

            # ... main cat handles user messages normally ...

            # Later, check result
            result = await colony.await_task(task_id, poll_interval=10)

        Args:
            from_id: Delegating cat ID.
            to_id: Kitten cat ID.
            to_category: Target organ category.
            to_name: Target organ name.
            method: Target method name.
            *args, **kw: Forwarded to target method.
            timeout: Max seconds per single signal_between attempt.

        Returns:
            Task ID string for status tracking.
        """
        task_id = f"{from_id}-{to_id}-{uuid.uuid4().hex[:8]}"
        started_at = time.monotonic()
        payload: dict[str, object] = {
            "status": "pending",
            "from_id": from_id,
            "to_id": to_id,
            "to_category": to_category,
            "to_name": to_name,
            "method": method,
            "started_at": started_at,
        }
        # type: ignore[attr-defined]
        await self.ns_set(self._TASKS_NS, task_id, json.dumps(payload))

        async def _runner() -> None:
            try:
                payload["status"] = "running"
                # type: ignore[attr-defined]
                await self.ns_set(self._TASKS_NS, task_id, json.dumps(payload))
                result = await self.signal_between(  # type: ignore[attr-defined]
                    from_id,
                    to_id,
                    to_category,
                    to_name,
                    method,
                    *args,
                    timeout=timeout,
                    **kw,
                )
                # Store actual result in memory (non-serialized)
                # type: ignore[attr-defined]
                self._task_results[task_id] = result
                payload["status"] = "done"
                payload["result"] = repr(result)
                payload["finished_at"] = time.monotonic()
                await self.ns_set(  # type: ignore[attr-defined]
                    self._TASKS_NS,
                    task_id,
                    json.dumps(payload, default=str),
                )
            except asyncio.TimeoutError:
                payload["status"] = "timed_out"
                payload["finished_at"] = time.monotonic()
                await self.ns_set(  # type: ignore[attr-defined]
                    self._TASKS_NS,
                    task_id,
                    json.dumps(payload),
                )
            except Exception as exc:
                payload["status"] = "errored"
                payload["error"] = repr(exc)
                payload["finished_at"] = time.monotonic()
                await self.ns_set(  # type: ignore[attr-defined]
                    self._TASKS_NS,
                    task_id,
                    json.dumps(payload, default=str),
                )

        asyncio.create_task(_runner())
        return task_id

    async def task_status(self, task_id: str) -> dict[str, object]:
        """Query the status of a delegated task.

        Args:
            task_id: Task ID from :meth:`delegate_async`.

        Returns:
            Dict with keys: ``status`` (pending|running|done|errored|
            timed_out|unknown), and optionally ``result``, ``error``,
            ``started_at``, ``finished_at``, ``from_id``, ``to_id``.
        """
        raw = await self.ns_get(self._TASKS_NS, task_id)  # type: ignore[attr-defined]
        if raw is None:
            return {"status": "unknown"}
        return json.loads(raw) if isinstance(raw, str) else raw

    async def await_task(
        self,
        task_id: str,
        *,
        poll_interval: float = 10.0,
        max_wait: float = 600.0,
    ) -> Any:
        """Wait for a delegated task with intelligent status checking.

        Polls every ``poll_interval`` seconds.  If the kitten hasn't
        responded:

        - Checks kitten health via :meth:`check_cat`
        - If still alive → keeps waiting
        - If stuck or dead → raises immediately

        The event loop is NOT blocked — ``asyncio.sleep`` yields to other
        tasks (including user conversations with other cats).

        Args:
            task_id: Task ID from :meth:`delegate_async`.
            poll_interval: Seconds between status checks (default 10s).
            max_wait: Maximum total wait time (default 600s).

        Returns:
            Task result on success (the actual Python object, not
            serialized).

        Raises:
            asyncio.TimeoutError: Total wait time exceeded.
            RuntimeError: Kitten cat is dead or stuck.
        """
        start = time.monotonic()

        while True:
            # type: ignore[attr-defined]
            status = await self.task_status(task_id)
            st = status.get("status", "unknown")

            if st == "done":
                # Return actual result from memory, fallback to serialized
                return self._task_results.pop(  # type: ignore[attr-defined]
                    task_id,
                    status.get("result"),
                )
            if st in ("errored", "timed_out"):
                raise RuntimeError(
                    f"Task {task_id} {st}: {status.get('error', 'no detail')}")

            elapsed = time.monotonic() - start
            if elapsed >= max_wait:
                raise asyncio.TimeoutError(
                    f"Task {task_id} exceeded max_wait {max_wait}s (current status: {st})"
                )

            # Check kitten health if we know who the kitten is
            to_id = status.get("to_id", "")
            if to_id and st == "running":
                # type: ignore[attr-defined]
                cat_health = await self.check_cat(str(to_id))
                if cat_health == "dead":
                    raise RuntimeError(
                        f"Kitten cat '{to_id}' is dead (task {task_id})")

            await asyncio.sleep(poll_interval)

    async def check_cat(self, cat_uid: str) -> str:
        """Check if a cat is alive and responsive.

        Args:
            cat_uid: Cat unique identifier.

        Returns:
            ``"alive"`` — cat exists in colony.
            ``"dead"`` — cat does not exist in colony.
        """
        cat = self._cats.get(cat_uid)  # type: ignore[attr-defined]
        if cat is None:
            return "dead"

        return "alive"
