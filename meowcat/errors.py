# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat framework-level exceptions.

Only defines framework-internal error types, no business exceptions.
"""

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
        super().__init__(f"Stage '{stage_name}' timed out after {timeout}s")


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
        super().__init__(f"Reflex '{reflex_name}' hop illegal: {frm[0]}/{frm[1]} → {to[0]}/{to[1]}")


class NoReflexMatchedError(MeowCatError):
    """No registered reflex trigger matched during ``cat.perceive(input)``."""

    def __init__(self, input_repr: str) -> None:
        self.input_repr = input_repr
        super().__init__(f"No reflex matched input: {input_repr[:80]}")


class StandaloneCatError(MeowCatError):
    """Raised when a cat is created without a container (Colony is mandatory since v1.1.3)."""

    def __init__(self, cat_uid: str) -> None:
        self.cat_uid = cat_uid
        super().__init__(
            f"Cat '{cat_uid}' must belong to a Colony — pass container=colony to CatBase()"
        )


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


class OrganDelegateError(MeowCatError):
    """Raised when an AgentOrgan/SkillOrgan fails to delegate to its external agent/skill.

    v1.2.14: Added for AgentOrgan/SkillOrgan adapter system.
    """

    def __init__(self, adapter: str, method: str, detail: str = "") -> None:
        self.adapter = adapter
        self.method = method
        self.detail = detail
        msg = f"{adapter}.{method}() delegate failed"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


# -- v1.2.19: signal circuit breaker ----------------------------------------


class CircuitOpenError(MeowCatError):
    """Raised when a signal() call is blocked by an open circuit breaker.

    The circuit opens when consecutive failures on a (to_organ, method) pair
    reach the configured threshold. It stays open for cb_timeout seconds,
    then transitions to half-open to allow one probe call.
    """

    def __init__(
        self,
        to_organ: tuple[str, str],
        method: str,
        failures: int,
        retry_after: float,
    ) -> None:
        self.to_organ = to_organ
        self.method = method
        self.failures = failures
        self.retry_after = retry_after
        super().__init__(
            f"Circuit open for {to_organ[0]}/{to_organ[1]}.{method}() — "
            f"{failures} failures, retry in {retry_after:.1f}s"
        )


__all__ = [
    "MeowCatError",
    "OrganNotMountedError",
    "LoopFailedError",
    "StageTimeoutError",
    "IllegalNeuralPathError",
    "ReflexPathInvalidError",
    "NoReflexMatchedError",
    "StandaloneCatError",
    "OrganProtocolMismatchError",
    "OrganDelegateError",
    "CircuitOpenError",
]
