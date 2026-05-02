"""meowcat Pluggable mixin — 给 Noop 器官提供插件挂载/卸载能力。

v1.0.7: 15 个 Noop 器官全部获得 mount_plug / unmount_plug / _run_plugs，
使应用层可在框架默认行为上挂载插件（LLM 安全检测、TTS adapter 等）。

三种执行模式由各 Noop 类的方法自行实现（不在 Pluggable 层约束）：
- A 首命中覆盖：首个非默认值直接返回
- B 合并增强：所有插件结果 merge 到默认值
- C 完全替代：首个插件直接替代默认行为
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class Pluggable:
    """插件化 mixin — 给器官提供 hook 注册/注销/运行能力。

    **用法**::

        class NoopAmygdala(Pluggable):
            HOOKS: dict[str, dict[str, str]] = {
                "assess_safety": {"in": "user_input: str", "out": "dict[str, Any]"},
                "assess_tool_risk": {"in": "tool: str, params: dict", "out": "dict[str, Any]"},
            }

            async def assess_safety(self, user_input: str) -> dict[str, Any]:
                for _name, r in self._run_plugs("assess_safety", user_input):
                    if isinstance(r, dict) and not r.get("safe", True):
                        return r
                return {"safe": True, "risk": "none"}

    ``__slots__`` 只为 Pluggable 分配一个 ``_plugs`` 字段（dict），
    不干扰子类的 ``__dict__`` 或 ``__slots__``。
    """

    __slots__ = ("_plugs",)

    # 子类声明可挂载的 hook 及其建议签名（文档用途，不影响运行时）
    HOOKS: dict[str, dict[str, str]] = {}

    def __init__(self) -> None:
        self._plugs: dict[str, list[Callable[..., Any]]] = {}

    def mount_plug(self, hook: str, fn: Callable[..., Any]) -> None:
        """在指定 hook 上挂载插件。

        Args:
            hook: hook 名称（如 ``"assess_safety"``）。
            fn: 插件函数/协程，签名需与该 hook 的建议入参/出参兼容。
        """
        if hook not in self._plugs:
            self._plugs[hook] = []
        self._plugs[hook].append(fn)

    def unmount_plug(self, hook: str, fn: Callable[..., Any] | None = None) -> None:
        """卸载插件。

        Args:
            hook: hook 名称。
            fn: 要卸载的具体函数，None 则卸载该 hook 上的所有插件。
        """
        if hook not in self._plugs:
            return
        if fn is None:
            self._plugs[hook].clear()
            self._plugs.pop(hook, None)
        else:
            self._plugs[hook] = [f for f in self._plugs[hook] if f is not fn]
            if not self._plugs[hook]:
                self._plugs.pop(hook, None)

    def _run_plugs(
        self, hook: str, *args: Any, **kwargs: Any
    ) -> Iterator[tuple[str, Any]]:
        """按注册顺序运行插件，yield (hook_name, result)。

        调用方可自行决定如何处理返回值（取首个/合并/替代）。

        Args:
            hook: hook 名称。
            *args: 传给插件的位置参数。
            **kwargs: 传给插件的关键字参数。

        Yields:
            ``(hook_name, result)`` 元组，每个注册的插件 yield 一次。
        """
        for fn in self._plugs.get(hook, ()):
            yield hook, fn(*args, **kwargs)

    def list_plugs(self) -> dict[str, int]:
        """列出所有已挂载的 hook 及其插件数量。

        Returns:
            ``{hook_name: plugin_count}``。
        """
        return {h: len(fns) for h, fns in self._plugs.items()}


__all__ = ["Pluggable"]
