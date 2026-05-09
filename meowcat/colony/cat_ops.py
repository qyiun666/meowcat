# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Cat management Mixin (v1.3.9: extracted from colony/__init__.py)."""

from __future__ import annotations

from typing import Any

from meowcat.assembly import CatBase


class _CatOpsMixin:
    """Cat CRUD methods extracted from Colony.

    Provides cat creation (create_cat, spawn_cat), registration
    (register, adopt), removal (unregister, release), and lookup
    (get_cat, list_cats).

    Requires the host class to provide:
        - ``self.is_full`` (bool property)
        - ``self._next_cat_uid()`` -> str
        - ``self._cats`` (dict of cat_uid -> CatBase)
        - ``self.colony_id`` (str)
        - ``self._storage`` (SharedStore | None)
        - ``self.memory`` (SharedMemoryPool property)
    """

    def _inject_colony_memory(self, cat: CatBase) -> None:
        """v1.2.36: Inject colony shared memory pool after organs are mounted.

        Called by the on_organs_mounted hook — at this point
        has_organ("brain", "hippocampus") is guaranteed to work.
        """
        if cat.has_organ("brain", "hippocampus"):
            hippo = cat.organ("brain", "hippocampus")
            if hasattr(hippo, "set_colony_memory"):
                # type: ignore[attr-defined]
                hippo.set_colony_memory(self.memory)

    # -- Create -------------------------------------------------------

    def create_cat(
        self,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a cat in the colony and auto-register it.

        The ``cat_uid`` is auto-generated (2-digit increment).

        Args:
            name: Optional display name (defaults to cat_uid).
            parent_id: Parent cat identifier (string, no object reference).
            allowed_organs: Organ access allowlist, None = allow all.
            memory_snapshot: Context slice assigned by parent cat.
            **cat_kwargs: Additional arguments passed to CatBase.

        Returns:
            Registered CatBase instance.
        """
        if self.is_full:  # type: ignore[attr-defined]
            raise RuntimeError(
                # type: ignore[attr-defined]
                f"Colony '{self.colony_id}' is full ({len(self._cats)}/{self._max_cats} cats)"
            )

        cat_uid = self._next_cat_uid()  # type: ignore[attr-defined]
        cat = CatBase(
            cat_uid,
            container=self,  # type: ignore[arg-type]
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )
        if name is not None:
            cat._name = name  # type: ignore[attr-defined]
        # type: ignore[attr-defined]
        # type: ignore[attr-defined]
        cat._address = f"{self.colony_id}_{cat_uid}"

        # Inject shared storage reference
        if self._storage is not None:  # type: ignore[attr-defined]
            cat._colony_storage = self._storage  # type: ignore[attr-defined]

        # Inject memory_snapshot (context slice)
        if memory_snapshot:
            # type: ignore[attr-defined]
            cat._memory_snapshot = memory_snapshot

        # v1.2.36: Register hook to inject colony memory after organs are mounted.
        # Replaces the dead code that called set_colony_memory before organs existed.
        cat.on_organs_mounted(lambda c: self._inject_colony_memory(c))

        self.register(cat)
        return cat

    # -- v1.1.21 Delegation: spawn cat with memory snapshot ----------

    def spawn_cat(
        self,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        memory_snapshot: dict | None = None,
        allowed_organs: frozenset[str] | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a kitten with inherited memory context.

        Convenience wrapper around :meth:`create_cat` that explicitly
        names the delegation intent.

        Usage::

            slice = parent.hippocampus.snapshot("users表", "auth模块")
            kitten = colony.spawn_cat(
                parent_id=parent.cat_uid,
                memory_snapshot=slice,
            )

        Args:
            name: Optional display name (defaults to cat_uid).
            parent_id: Parent cat identifier.
            memory_snapshot: Context slice from parent's hippocampus.
            allowed_organs: Organ access allowlist.
            **cat_kwargs: Forwarded to CatBase.
        """
        return self.create_cat(
            name=name,
            parent_id=parent_id,
            memory_snapshot=memory_snapshot,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )

    # -- Register / Remove --------------------------------------------

    def register(self, cat: CatBase) -> None:
        """Register a cat into the colony (overwrites if already exists).

        Args:
            cat: CatBase instance.
        """
        if self._storage is not None:  # type: ignore[attr-defined]
            cat._colony_storage = self._storage  # type: ignore[attr-defined]
        self._cats[cat.cat_uid] = cat  # type: ignore[attr-defined]

    def unregister(self, cat_uid: str) -> None:
        """Remove a cat from the colony.

        Args:
            cat_uid: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        del self._cats[cat_uid]  # type: ignore[attr-defined]

    def get_cat(self, cat_uid: str) -> CatBase:
        """Get a cat by uid.

        Args:
            cat_uid: Unique identifier for the cat.

        Returns:
            CatBase instance.

        Raises:
            KeyError: Cat does not exist.
        """
        return self._cats[cat_uid]  # type: ignore[attr-defined]

    def list_cats(self) -> list[str]:
        """List all cat uids in the colony.

        Returns:
            List of cat_uid strings.
        """
        return list(self._cats.keys())  # type: ignore[attr-defined]

    # -- Alias methods (v1.0.9) ---------------------------------------

    def adopt(self, cat: CatBase) -> None:
        """Adopt a cat (semantic alias for register).

        Args:
            cat: CatBase instance.
        """
        self.register(cat)

    def release(self, cat_uid: str) -> None:
        """Release a cat (semantic alias for unregister).

        Args:
            cat_uid: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        self.unregister(cat_uid)
