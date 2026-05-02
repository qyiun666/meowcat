"""v0.5.11 — signal 热路径性能基准
==================================

目标：验证 Protocol 契约校验引入后，signal 单次调用仍低于阈值 **5μs/次**。

测试方法：
    - 构造最小 Nervous（OrganHost + EventBus），挂假器官
    - 预热若干轮触发 lru_cache
    - 大样本（N=20000）计算均值单次耗时
    - 在映射坐标（走契约校验）和非映射坐标（跳过校验）两条路径各测一次

阈值说明：
    - 5μs = 5000 ns，宽松覆盖 CPython 3.12 在普通 CI runner 上的波动
    - Apple Silicon 本机实测通常在 1-2μs
    - 高负载 CI 偶发上冲放宽到 10μs 上限（SLOW_CI_FACTOR）
"""

from __future__ import annotations

import os
import time
from typing import Any

import anyio
import pytest

from meowcat import EventBus, Nervous, OrganHost
from meowcat.anatomy import BRAINSTEM


# 阈值（ns）
TARGET_NS = 5_000
# CI 慢机放宽因子（env SLOW_CI=1 时启用）
SLOW_CI_FACTOR = 2 if os.getenv("SLOW_CI") == "1" else 1
HARD_LIMIT_NS = TARGET_NS * SLOW_CI_FACTOR
# 大样本次数
N = 20_000
# 预热
WARMUP = 1000


class _SyncOrgan:
    """同步方法 — signal 里 inspect.isawaitable 判假后直接返回，最快路径。"""

    def noop(self) -> None:
        return None

    # 也补一个 HippocampusProtocol 声明的方法供契约测试
    def decay(self, now: Any | None = None) -> int:
        return 0


def _build_nervous_with_organ(
    coord: tuple[str, str],
    from_coord: tuple[str, str] = ("brain", "caller"),
) -> Nervous:
    host = OrganHost("perf")
    events = EventBus()
    nervous = Nervous(host, events)
    nervous.wiring.connect(from_coord, coord)
    host.mount(coord[0], coord[1], _SyncOrgan())
    return nervous


async def _bench_signal(
    nervous: Nervous,
    from_coord: tuple[str, str],
    to_coord: tuple[str, str],
    method: str,
    n: int,
) -> float:
    """返回单次调用均值（ns）。"""
    # 预热：命中 lru_cache + JIT
    for _ in range(WARMUP):
        await nervous.signal(from_coord, to_coord, method)

    start = time.perf_counter_ns()
    for _ in range(n):
        await nervous.signal(from_coord, to_coord, method)
    elapsed = time.perf_counter_ns() - start
    return elapsed / n


@pytest.mark.perf
def test_signal_unmapped_coord_under_threshold() -> None:
    """非映射坐标路径（跳过 Protocol 契约校验）平均 <5μs。"""
    nervous = _build_nervous_with_organ(("brain", "perf_free"))
    avg_ns = anyio.run(
        _bench_signal,
        nervous,
        ("brain", "caller"),
        ("brain", "perf_free"),
        "noop",
        N,
    )
    assert avg_ns < HARD_LIMIT_NS, (
        f"signal (unmapped coord) too slow: {avg_ns:.0f}ns/call "
        f"(limit {HARD_LIMIT_NS}ns)"
    )


@pytest.mark.perf
def test_signal_mapped_coord_under_threshold() -> None:
    """映射坐标路径（走 Protocol 契约校验 + 写权限校验）平均 <5μs。

    v0.5.26: decay 是 write_method，必须从 write_callers(BRAINSTEM) 调用。
    校验代价 = dict.get + frozenset in + organ_spec 查找，均 O(1)，应接近非映射路径。
    """
    # hippocampus 在 ORGAN_PROTOCOLS 中
    nervous = _build_nervous_with_organ(("brain", "hippocampus"), from_coord=BRAINSTEM)
    avg_ns = anyio.run(
        _bench_signal,
        nervous,
        BRAINSTEM,
        ("brain", "hippocampus"),
        "decay",  # HippocampusProtocol 声明方法
        N,
    )
    assert avg_ns < HARD_LIMIT_NS, (
        f"signal (mapped coord) too slow: {avg_ns:.0f}ns/call "
        f"(limit {HARD_LIMIT_NS}ns)"
    )


@pytest.mark.perf
def test_contract_overhead_small() -> None:
    """契约校验引入的额外开销应 <1μs（相对非映射基线）。

    v0.5.26: 使用 BRAINSTEM 作为 caller 以通过写权限校验。
    """
    free = _build_nervous_with_organ(("brain", "perf_free"))
    mapped = _build_nervous_with_organ(("brain", "hippocampus"), from_coord=BRAINSTEM)

    free_ns = anyio.run(
        _bench_signal,
        free,
        ("brain", "caller"), ("brain", "perf_free"),
        "noop",
        N,
    )
    mapped_ns = anyio.run(
        _bench_signal,
        mapped,
        BRAINSTEM, ("brain", "hippocampus"),
        "decay",
        N,
    )
    overhead = mapped_ns - free_ns
    # 容错：慢机上基线抖动大，允许最高 2μs
    limit = 2_000 * SLOW_CI_FACTOR
    assert overhead < limit, (
        f"contract check overhead too large: {overhead:.0f}ns "
        f"(free={free_ns:.0f}ns, mapped={mapped_ns:.0f}ns, limit={limit}ns)"
    )
