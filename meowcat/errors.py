"""meowcat framework-level exceptions.

Only defines framework-internal error types, no business exceptions.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from typing import Any


class MeowCatError(Exception):
    """Base class for all meowcat framework exceptions."""


class OrganNotMountedError(MeowCatError):
    """Raised when attempting to access an unmounted organ."""

    def __init__(self, category: str, name: str) -> None:
        self.category = category
        self.name = name
        super().__init__(f"Organ not mounted: {category}/{name}")


class LoopFailedError(MeowCatError):
    """Raised when a loop execution fails."""

    def __init__(self, loop_name: str, reason: str = "") -> None:
        self.loop_name = loop_name
        self.reason = reason
        msg = f"Loop '{loop_name}' failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class StageTimeoutError(MeowCatError):
    """Raised when a Pipeline Stage execution times out."""

    def __init__(self, stage_name: str, timeout: float) -> None:
        self.stage_name = stage_name
        self.timeout = timeout
        super().__init__(
            f"Stage '{stage_name}' timed out after {timeout}s"
        )


# -- v0.5.1 added: nervous system exceptions ----------------------------------


class IllegalNeuralPathError(MeowCatError):
    """Called via cat.signal() on a path not allowed (or explicitly forbidden) by the wiring graph.

    Biological meaning: violates neuroanatomical rules such as "brain does not directly connect to limbs".
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
    """A hop in a reflex arc path is illegal according to wiring.

    Validated and raised during ``cat.freeze_nervous_system()``.
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
    """No registered reflex trigger matched during ``cat.perceive(input)``."""

    def __init__(self, input_repr: str) -> None:
        self.input_repr = input_repr
        super().__init__(f"No reflex matched input: {input_repr[:80]}")


class OrganProtocolMismatchError(MeowCatError):
    """Organ does not satisfy protocol P during ``cat.mount(category, name, organ, protocol=P)``."""

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
