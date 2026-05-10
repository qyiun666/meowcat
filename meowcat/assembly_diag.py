# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat CatBase diagnostic mixin — health check, wiring diagram, CLI facades.

Extracted from assembly.py (v1.2.37) to keep CatBase under 500 lines.
Provides ``DiagnosticMixin`` with diagnostic shortcuts and CLI facade methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS
from meowcat.wiring import Organ, Wiring

if TYPE_CHECKING:
    from meowcat.chain import ChainRegistry
    from meowcat.host import OrganHost
    from meowcat.loops import LoopSequenceRegistry


class DiagnosticHost(Protocol):
    """Protocol declaring the CatBase attributes that DiagnosticMixin depends on.

    .. note:: The ``signal()`` method is provided by :class:`SignalSystemMixin`
       in the MRO and is NOT declared here to avoid shadowing.
    """

    _host: OrganHost
    wiring: Wiring
    cat_uid: str
    chain_registry: ChainRegistry
    loopseq_registry: LoopSequenceRegistry


class DiagnosticMixin(DiagnosticHost):
    """Mixin providing diagnostic shortcuts and CLI facade methods for CatBase.

    All methods access ``self._*`` private attributes set by ``CatBase.__init__``.
    This mixin has no ``__init__`` — CatBase is responsible for initialising
    the attributes these methods depend on.
    """

    # -- Diagnostic shortcuts --------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Full-body checkup — returns diagnostic snapshots of all organs.

        Shortcut, equivalent to ``Stethoscope.probe_all(self)``.

        Returns:
            ``{"brain:hippocampus": {...}, "sense:ears": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope

        return await Stethoscope.probe_all(self)

    async def brain_check(self) -> dict[str, Any]:
        """Check brain-area organs only.

        Shortcut, equivalent to ``Stethoscope.probe_category(self, "brain")``.

        Returns:
            ``{"hippocampus": {...}, "cerebrum": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope

        return await Stethoscope.probe_category(self, "brain")

    def wiring_diagram(self, format: str = "mermaid") -> str:
        """Generate a visualization string of the wiring diagram.

        Raises :class:`AttributeError` when wiring is disabled.

        Args:
            format: ``"mermaid"`` or ``"dot"``

        Returns:
            Diagram description string in mermaid or dot format

        Examples:

            >>> print(cat.wiring_diagram())
            >>> print(cat.wiring_diagram(format="dot"))
        """
        from meowcat.diagnose import render_wiring

        # Collect all mounted organs as input for orphan node detection
        mounted: frozenset[Organ] = frozenset(self._host.list_all_organs())
        return render_wiring(self.wiring, format=format, organs=mounted)

    # -- CLI facade methods (v1.0.9) ------------------------------------------

    async def search_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search memory. Equivalent to ``/search <query>``.

        Executes the ``memory_search`` chain (locate path), retrieving
        relevant memories from the hippocampus.

        Args:
            query: Search keywords
            limit: Max results to return

        Returns:
            Memory retrieval result dict
        """
        return await self.chain_registry.run(
            self, "memory_search", msg=query, session_id=self.cat_uid)

    async def memory_stats(self) -> dict[str, Any]:
        """Memory stats. Equivalent to ``/stats``.

        Calls the hippocampus ``stats`` method via signal to get memory stats.

        Returns:
            Memory stats dict
        """
        result = await self.signal(BRAINSTEM, HIPPOCAMPUS, "stats")
        if isinstance(result, dict):
            return result
        return {"stats": result}

    async def run_maintenance(
        self,
        country_code: str | None = None,
    ) -> dict[str, Any]:
        """Run maintenance. Equivalent to ``/maintenance``.

        Executes the ``daily_maintenance`` loop sequence (self-maintenance
        then health check).

        Args:
            country_code: Optional country code for regional decay strategy

        Returns:
            Maintenance result dict
        """
        return await self.loopseq_registry.run(self, "daily_maintenance")


__all__ = ["DiagnosticMixin"]
