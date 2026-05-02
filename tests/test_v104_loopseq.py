"""
v1.0.4 — LoopSequence 测试
============================

验证:
    1. TestLoopSequenceFields       — LoopSequence dataclass 字段验证
    2. TestLoopSequenceRegistry     — LoopSequenceRegistry CRUD
    3. TestRunSequential            — sequential 模式执行
    4. TestRunSequentialStopOnError — sequential + stop_on_error
    5. TestRunSequentialNoStopError — sequential + 跳过失败
    6. TestRunEventDriven           — event_driven 模式执行
    7. TestRunEventDrivenStopError  — event_driven + stop_on_error
    8. TestRunEdgeCases             — 空序列 / 不存在 LoopSeq / 不存在 Loop
    9. TestCatIntegration           — CatBase.run_loopseq 快捷方法
   10. TestBuiltinLoopseq           — DAILY_MAINTENANCE_SEQ 内置定义
"""

from __future__ import annotations

import pytest

from meowcat.assembly import CatBase
from meowcat.chain import Chain
from meowcat.path import Path
from meowcat.loops import (
    Loop,
    LoopSequence,
    LoopSequenceRegistry,
    DAILY_MAINTENANCE_SEQ,
    BUILTIN_LOOPSEQS,
)


# -- 辅助 ---------------------------------------------------------

class _MockOrgan:
    """模拟器官，记录调用顺序。"""

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

    def step_c(self, **kwargs: object) -> dict:
        self.calls.append("step_c")
        return {"from_c": "ok"}

    def diagnose(self) -> dict:
        return {"calls": len(self.calls)}


def _make_test_loop(name: str, path_name: str, trigger: str | None = None) -> Loop:
    """创建测试用 Loop（单 Path 链）。"""
    return Loop(
        name,
        f"Test loop {name}",
        chain=Chain(f"{name}_chain", (path_name,), f"Chain for {name}"),
        trigger=trigger,
    )


def _setup_cat_with_loops(
    *loop_defs: tuple[str, str],  # (loop_name, path_name)
    fail_on: str | None = None,
) -> CatBase:
    """创建带模拟器官和测试 Loop 的猫。

    每个 loop 有对应 path: brain:hippocampus → brain:hippocampus.xxx
    """
    organ = _MockOrgan(fail_on=fail_on)
    cat = CatBase("test-cat")
    cat.mount("brain", "hippocampus", organ)

    # 注册路径
    for _, path_name in loop_defs:
        if path_name not in {"step_a", "step_b", "step_c"}:
            # 动态路径名也注册
            cat.path_registry.register(Path(
                path_name, ("brain", "hippocampus"), ("brain", "hippocampus"),
                "step_a" if path_name.startswith("step_a") else
                "step_b" if path_name.startswith("step_b") else "step_c",
                "write", f"Path {path_name}",
            ))

    # 确保基础路径存在
    for pn in ("step_a", "step_b", "step_c"):
        if cat.path_registry.get(pn) is None:
            cat.path_registry.register(Path(
                pn, ("brain", "hippocampus"), ("brain", "hippocampus"),
                pn, "write", f"Path {pn}",
            ))

    # 注册 loop 和其 chain
    for loop_name, path_name in loop_defs:
        chain = Chain(f"{loop_name}_chain", (path_name,),
                      f"Chain for {loop_name}")
        cat.chain_registry.register(chain)
        cat.loop_registry.register(Loop(
            loop_name, f"Test loop {loop_name}", chain=chain,
        ))

    return cat


# -- 1. LoopSequence dataclass -------------------------------------

class TestLoopSequenceFields:
    """LoopSequence 字段与验证。"""

    def test_default_fields(self) -> None:
        """默认字段值。"""
        seq = LoopSequence("test")
        assert seq.name == "test"
        assert seq.description == ""
        assert seq.loops == ()
        assert seq.mode == "sequential"
        assert seq.stop_on_error is True

    def test_custom_fields(self) -> None:
        """自定义所有字段。"""
        seq = LoopSequence(
            "seq1",
            description="A test sequence",
            loops=("a", "b"),
            mode="event_driven",
            stop_on_error=False,
        )
        assert seq.name == "seq1"
        assert seq.description == "A test sequence"
        assert seq.loops == ("a", "b")
        assert seq.mode == "event_driven"
        assert seq.stop_on_error is False

    def test_invalid_mode(self) -> None:
        """非法 mode 抛 ValueError。"""
        with pytest.raises(ValueError, match="mode must be"):
            LoopSequence("bad", mode="parallel")

    def test_frozen_immutable(self) -> None:
        """LoopSequence 不可变。"""
        seq = LoopSequence("test", loops=("a",))
        with pytest.raises(Exception):
            seq.loops = ("b",)  # type: ignore[misc]


# -- 2. LoopSequenceRegistry CRUD ----------------------------------

class TestLoopSequenceRegistry:
    """注册中心 CRUD。"""

    def test_register_and_get(self) -> None:
        """注册并查询。"""
        registry = LoopSequenceRegistry()
        seq = LoopSequence("seq1", loops=("a", "b"))
        registry.register(seq)
        assert registry.get("seq1") is seq

    def test_get_nonexistent(self) -> None:
        """不存在的返回 None。"""
        registry = LoopSequenceRegistry()
        assert registry.get("missing") is None

    def test_list_all(self) -> None:
        """列出所有已注册。"""
        registry = LoopSequenceRegistry()
        s1 = LoopSequence("s1")
        s2 = LoopSequence("s2")
        registry.register(s1)
        registry.register(s2)
        all_seqs = registry.list_all()
        assert len(all_seqs) == 2
        assert s1 in all_seqs
        assert s2 in all_seqs

    def test_register_overwrite(self) -> None:
        """同名覆盖旧值。"""
        registry = LoopSequenceRegistry()
        s1 = LoopSequence("seq1", loops=("a",))
        s2 = LoopSequence("seq1", loops=("b", "c"))
        registry.register(s1)
        registry.register(s2)
        assert registry.get("seq1") is s2
        assert len(registry.list_all()) == 1

    def test_register_type_error(self) -> None:
        """非 LoopSequence 抛 TypeError。"""
        registry = LoopSequenceRegistry()
        with pytest.raises(TypeError, match="LoopSequence"):
            registry.register("not-a-seq")  # type: ignore[arg-type]


# -- 3. sequential 模式 --------------------------------------------

class TestRunSequential:
    """顺序执行 loops。"""

    @pytest.mark.asyncio
    async def test_sequential_two_loops(self) -> None:
        """两个 Loop 顺序执行，结果传递。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"), ("loop_b", "step_b"))
        seq = LoopSequence("test_seq", loops=("loop_a", "loop_b"))
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        # step_b 最后执行，返回 {"from_b": "ok"}
        assert result == {"from_b": "ok"}

    @pytest.mark.asyncio
    async def test_sequential_passes_result(self) -> None:
        """前一步结果传给下一步。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"), ("loop_b", "step_b"))
        seq = LoopSequence("test_seq", loops=("loop_a", "loop_b"))
        cat.loopseq_registry.register(seq)

        await cat.loopseq_registry.run(cat, "test_seq")
        organ = cat.organ("brain", "hippocampus")
        # 两个 step 都被调用
        assert organ.calls == ["step_a", "step_b"]

    @pytest.mark.asyncio
    async def test_sequential_single_loop(self) -> None:
        """单个 Loop 正常执行。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"))
        seq = LoopSequence("test_seq", loops=("loop_a",))
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        assert result == {"from_a": "ok"}


# -- 4. sequential + stop_on_error ---------------------------------

class TestRunSequentialStopOnError:
    """sequential + stop_on_error 行为。"""

    @pytest.mark.asyncio
    async def test_stop_on_error_true(self) -> None:
        """stop_on_error=True → 失败立即抛异常。"""
        cat = _setup_cat_with_loops(
            ("loop_a", "step_a"), ("loop_b", "step_b"),
            fail_on="step_a",
        )
        seq = LoopSequence("test_seq", loops=(
            "loop_a", "loop_b"), stop_on_error=True)
        cat.loopseq_registry.register(seq)

        with pytest.raises(RuntimeError, match="step_a failed"):
            await cat.loopseq_registry.run(cat, "test_seq")

        organ = cat.organ("brain", "hippocampus")
        # step_a 被调用（失败），step_b 未执行
        assert organ.calls == ["step_a"]

    @pytest.mark.asyncio
    async def test_stop_on_error_true_later_fails(self) -> None:
        """第一步成功、第二步失败。"""
        cat = _setup_cat_with_loops(
            ("loop_a", "step_a"), ("loop_b", "step_b"),
            fail_on="step_b",
        )
        seq = LoopSequence("test_seq", loops=(
            "loop_a", "loop_b"), stop_on_error=True)
        cat.loopseq_registry.register(seq)

        with pytest.raises(RuntimeError, match="step_b failed"):
            await cat.loopseq_registry.run(cat, "test_seq")

        organ = cat.organ("brain", "hippocampus")
        # step_a 成功，step_b 失败
        assert organ.calls == ["step_a", "step_b"]


# -- 5. sequential + stop_on_error=False ---------------------------

class TestRunSequentialNoStopError:
    """sequential + 跳过失败。"""

    @pytest.mark.asyncio
    async def test_skip_failed_loop_continue(self) -> None:
        """stop_on_error=False → 跳过失败的 Loop 继续执行。"""
        cat = _setup_cat_with_loops(
            ("loop_a", "step_a"), ("loop_b", "step_b"), ("loop_c", "step_c"),
            fail_on="step_a",
        )
        seq = LoopSequence(
            "test_seq", loops=("loop_a", "loop_b", "loop_c"),
            stop_on_error=False,
        )
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        # loop_b 和 loop_c 正常执行，最后一步 step_c 的结果
        assert result == {"from_c": "ok"}

        organ = cat.organ("brain", "hippocampus")
        # step_a 调用后失败，step_b, step_c 继续
        assert organ.calls == ["step_a", "step_b", "step_c"]


# -- 6. event_driven 模式 ------------------------------------------

class TestRunEventDriven:
    """event_driven 并发执行。"""

    @pytest.mark.asyncio
    async def test_event_driven_two_loops(self) -> None:
        """两个 Loop 并发执行。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"), ("loop_b", "step_b"))
        seq = LoopSequence("test_seq", loops=(
            "loop_a", "loop_b"), mode="event_driven")
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        # 返回 {loop_name: result, ...}
        assert result["loop_a"] == {"from_a": "ok"}
        assert result["loop_b"] == {"from_b": "ok"}

    @pytest.mark.asyncio
    async def test_event_driven_single_loop(self) -> None:
        """单个 Loop 并发执行。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"))
        seq = LoopSequence("test_seq", loops=("loop_a",), mode="event_driven")
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        assert result["loop_a"] == {"from_a": "ok"}


# -- 7. event_driven + stop_on_error -------------------------------

class TestRunEventDrivenStopError:
    """event_driven + stop_on_error 行为。"""

    @pytest.mark.asyncio
    async def test_stop_on_error_true_concurrent(self) -> None:
        """stop_on_error=True → 任一失败整体抛异常。"""
        cat = _setup_cat_with_loops(
            ("loop_a", "step_a"), ("loop_b", "step_b"),
            fail_on="step_b",
        )
        seq = LoopSequence(
            "test_seq", loops=("loop_a", "loop_b"),
            mode="event_driven", stop_on_error=True,
        )
        cat.loopseq_registry.register(seq)

        # 一个失败，gather 会传播异常
        with pytest.raises(RuntimeError, match="step_b failed"):
            await cat.loopseq_registry.run(cat, "test_seq")

    @pytest.mark.asyncio
    async def test_stop_on_error_false_concurrent(self) -> None:
        """stop_on_error=False → 失败 Loop 返回 _error。"""
        cat = _setup_cat_with_loops(
            ("loop_a", "step_a"), ("loop_b", "step_b"),
            fail_on="step_b",
        )
        seq = LoopSequence(
            "test_seq", loops=("loop_a", "loop_b"),
            mode="event_driven", stop_on_error=False,
        )
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "test_seq")
        assert result["loop_a"] == {"from_a": "ok"}
        assert "_error" in result["loop_b"]


# -- 8. 边界情况 ---------------------------------------------------

class TestRunEdgeCases:
    """边界/错误情况。"""

    @pytest.mark.asyncio
    async def test_empty_sequence(self) -> None:
        """空 loops 序列 → 返回空结果。"""
        cat = _setup_cat_with_loops()
        seq = LoopSequence("empty_seq", loops=())
        cat.loopseq_registry.register(seq)

        result = await cat.loopseq_registry.run(cat, "empty_seq")
        assert result == {"": {}}

    @pytest.mark.asyncio
    async def test_nonexistent_loopseq_raises(self) -> None:
        """不存在的 LoopSequence 抛 KeyError。"""
        cat = _setup_cat_with_loops()
        with pytest.raises(KeyError, match="not found"):
            await cat.loopseq_registry.run(cat, "nonexistent")

    @pytest.mark.asyncio
    async def test_nonexistent_loop_raises(self) -> None:
        """引用不存在的 Loop 抛 KeyError。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"))
        seq = LoopSequence("test_seq", loops=("loop_a", "nonexistent_loop"))
        cat.loopseq_registry.register(seq)

        with pytest.raises(KeyError):
            await cat.loopseq_registry.run(cat, "test_seq")


# -- 9. CatBase 集成 -----------------------------------------------

class TestCatIntegration:
    """CatBase.run_loopseq 快捷方法。"""

    @pytest.mark.asyncio
    async def test_run_loopseq_shortcut(self) -> None:
        """cat.run_loopseq() 等价于 cat.loopseq_registry.run()。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"), ("loop_b", "step_b"))
        seq = LoopSequence("test_seq", loops=("loop_a", "loop_b"))
        cat.loopseq_registry.register(seq)

        result = await cat.run_loopseq("test_seq")
        assert result == {"from_b": "ok"}

    @pytest.mark.asyncio
    async def test_run_loopseq_with_input(self) -> None:
        """run_loopseq 支持 initial_input。"""
        cat = _setup_cat_with_loops(("loop_a", "step_a"))
        seq = LoopSequence("test_seq", loops=("loop_a",))
        cat.loopseq_registry.register(seq)

        result = await cat.run_loopseq("test_seq", custom="value")
        assert result == {"from_a": "ok"}


# -- 10. 内置 LoopSequence -----------------------------------------

class TestBuiltinLoopseq:
    """DAILY_MAINTENANCE_SEQ 内置定义。"""

    def test_daily_maintenance_exists(self) -> None:
        """DAILY_MAINTENANCE_SEQ 有正确的名称和 loops。"""
        assert DAILY_MAINTENANCE_SEQ.name == "daily_maintenance"
        assert DAILY_MAINTENANCE_SEQ.loops == ("maintenance", "diagnostic")
        assert DAILY_MAINTENANCE_SEQ.mode == "sequential"
        assert DAILY_MAINTENANCE_SEQ.stop_on_error is True

    def test_builtin_loopseqs_contains(self) -> None:
        """BUILTIN_LOOPSEQS 包含 DAILY_MAINTENANCE_SEQ。"""
        assert DAILY_MAINTENANCE_SEQ in BUILTIN_LOOPSEQS
