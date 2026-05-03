"""meowcat 框架级异常。

仅定义框架自身的错误类型，不涉及业务异常。
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import Any


class MeowCatError(Exception):
    """meowcat 框架所有异常的基类。"""


class OrganNotMountedError(MeowCatError):
    """尝试访问未挂载的器官时抛出。"""

    def __init__(self, category: str, name: str) -> None:
        self.category = category
        self.name = name
        super().__init__(f"Organ not mounted: {category}/{name}")


class LoopFailedError(MeowCatError):
    """闭环执行失败时抛出。"""

    def __init__(self, loop_name: str, reason: str = "") -> None:
        self.loop_name = loop_name
        self.reason = reason
        msg = f"Loop '{loop_name}' failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StageTimeoutError(MeowCatError):
    """Pipeline Stage 执行超时时抛出。"""

    def __init__(self, stage_name: str, timeout: float) -> None:
        self.stage_name = stage_name
        self.timeout = timeout
        super().__init__(
            f"Stage '{stage_name}' timed out after {timeout}s"
        )


# -- v0.5.1 新增：神经系统异常 ----------------------------------


class IllegalNeuralPathError(MeowCatError):
    """通过 cat.signal() 调用了 wiring 图未允许（或明令禁止）的通路。

    生物学意义：违反"大脑不直连四肢"这类神经解剖学规律。
    """

    def __init__(
        self,
        from_organ: tuple[str, str],
        to_organ: tuple[str, str],
        reason: str = "not allowed by wiring",
    ) -> None:
        self.from_organ = from_organ
        self.to_organ = to_organ
        self.reason = reason
        super().__init__(
            f"Illegal neural path: {from_organ[0]}/{from_organ[1]} "
            f"→ {to_organ[0]}/{to_organ[1]} ({reason})"
        )


class ReflexPathInvalidError(MeowCatError):
    """反射弧 path 某一跳在 wiring 里不合法。

    在 ``cat.freeze_nervous_system()`` 时统一校验抛出。
    """

    def __init__(
        self,
        reflex_name: str,
        hop: tuple[tuple[str, str], tuple[str, str]],
    ) -> None:
        self.reflex_name = reflex_name
        self.hop = hop
        frm, to = hop
        super().__init__(
            f"Reflex '{reflex_name}' hop illegal: "
            f"{frm[0]}/{frm[1]} → {to[0]}/{to[1]}"
        )


class NoReflexMatchedError(MeowCatError):
    """``cat.perceive(input)`` 时没有任何已注册反射的 trigger 命中。"""

    def __init__(self, input_repr: str) -> None:
        self.input_repr = input_repr
        super().__init__(f"No reflex matched input: {input_repr[:80]}")


class OrganProtocolMismatchError(MeowCatError):
    """``cat.mount(category, name, organ, protocol=P)`` 时 organ 不满足 P。"""

    def __init__(
        self,
        category: str,
        name: str,
        protocol: Any,
        organ: Any,
    ) -> None:
        self.category = category
        self.name = name
        self.protocol = protocol
        self.organ = organ
        super().__init__(
            f"Organ {category}/{name} "
            f"(type={type(organ).__name__}) "
            f"does not satisfy protocol {getattr(protocol, '__name__', protocol)}"
        )


__all__ = [
    "MeowCatError",
    "OrganNotMountedError",
    "LoopFailedError",
    "StageTimeoutError",
    "IllegalNeuralPathError",
    "ReflexPathInvalidError",
    "NoReflexMatchedError",
    "OrganProtocolMismatchError",
]
