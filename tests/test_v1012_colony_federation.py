"""v1.0.12 — Colony 联邦测试
==============================

验证:
    1. TestFederationProtocol      — FederationTransport 协议校验
    2. TestColonyFederateLifecycle  — federate/unfederate 生命周期
    3. TestColonySignalRemote       — signal_remote 跨 Colony 通信
    4. TestColonySignalRemoteErrors — signal_remote 错误路径
    5. TestTCPSocketTransport       — TCP 传输层收发
    6. TestTCPSocketTransportErrors — TCP 传输层错误路径
    7. TestColonyFederationE2E      — 端到端联邦通信（双 Colony TCP）
    8. TestColonyFederationIsolation — 默认隔离（不 federate 不可见）
    9. TestColonyPendingCleanup     — unfederate 清理未完成请求
"""

from __future__ import annotations

import asyncio
import json

import pytest

from meowcat.assembly import CatBase
from meowcat.testing import make_cat
from meowcat.colony import Colony
from meowcat.colony_transports import TCPSocketTransport, RedisPubSubTransport
from meowcat.defaults.stores import InMemorySharedStore
from meowcat.errors import IllegalNeuralPathError
from meowcat.protocols_storage import FederationTransport


# -- 辅助 -------------------------------------------------------------

class _MockHippocampus:
    """模拟海马体。"""

    def __init__(self) -> None:
        self.memories: list[str] = []

    def locate(self, query: str) -> dict:
        return {"results": self.memories, "query": query}

    def remember(self, content: str) -> dict:
        self.memories.append(content)
        return {"stored": content}

    def diagnose(self) -> dict:
        return {"memories": len(self.memories)}


class _MockCerebrum:
    """模拟大脑。"""

    def generate(self, prompt: str) -> str:
        return f"echo: {prompt}"

    def diagnose(self) -> dict:
        return {"status": "ok"}


def _make_cat(name: str) -> CatBase:
    """创建一个带海马体和大脑的测试猫。"""
    cat = make_cat(name)
    cat.mount("brain", "hippocampus", _MockHippocampus())
    cat.mount("brain", "cerebrum", _MockCerebrum())
    return cat


# -- 1. FederationTransport 协议校验 ---------------------------------

class TestFederationProtocol:
    """FederationTransport 是 Protocol，可用 isinstance 校验。"""

    def test_tcp_transport_is_federation(self) -> None:
        t = TCPSocketTransport(host="127.0.0.1", port=19999)
        assert isinstance(t, FederationTransport)

    def test_redis_transport_is_federation(self) -> None:
        t = RedisPubSubTransport(colony_id="test", client=None)
        # RedisPubSubTransport 在构造时不检查 client，isinstance 仍应通过
        assert isinstance(t, FederationTransport)


# -- 2. Colony federate / unfederate 生命周期 ------------------------

class TestColonyFederateLifecycle:
    """federate / unfederate 生命周期管理。"""

    @pytest.mark.asyncio
    async def test_federate_and_unfederate(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test-colony", storage=store)
        transport = TCPSocketTransport(host="127.0.0.1", port=19990)

        assert not colony.is_federated

        await colony.federate(transport)
        assert colony.is_federated

        await colony.unfederate()
        assert not colony.is_federated

    @pytest.mark.asyncio
    async def test_double_federate_raises(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test-colony", storage=store)
        t1 = TCPSocketTransport(host="127.0.0.1", port=19991)
        t2 = TCPSocketTransport(host="127.0.0.1", port=19992)

        await colony.federate(t1)
        try:
            with pytest.raises(RuntimeError, match="already federated"):
                await colony.federate(t2)
        finally:
            await colony.unfederate()

    @pytest.mark.asyncio
    async def test_unfederate_idempotent(self) -> None:
        """重复 unfederate 不报错。"""
        store = InMemorySharedStore()
        colony = Colony("test-colony", storage=store)
        transport = TCPSocketTransport(host="127.0.0.1", port=19993)

        await colony.federate(transport)
        await colony.unfederate()
        await colony.unfederate()  # 不应报错
        assert not colony.is_federated

    @pytest.mark.asyncio
    async def test_signal_remote_without_federation(self) -> None:
        """未 federate 时调用 signal_remote 应报错。"""
        store = InMemorySharedStore()
        colony = Colony("test-colony", storage=store)

        with pytest.raises(RuntimeError, match="not federated"):
            await colony.signal_remote(
                "other", "cat-1", "brain", "hippocampus", "locate",
            )


# -- 3. signal_remote 跨 Colony 通信 --------------------------------

class TestColonySignalRemote:
    """signal_remote 通过 TCP 传输向远端 Colony 发送信号。"""

    @pytest.mark.asyncio
    async def test_signal_remote_tcp(self) -> None:
        """端到端: colony-a → TCP → colony-b → signal_remote 返回结果。"""
        store_a = InMemorySharedStore()
        store_b = InMemorySharedStore()

        colony_a = Colony("colony-a", storage=store_a)
        colony_b = Colony("colony-b", storage=store_b)

        # 挂载猫到 colony_b
        cat_b = _make_cat("cat-b")
        colony_b.register(cat_b)

        # 设置传输层
        t_a = TCPSocketTransport(host="127.0.0.1", port=19994)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19995)

        t_a.register_peer("colony-b", "127.0.0.1", 19995)
        t_b.register_peer("colony-a", "127.0.0.1", 19994)

        await colony_a.federate(t_a)
        await colony_b.federate(t_b)

        try:
            # 给传输一点时间建立连接
            await asyncio.sleep(0.05)

            result = await colony_a.signal_remote(
                "colony-b", cat_b.cat_uid,
                "brain", "hippocampus", "locate",
                query="hello federation",
            )
            assert result == {"results": [], "query": "hello federation"}
        finally:
            await colony_a.unfederate()
            await colony_b.unfederate()

    @pytest.mark.asyncio
    async def test_signal_remote_with_args(self) -> None:
        """signal_remote 带位置参数。"""
        store_a = InMemorySharedStore()
        store_b = InMemorySharedStore()

        colony_a = Colony("colony-a", storage=store_a)
        colony_b = Colony("colony-b", storage=store_b)

        cat_b = _make_cat("cat-b")
        colony_b.register(cat_b)

        t_a = TCPSocketTransport(host="127.0.0.1", port=19996)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19997)
        t_a.register_peer("colony-b", "127.0.0.1", 19997)
        t_b.register_peer("colony-a", "127.0.0.1", 19996)

        await colony_a.federate(t_a)
        await colony_b.federate(t_b)

        try:
            await asyncio.sleep(0.05)

            result = await colony_a.signal_remote(
                "colony-b", cat_b.cat_uid,
                "brain", "cerebrum", "generate",
                "test prompt",
            )
            assert result == "echo: test prompt"
        finally:
            await colony_a.unfederate()
            await colony_b.unfederate()

    @pytest.mark.asyncio
    async def test_signal_remote_cat_not_found(self) -> None:
        """远端猫不存在时返回 error。"""
        store_a = InMemorySharedStore()
        store_b = InMemorySharedStore()

        colony_a = Colony("colony-a", storage=store_a)
        colony_b = Colony("colony-b", storage=store_b)

        t_a = TCPSocketTransport(host="127.0.0.1", port=19998)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19999)
        t_a.register_peer("colony-b", "127.0.0.1", 19999)
        t_b.register_peer("colony-a", "127.0.0.1", 19998)

        await colony_a.federate(t_a)
        await colony_b.federate(t_b)

        try:
            await asyncio.sleep(0.05)

            with pytest.raises(IllegalNeuralPathError, match="not found"):
                await colony_a.signal_remote(
                    "colony-b", "nonexistent",
                    "brain", "hippocampus", "locate",
                )
        finally:
            await colony_a.unfederate()
            await colony_b.unfederate()


# -- 4. TCPSocketTransport 收发 --------------------------------------

class TestTCPSocketTransport:
    """TCPSocketTransport 基本收发功能。"""

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        t = TCPSocketTransport(host="127.0.0.1", port=19980)
        await t.start()
        await t.stop()

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self) -> None:
        """发布消息后能在 subscribe 中收到。"""
        t_a = TCPSocketTransport(host="127.0.0.1", port=19981)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19982)

        t_a.register_peer("colony-b", "127.0.0.1", 19982)

        await t_a.start()
        await t_b.start()

        try:
            await asyncio.sleep(0.02)

            # 发布一条消息
            await t_a.publish("colony-b", {"type": "hello", "msg": "world"})

            # 从 t_b 的 subscribe 中读取
            sub_iter = t_b.subscribe("colony-b")
            msg = await asyncio.wait_for(sub_iter.__anext__(), timeout=2.0)
            assert msg["type"] == "hello"
            assert msg["msg"] == "world"
        finally:
            await t_a.stop()
            await t_b.stop()

    @pytest.mark.asyncio
    async def test_request_response(self) -> None:
        """request 发送请求并通过 subscribe 收响应。"""
        t_a = TCPSocketTransport(host="127.0.0.1", port=19983)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19984)

        t_a.register_peer("colony-b", "127.0.0.1", 19984)
        t_b.register_peer("colony-a", "127.0.0.1", 19983)

        await t_a.start()
        await t_b.start()

        try:
            await asyncio.sleep(0.02)

            # 后台: t_b 收到请求后回传响应
            async def _responder() -> None:
                sub_iter = t_b.subscribe("colony-b")
                req = await asyncio.wait_for(sub_iter.__anext__(), timeout=2.0)
                # 回传响应（模拟 Colony 的联邦调度）
                await t_b.publish("colony-a", {
                    "type": "signal_response",
                    "request_id": req["request_id"],
                    "data": {"echo": req.get("msg")},
                })

            responder_task = asyncio.create_task(_responder())

            # t_a 发送请求并等待响应
            result = await t_a.request("colony-b", {"type": "test", "msg": "ping"})
            assert result["data"] == {"echo": "ping"}

            await responder_task
        finally:
            await t_a.stop()
            await t_b.stop()

    @pytest.mark.asyncio
    async def test_publish_unknown_peer(self) -> None:
        """publish 到未注册的 colony 报错。"""
        t = TCPSocketTransport(host="127.0.0.1", port=19985)
        await t.start()
        try:
            with pytest.raises(ValueError, match="Unknown peer"):
                await t.publish("unknown-colony", {"type": "test"})
        finally:
            await t.stop()


# -- 5. Colony 联邦安全隔离 ------------------------------------------

class TestColonyFederationIsolation:
    """联邦安全约束测试。"""

    @pytest.mark.asyncio
    async def test_default_isolation(self) -> None:
        """不调用 federate 的 Colony 互相不可见。"""
        store_a = InMemorySharedStore()
        store_b = InMemorySharedStore()

        colony_a = Colony("colony-a", storage=store_a)
        colony_b = Colony("colony-b", storage=store_b)

        assert not colony_a.is_federated
        assert not colony_b.is_federated

        # 没有联邦就无法 signal_remote
        with pytest.raises(RuntimeError, match="not federated"):
            await colony_a.signal_remote(
                "colony-b", "cat-b", "brain", "hippocampus", "locate",
            )

    @pytest.mark.asyncio
    async def test_cross_colony_wiring_still_applies(self) -> None:
        """远端 Colony 的 wiring 在 signal_remote 时仍然生效。"""
        store_a = InMemorySharedStore()
        store_b = InMemorySharedStore()

        colony_a = Colony("colony-a", storage=store_a)
        colony_b = Colony("colony-b", storage=store_b)

        # cat_b 只有 hippocampus，没有 paws
        cat_b = _make_cat("cat-b")
        colony_b.register(cat_b)

        t_a = TCPSocketTransport(host="127.0.0.1", port=19986)
        t_b = TCPSocketTransport(host="127.0.0.1", port=19987)
        t_a.register_peer("colony-b", "127.0.0.1", 19987)
        t_b.register_peer("colony-a", "127.0.0.1", 19986)

        await colony_a.federate(t_a)
        await colony_b.federate(t_b)

        try:
            await asyncio.sleep(0.05)

            # 调用不存在的器官 → 应报错
            with pytest.raises(IllegalNeuralPathError):
                await colony_a.signal_remote(
                    "colony-b", "cat-b",
                    "sense", "paws", "execute",
                )
        finally:
            await colony_a.unfederate()
            await colony_b.unfederate()


# -- 6. 未完成请求清理 ------------------------------------------------

class TestColonyPendingCleanup:
    """unfederate 时清理未完成的远程请求。"""

    @pytest.mark.asyncio
    async def test_unfederate_cancels_pending(self) -> None:
        store = InMemorySharedStore()
        colony = Colony("test-colony", storage=store)
        transport = TCPSocketTransport(host="127.0.0.1", port=19988)

        await colony.federate(transport)
        try:
            # 注入一个假的 pending request（模拟等待中的远程调用）
            fut: asyncio.Future = asyncio.get_event_loop().create_future()
            colony._pending_remote["fake-id"] = fut

            await colony.unfederate()

            # pending 应该被清理
            assert len(colony._pending_remote) == 0
            # future 应该被取消
            assert fut.cancelled()
        finally:
            if colony.is_federated:
                await colony.unfederate()


# -- 7. RedisPubSubTransport 基础 ------------------------------------

class TestRedisPubSubTransportBasic:
    """RedisPubSubTransport 基础初始化。"""

    def test_init_with_client_none(self) -> None:
        """构造时不校验 client，允许延迟注入。"""
        t = RedisPubSubTransport(colony_id="test", client=None)
        assert t._colony_id == "test"
        assert isinstance(t, FederationTransport)
