# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat coordination — async approval gate for multi-agent coordination (v1.1.29).

.. deprecated:: 2.3.0
    This module is deprecated and will be removed in v2.5.0.
    meowagent has its own approval system (see `meowagent.cat.approval`).
    No meowcat-internal or meowagent-external code references this module.

Provides :class:`AsyncApprovalGate` — a lightweight async coordination primitive
for human-in-the-loop and cross-cat approval workflows.

Framework-layer: provides the gate primitive with pluggable approval strategy.
App-layer: defines who approves, what requires approval, timeout/retry policies.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

warnings.warn(
    "meowcat.coordination is deprecated since v2.3.0 and will be removed in v2.5.0. "
    "Use meowagent's approval system (meowagent.cat.approval) instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval decision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


@dataclass
class ApprovalRequest:
    """A single approval request."""

    request_id: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    requester: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: str = ""
    rejected_reason: str = ""


class AsyncApprovalGate:
    """Async approval gate — coordinates multi-party approval workflows.

    An agent submits an action for approval; one or more approvers vote;
    the gate resolves when threshold is met or timeout expires.

    Usage::

        gate = AsyncApprovalGate(default_timeout=30.0)

        # Agent submits request
        req = await gate.submit("deploy", {"env": "prod"}, reason="User requested")

        # External approver votes
        await gate.approve(req.request_id, approver="human-ops")

        # Agent waits for resolution
        result = await gate.wait(req.request_id)
        assert result.status == ApprovalStatus.APPROVED

    **Pluggable strategy**::

        gate.plug("on_submit", my_custom_submit_hook)
        gate.plug("on_resolve", my_audit_logger)

    .. note:: (v1.2.33)

        Maintains its own ``_hooks`` / ``register()`` / ``_run_hooks()``
        pattern that duplicates :class:`meowcat.pluggable.Pluggable`.
        Migration tracked in roadmap B31.
    """

    def __init__(self, default_timeout: float = 60.0) -> None:
        self.default_timeout = default_timeout
        self._pending: dict[str, ApprovalRequest] = {}
        self._futures: dict[str, asyncio.Future[ApprovalRequest]] = {}
        self._hooks: dict[str, list[Callable[..., Any]]] = {}
        self._counter = 0

    # -- Plugin system (lightweight, Pluggable-compatible) ---------------

    def plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """Register a hook callback."""
        self._hooks.setdefault(hook, []).append(fn)

    def unplug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """Unregister hook callback(s)."""
        if hook not in self._hooks:
            return
        if fn is None:
            self._hooks.pop(hook, None)
        else:
            self._hooks[hook] = [f for f in self._hooks[hook] if f is not fn]

    def _run_hooks(self, hook: str, *args: Any, **kwargs: Any) -> None:
        for fn in self._hooks.get(hook, ()):
            try:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    logger.warning(
                        "AsyncApprovalGate hook '%s' returned coroutine; "
                        "hooks should be sync for fire-and-forget",
                        hook,
                    )
            except Exception:
                logger.exception("AsyncApprovalGate hook '%s' failed", hook)

    # -- Core API --------------------------------------------------------

    async def submit(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        *,
        reason: str = "",
        requester: str = "",
        timeout: float | None = None,
    ) -> ApprovalRequest:
        """Submit an action for approval. Returns immediately with PENDING status.

        Call :meth:`wait` to await resolution.
        """
        self._counter += 1
        req = ApprovalRequest(
            request_id=f"apr-{self._counter}",
            action=action,
            params=params or {},
            reason=reason,
            requester=requester,
        )
        self._pending[req.request_id] = req
        loop = asyncio.get_running_loop()
        self._futures[req.request_id] = loop.create_future()

        self._run_hooks("on_submit", req)

        # Auto-timeout
        effective_timeout = timeout if timeout is not None else self.default_timeout

        async def _timeout() -> None:
            await asyncio.sleep(effective_timeout)
            if req.request_id in self._pending and req.status == ApprovalStatus.PENDING:
                with contextlib.suppress(ValueError):
                    self._reject(
                        req.request_id,
                        reason=f"Timeout after {effective_timeout}s",
                        status=ApprovalStatus.TIMED_OUT,
                    )

        asyncio.create_task(_timeout())
        return req

    async def wait(self, request_id: str) -> ApprovalRequest:
        """Wait for an approval request to resolve."""
        if request_id not in self._futures:
            raise KeyError(f"Unknown request: {request_id}")
        return await self._futures[request_id]

    def approve(self, request_id: str, approver: str = "") -> ApprovalRequest:
        """Approve a pending request (sync, immediate)."""
        req = self._pending.get(request_id)
        if req is None:
            raise KeyError(f"Unknown request: {request_id}")
        if req.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} already resolved: {req.status}")
        req.status = ApprovalStatus.APPROVED
        req.approved_by = approver
        self._resolve(request_id, req)
        return req

    def reject(self, request_id: str, reason: str = "") -> ApprovalRequest:
        """Reject a pending request (sync, immediate)."""
        return self._reject(request_id, reason, ApprovalStatus.REJECTED)

    # -- Internal --------------------------------------------------------

    def _reject(
        self,
        request_id: str,
        reason: str,
        status: ApprovalStatus,
    ) -> ApprovalRequest:
        req = self._pending.get(request_id)
        if req is None:
            raise KeyError(f"Unknown request: {request_id}")
        if req.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Request {request_id} already resolved: {req.status}")
        req.status = status
        req.rejected_reason = reason
        self._resolve(request_id, req)
        return req

    def _resolve(self, request_id: str, req: ApprovalRequest) -> None:
        fut = self._futures.pop(request_id, None)
        if fut and not fut.done():
            fut.set_result(req)
        self._run_hooks("on_resolve", req)

    # -- Inspection ------------------------------------------------------

    def list_pending(self) -> list[ApprovalRequest]:
        """List all pending requests."""
        return [r for r in self._pending.values() if r.status == ApprovalStatus.PENDING]

    def get(self, request_id: str) -> ApprovalRequest | None:
        """Get a request by ID."""
        return self._pending.get(request_id)


__all__ = [
    "ApprovalStatus",
    "ApprovalRequest",
    "AsyncApprovalGate",
]
