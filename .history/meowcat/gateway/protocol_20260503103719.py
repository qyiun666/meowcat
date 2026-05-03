"""meowcat Gateway 协议层 — 猫与外部世界的 I/O 抽象。

Gateway = 猫的皮肤，所有协议适配器统一插在同一个 Gateway 上。
1 只猫 : 1 个 Gateway : N 个 Adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol, runtime_checkable


@dataclass(frozen=True)
class SignalContext:
    """随每次外部消息注入猫的上下文。所有 signal 隐式携带。

    核心设计: 同一只猫，同一个 Hippocampus，不同 session_id 对应不同平台。
    """

    session_id: str
    """会话标识。如 ``"cli-20260503"`` / ``"feishu-group-abc"`` / ``"desktop-zt"``。"""

    platform: str
    """平台标识。如 ``"cli"`` / ``"http"`` / ``"ws"`` / ``"feishu"`` / ``"wechat"`` / ``"desktop"``。"""

    user_id: str = "unknown"
    """外部用户标识。"""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    """ISO 8601 时间戳。构造时自动生成。"""


@runtime_checkable
class AdapterProtocol(Protocol):
    """适配器协议 — Gateway 的插件，负责一种协议/管道的收发。

    每个 Adapter 实例独立管理自己的连接/监听。Gateway 不关心
    Adapter 内部如何收发，只要求它通过回调桥接到猫的神经系统。
    """

    name: str
    """适配器唯一标识。同名挂载会覆盖。"""

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动监听循环。收到外部消息时回调，阻塞直到 stop()。

        Args:
            on_message: 收到完整消息时回调，返回猫的回复文本
            on_stream:  收到流式消息时回调，返回异步迭代器
        """
        ...

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """发送完整回复。"""
        ...

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """发送流式块。"""
        ...

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """流式结束标记。"""
        ...

    async def stop(self) -> None:
        """停止监听。"""
        ...


@runtime_checkable
class GatewayProtocol(Protocol):
    """网关协议 — 唯一外部 I/O 入口。1:1 绑定一只猫。"""

    async def start(self) -> None:
        """启动网关，开始接收所有 Adapter 的消息。"""
        ...

    async def stop(self) -> None:
        """关闭网关，停止所有 Adapter。"""
        ...

    def mount_adapter(self, adapter: AdapterProtocol) -> None:
        """挂载一个协议适配器。同名覆盖。"""
        ...

    def unmount_adapter(self, name: str) -> None:
        """卸载一个协议适配器。不存在则 no-op。"""
        ...


__all__ = ["SignalContext", "AdapterProtocol", "GatewayProtocol"]
