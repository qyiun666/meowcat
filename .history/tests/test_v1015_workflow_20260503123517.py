"""meowcat 独立测试: v1.0.15 长流程 Long-Running Workflow。

验证:
- WorkflowShape 数据模型（默认值、导入）
- NoopHippocampus.list_active_workflows()（过滤、空列表）
- CatBase workflow 跟踪（register/active/_active_workflows）
- CatBase start/shutdown 集成（checkpoint 存档、resume 恢复）
- BUILTIN_PATHS / BUILTIN_CHAINS 编排域新增
- 静默失败场景（无 Hippocampus / 无活跃 workflow）
"""

from __future__ import annotations
from meowcat.loop import Lifecycle

import anyio
import pytest

from meowcat import (
    CatBase,
    WorkflowShape,
    WORKFLOW_CHAIN,
    BUILTIN_PATHS,
    BUILTIN_CHAINS,
)
from meowcat.defaults.organs import NoopHippocampus


# ===================================================================
# 1. WorkflowShape 数据模型
# ===================================================================


class TestWorkflowShape:
    """WorkflowShape 数据形状。"""

    def test_import_from_meowcat(self):
        """WorkflowShape 可从 meowcat 导入。"""
        assert WorkflowShape is not None

    def test_default_values(self):
        """默认值正确。"""
        wf = WorkflowShape(
            entity_id="wf-1", cat_id="cat-1", session_id="sess-1",
        )
        assert wf.entity_id == "wf-1"
        assert wf.cat_id == "cat-1"
        assert wf.session_id == "sess-1"
        assert wf.status == "active"
        assert wf.plan == []
        assert wf.current_step == 0
        assert wf.checkpoint == {}
        assert wf.kittens_spawned == []
        assert wf.created_at == ""
        assert wf.updated_at == ""

    def test_custom_values(self):
        """自定义字段值正确存储。"""
        wf = WorkflowShape(
            entity_id="wf-2",
            cat_id="cat-2",
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
        """model_dump 可序列化。"""
        wf = WorkflowShape(
            entity_id="wf-3", cat_id="cat-3", session_id="sess-3",
            plan=["a", "b"],
        )
        d = wf.model_dump()
        assert d["entity_id"] == "wf-3"
        assert d["plan"] == ["a", "b"]
        assert d["status"] == "active"


# ===================================================================
# 2. NoopHippocampus.list_active_workflows()
# ===================================================================


class TestNoopHippocampusListActiveWorkflows:
    """NoopHippocampus 的 list_active_workflows 过滤逻辑。"""

    def test_empty_when_no_entities(self):
        """无实体时返回空列表。"""
        hippo = NoopHippocampus()
        result = hippo.list_active_workflows("cat-1")
        assert result == []

    def test_filters_by_type_workflow(self):
        """只返回 type="workflow" 的实体。"""
        hippo = NoopHippocampus()
        hippo.add_entity({
            "id": "e1", "type": "memory", "status": "active",
            "cat_id": "cat-1",
        })
        hippo.add_entity({
            "id": "e2", "type": "workflow", "status": "active",
            "cat_id": "cat-1",
        })
        result = hippo.list_active_workflows("cat-1")
        assert len(result) == 1
        assert result[0]["entity_id"] == "e2"

    def test_filters_by_status_active_or_awaiting(self):
        """只返回 status 为 active 或 awaiting_user 的 workflow。"""
        hippo = NoopHippocampus()
        hippo.add_entity({
            "id": "w1", "type": "workflow", "status": "active",
            "cat_id": "cat-1",
        })
        hippo.add_entity({
            "id": "w2", "type": "workflow", "status": "awaiting_user",
            "cat_id": "cat-1",
        })
        hippo.add_entity({
            "id": "w3", "type": "workflow", "status": "completed",
            "cat_id": "cat-1",
        })
        hippo.add_entity({
            "id": "w4", "type": "workflow", "status": "failed",
            "cat_id": "cat-1",
        })
        result = hippo.list_active_workflows("cat-1")
        assert len(result) == 2
        statuses = {r["status"] for r in result}
        assert statuses == {"active", "awaiting_user"}

    def test_filters_by_cat_id(self):
        """按 cat_id 过滤，不返回其他猫的 workflow。"""
        hippo = NoopHippocampus()
        hippo.add_entity({
            "id": "w1", "type": "workflow", "status": "active",
            "cat_id": "cat-a",
        })
        hippo.add_entity({
            "id": "w2", "type": "workflow", "status": "active",
            "cat_id": "cat-b",
        })
        result = hippo.list_active_workflows("cat-a")
        assert len(result) == 1
        assert result[0]["entity_id"] == "w1"

    def test_includes_entity_id_in_result(self):
        """结果中包含 entity_id 键。"""
        hippo = NoopHippocampus()
        hippo.add_entity({
            "id": "wf-x", "type": "workflow", "status": "active",
            "cat_id": "cat-1", "plan": ["step1"],
        })
        result = hippo.list_active_workflows("cat-1")
        assert result[0]["entity_id"] == "wf-x"
        assert result[0]["plan"] == ["step1"]


# ===================================================================
# 3. CatBase workflow 跟踪
# ===================================================================


class TestCatBaseWorkflowTracking:
    """CatBase 的 register_workflow / active_workflows。"""

    def test_active_workflows_starts_empty(self):
        """_active_workflows 初始为空。"""
        cat = CatBase("test")
        assert cat._active_workflows == {}

    def test_register_workflow(self):
        """register_workflow 正确添加到跟踪列表。"""
        cat = CatBase("test")
        wf = {
            "entity_id": "wf-1", "cat_id": "test",
            "status": "active", "plan": ["s1", "s2"],
        }
        cat.register_workflow(wf)
        assert "wf-1" in cat._active_workflows
        assert cat._active_workflows["wf-1"]["plan"] == ["s1", "s2"]

    def test_register_workflow_with_id_key(self):
        """register_workflow 兼容 "id" 键（旧代码兼容）。"""
        cat = CatBase("test")
        wf = {
            "id": "wf-old", "cat_id": "test",
            "status": "active",
        }
        cat.register_workflow(wf)
        assert "wf-old" in cat._active_workflows

    def test_register_workflow_no_id(self):
        """无 entity_id/id 键时静默跳过。"""
        cat = CatBase("test")
        cat.register_workflow({"status": "active"})
        assert cat._active_workflows == {}

    def test_active_workflows_filters_by_status(self):
        """active_workflows() 只返回 active/awaiting_user 的。"""
        cat = CatBase("test")
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
# 4. CatBase start/shutdown 集成
# ===================================================================


class TestCatBaseWorkflowLifecycle:
    """start()/shutdown() 的 workflow checkpoint/resume 集成。"""

    def _setup_cat_with_hippo(self, cat_id="test"):
        """创建带 NoopHippocampus 和 wiring 的 CatBase。"""
        cat = CatBase(cat_id)
        hippo = NoopHippocampus()
        cat.mount("brain", "hippocampus", hippo)
        # 需要 brainstem 以支持 signal
        from meowcat.defaults.organs import NoopBrainstem
        cat.mount("brain", "brainstem", NoopBrainstem())
        cat.wire_default_nervous_system()
        cat.freeze_nervous_system()
        return cat, hippo

    def test_start_without_hippocampus_does_not_fail(self):
        """无 Hippocampus 时 start() 不报错（静默跳过）。"""
        cat = CatBase("no-hippo")

        async def _run():
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)

    def test_start_with_hippocampus_no_workflows(self):
        """有 Hippocampus 但无 workflow 时 start() 正常。"""
        cat, hippo = self._setup_cat_with_hippo()

        async def _run():
            await cat.start()
            assert cat._active_workflows == {}
            await cat.shutdown()

        anyio.run(_run)

    def test_shutdown_without_active_workflows(self):
        """无活跃 workflow 时 shutdown() 零开销。"""
        cat, hippo = self._setup_cat_with_hippo()

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

    def test_shutdown_checkpoints_active_workflows(self):
        """shutdown() 对活跃 workflow 写 checkpoint 到 Hippocampus。"""
        cat, hippo = self._setup_cat_with_hippo()

        # 在 Hippocampus 中创建 workflow 实体
        hippo.add_entity({
            "id": "wf-1", "type": "workflow", "status": "active",
            "cat_id": "test", "content": "initial",
            "current_step": 1, "checkpoint": {"data": "step1"},
        })
        # 注册到 cat
        cat.register_workflow({
            "entity_id": "wf-1", "cat_id": "test",
            "status": "active", "current_step": 1,
            "checkpoint": {"data": "step1"},
        })

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

        # 验证 Hippocampus 中 entity 的 content 被追加了 checkpoint
        entity = hippo.get_entity("wf-1")
        assert entity is not None
        assert "[checkpoint]" in entity.get("content", "")

    def test_shutdown_only_checkpoints_active_status(self):
        """shutdown() 只存档 status 为 active/awaiting_user 的 workflow。"""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-active", "type": "workflow", "status": "active",
            "cat_id": "test", "content": "",
        })
        hippo.add_entity({
            "id": "wf-done", "type": "workflow", "status": "completed",
            "cat_id": "test", "content": "",
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

        # active 的应该有 checkpoint
        e_active = hippo.get_entity("wf-active")
        assert "[checkpoint]" in e_active.get("content", "")
        # completed 的不应该有
        e_done = hippo.get_entity("wf-done")
        assert e_done.get("content", "") == ""

    def test_start_resumes_workflows_from_hippocampus(self):
        """start() 扫描 Hippocampus 并加载未完成 workflow 到 _active_workflows。"""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-1", "type": "workflow", "status": "active",
            "cat_id": "test", "plan": ["step1", "step2"],
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
        """start() 只加载 status 为 active/awaiting_user 的 workflow。"""
        cat, hippo = self._setup_cat_with_hippo()

        hippo.add_entity({
            "id": "wf-active", "type": "workflow", "status": "active",
            "cat_id": "test",
        })
        hippo.add_entity({
            "id": "wf-done", "type": "workflow", "status": "completed",
            "cat_id": "test",
        })

        async def _run():
            await cat.start()
            assert "wf-active" in cat._active_workflows
            assert "wf-done" not in cat._active_workflows
            await cat.shutdown()

        anyio.run(_run)

    def test_start_lifecycle_event_order(self):
        """start() 顺序: _resume_workflows → emit lifecycle.start → hooks。"""
        cat, hippo = self._setup_cat_with_hippo()
        order = []

        async def hook(c):
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

        # _resume 在 start 调用后、lifecycle event 前执行（通过 _resume_workflows 内部无操作）
        # 验证 lifecycle.start 在 hook 之前
        ls_idx = order.index("lifecycle.start")
        hook_idx = order.index("hook")
        assert ls_idx < hook_idx, f"lifecycle.start should be before hook, got {order}"

    def test_shutdown_lifecycle_event_order(self):
        """shutdown() 顺序: _checkpoint_workflows → hooks → emit lifecycle.shutdown。"""
        cat, hippo = self._setup_cat_with_hippo()
        order = []

        async def hook(c):
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

        # hook 在 lifecycle.shutdown 之前
        hook_idx = order.index("hook")
        ls_idx = order.index("lifecycle.shutdown")
        assert hook_idx < ls_idx, f"hook should be before lifecycle.shutdown, got {order}"


# ===================================================================
# 5. Path / Chain 编排域新增
# ===================================================================


class TestWorkflowPathsAndChain:
    """BUILTIN_PATHS / BUILTIN_CHAINS 编排域验证。"""

    def test_workflow_paths_in_builtin(self):
        """3 条编排域路径在 BUILTIN_PATHS 中。"""
        names = {p.name for p in BUILTIN_PATHS}
        assert "workflow_create" in names
        assert "workflow_checkpoint" in names
        assert "workflow_resume" in names

    def test_workflow_paths_from_brainstem_to_hippocampus(self):
        """3 条编排域路径均从 BRAINSTEM 到 HIPPOCAMPUS。"""
        for name in ("workflow_create", "workflow_checkpoint", "workflow_resume"):
            p = next(pp for pp in BUILTIN_PATHS if pp.name == name)
            from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS
            assert p.from_organ == BRAINSTEM, f"{name} from_organ should be BRAINSTEM"
            assert p.to_organ == HIPPOCAMPUS, f"{name} to_organ should be HIPPOCAMPUS"

    def test_workflow_chain_in_builtin(self):
        """WORKFLOW_CHAIN 在 BUILTIN_CHAINS 中。"""
        names = {c.name for c in BUILTIN_CHAINS}
        assert "workflow_chain" in names

    def test_workflow_chain_path_sequence(self):
        """WORKFLOW_CHAIN 的 path 序列正确。"""
        wc = next(c for c in BUILTIN_CHAINS if c.name == "workflow_chain")
        assert wc.path_names == (
            "workflow_create", "execute_tool", "workflow_checkpoint")

    def test_workflow_chain_importable(self):
        """WORKFLOW_CHAIN 可从 meowcat 正确导入。"""
        assert WORKFLOW_CHAIN is not None
        assert WORKFLOW_CHAIN.name == "workflow_chain"


# ===================================================================
# 6. 静默失败场景
# ===================================================================


class TestGracefulDegradation:
    """无 Hippocampus / 无 wiring 时静默降级。"""

    def test_shutdown_without_nervous(self):
        """enable_wiring=False 时 shutdown() 不报错。"""
        cat = CatBase("no-wiring", enable_wiring=False)

        async def _run():
            await cat.shutdown()

        anyio.run(_run)

    def test_start_shutdown_no_organs_at_all(self):
        """裸 CatBase（无任何器官）start/shutdown 正常。"""
        cat = CatBase("bare")

        async def _run():
            await cat.start()
            await cat.shutdown()

        anyio.run(_run)

    def test_multiple_start_shutdown_cycles(self):
        """多次 start/shutdown 不累积错误。"""
        cat, hippo = CatBase("cycle"), NoopHippocampus()
        cat.mount("brain", "hippocampus", hippo)
        from meowcat.defaults.organs import NoopBrainstem
        cat.mount("brain", "brainstem", NoopBrainstem())
        cat.wire_default_nervous_system()
        cat.freeze_nervous_system()

        async def _run():
            for _ in range(3):
                await cat.start()
                await cat.shutdown()

        anyio.run(_run)  # 不抛异常即通过
