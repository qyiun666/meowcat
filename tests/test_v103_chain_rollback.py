# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""
v1.0.3 — Chain 事务性测试
============================

验证:
    1. TestChainRollbackFields     — Chain 支持 rollback_paths 字段
    2. TestChainRunSuccess         — 成功执行不触发回滚
    3. TestChainRunRollback        — 失败时逆序回滚
    4. TestChainRunRollbackErrors  — 回滚异常不掩盖原始异常
    5. TestChainRunEmptyRollback   — 空 rollback_paths 行为不变
"""

from __future__ import annotations

import pytest

from meowcat.assembly import CatBase
from meowcat.chain import Chain
from meowcat.path import Path
from meowcat.testing import make_cat

# -- 辅助 ---------------------------------------------------------

class _MockOrgan:
    """模拟器官，方法可配置为成功或失败。"""

    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self._fail_on = fail_on

    def step_a(self, **kwargs: object) -> dict:
        self.calls.append("step_a")
        if self._fail_on == "step_a":
            raise RuntimeError("step_a failed")
        return {"from_a": "ok"}

    def step_b(self, **kwargs: object) -> dict:
        self.calls.append("step_b")
        if self._fail_on == "step_b":
            raise RuntimeError("step_b failed")
        return {"from_b": "ok"}

    def rollback_a(self, **kwargs: object) -> dict:
        self.calls.append("rollback_a")
        return {"rolled_back": "a"}

    def rollback_b(self, **kwargs: object) -> dict:
        self.calls.append("rollback_b")
        return {"rolled_back": "b"}

    def rollback_fail(self, **kwargs: object) -> dict:
        self.calls.append("rollback_fail")
        raise RuntimeError("rollback_fail failed")

    def diagnose(self) -> dict:
        return {"calls": len(self.calls)}


def _setup_cat_and_registry(fail_on: str | None = None) -> tuple[CatBase, _MockOrgan]:
    """创建带模拟器官和自定义路径的猫 + 链注册中心。

    注册路径: step_a, step_b, rollback_a, rollback_b, rollback_fail
    """
    organ = _MockOrgan(fail_on=fail_on)
    cat = make_cat("test-cat")
    cat.mount("brain", "hippocampus", organ)

    # 注册自定义路径（自环路径：from == to，直接调本地方法）
    cat.path_registry.register(Path(
        "step_a", ("brain", "hippocampus"), ("brain", "hippocampus"),
        "step_a", "write", "步骤 A",
    ))
    cat.path_registry.register(Path(
        "step_b", ("brain", "hippocampus"), ("brain", "hippocampus"),
        "step_b", "write", "步骤 B",
    ))
    cat.path_registry.register(Path(
        "rollback_a", ("brain", "hippocampus"), ("brain", "hippocampus"),
        "rollback_a", "write", "回滚 A",
    ))
    cat.path_registry.register(Path(
        "rollback_b", ("brain", "hippocampus"), ("brain", "hippocampus"),
        "rollback_b", "write", "回滚 B",
    ))
    cat.path_registry.register(Path(
        "rollback_fail", ("brain", "hippocampus"), ("brain", "hippocampus"),
        "rollback_fail", "write", "回滚失败",
    ))

    return cat, organ


# -- 1. Chain rollback_paths 字段 -----------------------------------

class TestChainRollbackFields:
    """Chain 支持 rollback_paths 字段。"""

    def test_default_no_rollback(self) -> None:
        """默认 rollback_paths 为空。"""
        chain = Chain("test", ("a", "b"))
        assert chain.rollback_paths == ()

    def test_with_rollback_paths(self) -> None:
        """可指定 rollback_paths。"""
        chain = Chain(
            "test", ("a", "b"),
            rollback_paths=("r1", "r2"),
        )
        assert chain.rollback_paths == ("r1", "r2")

    def test_rollback_paths_immutable(self) -> None:
        """Chain 是 frozen dataclass，不可变。"""
        chain = Chain("test", ("a",), rollback_paths=("r",))
        with pytest.raises(Exception):  # FrozenInstanceError 或 AttributeError
            chain.rollback_paths = ("x",)  # type: ignore[misc]


# -- 2. 成功执行不触发回滚 ------------------------------------------

class TestChainRunSuccess:
    """Path 全部成功时不触发回滚。"""

    @pytest.mark.anyio
    async def test_success_no_rollback(self) -> None:
        """成功执行 → 不回滚。"""
        cat, organ = _setup_cat_and_registry()

        chain = Chain(
            "test_chain", ("step_a", "step_b"),
            rollback_paths=("rollback_a",),
        )
        cat.chain_registry.register(chain)

        result = await cat.chain_registry.run(cat, "test_chain")
        assert result == {"from_b": "ok"}
        assert organ.calls == ["step_a", "step_b"]

    @pytest.mark.anyio
    async def test_single_step_success(self) -> None:
        """单步成功 → 不回滚。"""
        cat, organ = _setup_cat_and_registry()

        chain = Chain(
            "single", ("step_a",),
            rollback_paths=("rollback_a",),
        )
        cat.chain_registry.register(chain)

        result = await cat.chain_registry.run(cat, "single")
        assert result == {"from_a": "ok"}
        assert organ.calls == ["step_a"]


# -- 3. 失败时逆序回滚 ----------------------------------------------

class TestChainRunRollback:
    """失败时逆序执行 rollback_paths。"""

    @pytest.mark.anyio
    async def test_rollback_on_failure(self) -> None:
        """第一步成功，第二步失败 → 回滚第一步。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_b")

        chain = Chain(
            "test_chain", ("step_a", "step_b"),
            rollback_paths=("rollback_a",),
        )
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_b failed"):
            await cat.chain_registry.run(cat, "test_chain")

        # step_a 成功、step_b 调用后失败（已记录）、rollback_a 被调用
        assert organ.calls == ["step_a", "step_b", "rollback_a"]

    @pytest.mark.anyio
    async def test_rollback_reverse_order(self) -> None:
        """回滚按逆序执行（后注册的路径先回滚）。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_a")

        chain = Chain(
            "test_chain", ("step_a",),
            rollback_paths=("rollback_a", "rollback_b"),
        )
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_a failed"):
            await cat.chain_registry.run(cat, "test_chain")

        # step_a 调用后失败（已记录）、回滚逆序: rollback_b 先, rollback_a 后
        assert organ.calls == ["step_a", "rollback_b", "rollback_a"]

    @pytest.mark.anyio
    async def test_rollback_multiple_after_multi_step(self) -> None:
        """多步成功后某步失败，所有前置步骤的回滚都执行。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_b")

        chain = Chain(
            "multi", ("step_a", "step_b"),
            rollback_paths=("rollback_a", "rollback_b"),
        )
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_b failed"):
            await cat.chain_registry.run(cat, "multi")

        # step_a 成功、step_b 调用后失败（已记录）、回滚逆序
        assert organ.calls == ["step_a", "step_b", "rollback_b", "rollback_a"]


# -- 4. 回滚异常不掩盖原始异常 --------------------------------------

class TestChainRunRollbackErrors:
    """回滚中的异常不掩盖原始异常。"""

    @pytest.mark.anyio
    async def test_rollback_exception_not_masked(self) -> None:
        """回滚步失败 → 原始异常仍然抛出，回滚异常被吞掉。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_a")

        chain = Chain(
            "test_chain", ("step_a",),
            rollback_paths=("rollback_fail", "rollback_a"),
        )
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_a failed"):
            await cat.chain_registry.run(cat, "test_chain")

        # step_a 调用后失败（已记录）、回滚逆序: rollback_a 先执行成功，rollback_fail 后执行失败（已记录）
        assert organ.calls == ["step_a", "rollback_a", "rollback_fail"]

    @pytest.mark.anyio
    async def test_all_rollbacks_fail(self) -> None:
        """所有回滚都失败 → 原始异常仍然抛出。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_a")

        # 两个回滚路径都指向 rollback_fail
        chain = Chain(
            "test_chain", ("step_a",),
            rollback_paths=("rollback_fail", "rollback_fail"),
        )
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_a failed"):
            await cat.chain_registry.run(cat, "test_chain")

        # step_a 调用后失败（已记录）、两个回滚都调用了（失败被吞掉）
        assert organ.calls == ["step_a", "rollback_fail", "rollback_fail"]


# -- 5. 空 rollback_paths 行为不变 ----------------------------------

class TestChainRunEmptyRollback:
    """空 rollback_paths 时行为不变（向后兼容）。"""

    @pytest.mark.anyio
    async def test_empty_rollback_no_effect_on_success(self) -> None:
        """成功 + 空回滚 → 正常返回。"""
        cat, organ = _setup_cat_and_registry()

        chain = Chain("test_chain", ("step_a",))
        cat.chain_registry.register(chain)

        result = await cat.chain_registry.run(cat, "test_chain")
        assert result == {"from_a": "ok"}
        assert organ.calls == ["step_a"]

    @pytest.mark.anyio
    async def test_empty_rollback_on_failure(self) -> None:
        """失败 + 空回滚 → 原始异常直接抛出。"""
        cat, organ = _setup_cat_and_registry(fail_on="step_a")

        chain = Chain("test_chain", ("step_a",))
        cat.chain_registry.register(chain)

        with pytest.raises(RuntimeError, match="step_a failed"):
            await cat.chain_registry.run(cat, "test_chain")

        # step_a 调用后失败（已记录），没有回滚
        assert organ.calls == ["step_a"]

    @pytest.mark.anyio
    async def test_nonexistent_chain_raises(self) -> None:
        """不存在的链路抛出 KeyError。"""
        cat, _ = _setup_cat_and_registry()

        with pytest.raises(KeyError, match="not found"):
            await cat.chain_registry.run(cat, "nonexistent")
