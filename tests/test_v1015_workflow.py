# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat standalone tests: v1.0.15 Long-Running Workflow.

Validates:
- WorkflowShape data model (defaults, import)
- DefaultHippocampus.list_active_workflows() (filtering, empty list)
- CatBase workflow tracking (register/active/_active_workflows)
- CatBase start/shutdown integration (checkpoint save, resume restore)
- BUILTIN_PATHS / BUILTIN_CHAINS orchestration additions
- Graceful degradation (no Hippocampus / no active workflows)
"""

from __future__ import annotations

import anyio

from meowcat import (
    BUILTIN_CHAINS,
    BUILTIN_PATHS,
    WORKFLOW_CHAIN,
    WorkflowShape,
)
from meowcat.defaults.organs import DefaultHippocampus
from meowcat.events import Lifecycle
from meowcat.testing import make_cat

# ===================================================================
# 1. WorkflowShape data model
# ===================================================================


class TestWorkflowShape:
    """WorkflowShape data shape."""

    def test_import_from_meowcat(self):
        """WorkflowShape importable from meowcat."""
        assert WorkflowShape is not None

    def test_default_values(self):
        """Default values are correct."""
        wf = WorkflowShape(
            entity_id="wf-1", cat_uid="cat-1", session_id="sess-1",
        )
        assert wf.entity_id == "wf-1"
        assert wf.cat_uid == "cat-1"
        assert wf.session_id == "sess-1"
        assert wf.status == "active"
        assert wf.plan == []
        assert wf.current_step == 0
        assert wf.checkpoint == {}
        assert wf.kittens_spawned == []
        assert wf.created_at == ""
        assert wf.updated_at == ""

    def test_custom_values(self):
        """Custom field values stored correctly."""
        wf = WorkflowShape(
            entity_id="wf-2",
            cat_uid="cat-2",
            session_id="sess-2",
            status="awaiting_user",
            plan=["step1", "step2", "step3"],
            current_step=2,
            checkpoint={"last_result": "ok"},
            kittens_spawned=["kitten-a"],
            created_at="2026-05-03T00:00:00",
            updated_at="2026-05-03T12:00:00",
        )
        assert wf.status == "awaiting_user"
        assert wf.plan == ["step1", "step2", "step3"]
        assert wf.current_step == 2
        assert wf.checkpoint == {"last_result": "ok"}
        assert wf.kittens_spawned == ["kitten-a"]

    def test_model_dump(self):
        """model_dump is serializable."""
        wf = WorkflowShape(
            entity_id="wf-3", cat_uid="cat-3", session_id="sess-3",
            plan=["a", "b"],
        )
        d = wf.model_dump()
        assert d["entity_id"] == "wf-3"
        assert d["plan"] == ["a", "b"]
        assert d["status"] == "active"


# ===================================================================
# 2. DefaultHippocampus.list_active_workflows()
# ===================================================================


class TestDefaultHippocampusListActiveWorkflows:
    """DefaultHippocampus list_active_workflows filtering logic."""

    def test_empty_when_no_entities(self):
        """Empty list when no entities."""
        hippo = DefaultHippocampus()
        result = hippo.list_active_workflows("cat-1")
        assert result == []

    def test_filters_by_type_workflow(self):
        """Only returns type="workflow" entities."""
        hippo = DefaultHippocampus()
        hippo.add_entity({
            "id": "e1", "type": "memory", "status": "active",
            "cat_uid": "cat-1",
        })
        hippo.add_entity({
            "id": "e2", "type": "workflow", "status": "active",
            "cat_uid": "cat-1",
        })
        result = hippo.list_active_workflows("cat-1")
        assert len(result) == 1
        assert result[0]["entity_id"] == "e2"

    def test_filters_by_status_active_or_awaiting(self):
        """Only returns workflows with active or awaiting_user status."""
        hippo = DefaultHippocampus()
        hippo.add_entity({
            "id": "w1", "type": "workflow", "status": "active",
            "cat_uid": "cat-1",
        })
        hippo.add_entity({
            "id": "w2", "type": "workflow", "status": "awaiting_user",
            "cat_uid": "cat-1",
        })
        hippo.add_entity({
            "id": "w3", "type": "workflow", "status": "completed",
            "cat_uid": "cat-1",
        })
        hippo.add_entity({
            "id": "w4", "type": "workflow", "status": "failed",
            "cat_uid": "cat-1",
        })
        result = hippo.list_active_workflows("cat-1")
        assert len(result) == 2
        statuses = {r["status"] for r in result}
        assert statuses == {"active", "awaiting_user"}

    def test_filters_by_cat_id(self):
        """Filters by cat_uid, does not return other cats' workflows."""
        hippo = DefaultHippocampus()
        hippo.add_entity({
            "id": "w1", "type": "workflow", "status": "active",
            "cat_uid": "cat-a",
        })
        hippo.add_entity({
            "id": "w2", "type": "workflow", "status": "active",
            "cat_uid": "cat-b",
        })
        result = hippo.list_active_workflows("cat-a")
        assert len(result) == 1
        assert result[0]["entity_id"] == "w1"

    def test_includes_entity_id_in_result(self):
        """Result includes entity_id key."""
        hippo = DefaultHippocampus()
        hippo.add_entity({
            "id": "wf-x", "type": "workflow", "status": "active",
            "cat_uid": "cat-1", "plan": ["step1"],
        })
        result = hippo.list_active_workflows("cat-1")
        assert result[0]["entity_id"] == "wf-x"
        assert result[0]["plan"] == ["step1"]


# ===================================================================
# 3. CatBase workflow tracking
# ===================================================================


class TestCatBaseWorkflowTracking:
    """CatBase register_workflow / active_workflows."""

    def test_active_workflows_starts_empty(self):
        """_active_workflows starts empty."""
        cat = make_cat("test")
        assert cat._active_workflows == {}

    def test_register_workflow(self):
        """register_workflow correctly adds to tracking list."""
        cat = make_cat("test")
        wf = {
            "entity_id": "wf-1", "cat_uid": cat.cat_uid,
            "status": "active", "plan": ["s1", "s2"],
        }
        cat.register_workflow(wf)
        assert "wf-1" in cat._active_workflows
        assert cat._active_workflows["wf-1"]["plan"] == ["s1", "s2"]

    def test_register_workflow_with_id_key(self):
        """register_workflow compatible with "id" key (legacy compat)."""
        cat = make_cat("test")
        wf = {
            "id": "wf-old", "cat_uid": cat.cat_uid,
            "status": "active",
        }
        cat.register_workflow(wf)
        assert "wf-old" in cat._active_workflows

    def test_register_workflow_no_id(self):
        """Silently skipped when no entity_id/id key."""
        cat = make_cat("test")
        cat.register_workflow({"status": "active"})
        assert cat._active_workflows == {}

    def test_active_workflows_filters_by_status(self):
        """active_workflows() only returns active/awaiting_user ones."""
        cat = make_cat("test")
        cat.register_workflow({
            "entity_id": "w1", "status": "active",
        })
        cat.register_workflow({
            "entity_id": "w2", "status": "awaiting_user",
        })
        cat.register_workflow({
            "entity_id": "w3", "status": "completed",
        })
        cat.register_workflow({
            "entity_id": "w4", "status": "failed",
        })
        active = cat.active_workflows()
        assert len(active) == 2
        ids = {w["entity_id"] for w in active}
        assert ids == {"w1", "w2"}


# ===================================================================
# 4. CatBase start/shutdown integration
# ===================================================================


class TestCatBaseWorkflowLifecycle:
    """start()/shutdown() workflow checkpoint/resume integration."""

    def _setup_cat_with_hippo(self, name="test"):
        """Create CatBase with DefaultHippocampus and wiring."""
        cat = make_cat(name)
        hippo = DefaultHippocampus()
        cat.mount("brain", "hippocampus", hippo)
        # need brainstem for signal support
        from meowcat.defaults.organs import DefaultBrainstem
        cat.mount("brain", "brainstem", DefaultBrainstem())
        cat.wire_default_nervous_system()
        cat.freeze_nervous_system()
        return cat, hippo

    def test_start_without_hippocampus_does_not_fail(self):
        """start() does not crash without Hippocampus (silent skip)."""
        cat = make_cat("no-hippo")

        async def _run():
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)

    def test_start_with_hippocampus_no_workflows(self):
        """start() succeeds with Hippocampus but no workflows."""
        cat, hippo = self._setup_cat_with_hippo()

        async def _run():
            await cat.start()
            assert cat._active_workflows == {}
            await cat.shutdown()

        anyio.run(_run)

    def test_shutdown_without_active_workflows(self):
        """shutdown() zero overhead when no active workflows."""
        cat, hippo = self._setup_cat_with_hippo()

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

    def test_shutdown_checkpoints_active_workflows(self):
        """shutdown() writes checkpoint for active workflows to Hippocampus."""
        cat, hippo = self._setup_cat_with_hippo()

        # Create workflow entity in Hippocampus
        hippo.add_entity({
            "id": "wf-1", "type": "workflow", "status": "active",
            "cat_uid": cat.cat_uid, "content": "initial",
            "current_step": 1, "checkpoint": {"data": "step1"},
        })
        # Register with cat
        cat.register_workflow({
            "entity_id": "wf-1", "cat_uid": cat.cat_uid,
            "status": "active", "current_step": 1,
            "checkpoint": {"data": "step1"},
        })

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

        # Verify Hippocampus entity's content was appended with checkpoint
        entity = hippo.get_entity("wf-1")
        assert entity is not None
        assert "[checkpoint]" in entity.get("content", "")

    def test_shutdown_only_checkpoints_active_status(self):
        """shutdown() only checkpoints active/awaiting_user status workflows."""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-active", "type": "workflow", "status": "active",
            "cat_uid": cat.cat_uid, "content": "",
        })
        hippo.add_entity({
            "id": "wf-done", "type": "workflow", "status": "completed",
            "cat_uid": cat.cat_uid, "content": "",
        })
        cat.register_workflow({
            "entity_id": "wf-active", "status": "active",
        })
        cat.register_workflow({
            "entity_id": "wf-done", "status": "completed",
        })

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

        # active ones should have checkpoint
        e_active = hippo.get_entity("wf-active")
        assert "[checkpoint]" in e_active.get("content", "")
        # completed ones should not have checkpoint
        e_done = hippo.get_entity("wf-done")
        assert e_done.get("content", "") == ""

    def test_start_resumes_workflows_from_hippocampus(self):
        """start() scans Hippocampus and loads unfinished workflows into _active_workflows."""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-1", "type": "workflow", "status": "active",
            "cat_uid": cat.cat_uid, "plan": ["step1", "step2"],
            "current_step": 1,
        })

        async def _run():
            await cat.start()
            assert "wf-1" in cat._active_workflows
            wf = cat._active_workflows["wf-1"]
            assert wf["plan"] == ["step1", "step2"]
            assert wf["current_step"] == 1
            await cat.shutdown()

        anyio.run(_run)

    def test_start_only_loads_active_or_awaiting(self):
        """start() only loads workflows with active/awaiting_user status."""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-active", "type": "workflow", "status": "active",
            "cat_uid": cat.cat_uid,
        })
        hippo.add_entity({
            "id": "wf-done", "type": "workflow", "status": "completed",
            "cat_uid": cat.cat_uid,
        })

        async def _run():
            await cat.start()
            assert "wf-active" in cat._active_workflows
            assert "wf-done" not in cat._active_workflows
            await cat.shutdown()

        anyio.run(_run)

    def test_start_lifecycle_event_order(self):
        """start() order: _resume_workflows → emit lifecycle.start → hooks."""
        cat, hippo = self._setup_cat_with_hippo()
        order = []

        def hook(c):
            order.append("hook")

        async def on_start_handler(payload):
            order.append("lifecycle.start")

        cat.on(Lifecycle.START, on_start_handler)
        cat.on_start(hook)

        async def _run():
            order.append("before_start")
            await cat.start()
            order.append("after_start")
            await cat.shutdown()

        anyio.run(_run)

        # _resume runs after start() call, before lifecycle event (no-op internally via _resume_workflows)
        # Verify lifecycle.start fires before hooks
        ls_idx = order.index("lifecycle.start")
        hook_idx = order.index("hook")
        assert ls_idx < hook_idx, f"lifecycle.start should be before hook, got {order}"

    def test_shutdown_lifecycle_event_order(self):
        """shutdown() order: _checkpoint_workflows → hooks → emit lifecycle.shutdown."""
        cat, hippo = self._setup_cat_with_hippo()
        order = []

        def hook(c):
            order.append("hook")

        async def on_shutdown_handler(payload):
            order.append("lifecycle.shutdown")

        cat.on(Lifecycle.SHUTDOWN, on_shutdown_handler)
        cat.on_shutdown(hook)

        async def _run():
            await cat.start()
            order.append("before_shutdown")
            await cat.shutdown()
            order.append("after_shutdown")

        anyio.run(_run)

        # hooks run before lifecycle.shutdown
        hook_idx = order.index("hook")
        ls_idx = order.index("lifecycle.shutdown")
        assert hook_idx < ls_idx, f"hook should be before lifecycle.shutdown, got {order}"


# ===================================================================
# 5. Path / Chain orchestration additions
# ===================================================================


class TestWorkflowPathsAndChain:
    """BUILTIN_PATHS / BUILTIN_CHAINS orchestration validation."""

    def test_workflow_paths_in_builtin(self):
        """3 orchestration domain paths exist in BUILTIN_PATHS."""
        names = {p.name for p in BUILTIN_PATHS}
        assert "workflow_create" in names
        assert "workflow_checkpoint" in names
        assert "workflow_resume" in names

    def test_workflow_paths_from_brainstem_to_hippocampus(self):
        """3 orchestration domain paths all go from BRAINSTEM to HIPPOCAMPUS."""
        for name in ("workflow_create", "workflow_checkpoint", "workflow_resume"):
            p = next(pp for pp in BUILTIN_PATHS if pp.name == name)
            from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS
            assert p.from_organ == BRAINSTEM, f"{name} from_organ should be BRAINSTEM"
            assert p.to_organ == HIPPOCAMPUS, f"{name} to_organ should be HIPPOCAMPUS"

    def test_workflow_chain_in_builtin(self):
        """WORKFLOW_CHAIN is in BUILTIN_CHAINS."""
        names = {c.name for c in BUILTIN_CHAINS}
        assert "workflow_chain" in names

    def test_workflow_chain_path_sequence(self):
        """WORKFLOW_CHAIN path sequence is correct."""
        wc = next(c for c in BUILTIN_CHAINS if c.name == "workflow_chain")
        assert wc.path_names == (
            "workflow_create", "execute_tool", "workflow_checkpoint")

    def test_workflow_chain_importable(self):
        """WORKFLOW_CHAIN importable from meowcat."""
        assert WORKFLOW_CHAIN is not None
        assert WORKFLOW_CHAIN.name == "workflow_chain"


# ===================================================================
# 6. Graceful degradation scenarios
# ===================================================================


class TestGracefulDegradation:
    """Graceful degradation without Hippocampus / wiring."""

    def test_shutdown_without_nervous(self):
        """shutdown() does not crash with enable_wiring=False."""
        cat = make_cat("no-wiring", enable_wiring=False)

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

    def test_start_shutdown_no_organs_at_all(self):
        """Bare CatBase (no organs) start/shutdown works."""
        cat = make_cat("bare")

        async def _run():
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)

    def test_multiple_start_shutdown_cycles(self):
        """Multiple start/shutdown cycles do not accumulate errors."""
        cat, hippo = make_cat("cycle"), DefaultHippocampus()
        cat.mount("brain", "hippocampus", hippo)
        from meowcat.defaults.organs import DefaultBrainstem
        cat.mount("brain", "brainstem", DefaultBrainstem())
        cat.wire_default_nervous_system()
        cat.freeze_nervous_system()

        async def _run():
            for _ in range(3):
                await cat.start()
                await cat.shutdown()

        anyio.run(_run)  # no exception = pass
