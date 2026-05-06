# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat tool base — framework-layer Tool abstraction.

Every cat has paws, and paws can execute tools. The framework defines what a tool is,
how to register, and how to execute. The application layer provides concrete tool implementations.
"""


from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Tool execution risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolSpec:
    """Tool spec — framework-layer common format."""
    name: str
    description: str
    parameters: dict[str, dict[str, str]] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.MEDIUM
    category: str = "general"


class Tool:
    """An executable tool.

    Application layer subclasses this to implement concrete logic.
    The framework provides generic built-in tools in
    :mod:`meowcat.tools.builtin`.

    Usage::

        tool = Tool(ToolSpec(
            name="read_file",
            description="Read file contents",
            parameters={"path": {"type": "string", "description": "File path"}},
            risk=RiskLevel.LOW, category="file",
        ), handler=my_read_file_fn)

        await tool.execute(path="/tmp/hello.txt")
    """

    def __init__(
        self,
        spec: ToolSpec,
        handler: Callable[..., Awaitable[Any]] | None = None,
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
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    # -- Schema generation -------------------------------------------

    def to_openai_schema(self) -> dict:
        """Generate OpenAI function call format schema."""
        props: dict[str, dict] = {}
        required: list[str] = []
        for pname, pdef in self.spec.parameters.items():
            prop: dict[str, str] = {
                "type": pdef.get("type", "string"),
                "description": pdef.get("description", ""),
            }
            # Support array-type items
            if prop["type"] == "array" and "items" in pdef:
                prop["items"] = pdef["items"]
            props[pname] = prop
            required.append(pname)
        return {
            "type": "function",
            "function": {
                "name": self.spec.name,
                "description": self.spec.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        }

    # -- Execute ------------------------------------------------------

    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool, return result string."""
        if self._handler is None:
            raise RuntimeError(f"Tool '{self.name}' has no handler")
        try:
            result = self._handler(**kwargs)
            if hasattr(result, "__await__"):
                return str(await result)
            return str(result)
        except Exception as exc:
            logger.error("Tool '%s' failed: %s", self.name, exc)
            return f"Error executing '{self.name}': {exc}"


class ToolRegistry:
    """Tool registry — globally unique, mounted on cat instance.

    v1.1.5: Two-level cascade lookup — private tools first, then colony shared.

    Usage::

        registry = ToolRegistry()
        registry.register(tool)
        schemas = registry.to_openai_schemas()  # feed directly to LLM
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._by_category: dict[str, list[str]] = {}
        self._shared: ToolRegistry | None = None  # v1.1.5: colony shared tools

    def set_shared(self, registry: ToolRegistry) -> None:
        """Link to colony's shared tool registry for cascade lookup."""
        self._shared = registry

    def resolve(self, name: str) -> Tool | None:
        """Two-level lookup: private → colony shared."""
        tool = self._tools.get(name)
        if tool is not None:
            return tool
        if self._shared is not None:
            return self._shared.get(name)
        return None

    def register(self, tool: Tool) -> None:
        """Register a tool. Same-named tool will be overwritten."""
        if tool.name in self._tools:
            logger.warning(
                "Tool '%s' already registered, overwriting", tool.name)
        self._tools[tool.name] = tool
        cat = tool.spec.category
        self._by_category.setdefault(cat, []).append(tool.name)

    def unregister(self, name: str) -> bool:
        """Unregister a tool. Returns whether successful."""
        tool = self._tools.pop(name, None)
        if tool is None:
            return False
        cat = tool.spec.category
        cat_list = self._by_category.get(cat, [])
        if name in cat_list:
            cat_list.remove(name)
        return True

    def get(self, name: str) -> Tool | None:
        """Get tool by name."""
        return self._tools.get(name)

    def list_all(self, enabled_only: bool = True) -> list[Tool]:
        """List all tools."""
        if enabled_only:
            return [t for t in self._tools.values() if t.enabled]
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[Tool]:
        """List tools by category."""
        names = self._by_category.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def to_openai_schemas(self) -> list[dict]:
        """Generate OpenAI function call schemas for all registered tools."""
        return [t.to_openai_schema() for t in self.list_all()]

    def count(self) -> int:
        """Count of registered tools."""
        return len(self._tools)

    def enable(self, name: str) -> bool:
        """Enable a tool. Returns whether successful."""
        tool = self._tools.get(name)
        if tool:
            tool.enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool. Returns whether successful."""
        tool = self._tools.get(name)
        if tool:
            tool.disable()
            return True
        return False

