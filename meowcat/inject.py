"""meowcat injection needle — bypass wiring validation, directly operate any organ.

The third communication mode alongside :meth:`signal` and :meth:`probe`.
For debug/admin/test scenarios only; can be disabled in production via environment variable.

Safety design:
- Not attached to ``CatBase``, must be explicitly ``import``ed + constructed
- Emits ``warning`` log at construction
- Production can disable via ``MEOWCAT_DISABLE_NEEDLE=1``

Usage::

    from meowcat.inject import Needle

    needle = Needle(cat)
    await needle.poke(("brain", "hippocampus"), "add_entity", name="Python")
    await needle.poke_memory({"name": "fix", "content": "corrected"})
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import logging
import os
from typing import Any

from meowcat.wiring import Organ

logger = logging.getLogger("meowcat.needle")


class NeedleDisabledError(RuntimeError):
    """Raised when constructing Needle with ``MEOWCAT_DISABLE_NEEDLE=1``."""


class Needle:
    """Injector — bypass wiring validation, directly operate any organ.

    Safety design:
    - Not attached to CatBase, must explicitly import + construct
    - Emits warning log at construction
    - Production can disable via ``MEOWCAT_DISABLE_NEEDLE=1``
    """

    def __init__(self, cat) -> None:
        """Construct the injector.

        Args:
            cat: ``CatBase`` or instance with ``_host`` attribute

        Raises:
            NeedleDisabledError: when ``MEOWCAT_DISABLE_NEEDLE=1``
        """
        if os.environ.get("MEOWCAT_DISABLE_NEEDLE") == "1":
            raise NeedleDisabledError(
                "Needle is disabled by MEOWCAT_DISABLE_NEEDLE=1"
            )
        self._cat = cat
        logger.warning(
            "Needle created — this bypasses wiring checks. "
            "For debugging/admin use only."
        )

    async def poke(self, to_organ: Organ, method: str, **kwargs: Any) -> Any:
        """Directly call a method on the target organ, without wiring validation.

        Args:
            to_organ: Target organ coordinate, e.g. ``("brain", "hippocampus")``
            method: Method name
            **kwargs: Method parameters

        Returns:
            Method return value

        Raises:
            ValueError: Organ not mounted
            AttributeError: Method does not exist
        """
        import inspect

        target = self._cat._host.organ(*to_organ)
        if target is None:
            raise ValueError(f"Organ {to_organ} not mounted")
        fn = getattr(target, method, None)
        if fn is None:
            raise AttributeError(
                f"Organ {to_organ} has no method '{method}'"
            )
        result = fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def poke_memory(self, **entity_data: Any) -> Any:
        """Shortcut: directly write to hippocampus.

        Args:
            **entity_data: Entity data passed to ``add_entity()``
        """
        return await self.poke(
            ("brain", "hippocampus"), "add_entity", **entity_data,
        )

    async def poke_focus(self, topic: str) -> Any:
        """Shortcut: directly update frontal focus.

        Args:
            topic: Focus topic
        """
        return await self.poke(
            ("brain", "frontal"), "update_focus", result=topic,
        )

    async def poke_worldview(self, layer: str, key: str, value: Any) -> Any:
        """Shortcut: directly write to cortex worldview.

        Args:
            layer: Worldview layer name (axioms/others/values/self)
            key: Key
            value: Value
        """
        return await self.poke(
            ("brain", "cortex"), "ingest",
            source="needle", layer=layer, key=key, value=value,
        )


__all__ = ["Needle", "NeedleDisabledError"]
