"""meowcat tool system — framework-layer Tool/Skill/Paws abstraction.

Every cat has paws, and paws can execute tools. The framework defines what a tool is,
how to register, and how to execute. The application layer provides concrete tool implementations.

``meowcat/tools/`` has zero meowagent dependency.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry, ToolSpec
from meowcat.tools.skill import Skill, SkillRegistry, SkillSpec
from meowcat.tools.builtin import BUILTIN_TOOLS
from meowcat.tools.paws import PawsEngine

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
]
