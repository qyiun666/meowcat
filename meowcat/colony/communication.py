# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Communication & Storage Mixin (v2.0 simplified)."""

from __future__ import annotations

import asyncio
from typing import Any


class _CommunicationMixin:
    """Inter-cat communication, broadcast, and shared storage methods.

    Provides inter-cat signal routing (signal_between), broadcast,
    and cat-specific shared storage (storage_get/set/delete).

    Requires the host class to provide:
        - ``self._storage`` (SharedStore | None)
        - ``self._cats`` (dict of cat_uid -> CatBase)
        - ``self.colony_id`` (str)
        - ``self._assert_cross_allowed()`` (cross-wiring validator)
    """

    # -- Shared storage (namespace isolation) -------------------------

    def _ensure_storage(self):  # type: ignore[no-untyped-def]
        # type: ignore[has-type]  # type: ignore[attr-defined]
        if self._storage is None:
            from meowcat.defaults.stores import InMemorySharedStore
            self._storage = InMemorySharedStore()  # type: ignore[attr-defined]
        return self._storage  # type: ignore[attr-defined]

    def _cat_key(self, cat_uid: str, key: str) -> str:
        """Construct a cat-isolated storage key: ``cat_uid/key``."""
        return f"{cat_uid}/{key}"

    async def storage_get(self, cat_uid: str, key: str) -> Any:
        """Cat reads from shared storage (auto cat_uid prefix isolation)."""
        return await self._ensure_storage().get(self._cat_key(cat_uid, key))

    async def storage_set(self, cat_uid: str, key: str, value: Any) -> None:
        """Cat writes to shared storage (auto cat_uid prefix isolation)."""
        await self._ensure_storage().set(self._cat_key(cat_uid, key), value)

    async def storage_delete(self, cat_uid: str, key: str) -> None:
        """Cat deletes a shared storage entry."""
        await self._ensure_storage().delete(self._cat_key(cat_uid, key))

    async def storage_list_keys(self, cat_uid: str) -> list[str]:
        """List all shared storage keys for a cat (prefix stripped)."""
        prefix = f"{cat_uid}/"
        all_keys = await self._ensure_storage().list_keys()
        return [k[len(prefix):] for k in all_keys if k.startswith(prefix)]

    async def storage_watch(
        self,
        cat_uid: str,
        pattern: str,
    ) -> Any:
        """Watch shared storage key changes matching pattern."""
        ns_pattern = f"{cat_uid}/{pattern}"
        # type: ignore[attr-defined]
        async for item in self._ensure_storage().watch(ns_pattern):
            yield item

    # -- Broadcast ----------------------------------------------------

    async def broadcast(self, event: str, **data: Any) -> None:
        """Broadcast an event to all cats in the colony (fire-and-forget).

        Args:
            event: Event name.
            **data: Event data.
        """
        for cat in self._cats.values():  # type: ignore[attr-defined]
            await cat.emit(event, data)

    # -- Inter-cat communication --------------------------------------

    async def signal_between(
        self,
        from_id: str,
        to_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        timeout: float | None = None,
        **kw: Any,
    ) -> Any:
        """Inter-cat signal communication.

        One cat sends a signal to another cat's organ via the colony.

        Args:
            from_id: Sender cat ID.
            to_id: Receiver cat ID.
            to_category: Target organ category (e.g. "brain").
            to_name: Target organ name (e.g. "hippocampus").
            method: Target method name.
            *args, **kw: Forwarded to target method.
            timeout: Optional timeout in seconds. None = no timeout.

        Returns:
            Return value of target method.

        Raises:
            KeyError: Sender or receiver cat does not exist.
            PermissionError: Cross-cat edge is not allowed.
            OrganNotMountedError: Target organ does not exist.
            asyncio.TimeoutError: If timeout is set and exceeded.
        """
        # type: ignore[attr-defined]
        self._assert_cross_allowed(from_id, to_id)

        target_cat = self._cats[to_id]  # type: ignore[attr-defined]
        target_organ = target_cat.organ(to_category, to_name)
        fn = getattr(target_organ, method)
        import inspect as _inspect

        result = fn(*args, **kw)
        if _inspect.isawaitable(result):
            if timeout is not None:
                result = await asyncio.wait_for(result, timeout=timeout)
            else:
                result = await result
        return result
