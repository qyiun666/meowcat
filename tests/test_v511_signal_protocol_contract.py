"""v0.5.11 — Nervous.signal Protocol 契约校验测试
===================================================

契约（对照 docs/v0.5.11/design.md Task 3）：
    1. to_organ 坐标在 ``ORGAN_PROTOCOLS`` 中有 Protocol 映射时，
       ``method`` 必须在该 Protocol 上声明，否则抛 :class:`IllegalNeuralPathError`
    2. to_organ 坐标无 Protocol 映射时，不做 method 校验（保留器官自定义自由度）
    3. 校验发生在 wiring.assert_allowed 之后、真正 dispatch 之前
    4. ``_protocol_public_members`` 使用 lru_cache，第二次查询同 Protocol 命中缓存
"""

from __future__ import annotations

from typing import Any

import pytest

from meowcat import CatBase, IllegalNeuralPathError
from meowcat.anatomy import BRAINSTEM
from meowcat.biology import ORGAN_PROTOCOLS
from meowcat.nervous import _protocol_public_members
from meowcat.protocols import HippocampusProtocol


class _FakeHippocampus:
    """假海马体，只定义被 signal 调用的方法（不声明 Protocol 字段）。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def add_entity(self, entity: Any) -> None:  # Protocol 声明方法
        self.calls.append(("add_entity", (entity,), {}))

    def stats(self, session_id: str | None = None) -> dict[str, Any]:
        self.calls.append(("stats", (session_id,), {}))
        return {"total": 0}

    def no_such_method(self) -> None:  # noqa: D401 — Protocol 未声明方法
        """存在于实现但不在 Protocol 上——signal 应拦截。"""
        self.calls.append(("no_such_method", (), {}))


class _FreeOrgan:
    """未在 ORGAN_SPECS 中声明坐标的器官，调任何方法都应通过契约层。"""

    def anything(self, *args: Any, **kwargs: Any) -> str:
        return "ok"


def _cat_with_edge(from_: tuple[str, str], to: tuple[str, str]) -> CatBase:
    cat = CatBase("test_v511")
    cat.wiring.connect(from_, to)
    return cat


# -- 1. 合法 method 通过 ------------------------------------------

class TestProtocolContractAccept:
    """Protocol 上声明的 method 应正常放行。"""

    async def test_declared_method_passes(self) -> None:
        hippo_coord = ("brain", "hippocampus")
        # 前提：ORGAN_PROTOCOLS 已登记海马体映射
        assert ORGAN_PROTOCOLS.get(hippo_coord) is HippocampusProtocol

        # v0.5.26: add_entity 是 write_method，只有 write_callers 能调。
        # BRAINSTEM 在 write_callers 中，可通过信号调用写方法。
        cat = _cat_with_edge(BRAINSTEM, hippo_coord)
        organ = _FakeHippocampus()
        cat.mount("brain", "hippocampus", organ)

        # add_entity 在 HippocampusProtocol 上声明
        await cat.signal(
            BRAINSTEM, hippo_coord, "add_entity", {"id": "x"},
        )
        assert organ.calls == [("add_entity", ({"id": "x"},), {})]

    async def test_stats_method_passes(self) -> None:
        """stats 也是新补齐的 Protocol 方法（v0.5.11 protocols.py 补丁）。"""
        hippo_coord = ("brain", "hippocampus")
        cat = _cat_with_edge(("brain", "caller"), hippo_coord)
        organ = _FakeHippocampus()
        cat.mount("brain", "hippocampus", organ)

        result = await cat.signal(
            ("brain", "caller"), hippo_coord, "stats",
        )
        assert result == {"total": 0}


# -- 2. 未声明 method 被拦截 --------------------------------------

class TestProtocolContractReject:
    """调用 Protocol 未声明的 method 应抛 IllegalNeuralPathError。"""

    async def test_undeclared_method_raises(self) -> None:
        hippo_coord = ("brain", "hippocampus")
        cat = _cat_with_edge(("brain", "caller"), hippo_coord)
        organ = _FakeHippocampus()
        cat.mount("brain", "hippocampus", organ)

        with pytest.raises(IllegalNeuralPathError) as exc_info:
            await cat.signal(
                ("brain", "caller"), hippo_coord, "no_such_method",
            )
        msg = str(exc_info.value)
        assert "no_such_method" in msg
        assert "HippocampusProtocol" in msg
        # 契约拦截发生在 dispatch 之前，目标方法未被调用
        assert organ.calls == []

    async def test_rejected_before_dispatch(self) -> None:
        """契约失败不应 emit nerve.signal（校验在 emit 之前）。"""
        from meowcat import NerveEvent

        hippo_coord = ("brain", "hippocampus")
        cat = _cat_with_edge(("brain", "caller"), hippo_coord)
        cat.mount("brain", "hippocampus", _FakeHippocampus())

        seen: list[dict] = []

        @cat.on(NerveEvent.SIGNAL)
        def _trap(payload: dict) -> None:  # noqa: ARG001
            seen.append(payload)

        with pytest.raises(IllegalNeuralPathError):
            await cat.signal(
                ("brain", "caller"), hippo_coord, "ghost_method",
            )
        assert seen == []


# -- 3. 无 Protocol 映射坐标保留自由度 -----------------------------

class TestProtocolContractFreeOrgan:
    """未登记 ORGAN_PROTOCOLS 的坐标可任意定义方法。"""

    async def test_unmapped_coord_skips_contract(self) -> None:
        free_coord = ("brain", "free_custom")
        # 前提：该坐标确实不在 ORGAN_PROTOCOLS 里
        assert free_coord not in ORGAN_PROTOCOLS

        cat = _cat_with_edge(("brain", "caller"), free_coord)
        cat.mount("brain", "free_custom", _FreeOrgan())

        result = await cat.signal(
            ("brain", "caller"), free_coord, "anything", 1, key="val",
        )
        assert result == "ok"


# -- 4. lru_cache 行为 --------------------------------------------

class TestProtocolMemberCache:
    """_protocol_public_members 第二次查询同 Protocol 应命中缓存。"""

    def test_same_protocol_returns_cached_set(self) -> None:
        first = _protocol_public_members(HippocampusProtocol)
        second = _protocol_public_members(HippocampusProtocol)
        # lru_cache 返回同一对象
        assert first is second
        # 集合内容包含 v0.5.11 补齐的方法
        assert "add_entity" in first
        assert "stats" in first
        # 不包含 dunder
        assert not any(n.startswith("_") for n in first)
