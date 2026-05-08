# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Namespace storage Mixin (v1.3.8: extracted from colony/__init__.py)."""

from __future__ import annotations

from typing import Any


class _NamespaceMixin:
    """Namespace storage methods extracted from Colony.

    Provides colony-level namespaced storage (owner/rules/knowledge/growth/cats)
    with prefix-isolated key management and watcher support.

    Requires the host class to provide:
        - ``self._registered_ns`` (set of registered namespace names)
        - ``self._ensure_storage()`` -> SharedStore
    """

    _NS_PREFIX = "__colony__"

    def _ns_key(self, namespace: str, key: str) -> str:
        """Construct a namespace-isolated storage key: ``__colony__/{ns}/{key}``."""
        return f"{self._NS_PREFIX}/{namespace}/{key}"

    def _ns_prefix(self, namespace: str) -> str:
        """Prefix for listing keys in a namespace."""
        return f"{self._NS_PREFIX}/{namespace}/"

    async def ns_get(self, namespace: str, key: str) -> Any:
        """Read from a colony-level namespace in shared storage.

        Args:
            namespace: e.g. ``"owner"``, ``"rules"``, ``"knowledge"``, ``"growth"``, ``"cats"``.
            key: Key within the namespace.
        """
        return await self._ensure_storage().get(self._ns_key(namespace, key))  # type: ignore[attr-defined]

    async def ns_set(self, namespace: str, key: str, value: Any) -> None:
        """Write to a colony-level namespace in shared storage.

        Args:
            namespace: e.g. ``"knowledge"``.
            key: Key within the namespace.
            value: Arbitrary value to store.
        """
        await self._ensure_storage().set(self._ns_key(namespace, key), value)  # type: ignore[attr-defined]

    async def ns_delete(self, namespace: str, key: str) -> None:
        """Delete a key from a colony-level namespace."""
        await self._ensure_storage().delete(self._ns_key(namespace, key))  # type: ignore[attr-defined]

    async def ns_list_keys(self, namespace: str) -> list[str]:
        """List all keys in a colony-level namespace (prefix stripped).

        Args:
            namespace: e.g. ``"knowledge"``.

        Returns:
            List of keys within the namespace, without prefix.
        """
        prefix = self._ns_prefix(namespace)
        all_keys = await self._ensure_storage().list_keys()  # type: ignore[attr-defined]
        return [k[len(prefix) :] for k in all_keys if k.startswith(prefix)]

    async def ns_watch(self, namespace: str, pattern: str) -> Any:
        """Watch namespace key changes matching pattern.

        Args:
            namespace: e.g. ``"growth"``.
            pattern: Key pattern for matching.

        Yields:
            ``(key, value)`` tuples.
        """
        ns_pattern = f"{self._ns_prefix(namespace)}{pattern}"
        async for item in self._ensure_storage().watch(ns_pattern):  # type: ignore[attr-defined]
            yield item

    @property
    def registered_namespaces(self) -> frozenset[str]:
        """Currently registered namespace names (frozen snapshot)."""
        return frozenset(self._registered_ns)  # type: ignore[attr-defined]

    def storage_plug(self, slot: str, name: str) -> None:
        """Register a custom namespace or other storage-level plugin.

        Usage::

            colony.storage_plug("namespace", "audit")  # 新增 audit/ 命名空间

        Args:
            slot: Plugin slot name (currently supports ``"namespace"``).
            name: Namespace name to register.
        """
        if slot == "namespace":
            self._registered_ns.add(name)  # type: ignore[attr-defined]
