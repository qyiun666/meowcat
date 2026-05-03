"""meowcat 工具系统 — 框架层工具/Skill/Paws 抽象。

每只猫都有爪子，爪子能执行工具。框架定义什么是工具、怎么注册、
怎么执行。应用层负责提供具体工具实现。

``meowcat/tools/`` 零依赖 meowagent。
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
