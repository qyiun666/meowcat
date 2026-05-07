# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""PlanReviser — pluggable strategy chain framework for plan revision.

T-25 (v1.3.6): Framework-level strategy chain executor.  Application layer
registers concrete revision strategies in order; the reviser runs them in
sequence on failure, tracking attempts and enforcing a maximum retry cap.

The framework provides the chain infrastructure and abstract base classes.
It does **not** provide specific revision strategies (retry / switch-role /
split / augment / escalate) — those are app-layer concerns.

Architecture::

    ┌──────────────────────────────────────────────┐
    │  PlanReviser                                 │
    │                                              │
    │  strategies: [Strategy₁, Strategy₂, ...]     │
    │  max_attempts: 3                             │
    │                                              │
    │  revise(ctx)                                 │
    │    for each strategy in chain:               │
    │      if strategy.can_apply(ctx):             │
    │        result = strategy.revise(ctx)         │
    │        if result.success: return result      │
    │    return escalate (chain exhausted)         │
    └──────────────────────────────────────────────┘

Usage::

    reviser = PlanReviser(max_attempts=3)

    # App layer registers strategies
    reviser.register(RetrySameStrategy())
    reviser.register(SwitchRoleStrategy())
    reviser.register(SplitTaskStrategy())
    reviser.register(AugmentContextStrategy())

    # On task failure
    ctx = RevisionContext(
        attempt=1,
        error=TimeoutError("task timed out"),
        task_id="task_01",
        plan={"steps": [...]},
    )
    result = await reviser.revise(ctx)
    if result.success:
        # Re-execute with result.revised_plan
        ...
    else:
        # All strategies exhausted → escalate to user
        ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class PlanReviserConfig:
    """Plan reviser configuration.

    Attributes:
        max_attempts: Maximum total revision attempts before giving up
                      and escalating to the user.  Attempts are counted
                      across all strategies in the chain.
    """

    max_attempts: int = 3


# ── Context & Result ──────────────────────────────────────────────────


@dataclass
class RevisionContext:
    """Context passed to each revision strategy.

    Strategies use this to decide whether they apply and to produce
    a revised plan.

    Attributes:
        attempt:   1-based attempt counter (incremented before each
                   strategy invocation).
        error:     The exception or error description that triggered
                   revision, or ``None`` if revision was requested
                   proactively.
        task_id:   Identifier of the task that failed / needs revision.
        plan:      The current plan state (opaque dict — framework does
                   not interpret its structure).
        result:    The partial result or output from the failed attempt,
                   or ``None``.
        metadata:  Arbitrary app-layer key-value pairs for strategy use
                   (e.g. ``{"role": "coder", "kitten_id": "k_01"}``).
    """

    attempt: int = 1
    error: Exception | str | None = None
    task_id: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevisionResult:
    """Outcome of a single revision strategy or the full chain.

    Attributes:
        success:       Whether the revision produced a viable new plan.
        revised_plan:  The revised plan (if *success* is True), or
                       ``None``.
        action:        Human-readable action label, e.g. ``"retry"``,
                       ``"switch_role"``, ``"split"``, ``"escalate"``.
                       Used for logging and diagnostics.
        message:       Human-readable explanation of what was done
                       or why it failed.
        metadata:      Arbitrary app-layer data attached by the strategy
                       (e.g. new role, dependency changes).
    """

    success: bool = False
    revised_plan: dict[str, Any] | None = None
    action: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Revision Strategy (abstract base) ─────────────────────────────────


class RevisionStrategy(ABC):
    """Abstract base class for a single plan revision strategy.

    Each concrete strategy provides:

    * :attr:`name` — a unique identifier (e.g. ``"retry_same"``).
    * :meth:`can_apply` — predicate: does this strategy apply to the
      given context?
    * :meth:`revise` — produces a :class:`RevisionResult` with a
      (possibly) revised plan.

    Strategies are **stateless** with respect to the PlanReviser —
    they receive all necessary state via :class:`RevisionContext`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy name, e.g. ``"retry_same"``."""
        ...

    @abstractmethod
    async def can_apply(self, ctx: RevisionContext) -> bool:
        """Return ``True`` if this strategy is applicable to *ctx*.

        Typical checks: error type, attempt count, task role, etc.
        """
        ...

    @abstractmethod
    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        """Produce a revised plan (or indicate failure).

        Called only when :meth:`can_apply` returned ``True``.
        Must return a :class:`RevisionResult` — set ``success=True``
        and populate ``revised_plan`` if revision succeeded.
        """
        ...


# ── PlanReviser ───────────────────────────────────────────────────────


class PlanReviser:
    """Pluggable strategy chain for plan revision.

    Strategies are registered in order and evaluated sequentially.
    The first applicable strategy that produces a successful revision
    wins.  If the chain is exhausted or ``max_attempts`` is reached,
    the reviser returns a failure result (signalling escalation).

    Design decisions:

    - **Stateless strategies**: Each strategy is a pure function of
      ``RevisionContext``.  The reviser only tracks the attempt counter.
    - **Ordered chain**: Strategy registration order is significant —
      register more conservative strategies first.
    - **Framework only provides infrastructure**: The five classic
      strategies (retry / switch-role / split / augment / escalate)
      are app-layer concerns.  The framework gives the chain executor.

    Usage::

        reviser = PlanReviser(max_attempts=3)
        reviser.register(MyRetryStrategy())
        reviser.register(MySplitStrategy())

        ctx = RevisionContext(attempt=1, error=e, task_id="t1", plan={...})
        result = await reviser.revise(ctx)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        strategies: Sequence[RevisionStrategy] | None = None,
    ) -> None:
        self._config = PlanReviserConfig(max_attempts=max_attempts)
        self._strategies: list[RevisionStrategy] = (
            list(strategies) if strategies is not None else []
        )
        self._attempt_count: int = 0

    # ── Properties ─────────────────────────────────────────────────

    @property
    def config(self) -> PlanReviserConfig:
        """Current configuration (read-only copy)."""
        return PlanReviserConfig(max_attempts=self._config.max_attempts)

    @property
    def strategies(self) -> list[str]:
        """Ordered list of registered strategy names."""
        return [s.name for s in self._strategies]

    @property
    def attempt_count(self) -> int:
        """Total revision attempts made so far."""
        return self._attempt_count

    # ── Strategy registration ──────────────────────────────────────

    def register(self, strategy: RevisionStrategy) -> None:
        """Register a revision strategy at the end of the chain.

        Strategies are tried in registration order.  Duplicate names
        are allowed (the chain is positional, not name-keyed).

        Args:
            strategy: A concrete :class:`RevisionStrategy` instance.
        """
        self._strategies.append(strategy)

    def unregister(self, name: str) -> bool:
        """Remove the first strategy with the given *name*.

        Returns ``True`` if a strategy was removed, ``False`` if no
        strategy with that name was found.
        """
        for i, s in enumerate(self._strategies):
            if s.name == name:
                self._strategies.pop(i)
                return True
        return False

    def clear(self) -> None:
        """Remove all registered strategies and reset the attempt counter."""
        self._strategies.clear()
        self._attempt_count = 0

    # ── Main entry ─────────────────────────────────────────────────

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        """Run the strategy chain against *ctx*.

        Iterates through registered strategies in order.  For each:

        1. Checks ``can_apply(ctx)``.
        2. If applicable, increments the attempt counter and calls
           ``revise(ctx)``.
        3. If the result is successful, returns it immediately.
        4. If ``max_attempts`` is reached, returns an escalate result.

        If no strategy applies or all applicable strategies fail,
        returns a failure result indicating escalation.

        Args:
            ctx: The revision context (attempt, error, task, plan).

        Returns:
            A :class:`RevisionResult` — ``success=True`` with a revised
            plan, or ``success=False`` signalling escalation.
        """
        for strategy in self._strategies:
            if not await strategy.can_apply(ctx):
                continue

            self._attempt_count += 1

            result = await strategy.revise(ctx)
            if result.success:
                return result

            # Strategy applied but failed — check max attempts
            if self._attempt_count >= self._config.max_attempts:
                return RevisionResult(
                    success=False,
                    action="escalate",
                    message=(
                        f"Max attempts ({self._config.max_attempts}) "
                        f"reached after strategy '{strategy.name}' "
                        f"failed: {result.message}"
                    ),
                    metadata={
                        "attempts": self._attempt_count,
                        "last_strategy": strategy.name,
                        "last_message": result.message,
                    },
                )

        # Chain exhausted — no strategy could help
        return RevisionResult(
            success=False,
            action="escalate",
            message=(
                f"No strategy in chain [{', '.join(self.strategies)}] "
                f"could revise task '{ctx.task_id}'."
            ),
            metadata={
                "attempts": self._attempt_count,
                "chain": self.strategies,
            },
        )

    def reset(self) -> None:
        """Reset the internal attempt counter (does not clear strategies)."""
        self._attempt_count = 0

    # ── Diagnostics ────────────────────────────────────────────────

    def diagnose(self) -> dict[str, Any]:
        """Return diagnostic snapshot of current state."""
        return {
            "max_attempts": self._config.max_attempts,
            "attempt_count": self._attempt_count,
            "strategies": self.strategies,
        }
