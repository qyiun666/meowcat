"""meowcat tool system — framework-layer Tool/Skill/Paws abstraction.

Every cat has paws, and paws can execute tools. The framework defines what a tool is,
how to register, and how to execute. Concrete implementations live in ``meowcat.plus``.

``meowcat/tools/`` has zero meowagent dependency and zero concrete I/O.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec
from meowcat.tools.skill import Skill, SkillRegistry, SkillSpec
from meowcat.tools.paws import PawsEngine
from meowcat.tools.matcher import KeywordToolMatcher

# -- Re-export concrete plus/ implementations for backward compatibility -----
# Lazy-loaded to avoid circular import with meowcat.plus

_PLUS_LAZY: dict[str, str] = {
    "BUILTIN_TOOLS": "meowcat.plus.tools",
    "BrowserTool": "meowcat.plus",
    "ChromaStore": "meowcat.plus",
    "Crystallizer": "meowcat.plus",
    "DefaultDetector": "meowcat.plus",
    "MCPClient": "meowcat.plus",
    "MCPServerConfig": "meowcat.plus",
    "MCPTool": "meowcat.plus",
    "SkillLoader": "meowcat.plus",
}


def __getattr__(name: str):
    if name in _PLUS_LAZY:
        import importlib
        try:
            mod = importlib.import_module(_PLUS_LAZY[name])
        except ImportError as e:
            raise ImportError(
                f"'{name}' requires the 'meowcat.plus' package, "
                f"which is not installed. Install with: pip install meowcat[plus]"
            ) from e
        attr = getattr(mod, name)
        # Cache in module globals
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Remove eager imports that cause circular dependency
# (previously: from meowcat.plus.tools import BUILTIN_TOOLS; from meowcat.plus import ...)

__all__ = [
    "Tool",
    "ToolSpec",
    "RiskLevel",
    "ToolRegistry",
    "Skill",
    "SkillSpec",
    "SkillRegistry",
    "BUILTIN_TOOLS",
    "PawsEngine",
    "MCPClient",
    "MCPServerConfig",
    "MCPTool",
    "SkillLoader",
    "BrowserTool",
    "ChromaStore",
    "Crystallizer",
    "DefaultDetector",
    "KeywordToolMatcher",
]
