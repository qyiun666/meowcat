# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat organ container — OrganHost pure container subsystem (extracted in v0.5.9).

Single responsibility: **store/retrieve organs**. Zero dependencies (no wiring/events/reflex),
can be independently instantiated for minimal "organ registry only" scenarios::

    host = OrganHost("toy")
    host.mount("brain", "cerebrum", my_brain, protocol=LLMBrainProtocol)
    brain = host.organ("brain", "cerebrum")

Nervous / CatBase both hold OrganHost instances via explicit dependency injection,
no longer scattering container state across multiple classes.

P-02 philosophy: minimal code. OrganHost does no events, no wiring, no protocol
lookup — those are the responsibility of Nervous / assembly.
"""


from __future__ import annotations

from typing import Any

from meowcat.errors import OrganNotMountedError, OrganProtocolMismatchError


class OrganHost:
    """Organ container — pure data structure for mount / organ / has / unmount."""

    def __init__(self, uid: str) -> None:
        self.uid = uid
        self._organs: dict[str, dict[str, Any]] = {}

    # -- Write interface ------------------------------------------------

    def mount(
        self,
        category: str,
        name: str,
        organ: Any,
        *,
        protocol: type | None = None,
    ) -> None:
        """Mount an organ.

        Args:
            category: Organ category (``brain`` / ``sense`` / ``voice`` / ``storage`` etc.)
            name: Organ name (``hippocampus`` / ``ears`` / ``tail`` etc.)
            organ: Concrete implementation instance
            protocol: Optional ``@runtime_checkable`` Protocol class;
                when not None, ``isinstance(organ, protocol)`` is checked;
                raises :class:`OrganProtocolMismatchError` on mismatch.
        """
        if protocol is not None and not isinstance(organ, protocol):
            raise OrganProtocolMismatchError(
                category, name, protocol, organ,
            )
        self._organs.setdefault(category, {})[name] = organ

    def unmount(self, category: str, name: str) -> bool:
        """Unmount an organ, return False if not found."""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            return False
        del bucket[name]
        return True

    # -- Read interface -------------------------------------------------

    def organ(self, category: str, name: str) -> Any:
        """Get a mounted organ. Raises :class:`OrganNotMountedError` if not mounted."""
        bucket = self._organs.get(category)
        if bucket is None or name not in bucket:
            raise OrganNotMountedError(category, name)
        return bucket[name]

    def organs(self, category: str) -> dict[str, Any]:
        """Return a snapshot of all organs in a category (read-only copy)."""
        return dict(self._organs.get(category, {}))

    def has_organ(self, category: str, name: str) -> bool:
        """Check whether an organ is mounted."""
        return name in self._organs.get(category, {})

    def list_all_organs(self) -> list[tuple[str, str]]:
        """Return coordinate list of all mounted organs ``[(category, name), ...]``.

        v0.5.14: for /healthz stethoscope to iterate all organs.
        """
        result: list[tuple[str, str]] = []
        for category, bucket in sorted(self._organs.items()):
            for name in sorted(bucket.keys()):
                result.append((category, name))
        return result

    def assert_organs_mounted(
        self, required: list[tuple[str, str]],
    ) -> None:
        """Assert required organs are mounted, otherwise raises :class:`OrganNotMountedError`.

        Used by the application layer to verify anatomical integrity after assembly.
        Which specific organs a "main cat must have" is decided by the application layer;
        OrganHost only provides the verification mechanism.

        Args:
            required: ``[(category, name), ...]`` required organ checklist
        """
        for category, name in required:
            if not self.has_organ(category, name):
                raise OrganNotMountedError(category, name)


__all__ = ["OrganHost"]

