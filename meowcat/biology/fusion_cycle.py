"""FusionCycle — pre-built fusion trigger strategies for PinealGland.

Provides ``on_full`` / ``on_timer`` / ``on_event`` static factories
that produce ``Callable[[ScribblePad], bool]`` conditions for
:meth:`PinealGland.trigger_if`.

Usage::

    from meowcat.biology.fusion_cycle import FusionCycle

    # Trigger when ScribblePad has 50+ entries
    gland.trigger_if(FusionCycle.on_full(50))

    # Trigger every 30 minutes (timer checked per invocation)
    gland.trigger_if(FusionCycle.on_timer(30))

    # Trigger on a named event
    gland.trigger_if(FusionCycle.on_event("conversation_end"))
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import time as _time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meowcat.biology.scribble_pad import ScribblePad


class FusionCycle:
    """Static factory for fusion trigger conditions.

    Each method returns a ``Callable[[ScribblePad], bool]`` suitable for
    passing to ``PinealGland.trigger_if()``.
    """

    @staticmethod
    def on_full(min_count: int) -> Callable[[ScribblePad], bool]:
        """Trigger when ScribblePad entry count reaches or exceeds *min_count*.

        Args:
            min_count: Minimum entries before triggering.

        Returns:
            A callable condition.
        """
        if min_count < 1:
            raise ValueError(f"min_count must be >= 1, got {min_count}")

        def _condition(pad: ScribblePad) -> bool:
            return pad.count() >= min_count

        # type: ignore[attr-defined]
        _condition.__name__ = f"on_full({min_count})"
        return _condition

    @staticmethod
    def on_timer(minutes: int) -> Callable[[ScribblePad], bool]:
        """Trigger based on elapsed time since last trigger.

        Uses a mutable closure to track the last trigger timestamp.
        Triggers when at least *minutes* have passed and the pad has entries.

        Args:
            minutes: Minimum minutes between triggers.

        Returns:
            A callable condition with internal timer state.
        """
        if minutes < 1:
            raise ValueError(f"minutes must be >= 1, got {minutes}")

        last_trigger = [0.0]  # mutable cell

        def _condition(pad: ScribblePad) -> bool:
            now = _time.time()
            elapsed = (now - last_trigger[0]) / 60.0
            if elapsed >= minutes and pad.count() > 0:
                last_trigger[0] = now
                return True
            return False

        # type: ignore[attr-defined]
        _condition.__name__ = f"on_timer({minutes}m)"
        return _condition

    @staticmethod
    def on_event(event: str) -> Callable[[ScribblePad], bool]:
        """Trigger unconditionally — the event name is metadata for the caller.

        The returned callable always returns True, signalling that the
        current event justifies a fusion attempt. Useful when the app layer
        knows a meaningful boundary has been reached (e.g. conversation end).

        Args:
            event: Event name for documentation / logging.

        Returns:
            A callable that always returns True.
        """

        def _condition(pad: ScribblePad) -> bool:
            return True

        # type: ignore[attr-defined]
        _condition.__name__ = f"on_event({event})"
        return _condition


__all__ = ["FusionCycle"]
