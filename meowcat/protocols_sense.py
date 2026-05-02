"""meowcat 感官协议 — 耳朵/眼睛/胡须/爪子等感觉器官接口。

全部 typing.Protocol（鸭子类型），零第三方依赖。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "EarsProtocol", "EyesProtocol", "WhiskersProtocol", "PawsProtocol",
]


@runtime_checkable
class EarsProtocol(Protocol):
    """耳朵 — 文本与音频输入接收中枢。所有外部文本/语音经此进入神经系统。

    **坐标**: ``("sense", "ears")``
    **入边**: 无（纯输入端，仅接受外部调用）
    **出边**: THALAMUS
    **反射弧**: text_dialogue, danger, action_order
    **实现方**: 应用层（感官器官）
    """
    name: str
    async def hear(self, raw_input: str | bytes) -> dict[str, Any]: ...
    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]: ...
    def detect_language(self, text: str) -> str: ...
    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class EyesProtocol(Protocol):
    """眼睛 — 图像/视频视觉输入。

    v1.0.8: scan_screen / describe 已移除（属于应用层特定功能），
    只保留通用 see 方法。

    **坐标**: ``("sense", "eyes")``
    **入边**: 无（纯输入端，仅接受外部调用）
    **出边**: THALAMUS
    **反射弧**: visual (EYES→THALAMUS→CEREBRUM→CEREBELLUM→MOUTH)
    **实现方**: 应用层（感官器官）
    """
    name: str

    async def see(self, image_data: bytes,
                  mime_type: str = "image/png") -> dict[str, Any]: ...


@runtime_checkable
class WhiskersProtocol(Protocol):
    """胡须 — 环境感知与安全检测。输入/输出感觉、漂移检测、幻觉检测。

    **坐标**: ``("sense", "whiskers")``
    **入边**: 无（纯输入端，仅接受外部调用）
    **出边**: THALAMUS
    **反射弧**: 无直接反射弧，通过 feel_input/feel_output 在 Pipeline 中被调用
    **实现方**: 应用层（感官器官）
    """
    name: str
    async def feel_input(self, text: str) -> dict[str, Any]: ...
    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]: ...
    def check_hallucination(
        self, reply: str, session_id: str | None = None) -> dict[str, Any]: ...


@runtime_checkable
class PawsProtocol(Protocol):
    """爪子 — 工具执行与文件操作。Skills + MCP 工具调用的效应器。

    **坐标**: ``("sense", "paws")``
    **入边**: CEREBELLUM（唯一入边，大脑不直连四肢）
    **出边**: 无（终端效应器，只接受命令不主动调用）
    **反射弧**: action_order (EARS→THALAMUS→AMYGDALA→CEREBELLUM→PAWS)
    **实现方**: 应用层（感官器官）
    """
    name: str

    async def execute(self, tool_name: str,
                      params: dict[str, Any]) -> dict[str, Any]: ...

    # -- deprecated（v1.0.8，内部 delegate 到 execute）-----------
    async def touch_file(self, path: str, content: str |
                         None = None) -> dict[str, Any]: ...

    async def run_command(self, command: str, **
                          kwargs: Any) -> dict[str, Any]: ...

    async def interact_with_tool(
        self, skill_name: str, params: dict[str, Any]) -> dict[str, Any]: ...
