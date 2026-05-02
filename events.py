"""meowcat 事件总线 — 猫的神经信号系统。

零业务语义：
- 事件名是字符串（推荐用 ``meowcat.loop`` 里的常量）
- handler 可以是同步或异步函数，``emit`` 会自动 await awaitable 返回值
- 失败的 handler 不吞，抛出由调用方处理（框架不替业务决定）

P-02 哲学：最少代码量。EventBus 只做"事件名 → 回调列表"的转发。
"""

from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any, Callable


Handler = Callable[..., Any]

__all__ = ["EventBus", "Handler"]


class EventBus:
    """猫神经系统：事件名 ↔ handler 列表。"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    # -- 注册 --------------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """注册 handler。

        两种用法：

            bus.on("locate.pre", my_handler)

            @bus.on("locate.pre")
            def my_handler(payload): ...
        """
        if handler is None:
            def decorator(fn: Handler) -> Handler:
                self._handlers[event].append(fn)
                return fn
            return decorator
        self._handlers[event].append(handler)
        return handler

    def off(self, event: str, handler: Handler) -> bool:
        """注销 handler。handler 不存在返回 False，不抛。"""
        lst = self._handlers.get(event)
        if not lst or handler not in lst:
            return False
        lst.remove(handler)
        return True

    def clear(self, event: str | None = None) -> None:
        """清空指定事件或全部事件的 handler。"""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)

    # -- 触发 --------------------------------------------------------

    async def emit(self, event: str, payload: Any = None) -> None:
        """按注册顺序同步触发；awaitable 返回值自动 await。

        handler 接受 0 或 1 个参数均可：
        - ``def h(): ...``         → 被调用时不传参
        - ``def h(payload): ...``  → 传入 payload
        """
        for handler in list(self._handlers.get(event, [])):
            result = self._invoke(handler, payload)
            if inspect.isawaitable(result):
                await result

    @staticmethod
    def _invoke(handler: Handler, payload: Any) -> Any:
        """根据 handler 形参个数决定是否传 payload。"""
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            return handler(payload)
        if len(sig.parameters) == 0:
            return handler()
        return handler(payload)

    # -- 内省 --------------------------------------------------------

    def handlers(self, event: str) -> list[Handler]:
        """返回已注册的 handler 快照（方便测试/调试）。"""
        return list(self._handlers.get(event, []))

    def events(self) -> list[str]:
        """返回所有有 handler 的事件名。"""
        return [e for e, hs in self._handlers.items() if hs]
