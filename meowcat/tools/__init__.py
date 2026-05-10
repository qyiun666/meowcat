# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat tool system — framework-layer Tool/Skill/Paws abstraction.

Every cat has paws, and paws can execute tools. The framework defines what a tool is,
how to register, and how to execute. Concrete implementations live in ``meowcat.plus``.

``meowcat/tools/`` has zero meowagent dependency and zero concrete I/O.
"""

from __future__ import annotations

from meowcat.tools.matcher import KeywordToolMatcher
from meowcat.tools.paws import PawsEngine
from meowcat.tools.skill import Skill, SkillRegistry, SkillSpec
from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec
from meowcat.tools.tool_call import DoTaskResult, ToolCall, XmlToolCallParser

# -- Re-export concrete plus/ implementations for backward compatibility -----
# Delegates to the central _LAZY_MAP from meowcat._exports (single source of truth).


def __getattr__(name: str):
    # Delegate to the top-level _LAZY_MAP (eliminates duplicate maintenance)
    from meowcat import _LAZY_MAP

    entry = _LAZY_MAP.get(name)
    if entry is not None:
        import importlib

        mod_path, attr = entry
        try:
            module = importlib.import_module(mod_path)
        except ImportError as e:
            raise ImportError(
                f"'{name}' requires the '{mod_path}' package, which may not be installed."
            ) from e
        value = getattr(module, attr)
        globals()[name] = value
        return value
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
    "PawsEngine",
    "ChromaStore",
    "Crystallizer",
    "DefaultDetector",
    "KeywordToolMatcher",
    "SkillLoader",
    # v2.2.0
    "ToolCall",
    "DoTaskResult",
    "XmlToolCallParser",
]
