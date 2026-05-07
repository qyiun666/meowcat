# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for PlanReviser strategy chain (T-25 / v1.3.6)."""

from __future__ import annotations

import pytest

from meowcat.plan_reviser import (
    PlanReviser,
    PlanReviserConfig,
    RevisionContext,
    RevisionResult,
    RevisionStrategy,
)


# ── PlanReviserConfig ─────────────────────────────────────────────────


class TestPlanReviserConfig:
    """PlanReviserConfig dataclass."""

    def test_defaults(self):
        cfg = PlanReviserConfig()
        assert cfg.max_attempts == 3

    def test_custom(self):
        cfg = PlanReviserConfig(max_attempts=5)
        assert cfg.max_attempts == 5


# ── RevisionContext ───────────────────────────────────────────────────


class TestRevisionContext:
    """RevisionContext dataclass."""

    def test_defaults(self):
        ctx = RevisionContext()
        assert ctx.attempt == 1
        assert ctx.error is None
        assert ctx.task_id == ""
        assert ctx.plan == {}
        assert ctx.result is None
        assert ctx.metadata == {}

    def test_custom(self):
        ctx = RevisionContext(
            attempt=2,
            error="timeout",
            task_id="t01",
            plan={"steps": ["a", "b"]},
            result={"partial": True},
            metadata={"role": "coder"},
        )
        assert ctx.attempt == 2
        assert ctx.error == "timeout"
        assert ctx.task_id == "t01"
        assert ctx.plan == {"steps": ["a", "b"]}
        assert ctx.result == {"partial": True}
        assert ctx.metadata == {"role": "coder"}


# ── RevisionResult ────────────────────────────────────────────────────


class TestRevisionResult:
    """RevisionResult dataclass."""

    def test_defaults(self):
        r = RevisionResult()
        assert r.success is False
        assert r.revised_plan is None
        assert r.action == ""
        assert r.message == ""
        assert r.metadata == {}

    def test_success(self):
        r = RevisionResult(
            success=True,
            revised_plan={"steps": ["x"]},
            action="retry",
            message="retrying with delay",
        )
        assert r.success is True
        assert r.revised_plan == {"steps": ["x"]}
        assert r.action == "retry"


# ── RevisionStrategy (abstract base) ──────────────────────────────────


class _EmptyStrategy(RevisionStrategy):
    """Minimal concrete strategy — raises NotImplementedError on methods."""

    @property
    def name(self) -> str:
        return "empty"

    async def can_apply(self, ctx: RevisionContext) -> bool:
        raise NotImplementedError

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        raise NotImplementedError


class TestRevisionStrategyBase:
    """RevisionStrategy abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            RevisionStrategy()  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self):
        s = _EmptyStrategy()
        assert s.name == "empty"


# ── PlanReviser helpers ───────────────────────────────────────────────


class _AlwaysApply(RevisionStrategy):
    """Strategy that always applies and succeeds."""

    @property
    def name(self) -> str:
        return "always_apply"

    async def can_apply(self, ctx: RevisionContext) -> bool:
        return True

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        return RevisionResult(
            success=True,
            revised_plan=ctx.plan,
            action="always",
            message="always works",
        )


class _NeverApply(RevisionStrategy):
    """Strategy that never applies."""

    @property
    def name(self) -> str:
        return "never_apply"

    async def can_apply(self, ctx: RevisionContext) -> bool:
        return False

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        return RevisionResult(success=False, action="unreachable")


class _FailStrategy(RevisionStrategy):
    """Strategy that applies but always fails."""

    def __init__(self, name: str = "fails"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def can_apply(self, ctx: RevisionContext) -> bool:
        return True

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        return RevisionResult(
            success=False,
            action=self._name,
            message=f"{self._name} failed",
        )


class _ConditionalStrategy(RevisionStrategy):
    """Strategy that applies only when a condition is met."""

    def __init__(self, name: str, *, applies: bool, succeed: bool = True):
        self._name = name
        self._applies = applies
        self._succeed = succeed

    @property
    def name(self) -> str:
        return self._name

    async def can_apply(self, ctx: RevisionContext) -> bool:
        return self._applies

    async def revise(self, ctx: RevisionContext) -> RevisionResult:
        if self._succeed:
            return RevisionResult(
                success=True,
                revised_plan={"from": self._name},
                action=self._name,
                message="ok",
            )
        return RevisionResult(success=False, action=self._name, message="nope")


# ── PlanReviser: constructor / registration ───────────────────────────


class TestPlanReviserConstruct:
    """PlanReviser constructor and initial state."""

    def test_default_construct(self):
        r = PlanReviser()
        assert r.config.max_attempts == 3
        assert r.strategies == []
        assert r.attempt_count == 0

    def test_custom_max_attempts(self):
        r = PlanReviser(max_attempts=5)
        assert r.config.max_attempts == 5

    def test_construct_with_strategies(self):
        s = _AlwaysApply()
        r = PlanReviser(strategies=[s])
        assert r.strategies == ["always_apply"]
        assert r.attempt_count == 0


class TestPlanReviserRegister:
    """Strategy registration and lifecycle."""

    def test_register(self):
        r = PlanReviser()
        r.register(_AlwaysApply())
        assert r.strategies == ["always_apply"]

    def test_register_order_preserved(self):
        r = PlanReviser()
        r.register(_AlwaysApply())
        r.register(_FailStrategy("second"))
        assert r.strategies == ["always_apply", "second"]

    def test_unregister_by_name(self):
        r = PlanReviser()
        r.register(_FailStrategy("a"))
        r.register(_FailStrategy("b"))
        assert r.unregister("a") is True
        assert r.strategies == ["b"]

    def test_unregister_first_match_only(self):
        r = PlanReviser()
        r.register(_FailStrategy("dup"))
        r.register(_FailStrategy("dup"))
        r.unregister("dup")
        assert r.strategies == ["dup"]  # Only first removed

    def test_unregister_missing(self):
        r = PlanReviser()
        assert r.unregister("ghost") is False

    def test_clear(self):
        r = PlanReviser()
        r.register(_AlwaysApply())
        r.register(_FailStrategy("b"))
        r.clear()
        assert r.strategies == []
        assert r.attempt_count == 0


class TestPlanReviserReset:
    """Attempt counter reset."""

    @pytest.mark.anyio
    async def test_reset_counter(self):
        r = PlanReviser(max_attempts=10)
        r.register(_FailStrategy("a"))
        r.register(_FailStrategy("b"))
        r.register(_FailStrategy("c"))
        ctx = RevisionContext(task_id="t1")
        # Run through a few failures
        await r.revise(ctx)
        r.reset()
        assert r.attempt_count == 0
        assert r.strategies == ["a", "b", "c"]  # Strategies untouched


# ── PlanReviser: revise ───────────────────────────────────────────────


class TestPlanReviserRevise:
    """revise() strategy chain execution."""

    @pytest.mark.anyio
    async def test_first_strategy_wins(self):
        r = PlanReviser()
        r.register(_AlwaysApply())
        r.register(_FailStrategy("second"))
        ctx = RevisionContext(task_id="t1", plan={"v": 1})
        result = await r.revise(ctx)
        assert result.success is True
        assert result.action == "always"
        assert r.attempt_count == 1

    @pytest.mark.anyio
    async def test_skips_non_applicable(self):
        r = PlanReviser()
        r.register(_NeverApply())
        r.register(_AlwaysApply())
        ctx = RevisionContext(task_id="t2")
        result = await r.revise(ctx)
        assert result.success is True
        assert result.action == "always"
        assert r.attempt_count == 1

    @pytest.mark.anyio
    async def test_falls_through_to_next_on_failure(self):
        r = PlanReviser()
        r.register(_FailStrategy("first"))
        r.register(_AlwaysApply())
        ctx = RevisionContext(task_id="t3")
        result = await r.revise(ctx)
        assert result.success is True
        assert result.action == "always"
        assert r.attempt_count == 2  # first failed, second succeeded

    @pytest.mark.anyio
    async def test_max_attempts_exceeded(self):
        r = PlanReviser(max_attempts=1)
        r.register(_FailStrategy("a"))
        r.register(_AlwaysApply())
        ctx = RevisionContext(task_id="t4")
        result = await r.revise(ctx)
        assert result.success is False
        assert result.action == "escalate"
        assert "Max attempts" in result.message
        assert r.attempt_count == 1

    @pytest.mark.anyio
    async def test_chain_exhausted(self):
        r = PlanReviser()
        r.register(_NeverApply())
        ctx = RevisionContext(task_id="t5")
        result = await r.revise(ctx)
        assert result.success is False
        assert result.action == "escalate"
        assert "No strategy" in result.message
        assert r.attempt_count == 0

    @pytest.mark.anyio
    async def test_empty_chain(self):
        r = PlanReviser()
        ctx = RevisionContext(task_id="t6")
        result = await r.revise(ctx)
        assert result.success is False
        assert result.action == "escalate"

    @pytest.mark.anyio
    async def test_all_strategies_fail_within_limit(self):
        r = PlanReviser(max_attempts=5)
        r.register(_FailStrategy("a"))
        r.register(_FailStrategy("b"))
        ctx = RevisionContext(task_id="t7")
        result = await r.revise(ctx)
        assert result.success is False
        assert result.action == "escalate"
        assert "No strategy" in result.message
        assert r.attempt_count == 2  # Both failed, chain exhausted

    @pytest.mark.anyio
    async def test_conditional_apply(self):
        r = PlanReviser()
        r.register(_ConditionalStrategy("cond", applies=False, succeed=True))
        r.register(_ConditionalStrategy("winner", applies=True, succeed=True))
        ctx = RevisionContext(task_id="t8")
        result = await r.revise(ctx)
        assert result.success is True
        assert result.action == "winner"

    @pytest.mark.anyio
    async def test_attempt_counter_incremented(self):
        r = PlanReviser(max_attempts=5)
        r.register(_FailStrategy("a"))
        r.register(_FailStrategy("b"))
        r.register(_AlwaysApply())
        ctx = RevisionContext(task_id="t9")
        result = await r.revise(ctx)
        assert result.success is True
        assert r.attempt_count == 3

    @pytest.mark.anyio
    async def test_context_attempt_updated(self):
        r = PlanReviser(max_attempts=5)
        r.register(_FailStrategy("a"))
        r.register(_AlwaysApply())
        ctx = RevisionContext(task_id="t10", attempt=99)
        result = await r.revise(ctx)
        assert result.success is True
        # ctx.attempt is no longer mutated by revise() — use attempt_count instead
        assert r.attempt_count == 2


# ── PlanReviser: diagnose ─────────────────────────────────────────────


class TestPlanReviserDiagnose:
    """Diagnose snapshot."""

    def test_diagnose_empty(self):
        r = PlanReviser(max_attempts=4)
        diag = r.diagnose()
        assert diag["max_attempts"] == 4
        assert diag["attempt_count"] == 0
        assert diag["strategies"] == []

    def test_diagnose_with_strategies(self):
        r = PlanReviser()
        r.register(_AlwaysApply())
        r.register(_FailStrategy("b"))
        diag = r.diagnose()
        assert diag["strategies"] == ["always_apply", "b"]
        assert diag["max_attempts"] == 3
