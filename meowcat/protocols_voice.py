"""meowcat 嗓音协议 — 嘴巴/咕噜/尾巴三个输出器官接口。

v1.0.7: 为 Mouth/Purr/Tail 补齐 Protocol 定义，
替换 biology.py 中 ``protocol=None`` 的弱约束。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MouthProtocol(Protocol):
    """嘴巴 — 文本输出中枢。负责最终回复的格式化与输出。

    **坐标**: ``("voice", "mouth")``
    **入边**: CEREBELLUM, AMYGDALA, BRAINSTEM
    **出边**: 无（终端输出器官）
    **反射弧**: text_dialogue, danger
    **实现方**: 应用层（输出器官）
    """

    name: str

    async def speak(self, text: str, **kwargs: Any) -> str: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class PurrProtocol(Protocol):
    """咕噜 — 流式输出中枢。负责逐 token 推送回复。

    **坐标**: ``("voice", "purr")``
    **入边**: CEREBELLUM, BRAINSTEM
    **出边**: 无（终端输出器官）
    **反射弧**: text_dialogue (stream 路径)
    **实现方**: 应用层（输出器官）
    """

    name: str

    async def stream(self, text: str, **kwargs: Any) -> Any: ...

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class TailProtocol(Protocol):
    """尾巴 — 状态栏渲染中枢。负责终端 UI / 进度条渲染。

    **坐标**: ``("voice", "tail")``
    **入边**: CEREBELLUM, BRAINSTEM
    **出边**: 无（终端输出器官）
    **反射弧**: 无直接反射弧
    **实现方**: 应用层（输出器官）
    """

    name: str

    async def render(self, state: dict[str, Any]) -> None: ...

    def diagnose(self) -> dict[str, Any]: ...


__all__ = ["MouthProtocol", "PurrProtocol", "TailProtocol"]
