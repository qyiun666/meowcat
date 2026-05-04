"""GlobalColonyRegistry — process-wide multi-Colony registry.

Cross-colony cat lookup by global address (``colony_id/cat_id``).
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.assembly import CatBase
    from meowcat.colony import Colony


class GlobalColonyRegistry(Pluggable):
    """Global registry for multiple Colonies — cross-colony cat lookup.

    A process-wide registry that holds references to all Colony instances,
    enabling cat lookup by global address (``colony_id/cat_id``) across
    multiple colonies.  Useful for multi-tenant or multi-team deployments
    where external systems need to route messages to any cat in any colony.

    Extends :class:`Pluggable` with ``on_register`` / ``on_unregister`` hooks.

    Usage::

        registry = GlobalColonyRegistry()

        feishu = Colony("feishu", storage=...)
        wechat = Colony("wechat", storage=...)

        registry.register(feishu)
        registry.register(wechat)

        # Look up a cat by global address
        cat = registry.find_cat("feishu/planner")
        # or with UID: registry.find_cat("feishu/planner-d4e5f60001")

        # List everything
        for cid in registry.list_colonies():
            for c in registry.list_cats(cid):
                print(c)

        # Plugin hooks
        registry.plug("on_register", my_health_check)
        registry.plug("on_unregister", my_cleanup)
    """

    HOOKS = {
        "on_register": {"in": "colony: Colony", "out": "None"},
        "on_unregister": {"in": "colony_id: str", "out": "None"},
    }

    def __init__(self) -> None:
        super().__init__()
        self._colonies: dict[str, Colony] = {}

    # -- Registration -------------------------------------------------

    def register(self, colony: Colony) -> None:
        """Register a Colony into the global registry.

        If a colony with the same ``colony_id`` already exists, it is
        overwritten (last-write-wins).

        Fires ``on_register`` hook(s) after registration.

        Args:
            colony: Colony instance to register.
        """
        self._colonies[colony.colony_id] = colony
        # Fire on_register hooks (fire-and-forget)
        for _hook, _r in self._run_plugs_sync("on_register", colony):
            pass

    def unregister(self, colony_id: str) -> bool:
        """Remove a Colony from the global registry.

        Fires ``on_unregister`` hook(s) before removal.

        Args:
            colony_id: Colony identifier.

        Returns:
            True if the colony was registered and removed, False if not found.
        """
        if colony_id not in self._colonies:
            return False
        # Fire on_unregister hooks (fire-and-forget)
        for _hook, _r in self._run_plugs_sync("on_unregister", colony_id):
            pass
        del self._colonies[colony_id]
        return True

    # -- Lookup -------------------------------------------------------

    def get_colony(self, colony_id: str) -> Colony:
        """Get a colony by ID.

        Args:
            colony_id: Colony identifier.

        Returns:
            Colony instance.

        Raises:
            KeyError: Colony not found.
        """
        if colony_id not in self._colonies:
            raise KeyError(
                f"Colony '{colony_id}' not found in global registry. "
                f"Registered: {list(self._colonies.keys())}"
            )
        return self._colonies[colony_id]

    def find_cat(self, address: str) -> CatBase:
        """Find a cat by global address.

        Address format: ``colony_id/cat_id`` or ``colony_id/cat_id-cat_uid``.
        The cat_id part is matched against registered cat IDs (exact or
        prefix match for UID-suffixed IDs).

        Usage::

            cat = registry.find_cat("feishu/planner")
            cat = registry.find_cat("feishu/planner-d4e5f60001")

        Args:
            address: Global cat address.

        Returns:
            CatBase instance.

        Raises:
            ValueError: Invalid address format.
            KeyError: Colony or cat not found.
        """
        parts = address.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid address '{address}': expected 'colony_id/cat_id'"
            )
        colony_id, cat_ref = parts
        colony = self.get_colony(colony_id)

        # Try exact match first
        try:
            return colony.get_cat(cat_ref)
        except KeyError:
            pass

        # Try prefix match (for UID-suffixed IDs: cat_id-cat_uid)
        for cat_id in colony.list_cats():
            cat = colony.get_cat(cat_id)
            cat_uid = getattr(cat, "_cat_uid", "")
            if cat_uid == cat_ref or cat_id == cat_ref:
                return cat
            # Match full address: cat_id-cat_uid
            if f"{cat_id}-{cat_uid}" == cat_ref:
                return cat

        raise KeyError(
            f"Cat '{cat_ref}' not found in colony '{colony_id}'. "
            f"Available: {colony.list_cats()}"
        )

    # -- Listing ------------------------------------------------------

    def list_colonies(self) -> list[str]:
        """List all registered colony IDs.

        Returns:
            List of colony_id strings.
        """
        return list(self._colonies.keys())

    def list_cats(self, colony_id: str) -> list[str]:
        """List all cat IDs in a registered colony.

        Args:
            colony_id: Colony identifier.

        Returns:
            List of cat_id strings.

        Raises:
            KeyError: Colony not found.
        """
        return self.get_colony(colony_id).list_cats()

    def list_all_cats(self) -> dict[str, list[str]]:
        """List all cats across all registered colonies.

        Returns:
            ``{colony_id: [cat_id, ...], ...}``
        """
        return {cid: colony.list_cats() for cid, colony in self._colonies.items()}

    # -- Count --------------------------------------------------------

    @property
    def colony_count(self) -> int:
        """Number of registered colonies."""
        return len(self._colonies)

    def total_cat_count(self) -> int:
        """Total number of cats across all registered colonies."""
        return sum(len(colony._cats) for colony in self._colonies.values())
