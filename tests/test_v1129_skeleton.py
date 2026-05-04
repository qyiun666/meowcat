"""v1.1.29 skeleton abstraction tests — coordination, matcher, model config, theme, worker."""

from __future__ import annotations

import asyncio
import pytest

from meowcat.coordination import AsyncApprovalGate, ApprovalRequest, ApprovalStatus
from meowcat.tools.matcher import KeywordToolMatcher
from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec
from meowcat.models import ModelConfig
from meowcat.cli.theme import Theme
from meowcat.worker import (
    BaseWorker,
    CheckpointStore,
    InMemoryCheckpointStore,
    WorkerState,
    WorkerStatus,
)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def _make_registry(*names: str) -> ToolRegistry:
    reg = ToolRegistry()
    for name in names:
        reg.register(Tool(ToolSpec(
            name=name,
            description=f"Tool: {name}",
            category="test",
        ), handler=lambda **kw: f"done:{name}"))
    return reg


# ════════════════════════════════════════════════════════════════════
# 1. AsyncApprovalGate
# ════════════════════════════════════════════════════════════════════

class TestApprovalGate:
    """Async approval gate coordination tests."""

    def test_submit_and_approve_sync(self):
        gate = AsyncApprovalGate()
        req = asyncio.run(gate.submit("deploy", reason="test"))
        assert req.status == ApprovalStatus.PENDING
        result = gate.approve(req.request_id, approver="ops")
        assert result.status == ApprovalStatus.APPROVED
        assert result.approved_by == "ops"

    def test_submit_and_reject_sync(self):
        gate = AsyncApprovalGate()
        req = asyncio.run(gate.submit("delete", reason="test"))
        result = gate.reject(req.request_id, reason="unsafe")
        assert result.status == ApprovalStatus.REJECTED
        assert result.rejected_reason == "unsafe"

    def test_wait_resolution(self):
        gate = AsyncApprovalGate()

        async def _flow():
            req = await gate.submit("restart")
            # Approve in background
            asyncio.create_task(_delayed_approve(gate, req.request_id))
            resolved = await gate.wait(req.request_id)
            return resolved

        result = asyncio.run(_flow())
        assert result.status == ApprovalStatus.APPROVED

    def test_timeout(self):
        gate = AsyncApprovalGate(default_timeout=0.05)

        async def _flow():
            req = await gate.submit("slow", timeout=0.05)
            resolved = await gate.wait(req.request_id)
            return resolved

        result = asyncio.run(_flow())
        assert result.status == ApprovalStatus.TIMED_OUT
        assert "Timeout" in result.rejected_reason

    def test_already_resolved_reject(self):
        gate = AsyncApprovalGate()
        req = asyncio.run(gate.submit("x"))
        gate.approve(req.request_id)
        with pytest.raises(ValueError, match="already resolved"):
            gate.approve(req.request_id)

    def test_unknown_request(self):
        gate = AsyncApprovalGate()
        with pytest.raises(KeyError, match="Unknown"):
            gate.approve("nonexistent")

    def test_list_pending(self):
        gate = AsyncApprovalGate()
        r1 = asyncio.run(gate.submit("a"))
        r2 = asyncio.run(gate.submit("b"))
        assert len(gate.list_pending()) == 2
        gate.approve(r1.request_id)
        assert len(gate.list_pending()) == 1

    def test_get(self):
        gate = AsyncApprovalGate()
        r = asyncio.run(gate.submit("check"))
        assert gate.get(r.request_id) is r
        assert gate.get("nope") is None

    def test_plugin_hooks(self):
        calls = []

        def on_submit(req):
            calls.append(("submit", req.action))

        def on_resolve(req):
            calls.append(("resolve", req.status.value))

        gate = AsyncApprovalGate()
        gate.plug("on_submit", on_submit)
        gate.plug("on_resolve", on_resolve)
        req = asyncio.run(gate.submit("deploy"))
        gate.approve(req.request_id)
        assert ("submit", "deploy") in calls
        assert ("resolve", "approved") in calls

    def test_unplug_hook(self):
        calls = []

        def hook(req):
            calls.append(1)

        gate = AsyncApprovalGate()
        gate.plug("on_submit", hook)
        gate.unplug("on_submit", hook)
        asyncio.run(gate.submit("x"))
        assert len(calls) == 0


async def _delayed_approve(gate: AsyncApprovalGate, request_id: str) -> None:
    await asyncio.sleep(0.02)
    gate.approve(request_id)


# ════════════════════════════════════════════════════════════════════
# 2. KeywordToolMatcher
# ════════════════════════════════════════════════════════════════════

class TestKeywordToolMatcher:
    """Keyword-based tool matching tests."""

    def test_match_by_name(self):
        reg = _make_registry("read_file", "write_file", "list_dir")
        matcher = KeywordToolMatcher(reg)
        results = matcher.match("read file")
        assert len(results) > 0
        assert results[0][0].name == "read_file"

    def test_match_by_description(self):
        reg = ToolRegistry()
        reg.register(Tool(ToolSpec(
            name="fetch_url",
            description="Download content from a URL",
            category="web",
        ), handler=lambda **kw: "ok"))
        matcher = KeywordToolMatcher(reg)
        results = matcher.match("download content")
        assert len(results) > 0
        assert results[0][0].name == "fetch_url"

    def test_best_match_returns_none_for_no_match(self):
        reg = ToolRegistry()
        reg.register(Tool(ToolSpec(
            name="git_commit", description="Make a git commit", category="vcs",
        ), handler=lambda **kw: "ok"))
        matcher = KeywordToolMatcher(reg)
        result = matcher.best_match("xyzzy blargh no match at all")
        assert result is None

    def test_best_match_returns_top(self):
        reg = _make_registry("read_file", "delete_file", "copy_file")
        matcher = KeywordToolMatcher(reg)
        result = matcher.best_match("read a file")
        assert result is not None
        assert result.name == "read_file"

    def test_empty_registry(self):
        matcher = KeywordToolMatcher(None)
        assert matcher.match("anything") == []
        assert matcher.best_match("anything") is None

    def test_top_n_limit(self):
        reg = _make_registry("t1", "t2", "t3", "t4", "t5")
        matcher = KeywordToolMatcher(reg)
        results = matcher.match("t", top_n=3)
        assert len(results) <= 3

    def test_custom_scorer(self):
        reg = _make_registry("alpha", "beta")
        matcher = KeywordToolMatcher(reg)
        matcher.plug("scorer", lambda tool,
                     kw: 100 if tool.name == "beta" else 0)
        results = matcher.match("alpha")
        assert results[0][0].name == "beta"

    def test_custom_filter(self):
        reg = _make_registry("read_file", "write_file")
        matcher = KeywordToolMatcher(reg)
        matcher.plug("filter", lambda tool: "write" in tool.name)
        results = matcher.match("file")
        names = {t.name for t, _ in results}
        assert "write_file" not in names
        assert "read_file" in names


# ════════════════════════════════════════════════════════════════════
# 3. ModelConfig
# ════════════════════════════════════════════════════════════════════

class TestModelConfig:
    """ModelConfig (litellm-free) tests."""

    def test_construct_minimal(self):
        cfg = ModelConfig(model="gpt-4o")
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096

    def test_construct_full(self):
        cfg = ModelConfig(
            provider="anthropic",
            model="claude-3",
            temperature=0.2,
            max_tokens=8192,
            top_p=0.9,
            stop=["\n\n"],
        )
        assert cfg.provider == "anthropic"
        assert cfg.stop == ["\n\n"]

    def test_to_llm_config(self):
        cfg = ModelConfig(model="gpt-4o-mini", temperature=0.3)
        with pytest.warns(DeprecationWarning):
            llm = cfg.to_llm_config()
        assert isinstance(llm, ModelConfig)
        assert llm.model == "gpt-4o-mini"
        assert llm.temperature == 0.3
        assert llm.provider == "openai"


# ════════════════════════════════════════════════════════════════════
# 4. Theme
# ════════════════════════════════════════════════════════════════════

class TestTheme:
    """Theme engine tests."""

    def test_ansi_codes_are_nonempty(self):
        assert len(Theme.RESET) > 0
        assert len(Theme.GREEN) > 0
        assert len(Theme.BOLD) > 0

    def test_semantic_aliases(self):
        assert Theme.SUCCESS == Theme.GREEN
        assert Theme.WARNING == Theme.YELLOW
        assert Theme.ERROR == Theme.RED
        assert Theme.INFO == Theme.CYAN

    def test_styled_wraps_and_resets(self):
        result = Theme.styled("hello", Theme.GREEN)
        assert result.startswith(Theme.GREEN)
        assert "hello" in result
        assert result.endswith(Theme.RESET)

    def test_semantic_helpers(self):
        assert "\033[" in Theme.success("ok")
        assert "\033[" in Theme.warning("warn")
        assert "\033[" in Theme.error("fail")
        assert "\033[" in Theme.info("note")
        assert "\033[" in Theme.header("title")
        assert "\033[" in Theme.muted("dim")


# ════════════════════════════════════════════════════════════════════
# 5. Worker
# ════════════════════════════════════════════════════════════════════

class _SumWorker(BaseWorker):
    """Test worker that sums numbers from steps."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results: list[int] = []

    async def execute_step(self, step: dict) -> int:
        n = step.get("n", 0)
        self.results.append(n)
        return n


class TestCheckpointStore:
    """InMemoryCheckpointStore tests."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        store = InMemoryCheckpointStore()
        state = WorkerState(worker_id="w1", status=WorkerStatus.RUNNING)
        await store.save(state)
        loaded = await store.load("w1")
        assert loaded is not None
        assert loaded.worker_id == "w1"
        assert loaded.status == WorkerStatus.RUNNING

    @pytest.mark.asyncio
    async def test_load_missing_returns_none(self):
        store = InMemoryCheckpointStore()
        assert await store.load("nope") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        store = InMemoryCheckpointStore()
        await store.save(WorkerState(worker_id="w1"))
        await store.delete("w1")
        assert await store.load("w1") is None

    @pytest.mark.asyncio
    async def test_list_all(self):
        store = InMemoryCheckpointStore()
        await store.save(WorkerState(worker_id="w1"))
        await store.save(WorkerState(worker_id="w2"))
        ids = await store.list_all()
        assert set(ids) == {"w1", "w2"}


class TestBaseWorker:
    """BaseWorker lifecycle tests."""

    @pytest.mark.asyncio
    async def test_run_completes(self):
        worker = _SumWorker()
        state = await worker.run("t1", [{"n": 1}, {"n": 2}, {"n": 3}])
        assert state.status == WorkerStatus.COMPLETED
        assert state.progress == 3.0
        assert worker.results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_run_empty_steps(self):
        worker = _SumWorker()
        state = await worker.run("t1", [])
        assert state.status == WorkerStatus.COMPLETED
        assert state.progress == 0.0

    @pytest.mark.asyncio
    async def test_checkpoint_saved(self):
        store = InMemoryCheckpointStore()
        worker = _SumWorker(store=store)
        await worker.run("t1", [{"n": 5}])
        saved = await store.load(worker.worker_id)
        assert saved is not None
        assert saved.status == WorkerStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self):
        store = InMemoryCheckpointStore()
        worker = _SumWorker(store=store)
        # Simulate failure after 2 steps by manually saving partial state
        partial = WorkerState(
            worker_id=worker.worker_id,
            status=WorkerStatus.PAUSED,
            task_id="t1",
            progress=2.0,
            checkpoint={"step_0": 1, "step_1": 2},
        )
        await store.save(partial)

        worker2 = _SumWorker(worker_id=worker.worker_id, store=store)
        state = await worker2.run(
            "t1",
            [{"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}],
            resume=True,
        )
        assert state.status == WorkerStatus.COMPLETED
        # Resumed from step 2, should execute only steps 3 and 4
        assert worker2.results == [3, 4]

    @pytest.mark.asyncio
    async def test_pause(self):
        worker = _SumWorker()
        await worker.run("t1", [{"n": 1}])
        await worker.pause()
        saved = await worker.store.load(worker.worker_id)
        assert saved is not None
        assert saved.status == WorkerStatus.PAUSED

    @pytest.mark.asyncio
    async def test_lifecycle_hooks(self):
        events = []

        def on_start(state):
            events.append("start")

        def on_complete(state):
            events.append("complete")

        worker = _SumWorker()
        worker.plug("on_start", on_start)
        worker.plug("on_complete", on_complete)
        await worker.run("t1", [{"n": 1}])
        assert "start" in events
        assert "complete" in events

    @pytest.mark.asyncio
    async def test_run_failure(self):
        class _FailingWorker(BaseWorker):
            async def execute_step(self, step):
                if step.get("fail"):
                    raise RuntimeError("boom")
                return step

        worker = _FailingWorker()
        state = await worker.run("t1", [{"n": 1}, {"fail": True}])
        assert state.status == WorkerStatus.FAILED
        assert "boom" in state.error
