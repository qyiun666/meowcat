# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Coordination 单元测试 — C-04 修复。

覆盖：
- ApprovalStatus / ApprovalRequest 基础类型
- AsyncApprovalGate submit / approve / reject / wait 完整流程
- 超时逻辑
- list_pending / get 检查方法
- plug / unplug 钩子系统
"""

from __future__ import annotations

import asyncio

import pytest

from meowcat.coordination import (
    ApprovalRequest,
    ApprovalStatus,
    AsyncApprovalGate,
)


# =============================================================================
# ApprovalStatus / ApprovalRequest
# =============================================================================


class TestApprovalStatus:
    """ApprovalStatus 枚举测试。"""

    def test_enum_values(self) -> None:
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.TIMED_OUT.value == "timed_out"


class TestApprovalRequest:
    """ApprovalRequest 数据类测试。"""

    def test_defaults(self) -> None:
        req = ApprovalRequest(request_id="r1", action="deploy")
        assert req.request_id == "r1"
        assert req.action == "deploy"
        assert req.params == {}
        assert req.reason == ""
        assert req.requester == ""
        assert req.status == ApprovalStatus.PENDING
        assert req.approved_by == ""
        assert req.rejected_reason == ""

    def test_custom_values(self) -> None:
        req = ApprovalRequest(
            request_id="r2",
            action="scale",
            params={"count": 3},
            reason="load spike",
            requester="auto-scaler",
        )
        assert req.params == {"count": 3}
        assert req.requester == "auto-scaler"


# =============================================================================
# AsyncApprovalGate — 提交 & 批准/拒绝
# =============================================================================


@pytest.mark.anyio
class TestAsyncApprovalGateSubmit:
    """AsyncApprovalGate.submit() 测试。"""

    @pytest.mark.asyncio
    async def test_submit_returns_pending_request(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy", {"env": "prod"}, reason="test")
        assert req.status == ApprovalStatus.PENDING
        assert req.action == "deploy"
        assert req.params == {"env": "prod"}
        assert req.request_id.startswith("apr-")

    @pytest.mark.asyncio
    async def test_submit_increments_ids(self) -> None:
        gate = AsyncApprovalGate()
        r1 = await gate.submit("a")
        r2 = await gate.submit("b")
        assert r1.request_id != r2.request_id


@pytest.mark.anyio
class TestAsyncApprovalGateApproveReject:
    """AsyncApprovalGate.approve() / reject() 测试。"""

    @pytest.mark.asyncio
    async def test_approve_changes_status(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")
        result = gate.approve(req.request_id, approver="admin")
        assert result.status == ApprovalStatus.APPROVED
        assert result.approved_by == "admin"

    @pytest.mark.asyncio
    async def test_reject_changes_status(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")
        result = gate.reject(req.request_id, reason="not now")
        assert result.status == ApprovalStatus.REJECTED
        assert result.rejected_reason == "not now"

    @pytest.mark.asyncio
    async def test_approve_unknown_raises(self) -> None:
        gate = AsyncApprovalGate()
        with pytest.raises(KeyError, match="Unknown request"):
            gate.approve("no-such-id")

    @pytest.mark.asyncio
    async def test_reject_unknown_raises(self) -> None:
        gate = AsyncApprovalGate()
        with pytest.raises(KeyError, match="Unknown request"):
            gate.reject("no-such-id")

    @pytest.mark.asyncio
    async def test_approve_already_resolved_raises(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")
        gate.approve(req.request_id)
        with pytest.raises(ValueError, match="already resolved"):
            gate.approve(req.request_id)

    @pytest.mark.asyncio
    async def test_reject_already_resolved_raises(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")
        gate.reject(req.request_id)
        with pytest.raises(ValueError, match="already resolved"):
            gate.reject(req.request_id)


# =============================================================================
# AsyncApprovalGate — wait 等待
# =============================================================================


@pytest.mark.anyio
class TestAsyncApprovalGateWait:
    """AsyncApprovalGate.wait() 测试。"""

    @pytest.mark.asyncio
    async def test_wait_approve_resolves(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")

        # approve() pops the future in _resolve(), so wait must start first
        wait_task = asyncio.create_task(gate.wait(req.request_id))
        await asyncio.sleep(0)  # let wait() start
        gate.approve(req.request_id, approver="ops")
        result = await wait_task
        assert result.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_wait_reject_resolves(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")

        wait_task = asyncio.create_task(gate.wait(req.request_id))
        await asyncio.sleep(0)  # let wait() start
        gate.reject(req.request_id, reason="no")
        result = await wait_task
        assert result.status == ApprovalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_wait_unknown_raises(self) -> None:
        gate = AsyncApprovalGate()
        with pytest.raises(KeyError, match="Unknown request"):
            await gate.wait("no-such-id")

    @pytest.mark.asyncio
    async def test_wait_timeout(self) -> None:
        gate = AsyncApprovalGate(default_timeout=0.05)
        req = await gate.submit("deploy")
        result = await gate.wait(req.request_id)
        assert result.status == ApprovalStatus.TIMED_OUT


# =============================================================================
# AsyncApprovalGate — 检查方法
# =============================================================================


@pytest.mark.anyio
class TestAsyncApprovalGateInspection:
    """AsyncApprovalGate list_pending / get 测试。"""

    @pytest.mark.asyncio
    async def test_list_pending(self) -> None:
        gate = AsyncApprovalGate()
        await gate.submit("a")
        await gate.submit("b")
        pending = gate.list_pending()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_list_pending_excludes_resolved(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("a")
        gate.approve(req.request_id)
        pending = gate.list_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_get(self) -> None:
        gate = AsyncApprovalGate()
        req = await gate.submit("deploy")
        found = gate.get(req.request_id)
        assert found is req

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        gate = AsyncApprovalGate()
        assert gate.get("nope") is None


# =============================================================================
# AsyncApprovalGate — 插件钩子
# =============================================================================


class TestAsyncApprovalGateHooks:
    """AsyncApprovalGate plug / unplug 测试。"""

    def test_plug_and_unplug(self) -> None:
        gate = AsyncApprovalGate()
        hooks_called: list[str] = []

        def my_hook(req):
            hooks_called.append(req.action)

        gate.plug("on_submit", my_hook)
        assert len(gate._hooks["on_submit"]) == 1

        gate.unplug("on_submit", my_hook)
        assert len(gate._hooks["on_submit"]) == 0

    def test_unplug_all(self) -> None:
        gate = AsyncApprovalGate()

        def h1(req):
            pass

        def h2(req):
            pass

        gate.plug("on_resolve", h1)
        gate.plug("on_resolve", h2)
        gate.unplug("on_resolve")  # remove all
        assert "on_resolve" not in gate._hooks

    def test_unplug_unknown_hook_noop(self) -> None:
        gate = AsyncApprovalGate()
        gate.unplug("no-such-hook")  # should not raise


@pytest.mark.anyio
class TestAsyncApprovalGateHooksAsync:
    """AsyncApprovalGate 插件触发测试（异步上下文）。"""

    @pytest.mark.asyncio
    async def test_on_submit_hook_fires(self) -> None:
        gate = AsyncApprovalGate()
        recorded: list[str] = []

        def hook(req):
            recorded.append(req.action)

        gate.plug("on_submit", hook)
        await gate.submit("deploy")
        assert recorded == ["deploy"]

    @pytest.mark.asyncio
    async def test_on_resolve_hook_fires_on_approve(self) -> None:
        gate = AsyncApprovalGate()
        recorded: list[str] = []

        def hook(req):
            recorded.append(req.status.value)

        gate.plug("on_resolve", hook)
        req = await gate.submit("deploy")
        gate.approve(req.request_id)
        assert recorded == ["approved"]

    @pytest.mark.asyncio
    async def test_on_resolve_hook_fires_on_reject(self) -> None:
        gate = AsyncApprovalGate()
        recorded: list[str] = []

        def hook(req):
            recorded.append(req.status.value)

        gate.plug("on_resolve", hook)
        req = await gate.submit("deploy")
        gate.reject(req.request_id)
        assert recorded == ["rejected"]
