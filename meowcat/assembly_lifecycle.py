# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat CatBase lifecycle mixin — start/shutdown/workflows/hooks/loop execution.

Extracted from assembly.py (v1.2.37) to keep CatBase under 500 lines.
Provides ``LifecycleMixin`` with all lifecycle-related methods.
"""

from __future__ import annotations

import inspect as _inspect
import json as _json
import logging as _logging
import time as _time
from collections.abc import Awaitable, Callable
from typing import Any

from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS
from meowcat.events import Lifecycle

_log = _logging.getLogger(__name__)

# v1.0.14: Lifecycle hook type — sync or async callable accepting a CatBase instance
# v1.3.6: extended to support async hooks (D14)
CatHook = Callable[[Any], None] | Callable[[Any], Awaitable[None]]


class LifecycleMixin:
    """Mixin providing lifecycle, workflow, and loop execution methods for CatBase.

    All methods access ``self._*`` private attributes set by ``CatBase.__init__``.
    This mixin has no ``__init__`` — CatBase is responsible for initialising
    the attributes these methods depend on.
    """

    @staticmethod
    async def _call_hook(hook: CatHook, cat: Any) -> None:
        """Call a lifecycle hook, supporting both sync and async.

        v1.3.6: auto-detects ``iscoroutinefunction`` so app layers
        can register ``async def`` hooks without manual await wrapping.
        """
        if _inspect.iscoroutinefunction(hook):
            await hook(cat)  # type: ignore[misc]
        else:
            hook(cat)  # type: ignore[call-arg]

    # -- Workflow tracking (v1.0.15) ----------------------------------------

    def register_workflow(self, wf: dict[str, Any]) -> None:
        """Register a workflow entity to the active tracking list.

        The application layer calls this after creating a WorkflowShape;
        the framework auto-saves checkpoints on shutdown.

        Args:
            wf: Dict form of WorkflowShape, must contain ``entity_id`` key
        """
        eid = wf.get("entity_id", wf.get("id", ""))
        if eid:
            self._active_workflows[eid] = wf  # type: ignore[attr-defined]

    def active_workflows(self) -> list[dict[str, Any]]:
        """Return all currently active (unfinished) workflows."""
        return [
            # type: ignore[attr-defined]
            wf
            for wf in self._active_workflows.values()
            if wf.get("status") in ("active", "awaiting_user")
        ]

    async def _resume_workflows(self) -> None:
        """Scan Hippocampus for unfinished Workflows and load into
        ``_active_workflows``.

        Logs failures at debug level — missing Hippocampus or query
        exceptions do not block startup.
        """
        if not self.has_organ("brain", "hippocampus"):  # type: ignore[attr-defined]
            return
        try:
            # type: ignore[attr-defined]
            hippo = self.organ("brain", "hippocampus")
            active = hippo.list_active_workflows(
                self.cat_uid)  # type: ignore[attr-defined]
            for wf in active:
                eid = wf.get("entity_id", wf.get("id", ""))
                if eid:
                    # type: ignore[attr-defined]
                    self._active_workflows[eid] = wf
        except Exception:
            _log.debug(
                "_resume_workflows: failed to load workflows", exc_info=True)

    async def _checkpoint_workflows(self) -> None:
        """Iterate all active Workflows and write checkpoint to Hippocampus.

        Logs failures at debug level — missing Hippocampus or write
        exceptions do not block shutdown.
        """
        if not self._active_workflows or not self.has_organ("brain", "hippocampus"):  # type: ignore[attr-defined]
            return
        if self._nervous is None:  # type: ignore[attr-defined]
            return
        try:
            # type: ignore[attr-defined]
            for eid, wf in self._active_workflows.items():
                if wf.get("status") not in ("active", "awaiting_user"):
                    continue
                checkpoint_data = {
                    "current_step": wf.get("current_step", 0),
                    "checkpoint": wf.get("checkpoint", {}),
                    "updated_at": str(_time.time()),
                }
                await self._nervous.signal(  # type: ignore[attr-defined]
                    BRAINSTEM,
                    HIPPOCAMPUS,
                    "append_content",
                    entity_id=eid,
                    text="\n[checkpoint] " + _json.dumps(checkpoint_data),
                )
        except Exception:
            _log.debug(
                "_checkpoint_workflows: failed to write checkpoint", exc_info=True)

    # -- Organs mounted hooks (v1.2.36) ------------------------------------

    def on_organs_mounted(self, hook: Callable[[Any], None]) -> None:
        """Register a hook called after all known organs are mounted.

        Use this when you need to interact with organs (e.g. inject colony
        memory into hippocampus) — at this point ``has_organ()`` and
        ``organ()`` are guaranteed to work.

        .. note::

            v1.3.6: ``on_organs_mounted`` hooks are always called
            **synchronously** during assembly — only sync callables are
            accepted.  For async initialisation that requires awaiting,
            register an ``on_start`` hook instead.

        Args:
            hook: Sync callable ``(cat: CatBase) -> None``.

        Examples:

            >>> cat.on_organs_mounted(lambda c: colony._inject_colony_memory(c))
        """
        self._organs_mounted_hooks.append(hook)  # type: ignore[attr-defined]

    def _notify_organs_mounted(self) -> None:
        """Internal: fire all on_organs_mounted hooks in registration order."""
        for hook in self._organs_mounted_hooks:  # type: ignore[attr-defined]
            # v1.3.6: sync-only hooks for organs_mounted (called during
            # sync assembly flow). For async needs, use on_start() instead.
            hook(self)  # type: ignore[call-arg]

    # -- Lifecycle hooks (v1.0.14) -----------------------------------------

    def on_start(self, hook: CatHook) -> None:
        """Register a start hook. Called in registration order after
        assembly completes.

        .. versionchanged:: 1.3.6
            Hooks may now be ``async def`` — the framework auto-detects
            coroutine functions and ``await``s them.

        Args:
            hook: Sync or async callable accepting a CatBase instance,
                  called after ``start()`` emits the lifecycle.start event.

        Examples:

            >>> cat.on_start(lambda c: c.colony.gateway.start())
        """
        self._start_hooks.append(hook)  # type: ignore[attr-defined]

    def on_shutdown(self, hook: CatHook) -> None:
        """Register a shutdown hook. Called in **reverse** registration
        order before shutdown.

        .. versionchanged:: 1.3.6
            Hooks may now be ``async def`` — the framework auto-detects
            coroutine functions and ``await``s them.

        Args:
            hook: Sync or async callable accepting a CatBase instance,
                  called in reverse order before ``shutdown()`` emits the
                  lifecycle.shutdown event.

        Examples:

            >>> cat.on_shutdown(lambda c: c.colony.gateway.stop())
        """
        self._shutdown_hooks.append(hook)  # type: ignore[attr-defined]

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start the cat. Scan unfinished Workflows → emit lifecycle.start
        → call on_start hooks in registration order.

        Subclasses may override, **must call ``await super().start()``**.
        """
        # v1.0.15: Scan Hippocampus for unfinished Workflows and load
        await self._resume_workflows()
        # type: ignore[attr-defined]
        await self._events.emit(Lifecycle.START, {"cat": self})
        for hook in self._start_hooks:  # type: ignore[attr-defined]
            await self._call_hook(hook, self)

    async def shutdown(self) -> None:
        """Shut down the cat. Save active Workflows → call on_shutdown hooks
        in reverse order → emit lifecycle.shutdown.

        Subclasses may override, **must call ``await super().shutdown()``**.
        """
        # v1.0.15: Save all active Workflows to Hippocampus
        await self._checkpoint_workflows()
        # type: ignore[attr-defined]
        for hook in reversed(self._shutdown_hooks):
            await self._call_hook(hook, self)
        # type: ignore[attr-defined]
        await self._events.emit(Lifecycle.SHUTDOWN, {"cat": self})

    # -- Loop execution -------------------------------------------------------

    async def run_loop(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a loop: trigger event → run chain → exit event.

        Equivalent to::

            self.loop_registry.run(self, name, **initial_input)

        Args:
            name: Loop name (e.g. ``"conversation"``)
            **initial_input: Initial input passed to chain's first step

        Returns:
            Chain execution result (dict)

        Raises:
            KeyError: Loop does not exist

        Examples:

            result = await cat.run_loop("conversation", message="hello")
        """
        return await self.loop_registry.run(self, name, **initial_input)  # type: ignore[attr-defined]

    # -- Loop sequence execution (v1.0.4) -------------------------------------

    async def run_loopseq(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a loop sequence: compose multiple Loops sequentially or concurrently.

        Equivalent to::

            self.loopseq_registry.run(self, name, **initial_input)

        Args:
            name: Loop sequence name (e.g. ``"daily_maintenance"``)
            **initial_input: Initial input

        Returns:
            Last step result (sequential) or ``{loop_name: result, ...}``
            (event_driven)

        Raises:
            KeyError: Loop sequence does not exist

        Examples:

            result = await cat.run_loopseq("daily_maintenance")
        """
        return await self.loopseq_registry.run(self, name, **initial_input)  # type: ignore[attr-defined]


__all__ = ["LifecycleMixin", "CatHook"]
