"""meowcat Gateway 子系统 — 猫的皮肤（外部 I/O 唯一入/出口）。

Gateway 是猫与外部世界之间的唯一 I/O 抽象层。所有协议适配器
（HTTP / WebSocket / Webhook / CLI / IPC）统一插在同一个 Gateway 上。

**1 只猫 : 1 个 Gateway : N 个 Adapter。**

使用示例::

    from meowcat import create_cat, Gateway
    from meowcat.gateway import HttpAdapter, CliAdapter

    cat = create_cat("my-cat", cerebrum=MyBrain())
    gw = Gateway(cat)
    gw.mount_adapter(HttpAdapter(port=8000))
    gw.mount_adapter(CliAdapter())
    await gw.start()  # 阻塞，所有 Adapter 并行运行
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict

from meowcat.gateway.protocol import (
    IoAdapterProtocol,
    GatewayProtocol,
    SignalContext,
)

if TYPE_CHECKING:
    from meowcat.assembly import CatBase


class Gateway:
    """猫的皮肤 — 外部 I/O 的唯一入/出口。

    非器官（不挂载到 OrganHost），是独立子系统，与 CatBase 组合而非继承。
    """

    def __init__(self, cat: CatBase) -> None:
        self.cat = cat
        self._adapters: Dict[str, IoAdapterProtocol] = {}

    # -- 适配器管理 --------------------------------------------------

    def mount_adapter(self, adapter: IoAdapterProtocol) -> None:
        """挂载一个协议适配器。同名覆盖。"""
        self._adapters[adapter.name] = adapter

    def unmount_adapter(self, name: str) -> None:
        """卸载一个协议适配器。不存在则 no-op。"""
        self._adapters.pop(name, None)

    @property
    def adapter_names(self) -> list[str]:
        """已挂载适配器名列表。"""
        return list(self._adapters.keys())

    # -- 生命周期 ----------------------------------------------------

    async def start(self) -> None:
        """启动所有 Adapter 的 serve() 循环，并行运行。"""
        if not self._adapters:
            return
        tasks = []
        for adapter in self._adapters.values():
            tasks.append(asyncio.create_task(
                adapter.serve(self._on_message, self._on_stream),
            ))
        # 所有 Adapter 并行运行，任一异常会传播
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        """停止所有 Adapter。"""
        for adapter in self._adapters.values():
            await adapter.stop()

    # -- 内部回调（Adapter → 猫神经系统）-----------------------------

    async def _on_message(self, text: str, ctx: SignalContext) -> str | None:
        """收到外部消息 → 注入猫 → 返回回复。"""
        async for event in self.cat.perceive(text, context=ctx):
            if isinstance(event, dict) and "output" in event:
                return event["output"]
        return None

    async def _on_stream(
        self, text: str, ctx: SignalContext,
    ) -> AsyncIterator[str] | None:
        """流式版本 — 逐 event 迭代。

        具体行为取决于 Purr.stream() / Mouth.speak() 在 Pipeline
        Stage 中如何 yield。此处仅迭代 perceive() 结果。
        """
        async for event in self.cat.perceive(text, context=ctx):
            if isinstance(event, dict):
                if "chunk" in event:
                    yield event["chunk"]
                elif "output" in event:
                    yield event["output"]


# -- 子模块 re-export ------------------------------------------------

from meowcat.gateway.http_adapter import HttpAdapter  # noqa: E402, F401
from meowcat.gateway.ws_adapter import WsAdapter  # noqa: E402, F401
from meowcat.gateway.webhook_adapter import WebhookAdapter  # noqa: E402, F401
from meowcat.gateway.cli_adapter import CliAdapter  # noqa: E402, F401
from meowcat.gateway.ipc_adapter import IpcAdapter  # noqa: E402, F401

__all__ = [
    "Gateway",
    "SignalContext",
    "IoAdapterProtocol",
    "GatewayProtocol",
    "HttpAdapter",
    "WsAdapter",
    "WebhookAdapter",
    "CliAdapter",
    "IpcAdapter",
]
