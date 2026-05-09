# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat v1.2.18 — 事件类型安全测试.

验证: payload TypedDict 可 import、EVENT_PAYLOAD_MAP 全覆盖、
现有 emit 模式向后兼容、TypedDict 可用于 handler 类型注解。
"""

from __future__ import annotations

from typing import get_type_hints

import pytest

from meowcat import (
    ALL_EVENTS,
    EventBus,
    KittenEvent,
    Lifecycle,
    NerveEvent,
)
from meowcat.events_payloads import (
    EVENT_PAYLOAD_MAP,
    CompressPostPayload,
    CompressPrePayload,
    CrystallizePayload,
    FusionColonyPayload,
    FusionSelfPayload,
    FusionTriggerEndPayload,
    FusionTriggerStartPayload,
    GrowthAnomalyPayload,
    GrowthCorrectionPayload,
    KittenCompletedPayload,
    KittenDismissedPayload,
    KittenExecutingPayload,
    KittenMergeAbsorbedPayload,
    KittenSpawnedPayload,
    KittenStuckPayload,
    LifecycleShutdownPayload,
    LifecycleStartPayload,
    LocatePostPayload,
    LocatePrePayload,
    NerveSignalPayload,
    OrchestrateEndPayload,
    OrchestrateStartPayload,
    PerceiveEndPayload,
    PerceiveStartPayload,
    RememberPostPayload,
    RememberPrePayload,
    RoleEmergePayload,
    RouteDecidedPayload,
    SelfReflectPayload,
    SelfSnapshotPayload,
)

# -- TypedDict 导入 + 存在性 -----------------------------------------------

class TestPayloadImports:
    """所有 TypedDict 类型可从 meowcat 和 events_payloads 导入。"""

    def test_import_from_meowcat(self) -> None:
        """通过 meowcat 顶层包可导入所有 payload TypedDict."""
        from meowcat import (
            NerveSignalPayload,
            PerceiveStartPayload,
        )
        assert NerveSignalPayload is not None
        assert PerceiveStartPayload is not None

    def test_import_from_payloads_module(self) -> None:
        """通过 events_payloads 模块可直接导入."""
        from meowcat.events_payloads import EVENT_PAYLOAD_MAP, NerveSignalPayload
        assert isinstance(NerveSignalPayload, type)
        assert isinstance(EVENT_PAYLOAD_MAP, dict)

    def test_all_payloads_are_types(self) -> None:
        """所有 payload 类型都是可实例化的 dict 子类型."""
        payload_types = [
            LifecycleStartPayload, LifecycleShutdownPayload,
            PerceiveStartPayload, PerceiveEndPayload,
            NerveSignalPayload,
            LocatePrePayload, LocatePostPayload, RouteDecidedPayload,
            RememberPrePayload, RememberPostPayload,
            CompressPrePayload, CompressPostPayload,
            OrchestrateStartPayload, OrchestrateEndPayload,
            GrowthAnomalyPayload, GrowthCorrectionPayload,
            CrystallizePayload, RoleEmergePayload,
            KittenSpawnedPayload, KittenExecutingPayload, KittenCompletedPayload,
            KittenStuckPayload, KittenDismissedPayload, KittenMergeAbsorbedPayload,
            SelfSnapshotPayload, SelfReflectPayload,
            FusionSelfPayload, FusionColonyPayload,
            FusionTriggerStartPayload, FusionTriggerEndPayload,
        ]
        for pt in payload_types:
            assert isinstance(pt, type), f"{pt} is not a type"
            # TypedDict types are types


# -- EVENT_PAYLOAD_MAP 全覆盖 ------------------------------------------------

class TestPayloadMapCoverage:
    """EVENT_PAYLOAD_MAP 覆盖 ALL_EVENTS 中所有事件名."""

    def test_all_events_have_payload_type(self) -> None:
        """ALL_EVENTS 中每个事件名在 EVENT_PAYLOAD_MAP 中都有对应类型."""
        for event_name in ALL_EVENTS:
            assert event_name in EVENT_PAYLOAD_MAP, (
                f"Missing payload type for event '{event_name}'"
            )

    def test_no_orphan_payload_types(self) -> None:
        """EVENT_PAYLOAD_MAP 中的每个键都是有效的事件名."""
        for event_name in EVENT_PAYLOAD_MAP:
            assert event_name in ALL_EVENTS, (
                f"EVENT_PAYLOAD_MAP has orphan entry '{event_name}' "
                f"not in ALL_EVENTS"
            )


# -- 向后兼容: 现有 emit 模式不受影响 ------------------------------------

class TestBackwardCompatibility:
    """框架 emit 代码正常执行，payload TypedDict 不影响运行时."""

    @pytest.mark.anyio
    async def test_nerve_signal_emit_works(self) -> None:
        """nervous.py 的 NerveEvent.SIGNAL emit 正常触发 handler."""
        bus = EventBus()
        received: list[dict] = []

        async def on_signal(payload: dict) -> None:
            received.append(payload)

        bus.on(NerveEvent.SIGNAL, on_signal)
        payload = {"from": ("brain", "thalamus"), "to": (
            "brain", "cerebrum"), "method": "locate"}
        await bus.emit(NerveEvent.SIGNAL, payload)
        assert len(received) == 1
        assert received[0]["from"] == ("brain", "thalamus")
        assert received[0]["to"] == ("brain", "cerebrum")
        assert received[0]["method"] == "locate"

    @pytest.mark.anyio
    async def test_perceive_events_emit_work(self) -> None:
        """reflex.py 的 PERCEIVE_START/END emit 正常触发 handler."""
        bus = EventBus()
        events: list[str] = []
        payloads: list[dict] = []

        async def on_event(payload: dict) -> None:
            events.append("hit")
            payloads.append(payload)

        bus.on(Lifecycle.PERCEIVE_START, on_event)
        bus.on(Lifecycle.PERCEIVE_END, on_event)

        await bus.emit(Lifecycle.PERCEIVE_START, {"input": "hello", "reflex_name": "text"})
        await bus.emit(Lifecycle.PERCEIVE_END, {"reflex_name": "text", "reply": "meow"})

        assert len(events) == 2
        assert payloads[1]["reply"] == "meow"

    @pytest.mark.anyio
    async def test_lifecycle_events_emit_work(self) -> None:
        """assembly.py 的 Lifecycle START/SHUTDOWN emit 正常触发."""
        bus = EventBus()
        received: list[dict] = []

        def on_lifecycle(payload: dict) -> None:
            received.append(payload)

        bus.on(Lifecycle.START, on_lifecycle)
        bus.on(Lifecycle.SHUTDOWN, on_lifecycle)

        await bus.emit(Lifecycle.START, {"cat": "me"})
        await bus.emit(Lifecycle.SHUTDOWN, {"cat": "me"})

        assert len(received) == 2

    @pytest.mark.anyio
    async def test_handler_without_payload_still_works(self) -> None:
        """无参 handler 仍然工作（向后兼容）."""
        bus = EventBus()
        received: list[str] = []

        def on_event() -> None:
            received.append("fired")

        bus.on(Lifecycle.START, on_event)
        await bus.emit(Lifecycle.START, {"cat": "me"})
        assert received == ["fired"]

    @pytest.mark.anyio
    async def test_off_then_emit_no_error(self) -> None:
        """取消订阅后 emit 不会报错."""
        bus = EventBus()
        hits: list[str] = []

        def handler(payload: dict) -> None:
            hits.append("on")

        bus.on(KittenEvent.SPAWNED, handler)
        assert bus.off(KittenEvent.SPAWNED, handler) is True
        await bus.emit(KittenEvent.SPAWNED, {"kitten_id": "k1", "parent_id": "p1", "task": {}, "role": "worker"})
        assert hits == []

    @pytest.mark.anyio
    async def test_all_event_names_emit_without_error(self) -> None:
        """每个 ALL_EVENTS 事件名都可以 emit（不注册 handler 也无异常）."""
        bus = EventBus()
        # 用一个 handler 捕获但不验证内容

        async def noop_handler(payload: dict) -> None:
            pass

        for event_name in ALL_EVENTS:
            bus.on(event_name, noop_handler)
            await bus.emit(event_name, {"test": True})
            bus.clear(event_name)


# -- TypedDict 可用于 handler 类型注解 ----------------------------------------

class TestTypedDictAnnotation:
    """TypedDict 作为 handler 参数类型注解正常使用."""

    def test_nerve_signal_payload_has_expected_keys(self) -> None:
        """NerveSignalPayload TypedDict 定义正确的键."""
        hints = get_type_hints(NerveSignalPayload)
        assert "from_" in hints  # 'from' 是关键字，用 from_
        assert "to" in hints
        assert "method" in hints

    def test_perceive_start_payload_keys(self) -> None:
        """PerceiveStartPayload 定义正确的键."""
        hints = get_type_hints(PerceiveStartPayload)
        assert "input" in hints
        assert "reflex_name" in hints

    def test_perceive_end_payload_keys(self) -> None:
        """PerceiveEndPayload 定义正确的键."""
        hints = get_type_hints(PerceiveEndPayload)
        assert "reflex_name" in hints
        assert "reply" in hints

    def test_lifecycle_payload_keys(self) -> None:
        """LifecycleStartPayload / LifecycleShutdownPayload 定义 cat 键."""
        hints_start = get_type_hints(LifecycleStartPayload)
        hints_shutdown = get_type_hints(LifecycleShutdownPayload)
        assert "cat" in hints_start
        assert "cat" in hints_shutdown

    def test_kitten_payloads_have_expected_keys(self) -> None:
        """Kitten 系列 TypedDict 定义正确的键."""
        spawned = get_type_hints(KittenSpawnedPayload)
        assert "kitten_id" in spawned
        assert "parent_id" in spawned
        assert "task" in spawned
        assert "role" in spawned

        dismissed = get_type_hints(KittenDismissedPayload)
        assert "kitten_id" in dismissed

        merge = get_type_hints(KittenMergeAbsorbedPayload)
        assert "kitten_id" in merge
        assert "proposal" in merge

    def test_fusion_payloads_have_expected_keys(self) -> None:
        """Fusion 系列 TypedDict 定义正确的键."""
        trigger_end = get_type_hints(FusionTriggerEndPayload)
        assert "insights_count" in trigger_end

        fusion_self = get_type_hints(FusionSelfPayload)
        assert "insights" in fusion_self
        assert "fusion_id" in fusion_self
