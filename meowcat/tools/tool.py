"""meowcat 工具基类 — 框架层 Tool 抽象。

每只猫都有爪子，爪子能执行工具。框架定义什么是工具、怎么注册、
怎么执行。应用层负责提供具体工具实现。
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """工具执行风险等级。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolSpec:
    """工具描述 — 框架层通用格式。"""
    name: str
    description: str
    parameters: dict[str, dict[str, str]] = field(default_factory=dict)
    risk: RiskLevel = RiskLevel.MEDIUM
    category: str = "general"


class Tool:
    """一个可执行工具。

    应用层继承此类实现具体逻辑。框架提供通用内置工具在
    :mod:`meowcat.tools.builtin` 中。

    用法::

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

    # -- 便捷属性 ---------------------------------------------------

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

    # -- Schema 生成 ------------------------------------------------

    def to_openai_schema(self) -> dict:
        """生成 OpenAI function call 格式的 schema。"""
        props: dict[str, dict] = {}
        required: list[str] = []
        for pname, pdef in self.spec.parameters.items():
            prop: dict[str, str] = {
                "type": pdef.get("type", "string"),
                "description": pdef.get("description", ""),
            }
            # 支持 array 类型的 items
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

    # -- 执行 -------------------------------------------------------

    async def execute(self, **kwargs: Any) -> str:
        """执行工具，返回结果字符串。"""
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
    """工具注册中心 — 全局唯一，挂载在 cat 实例上。

    用法::

        registry = ToolRegistry()
        registry.register(tool)
        schemas = registry.to_openai_schemas()  # 直接喂给 LLM
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._by_category: dict[str, list[str]] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具。同名工具会被覆盖。"""
        if tool.name in self._tools:
            logger.warning(
                "Tool '%s' already registered, overwriting", tool.name)
        self._tools[tool.name] = tool
        cat = tool.spec.category
        self._by_category.setdefault(cat, []).append(tool.name)

    def unregister(self, name: str) -> bool:
        """注销一个工具。返回是否成功。"""
        tool = self._tools.pop(name, None)
        if tool is None:
            return False
        cat = tool.spec.category
        cat_list = self._by_category.get(cat, [])
        if name in cat_list:
            cat_list.remove(name)
        return True

    def get(self, name: str) -> Tool | None:
        """按名称获取工具。"""
        return self._tools.get(name)

    def list_all(self, enabled_only: bool = True) -> list[Tool]:
        """列出所有工具。"""
        if enabled_only:
            return [t for t in self._tools.values() if t.enabled]
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[Tool]:
        """按分类列出工具。"""
        names = self._by_category.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def to_openai_schemas(self) -> list[dict]:
        """生成所有已注册工具的 OpenAI function call schemas。"""
        return [t.to_openai_schema() for t in self.list_all()]

    def count(self) -> int:
        """已注册工具数量。"""
        return len(self._tools)

    def enable(self, name: str) -> bool:
        """启用一个工具。返回是否成功。"""
        tool = self._tools.get(name)
        if tool:
            tool.enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用一个工具。返回是否成功。"""
        tool = self._tools.get(name)
        if tool:
            tool.disable()
            return True
        return False
