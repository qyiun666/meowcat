"""meowcat 感知上下文与模态推断。

:class:`PerceptionContext` 是 ``cat.perceive(input)`` 执行过程中跨 Stage
共享的状态容器；:func:`infer_modality` 根据输入形态做粗糙模态推断，
业务层可直接在 Reflex.trigger 里自定义更精细的判断。

零 meowagent 依赖。
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from meowcat.protocols import CatProtocol

Modality = Literal["text", "image", "audio", "tool_result", "unknown"]


class PerceptionContext(BaseModel):
    """``cat.perceive`` 的执行上下文。

    供 Reflex.stages 共享状态使用，是 Pipeline 上的 ``ctx``。
    """

    model_config = {"arbitrary_types_allowed": True}

    input: Any
    """原始输入——文字、字节流、dict、任意对象。"""

    modality: Modality = "unknown"
    """推断的输入模态。"""

    reflex_name: str = ""
    """命中的反射名。"""

    cat: Any = None
    """CatBase 实例的反向引用，便于 Stage 里 signal。"""

    short_circuited: bool = False
    """任一 Stage 触发 short_circuit 后置 True。"""

    final_reply: str | None = None
    """最终回复（给 CLI/TUI 取值用）。"""

    extras: dict[str, Any] = Field(default_factory=dict)
    """业务层自定义字段的兜底袋。"""


# -- 模态推断 ---------------------------------------------------

_IMAGE_MAGIC: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",    # PNG
    b"\xff\xd8\xff",           # JPEG
    b"GIF87a", b"GIF89a",       # GIF
    b"RIFF",                    # WEBP 开头
    b"BM",                      # BMP
)

_AUDIO_MAGIC: tuple[bytes, ...] = (
    b"RIFF",                    # WAV (RIFF....WAVE)；与 WEBP 首魔数冲突，按场景选其一
    b"ID3",                     # MP3 带 ID3
    b"\xff\xfb", b"\xff\xf3",   # MP3 帧头
    b"OggS",                    # OGG
    b"fLaC",                    # FLAC
)


def infer_modality(input: Any) -> Modality:
    """粗略判断输入模态。

    - ``str`` → ``text``
    - ``bytes`` 且匹配图像魔数 → ``image``
    - ``bytes`` 且匹配音频魔数 → ``audio``
    - ``dict`` 且含 ``tool_result`` 键 → ``tool_result``
    - 其余 → ``unknown``

    业务层若需要更精细的判别，直接在 ``Reflex.trigger`` 里自写。
    """
    if isinstance(input, str):
        return "text"

    if isinstance(input, (bytes, bytearray)):
        data = bytes(input[:16])
        for magic in _IMAGE_MAGIC:
            if data.startswith(magic):
                return "image"
        for magic in _AUDIO_MAGIC:
            if data.startswith(magic):
                return "audio"
        return "unknown"

    if isinstance(input, dict) and "tool_result" in input:
        return "tool_result"

    return "unknown"


__all__ = ["PerceptionContext", "Modality", "infer_modality"]
