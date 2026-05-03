"""v1.0.17 — Pipeline Stage base classes and Noop* Stage stubs."""

from __future__ import annotations

import pytest

from meowcat.defaults.stages import (
    BaseStage,
    NoopCompressStage,
    NoopExecuteStage,
    NoopIngestStage,
    NoopLocateStage,
    NoopPostStage,
    NoopRouteStage,
    build_default_pipeline,
)
from meowcat.pipeline import Pipeline
from meowcat.pluggable import Pluggable


class TestBaseStage:
    """BaseStage construction and interface."""

    def test_base_stage_name(self) -> None:
        s = BaseStage()
        assert s.name == "noop_base_stage"

    def test_base_stage_is_pluggable(self) -> None:
        s = BaseStage()
        assert isinstance(s, Pluggable)

    def test_base_stage_has_hooks(self) -> None:
        s = BaseStage()
        assert hasattr(s, "HOOKS")
        assert "run" in s.HOOKS

    def test_base_stage_diagnose_empty(self) -> None:
        s = BaseStage()
        assert s.diagnose() == {}


class TestNoopStageNames:
    """Each Noop* Stage auto-derives its name from class name."""

    STAGES = [
        (NoopIngestStage, "noop_ingest_stage"),
        (NoopLocateStage, "noop_locate_stage"),
        (NoopRouteStage, "noop_route_stage"),
        (NoopExecuteStage, "noop_execute_stage"),
        (NoopPostStage, "noop_post_stage"),
        (NoopCompressStage, "noop_compress_stage"),
    ]

    @pytest.mark.parametrize("cls, expected_name", STAGES)
    def test_name(self, cls: type, expected_name: str) -> None:
        s = cls()
        assert s.name == expected_name

    @pytest.mark.parametrize("cls, _", STAGES)
    def test_is_base_stage(self, cls: type, _: str) -> None:
        s = cls()
        assert isinstance(s, BaseStage)

    @pytest.mark.parametrize("cls, _", STAGES)
    def test_diagnose_empty(self, cls: type, _: str) -> None:
        s = cls()
        assert s.diagnose() == {}


@pytest.mark.anyio
class TestNoopStageRun:
    """Noop* Stages yield nothing from run()."""

    @pytest.mark.parametrize("cls", [
        NoopIngestStage, NoopLocateStage, NoopRouteStage,
        NoopExecuteStage, NoopPostStage, NoopCompressStage,
    ])
    async def test_run_yields_nothing(self, cls: type) -> None:
        s = cls()
        events = []
        async for ev in s.run(None):
            events.append(ev)
        assert len(events) == 0


class TestBuildDefaultPipeline:
    """build_default_pipeline() factory."""

    def test_returns_five_stages(self) -> None:
        pipe = build_default_pipeline()
        assert len(pipe) == 5

    def test_stages_are_base_stage(self) -> None:
        pipe = build_default_pipeline()
        for s in pipe:
            assert isinstance(s, BaseStage)

    def test_pipeline_constructs(self) -> None:
        pipe = build_default_pipeline()
        p = Pipeline(pipe)
        assert len(p.stages) == 5
