# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Communication & Storage Mixin (v1.3.9: extracted from colony/__init__.py)."""

from __future__ import annotations

import asyncio
from typing import Any


class _CommunicationMixin:
    """Inter-cat communication, broadcast, and cat-specific shared storage methods.

    Provides inter-cat signal routing (signal_between), group chat (broadcast,
    broadcast_request), external entry (receive_external), health checks, and
    cat-specific shared storage (storage_get/set/delete/list_keys/watch).

    Requires the host class to provide:
        - ``self._storage`` (SharedStore | None)
        - ``self._cats`` (dict of cat_uid -> CatBase)
        - ``self.colony_id`` (str)
        - ``self._assert_cross_allowed()`` (cross-wiring validator)
        - ``self.storage_set()`` (cat-specific storage writer)
    """

    # -- Shared storage (namespace isolation) -------------------------

    def _ensure_storage(self):  # type: ignore[no-untyped-def]
        """Lazy-init storage if not provided."""
        if self._storage is None:  # type: ignore[has-type]  # type: ignore[attr-defined]
            from meowcat.defaults.stores import InMemorySharedStore

            self._storage = InMemorySharedStore()  # type: ignore[attr-defined]
        return self._storage  # type: ignore[attr-defined]

    def _cat_key(self, cat_uid: str, key: str) -> str:
        """Construct a cat-isolated storage key: ``cat_uid/key``.

        cat_uid prefix provides automatic isolation.
        """
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
        """Watch shared storage key changes matching pattern.

        Delegates to the underlying storage.watch(). Returns AsyncIterator.
        """
        ns_pattern = f"{cat_uid}/{pattern}"
        # type: ignore[attr-defined]
        async for item in self._ensure_storage().watch(ns_pattern):
            yield item

    # -- Result delivery ---------------------------------------------

    async def deliver_result(
        self,
        parent_id: str,
        from_kitten: str,
        result: Any,
    ) -> None:
        """Kitten delivers result back to parent cat.

        Writes to shared storage ``{parent_id}/kitten:{from_kitten}/result``.

        Args:
            parent_id: Parent cat ID.
            from_kitten: Kitten ID.
            result: Arbitrary result to deliver.
        """
        key = f"kitten:{from_kitten}/result"
        await self.storage_set(parent_id, key, result)

    # -- Broadcast ----------------------------------------------------

    async def broadcast(self, event: str, **data: Any) -> None:
        """Broadcast an event to all cats in the colony (fire-and-forget).

        Args:
            event: Event name.
            **data: Event data.
        """
        for cat in self._cats.values():  # type: ignore[attr-defined]
            await cat.emit(event, data)

    async def broadcast_request(
        self,
        method: str,
        *,
        to_category: str = "brain",
        to_name: str = "amygdala",
        ignore_errors: bool = True,
        **kw: Any,
    ) -> dict[str, Any]:
        """Broadcast a request to all cats and collect responses (group chat).

        Calls ``method`` on ``to_category:to_name`` organ of every cat,
        collecting results keyed by cat_uid. This is the 1→many request-response
        pattern — group chat where every cat responds.

        Unlike :meth:`broadcast` (fire-and-forget event), this method waits
        for all cats to respond and returns a result dict. Unlike
        :meth:`signal_between` (1→1 private chat), this sends to everyone.

        Bypasses cross-wiring (colony-level operation, not cat-to-cat).

        Usage::

            # Safety assessment — every cat weighs in
            results = await colony.broadcast_request(
                "assess_safety", sql="DROP TABLE users"
            )
            # → {"planner": {"safe": True}, "executor": {"safe": False}}

            # Custom organ target
            results = await colony.broadcast_request(
                "diagnose", to_category="brain", to_name="hippocampus"
            )

        Args:
            method: Method name to call on the target organ.
            to_category: Target organ category (default: ``"brain"``).
            to_name: Target organ name (default: ``"amygdala"``).
            ignore_errors: If True, cat errors become ``{"error": str(exc)}``
                in results. If False, re-raises the first exception.
            **kw: Keyword arguments forwarded to the target method.

        Returns:
            ``{cat_uid: result, ...}`` — each cat's response keyed by cat_uid.
            Cat errors become ``{"error": "..."}`` when ``ignore_errors=True``.
        """
        results: dict[str, Any] = {}
        for cat_uid, cat in self._cats.items():  # type: ignore[attr-defined]
            try:
                organ = cat.organ(to_category, to_name)
                fn = getattr(organ, method)
                result = fn(**kw)
                import inspect as _inspect

                if _inspect.isawaitable(result):
                    result = await result
                results[cat_uid] = result
            except Exception as exc:
                if not ignore_errors:
                    raise
                results[cat_uid] = {"error": str(exc)}
        return results

    async def health_check_all(self) -> dict[str, dict]:
        """Run health check on all cats.

        Returns:
            ``{cat_uid: {...diagnose...}, ...}``
        """
        results: dict[str, dict] = {}
        for cat_uid, cat in self._cats.items():  # type: ignore[attr-defined]
            try:
                results[cat_uid] = await cat.health_check()
            except Exception as exc:
                results[cat_uid] = {"error": str(exc)}
        return results

    # -- Unified External Entry (v1.1.8) ------------------------------

    async def receive_external(self, address: str, **kwargs: Any) -> Any:
        """Receive external message addressed to a specific cat.

        This is the **unified external entry point** for a colony — any external
        system (CLI, HTTP, WebSocket, etc.) delivers messages through this method
        by specifying a cat address.

        Address format: ``colony_id/cat_uid``, e.g. ``"feishu/planner"``.

        Usage::

        result = await colony.receive_external("feishu_planner", message="查询表结构")

        Args:
            address: Cat address in ``colony_id_cat_uid`` format.
            **kwargs: Message payload — forwarded to the target cat as an event.

        Returns:
            ``{"status": "delivered", "cat_uid": ..., "cats_count": ...}``

        Raises:
            ValueError: Invalid address format or colony mismatch.
            KeyError: Target cat not found in colony.
        """
        parts = address.split("_", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid address '{address}': expected 'colony_id_cat_uid'")
        colony_id, cat_uid = parts
        if colony_id != self.colony_id:  # type: ignore[attr-defined]
            raise ValueError(
                # type: ignore[attr-defined]
                f"Address colony '{colony_id}' does not match this colony '{self.colony_id}'"
            )
        cat = self.get_cat(cat_uid)  # type: ignore[attr-defined]
        await cat.emit("external_message", {"address": address, **kwargs})
        return {
            "status": "delivered",
            "cat_uid": cat_uid,
            "cats_count": len(self._cats),  # type: ignore[attr-defined]
        }

    def list_cat_capabilities(self) -> dict[str, list[dict[str, Any]]]:
        """List capabilities of every cat in the colony.

        Each cat's capabilities are its mounted organ coordinates
        ``(category, name)``.

        Usage::

            caps = colony.list_cat_capabilities()
            # → {"planner": [{"category": "brain", "name": "cerebrum"}, ...]}

        Returns:
            ``{cat_uid: [{"category": ..., "name": ...}, ...], ...}``
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for cat_uid, cat in self._cats.items():  # type: ignore[attr-defined]
            organs = cat.list_all_organs()
            result[cat_uid] = [{"category": c, "name": n} for c, n in organs]
        return result

    def search_scope_guard(self, cat_uid: str, scope: str) -> None:
        """Validate search scope boundaries (v1.1.8).

        Enforces the search boundary contract defined in §2.2:

        - ``scope="self"``   → cat's own Hippocampus + public area (optional)
        - ``scope="colony"`` → SharedStorage ONLY, **never** other cats' private data

        Raises:
            ValueError: Invalid scope value.
            KeyError: Cat not found.
        """
        if scope not in ("self", "colony"):
            raise ValueError(
                f"Invalid search scope '{scope}': must be 'self' or 'colony'")
        # Ensure cat exists
        if cat_uid not in self._cats:  # type: ignore[attr-defined]
            raise KeyError(
                # type: ignore[attr-defined]
                f"Cat '{cat_uid}' not found in colony '{self.colony_id}'")

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

        Flow:
        1. Validate cross-cat wiring (if cross_wiring is set)
        2. Retrieve target organ from target cat
        3. Directly invoke method on target organ

        Args:
            from_id: Sender cat ID.
            to_id: Receiver cat ID.
            to_category: Target organ category (e.g. "brain").
            to_name: Target organ name (e.g. "hippocampus").
            method: Target method name.
            *args, **kw: Forwarded to target method.
            timeout: Optional timeout in seconds.  None = no timeout.

        Returns:
            Return value of target method.

        Raises:
            KeyError: Sender or receiver cat does not exist.
            IllegalNeuralPathError: Cross-cat edge is not allowed.
            OrganNotMountedError: Target organ does not exist.
            asyncio.TimeoutError: If timeout is set and exceeded.
        """
        # 1. Cross-cat wiring validation
        # type: ignore[attr-defined]
        self._assert_cross_allowed(from_id, to_id)

        # 2. Get target cat
        target_cat = self._cats[to_id]  # type: ignore[attr-defined]

        # 3. Retrieve target organ
        target_organ = target_cat.organ(to_category, to_name)

        # 4. Invoke method
        fn = getattr(target_organ, method)
        import inspect as _inspect

        result = fn(*args, **kw)
        if _inspect.isawaitable(result):
            if timeout is not None:
                result = await asyncio.wait_for(result, timeout=timeout)
            else:
                result = await result
        return result
