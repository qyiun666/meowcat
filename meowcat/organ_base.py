# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat organ convenience base — OrganMixin (added in v0.5.11).

**Positioning**: optional mixin providing zero-stack-frame-overhead signal/probe shortcuts for organs.

**Background**: since v0.5.0~v0.5.10, cross-organ calls required
``await self.cat.signal(FROM_ORGAN, TO_ORGAN, method, ...)``, which is verbose
and requires explicitly passing from_organ each time, prone to typos (e.g. ``BRAINSTEM`` written as ``CEREBRUM``).

v0.5.11 uses ``OrganMixin`` to let organs bind ``self._self_coord`` and ``cat``
weak reference once at construction, then write ``await self._signal_to(TO, method, ...)`` —
the framework auto-fills from_organ, eliminating manual typo risk at the call site.

**Comparison with cat.ask()**: the original plan proposed ``cat.ask(to, method)``
using ``inspect`` stack frames to infer from_organ, but inspect overhead is typically
2-5μs, conflicting with the signal hot-path ``<5μs`` target. ``OrganMixin``
uses constructor-time ``_self_coord`` binding to completely avoid stack frame reflection,
keeping the signal hot path at native speed.

**Backward compatibility**: fully optional. Existing organs not inheriting ``OrganMixin``
can continue explicitly writing ``self.cat.signal(...)`` with no issues.

**Typical usage**::

    from meowcat import OrganMixin
    from meowcat.biology import BRAINSTEM, CORTEX
    from meowcat.protocols import CatProtocol

    class BrainStem(OrganMixin):
        name = "brainstem"

        def __init__(self, cat: CatProtocol) -> None:
            OrganMixin.__init__(self, cat, BRAINSTEM)
            # business init...

        async def some_flow(self) -> None:
            # old: await self.cat.signal(BRAINSTEM, CORTEX, "synthesize", max_tokens=200)
            # new:
            wv = await self._signal_to(CORTEX, "synthesize", max_tokens=200)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.protocols import CatProtocol
    from meowcat.wiring import Organ


class OrganMixin:
    """Organ convenience base: binds ``(cat, self_coord)`` at construction, provides
    ``_signal_to`` / ``_probe`` shortcuts with zero stack-frame overhead.

    **This class holds no business state**, only ``_cat_ref`` and ``_self_coord`` — two pointers.
    Concrete organ business logic is the subclass's responsibility.

    ``__slots__`` declaration avoids allocating extra ``__dict__`` entries
    for these two fields per organ instance; if the subclass already uses
    ``__dict__`` (no ``__slots__``), mixin slots still work but produce no memory savings.
    """

    __slots__ = ("_cat_ref", "_self_coord")

    def __init__(self, cat: CatProtocol, self_coord: Organ) -> None:
        """Bind organ coordinate and cat weak reference.

        Args:
            cat: the cat instance this organ belongs to (weak reference semantics: organs should not mutate cat state)
            self_coord: this organ's coordinate in wiring ``(category, name)``
        """
        self._cat_ref = cat
        self._self_coord = self_coord

    async def _signal_to(
        self,
        to: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Send signal to target organ (auto-fills from_organ = ``self._self_coord``).

        Equivalent to ``await self._cat_ref.signal(self._self_coord, to, method, ...)``
        but shorter and less error-prone for from_organ.

        Raises:
            IllegalNeuralPathError: wiring forbids this edge, method blocklisted, or target
                Protocol does not declare this method (v0.5.11 contract check).
            OrganNotMountedError: target organ not mounted.
        """
        return await self._cat_ref.signal(
            self._self_coord,
            to,
            method,
            *args,
            **kwargs,
        )

    async def _probe(self, to: Organ) -> dict[str, Any]:
        """Send read-only diagnostic probe to target organ (forwards ``cat.probe``).

        probe is not inter-organ communication (bypasses wiring edge check); any wired organ
        can be probed.

        Raises:
            IllegalNeuralPathError: target organ not in wiring.
            TypeError: target does not implement Diagnosable or diagnose() returns non-dict.
        """
        return await self._cat_ref.probe(to)


__all__ = ["OrganMixin"]
