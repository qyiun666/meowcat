# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ColonyRules — safety policy, approval, rate limiting for a Colony.

Extends Pluggable for custom rule checking via ``on_check`` hook.
"""

from __future__ import annotations

from typing import Any

from meowcat.pluggable import Pluggable


class ColonyRules(Pluggable):
    """Colony rules — safety policy, approval, rate limiting.

    Extends :class:`Pluggable` for custom rule checking via ``on_check`` hook.

    Usage::

        ColonyRules(safety_policy="strict", approval_required=True, rate_limit_per_min=20)
        ColonyRules(extra={"custom_policy": "block_external_domains"})

# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

        # Custom rule checker
        colony.rules.plug("on_check", my_multi_tenant_checker)
    """

    HOOKS = {
        "on_check": {"in": "action: str, context: dict | None", "out": "dict"},
    }

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

    def check(self, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Check if an action passes rules. Runs ``on_check`` plugins (first-hit).

        Args:
            action: Action identifier string.
            context: Optional context dict for the check.

        Returns:
            ``{"allowed": True/False, "reason": ...}``
        """
        for _name, r in self._run_plugs_sync("on_check", action, context):
            if isinstance(r, dict) and not r.get("allowed", True):
                return r
        return {"allowed": True}

