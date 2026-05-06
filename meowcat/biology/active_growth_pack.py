# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ActiveGrowthPack — one-line enable for all three active growth components.

插座式设计: framework provides factory, app-layer calls ``install(cat)``.
Components are plugged into organs via Pluggable hooks.

Usage::

    from meowcat.biology.active_growth_pack import ActiveGrowthPack

    ActiveGrowthPack.install(cat)
    # BlindSpotDetector → cat.whiskers ("detect_blind_spot")
    # ToolFailureLearner → cat.paws ("on_tool_failure")
    # HotPathObserver   → cat.reflexes ("observe_hot_paths")
"""

from __future__ import annotations

from typing import Any

from meowcat.biology.active_growth import (
    BlindSpotDetector,
    HotPathObserver,
    ToolFailureLearner,
)


class ActiveGrowthPack:
    """Factory that plugs all three active growth components into a cat.

    Usage::

        ActiveGrowthPack.install(cat)
        # BlindSpotDetector → cat.whiskers ("detect_blind_spot")
        # ToolFailureLearner → cat.paws ("on_tool_failure")
        # HotPathObserver   → cat.reflexes ("observe_hot_paths")
    """
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    @staticmethod
    def install(
        cat: Any,
        *,
        bsd: BlindSpotDetector | None = None,
        tfl: ToolFailureLearner | None = None,
        hpo: HotPathObserver | None = None,
    ) -> dict[str, Any]:
        """Install all three active growth components with defaults.

        Args:
            cat: CatBase instance with whiskers/paws/reflexes organs.
            bsd: Custom BlindSpotDetector (defaults to new instance).
            tfl: Custom ToolFailureLearner (defaults to new instance).
            hpo: Custom HotPathObserver (defaults to new instance).

        Returns:
            Dict of ``{bsd, tfl, hpo}`` for further configuration.
        """
        bsd = bsd or BlindSpotDetector()
        tfl = tfl or ToolFailureLearner()
        hpo = hpo or HotPathObserver()

        # Plug into organs (organs expose plugin slots as Pluggable hooks)
        if hasattr(cat, "whiskers") and hasattr(cat.whiskers, "plug"):
            cat.whiskers.plug("detect_blind_spot", bsd.detect)
        if hasattr(cat, "paws") and hasattr(cat.paws, "plug"):
            cat.paws.plug("on_tool_failure", tfl.record)
        if hasattr(cat, "reflexes") and hasattr(cat.reflexes, "plug"):
            cat.reflexes.plug("observe_hot_paths", hpo.record)

        return {"bsd": bsd, "tfl": tfl, "hpo": hpo}

    @staticmethod
    def uninstall(cat: Any) -> None:
        """Remove all active growth components."""
        for organ_name in ("whiskers", "paws", "reflexes"):
            organ = getattr(cat, organ_name, None)
            if organ and hasattr(organ, "unplug"):
                organ.unplug("detect_blind_spot")
                organ.unplug("on_tool_failure")
                organ.unplug("observe_hot_paths")


__all__ = ["ActiveGrowthPack"]

