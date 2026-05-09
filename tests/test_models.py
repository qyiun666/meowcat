# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: 所有 Shape 构造 + 序列化 + 默认值。

验证:
- EntityShape / ConnectionShape / EpisodeShape / FocusShape 构造
- SubTaskShape / TaskResultShape / OrchestratorReportShape 构造
- MaintenanceReportShape / CandidateShape / LocateResultShape 构造
- StageEvent thinking/output/short_circuit 工厂方法
- PipelineContext / LoopEvent 构造
- MergeProposalShape / KittenCapability 构造与铁律
- model_dump 序列化往返
"""

from __future__ import annotations

import pytest

from meowcat.models import (
    CandidateShape,
    ConnectionShape,
    EntityShape,
    EpisodeShape,
    FocusShape,
    KittenCapability,
    LocateResultShape,
    LoopEvent,
    MaintenanceReportShape,
    MergeProposalShape,
    OrchestratorReportShape,
    PipelineContext,
    StageEvent,
    SubTaskShape,
    TaskResultShape,
)

# -- 脑区 Shape -----------------------------------------------------


class TestEntityShape:
    def test_default_values(self) -> None:
        e = EntityShape(id="e1", session_id="s1", name="test")
        assert e.id == "e1"
        assert e.type == "topic"
        assert e.content == ""
        assert e.source == "user_stated"
        assert e.importance == 0.5
        assert e.emotion == 0.0
        assert e.protection == "normal"
        assert e.is_dormant is False
        assert e.is_corrected is False

    def test_model_dump(self) -> None:
        e = EntityShape(id="e1", session_id="s1", name="test", content="hello")
        d = e.model_dump()
        assert d["id"] == "e1"
        assert d["content"] == "hello"
        assert d["type"] == "topic"


class TestConnectionShape:
    def test_default_values(self) -> None:
        c = ConnectionShape(id="c1", from_id="a", to_id="b")
        assert c.id == "c1"
        assert c.strength == 0.5
        assert c.confidence == 0.5
        assert c.source == "inferred"
        assert c.co_occurrence == 1

    def test_model_dump(self) -> None:
        c = ConnectionShape(id="c1", from_id="a", to_id="b", relation="related",
                            strength=0.8)
        d = c.model_dump()
        assert d["relation"] == "related"
        assert d["strength"] == 0.8


class TestEpisodeShape:
    def test_default_values(self) -> None:
        e = EpisodeShape(id="ep1")
        assert e.id == "ep1"
        assert e.type == "chat"
        assert e.turn == 0
        assert e.is_confirmed is False

    def test_model_dump(self) -> None:
        e = EpisodeShape(id="ep1", summary="talked about cats", turn=3)
        d = e.model_dump()
        assert d["summary"] == "talked about cats"
        assert d["turn"] == 3


class TestFocusShape:
    def test_default_values(self) -> None:
        f = FocusShape()
        assert f.entity_id is None
        assert f.topic_ids == []
        assert f.turn_count == 0

    def test_model_dump(self) -> None:
        f = FocusShape(entity_id="e1", turn_count=5)
        d = f.model_dump()
        assert d["entity_id"] == "e1"
        assert d["turn_count"] == 5


# -- Worker / 编排 --------------------------------------------------


class TestSubTaskShape:
    def test_default_values(self) -> None:
        s = SubTaskShape(task_id="t1", role="coder", prompt="write code")
        assert s.task_id == "t1"
        assert s.status == "pending"
        assert s.dependencies == []

    def test_model_dump(self) -> None:
        s = SubTaskShape(task_id="t1", role="coder", prompt="write code")
        d = s.model_dump()
        assert d["task_id"] == "t1"


class TestTaskResultShape:
    def test_default_values(self) -> None:
        r = TaskResultShape(task_id="t1", role="coder", success=True)
        assert r.task_id == "t1"
        assert r.success is True
        assert r.output == ""
        assert r.duration == 0.0

    def test_model_dump(self) -> None:
        r = TaskResultShape(task_id="t1", role="coder", success=False,
                            error="something went wrong")
        d = r.model_dump()
        assert d["error"] == "something went wrong"


class TestOrchestratorReportShape:
    def test_default_values(self) -> None:
        r = OrchestratorReportShape()
        assert r.subtasks == []
        assert r.status == "completed"
        assert r.total_duration == 0.0
        assert r.workers_spawned == 0

    def test_model_dump(self) -> None:
        r = OrchestratorReportShape(synthesis="all done", workers_spawned=3)
        d = r.model_dump()
        assert d["synthesis"] == "all done"


# -- 维护 / 定位 ----------------------------------------------------


class TestMaintenanceReportShape:
    def test_default_values(self) -> None:
        r = MaintenanceReportShape()
        assert r.decayed == 0
        assert r.orphans_cleaned == 0
        assert r.suggestions == []


class TestCandidateShape:
    def test_construction(self) -> None:
        e = EntityShape(id="e1", session_id="s1", name="test")
        c = CandidateShape(entity=e, weight=0.9, match_type="keyword")
        assert c.entity is e
        assert c.weight == 0.9
        assert c.match_type == "keyword"


class TestLocateResultShape:
    def test_default_values(self) -> None:
        r = LocateResultShape()
        assert r.candidates == []
        assert r.confidence == 0.0
        assert r.match_type == "none"
        assert r.is_ambiguous is False


# -- StageEvent -----------------------------------------------------


class TestStageEvent:
    def test_thinking_factory(self) -> None:
        ev = StageEvent.thinking("analyzing...")
        assert ev.kind == "thinking"
        assert ev.content == "analyzing..."

    def test_output_factory(self) -> None:
        ev = StageEvent.output("hello")
        assert ev.kind == "output"
        assert ev.content == "hello"

    def test_short_circuit_factory(self) -> None:
        ev = StageEvent.short_circuit("done")
        assert ev.kind == "short_circuit"
        assert ev.reply == "done"
        assert ev.content == ""


# -- PipelineContext / LoopEvent ------------------------------------


class TestPipelineContext:
    def test_construction(self) -> None:
        class FakeBS:
            inject_cat_self: bool = True
            async def process(self, msg: str) -> str: return msg

            async def process_stream(self, msg: str):
                yield {"content": msg}
                return

            def build_system_prompt(
                self, organ: str, route: str, cat_self_snapshot=None) -> str: return ""

            def cancel_current(self) -> bool: return False

        bs = FakeBS()
        ctx = PipelineContext(msg="hello", brainstem=bs)
        assert ctx.msg == "hello"
        assert ctx.brainstem is bs
        assert ctx.short_circuited is False


class TestLoopEvent:
    def test_construction(self) -> None:
        ev = LoopEvent(event="test", payload={"k": "v"}, timestamp="now")
        assert ev.event == "test"
        assert ev.payload == {"k": "v"}
        assert ev.timestamp == "now"


# -- 分身猫 Shape ---------------------------------------------------


class TestMergeProposalShape:
    def test_default_values(self) -> None:
        p = MergeProposalShape(
            kitten_id="k1", parent_id="p1", task_id="t1",
        )
        assert p.kitten_id == "k1"
        assert p.status == "completed"
        assert p.new_entities == []
        assert p.result == ""

    def test_model_dump(self) -> None:
        p = MergeProposalShape(
            kitten_id="k1", parent_id="p1", task_id="t1",
            status="completed", result="all done",
        )
        d = p.model_dump()
        assert d["kitten_id"] == "k1"
        assert d["result"] == "all done"


class TestKittenCapability:
    def test_default_values(self) -> None:
        k = KittenCapability()
        assert k.can_spawn is False
        assert k.can_promote is False
        assert k.has_paws is True
        assert k.has_cerebrum is True
        assert k.has_cerebellum is True

    def test_iron_laws_enforced(self) -> None:
        """铁律静默强制：can_spawn/can_promote 永远 False，has_paws 永远 True。"""
        k = KittenCapability(can_spawn=True, can_promote=True,
                             has_paws=False)  # type: ignore[arg-type]
        assert k.can_spawn is False
        assert k.can_promote is False
        assert k.has_paws is True

    def test_no_brain_raises(self) -> None:
        """至少一个脑（cerebrum/cerebellum）为 True。"""
        with pytest.raises(ValueError):
            KittenCapability(has_cerebrum=False, has_cerebellum=False)

    def test_inherit_memory_default(self) -> None:
        k = KittenCapability()
        assert k.inherit_memory == "none"
        assert k.inherit_entity_ids == []
        assert k.inherit_l6_recent == 0
        assert k.inherit_focus is False

    def test_model_dump(self) -> None:
        k = KittenCapability(
            has_cerebrum=True, has_ears=True,
            inherit_memory="partial", inherit_entity_ids=["e1"],
        )
        d = k.model_dump()
        assert d["inherit_memory"] == "partial"
        assert d["inherit_entity_ids"] == ["e1"]
