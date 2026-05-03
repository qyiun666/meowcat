"""meowcat Colony — 猫群容器（v1.0.2）+ 联邦（v1.0.12）。

Colony 管理多只猫的对等协作 + 共享存储。猫在 colony 中创建时
自动注册并共享存储。

v1.0.12: 联邦能力 — 跨主机 Colony 互相感知、通信（federate + signal_remote）。

与 Kitten（主从模式）正交：
- Kitten: 主猫 spawn 分身旁 → 结果回传 (parent → child)
- Colony: 多只独立猫对等协作 (peer ↔ peer)，通过 SharedStorage 共享状态
- Colony 联邦: 跨主机 Colony 对等通信 (colony ↔ colony)，通过 FederationTransport
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from meowcat.assembly import CatBase
from meowcat.errors import IllegalNeuralPathError
from meowcat.protocols import SharedStorageProtocol
from meowcat.protocols_storage import FederationTransport

logger = logging.getLogger("meowcat.colony")


class Colony:
    """猫群容器 — 管理多只猫的对等协作 + 共享存储。

    典型用法::

        from meowcat import Colony, CatBase
        from meowcat.defaults import InMemorySharedStore

        colony = Colony("my-colony", storage=InMemorySharedStore())

        # 创建猫（自动注册 + 共享存储）
        cat_a = colony.create_cat("a")
        cat_b = colony.create_cat("b", parent_id="a")

        # 猫间通信
        result = await colony.signal_between(
            "a", "b", "brain", "hippocampus", "locate",
            query="hello",
        )

        # 结果回传
        await colony.deliver_result("a", "b", {"done": True})

        # 广播
        results = await colony.broadcast("健康检查")

    **跨猫 wiring 校验**:
    Colony 维护可选的 ``cross_wiring``（跨猫 wiring 表）。
    设置后 ``signal_between()`` 会校验跨猫边是否被允许。
    不设置则跨猫 signal 不做 wiring 校验（直接放行）。
    """

    # -- 跨猫 wiring 边类型 -------------------------------------------
    # (from_cat_id, to_cat_id) 白名单/黑名单
    _CrossEdge = tuple[str, str]

    def __init__(
        self,
        colony_id: str,
        storage: SharedStorageProtocol,
        *,
        cross_wiring_allowed: set[_CrossEdge] | None = None,
        cross_wiring_forbidden: set[_CrossEdge] | None = None,
    ) -> None:
        """构造猫群容器。

        Args:
            colony_id: 猫群唯一标识。
            storage: 共享存储实例（满足 SharedStorageProtocol）。
            cross_wiring_allowed: 跨猫白名单边。None=不校验（默认全部允许）。
            cross_wiring_forbidden: 跨猫黑名单边（优先级高于白名单）。
        """
        self.colony_id = colony_id
        self._storage = storage
        self._cats: dict[str, CatBase] = {}
        self._cross_allowed: set[Colony._CrossEdge] = cross_wiring_allowed or set(
        )
        self._cross_forbidden: set[Colony._CrossEdge] = cross_wiring_forbidden or set(
        )
        self._has_cross_wiring = (
            cross_wiring_allowed is not None or cross_wiring_forbidden is not None
        )
        # -- 联邦 (v1.0.12) -----------------------------------------------
        self._transport: FederationTransport | None = None
        self._federation_task: asyncio.Task | None = None
        self._pending_remote: dict[str, asyncio.Future] = {}
        self._federated = False

    # -- 跨猫 wiring -------------------------------------------------

    def allow_cross(self, from_cat: str, to_cat: str) -> None:
        """声明一条跨猫白名单边（from_cat → to_cat 允许 signal）。"""
        self._cross_allowed.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def forbid_cross(self, from_cat: str, to_cat: str) -> None:
        """声明一条跨猫黑名单边（from_cat → to_cat 禁止 signal）。"""
        self._cross_forbidden.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def _assert_cross_allowed(self, from_id: str, to_id: str) -> None:
        """校验跨猫边是否允许。

        Raises:
            IllegalNeuralPathError: 跨猫边不被允许。
        """
        if not self._has_cross_wiring:
            return  # 未设置 cross_wiring → 全部放行

        if (from_id, to_id) in self._cross_forbidden:
            raise IllegalNeuralPathError(
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal forbidden: {from_id} → {to_id}",
            )

        if self._cross_allowed and (from_id, to_id) not in self._cross_allowed:
            raise IllegalNeuralPathError(
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal not allowed: {from_id} → {to_id}",
            )

    # -- 创建 --------------------------------------------------------

    def create_cat(
        self,
        cat_id: str,
        *,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """在 colony 中创建一只猫并自动注册。

        Args:
            cat_id: 猫唯一标识。
            parent_id: 父猫标识（字符串，无对象引用）。
            allowed_organs: 器官访问白名单，None=全部允许。
            memory_snapshot: 父猫分配的上下文切片（写入共享存储）。
            **cat_kwargs: 传递给 CatBase 的额外参数。

        Returns:
            已注册的 CatBase 实例。
        """
        cat = CatBase(
            cat_id,
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )
        # 注入共享存储引用
        cat._colony_storage = self._storage  # type: ignore[attr-defined]

        # 注入 memory_snapshot（上下文切片）
        if memory_snapshot:
            # type: ignore[attr-defined]
            cat._memory_snapshot = memory_snapshot

        self.register(cat)
        return cat

    # -- 注册 / 移除 -------------------------------------------------

    def register(self, cat: CatBase) -> None:
        """注册一只猫到猫群（已存在则覆盖）。

        Args:
            cat: CatBase 实例。
        """
        cat._colony_storage = self._storage  # type: ignore[attr-defined]
        self._cats[cat.cat_id] = cat

    def unregister(self, cat_id: str) -> None:
        """从猫群中移除一只猫。

        Args:
            cat_id: 猫唯一标识。

        Raises:
            KeyError: 猫不存在。
        """
        del self._cats[cat_id]

    def get_cat(self, cat_id: str) -> CatBase:
        """按 ID 获取猫。

        Args:
            cat_id: 猫唯一标识。

        Returns:
            CatBase 实例。

        Raises:
            KeyError: 猫不存在。
        """
        return self._cats[cat_id]

    def list_cats(self) -> list[str]:
        """列出猫群中所有猫的 ID。

        Returns:
            cat_id 列表。
        """
        return list(self._cats.keys())

    # -- 别名方法 (v1.0.9) -------------------------------------------

    def adopt(self, cat: CatBase) -> None:
        """收养一只猫（register 的语义别名）。

        Args:
            cat: CatBase 实例。
        """
        self.register(cat)

    def release(self, cat_id: str) -> None:
        """释放一只猫（unregister 的语义别名）。

        Args:
            cat_id: 猫唯一标识。

        Raises:
            KeyError: 猫不存在。
        """
        self.unregister(cat_id)

    # -- 共享存储（命名空间隔离）--------------------------------------

    def _ns_key(self, cat_id: str, key: str) -> str:
        """构造命名空间隔离的存储 key。

        cat_id 前缀自动隔离：``cat-a/memories/xxx`` vs ``cat-b/memories/xxx``。
        """
        return f"{cat_id}/{key}"

    async def storage_get(self, cat_id: str, key: str) -> Any:
        """猫读取共享存储（自动 cat_id 前缀隔离）。"""
        return await self._storage.get(self._ns_key(cat_id, key))

    async def storage_set(self, cat_id: str, key: str, value: Any) -> None:
        """猫写入共享存储（自动 cat_id 前缀隔离）。"""
        await self._storage.set(self._ns_key(cat_id, key), value)

    async def storage_delete(self, cat_id: str, key: str) -> None:
        """猫删除共享存储条目。"""
        await self._storage.delete(self._ns_key(cat_id, key))

    async def storage_list_keys(self, cat_id: str) -> list[str]:
        """列出猫的所有共享存储 key（去名前缀）。"""
        prefix = f"{cat_id}/"
        all_keys = await self._storage.list_keys()
        return [
            k[len(prefix):] for k in all_keys if k.startswith(prefix)
        ]

    async def storage_watch(
        self, cat_id: str, pattern: str,
    ) -> Any:
        """监听共享存储中匹配 pattern 的 key 变更。

        委托给底层 storage.watch()。返回 AsyncIterator。
        """
        ns_pattern = f"{cat_id}/{pattern}"
        # type: ignore[attr-defined]
        async for item in self._storage.watch(ns_pattern):
            yield item

    # -- 结果回传 ----------------------------------------------------

    async def deliver_result(
        self, parent_id: str, from_kitten: str, result: Any,
    ) -> None:
        """分身旁回传结果给父猫。

        写入共享存储 ``{parent_id}/kitten:{from_kitten}/result``。

        Args:
            parent_id: 父猫 ID。
            from_kitten: 分身旁 ID。
            result: 回传的任意结果。
        """
        key = f"kitten:{from_kitten}/result"
        await self.storage_set(parent_id, key, result)

    # -- 广播 --------------------------------------------------------

    async def broadcast(self, event: str, **data: Any) -> list[Any]:
        """向猫群中所有猫广播事件。

        对每只猫 emit 同名事件，收集所有 handler 返回值。

        Args:
            event: 事件名。
            **data: 事件数据。

        Returns:
            所有猫的 handler 返回值列表。
        """
        results: list[Any] = []
        for cat in self._cats.values():
            await cat.emit(event, data)
        return results

    async def health_check_all(self) -> dict[str, dict]:
        """对所有猫执行全身体检。

        Returns:
            ``{cat_id: {...diagnose...}, ...}``
        """
        results: dict[str, dict] = {}
        for cat_id, cat in self._cats.items():
            try:
                results[cat_id] = await cat.health_check()
            except Exception as exc:
                results[cat_id] = {"error": str(exc)}
        return results

    # -- 猫间通信 ----------------------------------------------------

    async def signal_between(
        self,
        from_id: str,
        to_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """猫间 signal 通信。

        一只猫通过 colony 向另一只猫的器官发送 signal。

        流程：
        1. 校验跨猫 wiring（如已设置 cross_wiring）
        2. 从目标猫取出目标器官
        3. 直接调用目标器官上的方法

        Args:
            from_id: 发送方猫 ID。
            to_id: 接收方猫 ID。
            to_category: 目标器官类别（如 "brain"）。
            to_name: 目标器官名（如 "hippocampus"）。
            method: 目标方法名。
            *args, **kw: 转发给目标方法。

        Returns:
            目标方法的返回值。

        Raises:
            KeyError: 发送方或接收方猫不存在。
            IllegalNeuralPathError: 跨猫边不被允许。
            OrganNotMountedError: 目标器官不存在。
        """
        # 1. 跨猫 wiring 校验
        self._assert_cross_allowed(from_id, to_id)

        # 2. 获取目标猫
        target_cat = self._cats[to_id]

        # 3. 取出目标器官
        target_organ = target_cat.organ(to_category, to_name)

        # 4. 调用方法
        fn = getattr(target_organ, method)
        import inspect as _inspect
        result = fn(*args, **kw)
        if _inspect.isawaitable(result):
            result = await result
        return result

    # -- 方便方法 ----------------------------------------------------

    @property
    def cat_count(self) -> int:
        """猫群中的猫数量。"""
        return len(self._cats)

    # -- 联邦 (v1.0.12) -----------------------------------------------

    @property
    def is_federated(self) -> bool:
        """是否已启用联邦。"""
        return self._federated

    async def federate(self, transport: FederationTransport) -> None:
        """启用联邦能力，接入跨主机 Colony 网络。

        启动传输层并开始监听来自其他 Colony 的入站消息。
        与 Colony.federate() 配对使用后，可调用 signal_remote()
        向远端 Colony 中的猫发送信号。

        Args:
            transport: 联邦传输实例（如 TCPSocketTransport 或 RedisPubSubTransport）。

        Raises:
            RuntimeError: 已启用联邦。
        """
        if self._federated:
            raise RuntimeError(f"Colony '{self.colony_id}' is already federated")

        self._transport = transport
        await transport.start()
        self._federated = True
        self._federation_task = asyncio.create_task(
            self._federation_loop(),
            name=f"colony-federation-{self.colony_id}",
        )
        logger.info("Colony '%s' federated", self.colony_id)

    async def unfederate(self) -> None:
        """停用联邦，断开跨主机连接。"""
        if not self._federated:
            return

        if self._federation_task:
            self._federation_task.cancel()
            try:
                await self._federation_task
            except asyncio.CancelledError:
                pass
            self._federation_task = None

        if self._transport:
            await self._transport.stop()
            self._transport = None

        # 取消所有未完成的远程请求
        for fut in self._pending_remote.values():
            if not fut.done():
                fut.cancel()
        self._pending_remote.clear()

        self._federated = False
        logger.info("Colony '%s' unfederated", self.colony_id)

    async def signal_remote(
        self,
        target_colony: str,
        cat_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """向远端 Colony 中的猫发送信号并等待响应。

        要求本 Colony 已调用 federate() 启用联邦。
        远端 Colony 的 wiring 仍然生效 — 远端猫自身的 wiring 会校验
        目标器官和方法是否可访问。

        Args:
            target_colony: 远端 colony_id。
            cat_id: 远端猫 ID。
            to_category: 目标器官类别。
            to_name: 目标器官名。
            method: 目标方法名。
            *args, **kw: 转发给目标方法的参数。

        Returns:
            远端方法的返回值（必须是 JSON 可序列化的）。

        Raises:
            RuntimeError: 本 Colony 未启用联邦。
            ConnectionError: 无法到达远端。
            TimeoutError: 等待远端响应超时。
            IllegalNeuralPathError: 远端 wiring 拒绝该通路。
        """
        if not self._federated or self._transport is None:
            raise RuntimeError(
                f"Colony '{self.colony_id}' is not federated. "
                f"Call colony.federate(transport) first."
            )

        request_id = uuid.uuid4().hex
        payload: dict[str, Any] = {
            "type": "signal_request",
            "request_id": request_id,
            "from_colony": self.colony_id,
            "to_cat": cat_id,
            "to_category": to_category,
            "to_name": to_name,
            "method": method,
            "args": args,
            "kw": kw,
        }

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_remote[request_id] = fut

        try:
            await self._transport.publish(target_colony, payload)
            result = await asyncio.wait_for(fut, timeout=30.0)
            if result.get("error"):
                raise IllegalNeuralPathError(
                    ("colony", cat_id), (to_category, to_name),
                    reason=result["error"],
                )
            return result.get("data")
        finally:
            self._pending_remote.pop(request_id, None)

    async def _federation_loop(self) -> None:
        """联邦后台循环：接收入站消息并分发处理。"""
        if self._transport is None:
            return

        try:
            async for msg in self._transport.subscribe(self.colony_id):
                await self._handle_federation_message(msg)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Federation loop error in colony '%s'", self.colony_id)

    async def _handle_federation_message(self, msg: dict) -> None:
        """处理一条入站联邦消息。"""
        msg_type = msg.get("type")

        if msg_type == "signal_request":
            await self._handle_signal_request(msg)
        elif msg_type == "signal_response":
            self._handle_signal_response(msg)
        else:
            logger.warning("Unknown federation message type: %s", msg_type)

    async def _handle_signal_request(self, msg: dict) -> None:
        """处理远端发来的 signal 请求。"""
        request_id = msg["request_id"]
        from_colony = msg.get("from_colony", "unknown")
        cat_id = msg["to_cat"]
        to_category = msg["to_category"]
        to_name = msg["to_name"]
        method = msg["method"]
        args = msg.get("args", ())
        kw = msg.get("kw", {})

        response: dict[str, Any] = {
            "type": "signal_response",
            "request_id": request_id,
            "from_colony": self.colony_id,
        }

        # 校验目标猫存在
        if cat_id not in self._cats:
            response["error"] = f"Cat '{cat_id}' not found in colony '{self.colony_id}'"
        else:
            try:
                # 获取目标猫和器官
                target_cat = self._cats[cat_id]
                target_organ = target_cat.organ(to_category, to_name)
                fn = getattr(target_organ, method)

                import inspect as _inspect
                result = fn(*args, **kw)
                if _inspect.isawaitable(result):
                    result = await result

                response["data"] = result
            except Exception as exc:
                response["error"] = str(exc)

        # 发回响应
        if self._transport:
            try:
                await self._transport.publish(from_colony, response)
            except Exception:
                logger.exception(
                    "Failed to send signal_response to '%s'", from_colony,
                )

    def _handle_signal_response(self, msg: dict) -> None:
        """处理远端发来的 signal 响应。"""
        request_id = msg["request_id"]
        fut = self._pending_remote.get(request_id)
        if fut and not fut.done():
            fut.set_result(msg)


__all__ = ["Colony", "FederationTransport"]
