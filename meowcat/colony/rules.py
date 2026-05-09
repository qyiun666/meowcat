# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ColonyRules — safety policy, approval, rate limiting for a Colony.

Simple configuration dataclass with Pluggable for extensibility.
"""

from __future__ import annotations

from typing import Any

from meowcat.pluggable import Pluggable


class ColonyRules(Pluggable):
    """Colony rules — safety policy, approval, rate limiting.

    Extends :class:`Pluggable` for custom hook extensions.

    Usage::

        ColonyRules(safety_policy="strict", approval_required=True, rate_limit_per_min=20)
        ColonyRules(extra={"custom_policy": "block_external_domains"})
    """

    def __init__(
        self,
        safety_policy: str = "normal",
        approval_required: bool = False,
        rate_limit_per_min: int = 60,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.safety_policy = safety_policy
        self.approval_required = approval_required
        self.rate_limit_per_min = rate_limit_per_min
        self.extra: dict[str, Any] = extra or {}
