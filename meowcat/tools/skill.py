"""meowcat Skill 系统 — 框架层可复用技能抽象。

与 Tool 的区别：
- Tool: 原子操作（"读文件"、"发请求"）
- Skill: 组合能力（"生成 CRUD 代码"、"审查安全性"）

Skill 是比 Tool 更粗粒度的能力单元，一个 Skill 内部可能调用多个 Tool。
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Union

logger = logging.getLogger(__name__)


@dataclass
class SkillSpec:
    """Skill 描述 — 比 ToolSpec 更粗粒度的能力单元。"""
    name: str
    description: str
    version: str = "0.1.0"
    parameters: dict[str, dict[str, str]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    source: str = "builtin"
    category: str = "general"


class Skill:
    """一个可复用技能。

    用法::

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

    # -- 便捷属性 ---------------------------------------------------

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

    # -- 执行 -------------------------------------------------------

    async def execute(self, **kwargs: Any) -> str:
        """执行技能，返回结果字符串。"""
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
    """技能注册中心。按 name 索引。

    用法::

        registry = SkillRegistry()
        registry.register(skill)
        results = registry.search("code review")
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册一个 Skill。同名会被覆盖。"""
        if skill.name in self._skills:
            logger.warning(
                "Skill '%s' already registered, overwriting", skill.name)
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """按名称获取 Skill。"""
        return self._skills.get(name)

    def list_all(self, enabled_only: bool = True) -> list[Skill]:
        """列出全部 Skill。"""
        if enabled_only:
            return [s for s in self._skills.values() if s.enabled]
        return list(self._skills.values())

    def list_by_source(self, source: str, enabled_only: bool = True) -> list[Skill]:
        """按 source 筛选。"""
        return [s for s in self._skills.values()
                if s.spec.source == source and (not enabled_only or s.enabled)]

    def list_by_category(self, category: str, enabled_only: bool = True) -> list[Skill]:
        """按 category 筛选。"""
        return [s for s in self._skills.values()
                if s.spec.category == category and (not enabled_only or s.enabled)]

    def enable(self, name: str) -> bool:
        """启用一个 Skill。"""
        skill = self._skills.get(name)
        if skill:
            skill.enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用一个 Skill。"""
        skill = self._skills.get(name)
        if skill:
            skill.disable()
            return True
        return False

    def count(self) -> int:
        """已注册 Skill 数量。"""
        return len(self._skills)

    def search(self, query: str) -> list[Skill]:
        """模糊搜索（name + description + tags）。"""
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
