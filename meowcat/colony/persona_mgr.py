# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Persona management Mixin (v2.5.0).

Stores persona definitions in the colony ``personas/`` namespace via
the colony's namespace storage (``ns_get/ns_set/ns_list_keys``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from meowcat.persona import Persona


class _PersonaMixinHost(Protocol):
    """Protocol declaring the Colony attributes that _PersonaMixin depends on."""

    async def ns_get(self, namespace: str, key: str) -> Any: ...
    async def ns_set(self, namespace: str, key: str, value: Any) -> None: ...
    async def ns_list_keys(self, namespace: str) -> list[str]: ...


class _PersonaMixin(_PersonaMixinHost):
    """Persona storage methods for Colony.

    Provides persona registration, listing, and retrieval using
    the colony's ``personas/`` namespace.

    Requires the host class to provide:
        - ``self.ns_get("personas", key)`` -> Any
        - ``self.ns_set("personas", key, value)`` -> None
        - ``self.ns_list_keys("personas")`` -> list[str]
    """

    _PERSONA_NS = "personas"

    async def register_persona(self, persona: Persona) -> None:  # noqa: F821
        """Register a persona into the colony's ``personas/`` namespace.

        Args:
            persona: Persona instance to register.
        """
        from meowcat.persona import Persona

        if not isinstance(persona, Persona):
            raise TypeError(
                f"Expected Persona, got {type(persona).__name__}",
            )
        await self.ns_set(self._PERSONA_NS, persona.name, persona.to_dict())

    async def list_personas(self) -> list[str]:
        """List all registered persona names.

        Returns:
            List of persona names.
        """
        return await self.ns_list_keys(self._PERSONA_NS)

    async def get_persona(self, name: str) -> Persona | None:  # noqa: F821
        """Retrieve a persona by name from the colony namespace.

        Args:
            name: Persona name.

        Returns:
            Persona instance, or None if not found.
        """
        from meowcat.persona import Persona

        data = await self.ns_get(self._PERSONA_NS, name)
        if data is None:
            return None
        return Persona.from_dict(data)
