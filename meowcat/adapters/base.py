"""meowcat adapter base classes — AgentOrgan / SkillOrgan.

v1.2.14: Two thin base classes that adapt any external agent or skill
into a meowcat organ.  Both inherit :class:`Pluggable` so hooks still work.

The only difference between ``AgentOrgan`` and ``SkillOrgan`` is semantic:
*Use whichever name conveys intent* — the delegation mechanics are identical.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import asyncio
import logging
from typing import Any

from meowcat.errors import OrganDelegateError
from meowcat.pluggable import Pluggable

_log = logging.getLogger(__name__)


class AgentOrgan(Pluggable):
    """Base class for organs backed by an external agent.

    Subclasses override each Protocol method to call ``self._delegate("method", **kw)``.

    Args:
        agent: Any object whose methods match the target organ's Protocol.
        name: Optional display name (defaults to agent class name).

    Example::

        class CerebrumAgent(AgentOrgan):
            async def generate(self, prompt, system_prompt=None, **kw):
                return await self._delegate("generate", prompt=prompt,
                                           system_prompt=system_prompt, **kw)
    """

    def __init__(self, agent: Any, *, name: str | None = None) -> None:
        Pluggable.__init__(self)
        self._agent = agent
        self.name: str = name or getattr(agent, "name", type(agent).__name__)

    # ------------------------------------------------------------------
    # Core delegation
    # ------------------------------------------------------------------

    async def _delegate(self, method: str, **kw: Any) -> Any:
        """Call ``agent.method(**kw)``, handling sync/async and errors.

        Raises:
            OrganDelegateError: If the agent has no such method or the call fails.
        """
        fn = getattr(self._agent, method, None)
        if fn is None:
            raise OrganDelegateError(
                type(self).__name__, method,
                f"agent {type(self._agent).__name__!r} has no method {method!r}",
            )
        try:
            result = fn(**kw)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except OrganDelegateError:
            raise
        except Exception as exc:
            _log.debug(
                "%s.%s() delegation error: %s",
                type(self).__name__, method, exc,
            )
            raise OrganDelegateError(
                type(self).__name__, method, str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Diagnosable
    # ------------------------------------------------------------------

    def diagnose(self) -> dict[str, Any]:
        """Return adapter metadata."""
        return {
            "adapter": type(self).__name__,
            "agent": type(self._agent).__name__,
            "agent_type": str(type(self._agent)),
        }


class SkillOrgan(AgentOrgan):
    """Base class for organs backed by an external skill.

    Identical to :class:`AgentOrgan` in mechanics; use this when the backing
    implementation is semantically a "skill" (coarser-grained capability unit)
    rather than a general agent.
    """

    def diagnose(self) -> dict[str, Any]:
        return {
            "adapter": type(self).__name__,
            "skill": type(self._agent).__name__,
            "skill_type": str(type(self._agent)),
        }


__all__ = ["AgentOrgan", "SkillOrgan"]
