# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Skill system — framework-layer reusable skill abstraction.

Difference from Tool:
- Tool: atomic operation ("read file", "send request")
- Skill: composite capability ("generate CRUD code", "review security")

A Skill is a coarser-grained capability unit than a Tool; a Skill may internally call multiple Tools.
"""


from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Union

logger = logging.getLogger(__name__)


@dataclass
class SkillSpec:
    """Skill spec — coarser-grained capability unit than ToolSpec."""
    name: str
    description: str
    version: str = "0.1.0"
    parameters: dict[str, dict[str, str]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    source: str = "builtin"
    category: str = "general"


class Skill:
    """A reusable skill.

    Usage::

        skill = Skill(SkillSpec(
            name="code_review",
            description="Review code for bugs and style",
            tags=["code", "quality"],
        ), handler=my_review_fn)

        result = await skill.execute(code="def foo(): pass")
    """

    def __init__(
        self,
        spec: SkillSpec,
        handler: Callable[..., Union[str,
                                     Coroutine[Any, Any, str]]] | None = None,
    ) -> None:
        self.spec = spec
        self._handler = handler
        self._enabled = True

    # -- Convenience properties ----------------------------------------

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def description(self) -> str:
        return self.spec.description

    @property
    def parameters(self) -> dict[str, dict[str, str]]:
        return self.spec.parameters

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    # -- Execute ------------------------------------------------------

    async def execute(self, **kwargs: Any) -> str:
        """Execute the skill, return result string."""
        if self._handler is None:
            raise RuntimeError(f"Skill '{self.name}' has no handler")
        try:
            import asyncio
            raw = self._handler(**kwargs)
            if asyncio.iscoroutine(raw):
                return str(await raw)
            return str(raw)
        except Exception as exc:
            logger.error("Skill '%s' failed: %s", self.name, exc)
            return f"Error executing '{self.name}': {exc}"


class SkillRegistry:
    """Skill registry. Indexed by name.

    v1.1.5: Two-level cascade lookup — private skills first, then colony shared.

    Usage::

        registry = SkillRegistry()
        registry.register(skill)
        results = registry.search("code review")
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._shared: SkillRegistry | None = None  # v1.1.5: colony shared skills

    def set_shared(self, registry: SkillRegistry) -> None:
        """Link to colony's shared skill registry for cascade lookup."""
        self._shared = registry

    def resolve(self, name: str) -> Skill | None:
        """Two-level lookup: private → colony shared."""
        skill = self._skills.get(name)
        if skill is not None:
            return skill
        if self._shared is not None:
            return self._shared.get(name)
        return None

    def register(self, skill: Skill) -> None:
        """Register a Skill. Same name will be overwritten."""
        if skill.name in self._skills:
            logger.warning(
                "Skill '%s' already registered, overwriting", skill.name)
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """Get Skill by name."""
        return self._skills.get(name)

    def list_all(self, enabled_only: bool = True) -> list[Skill]:
        """List all Skills."""
        if enabled_only:
            return [s for s in self._skills.values() if s.enabled]
        return list(self._skills.values())

    def list_by_source(self, source: str, enabled_only: bool = True) -> list[Skill]:
        """Filter by source."""
        return [s for s in self._skills.values()
                if s.spec.source == source and (not enabled_only or s.enabled)]

    def list_by_category(self, category: str, enabled_only: bool = True) -> list[Skill]:
        """Filter by category."""
        return [s for s in self._skills.values()
                if s.spec.category == category and (not enabled_only or s.enabled)]

    def enable(self, name: str) -> bool:
        """Enable a Skill."""
        skill = self._skills.get(name)
        if skill:
            skill.enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a Skill."""
        skill = self._skills.get(name)
        if skill:
            skill.disable()
            return True
        return False

    def count(self) -> int:
        """Count of registered Skills."""
        return len(self._skills)

    def search(self, query: str) -> list[Skill]:
        """Fuzzy search (name + description + tags)."""
        q = query.lower()
        results: list[Skill] = []
        for skill in self._skills.values():
            if q in skill.name.lower():
                results.append(skill)
            elif q in skill.description.lower():
                results.append(skill)
            elif any(q in t.lower() for t in skill.spec.tags):
                results.append(skill)
        return results

