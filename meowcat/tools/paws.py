"""meowcat Paws 执行引擎 — match → security → execute → audit。

每只猫的爪子执行工具的标准流程：
1. match — 根据名称/intent 匹配工具
2. security — 安全审查（风险等级、确认需求）
3. execute — 执行工具
4. audit — 记录执行日志

框架层定义这个流程，应用层可通过子类化定制各阶段行为。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry

logger = logging.getLogger(__name__)


class PawsEngine:
    """爪子执行引擎 — 框架层工具执行标准流程。

    执行流程::

        engine = PawsEngine(cat.tool_registry)
        result = await engine.execute("read_file", path="/tmp/hello.txt")
        # result = {"success": True, "output": "...", "tool": "read_file", ...}

    Args:
        tool_registry: 工具注册中心
        require_confirm: 是否要求高风险工具确认（默认 True）
        timeout_s: 工具执行超时秒数（默认 30）
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        *,
        require_confirm: bool = True,
        timeout_s: float = 30.0,
    ) -> None:
        self.tool_registry = tool_registry
        self.require_confirm = require_confirm
        self.timeout_s = timeout_s
        self._audit_log: list[dict[str, Any]] = []

    # -- 主入口 -------------------------------------------------------

    async def execute(
        self,
        name: str,
        **params: Any,
    ) -> dict[str, Any]:
        """执行一个工具：查找 → 安全审查 → 执行 → 记录日志。

        Returns:
            ``{"success": True/False, "output": str, "tool": name, ...}``
        """
        start = time.time()

        # 1. match: 按名称查找工具
        tool = self.tool_registry.get(name)
        if tool is None:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "output": f"Tool '{name}' not found",
                "tool": name,
                "elapsed_ms": elapsed,
            }

        # 2. security: 风险审查
        if not tool.enabled:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "output": f"Tool '{name}' is disabled",
                "tool": name,
                "elapsed_ms": elapsed,
            }

        # 高风险工具 + require_confirm → 标记需要确认
        needs_confirm = (
            self.require_confirm
            and tool.spec.risk in (RiskLevel.HIGH, RiskLevel.MEDIUM)
        )

        # 3. execute
        try:
            import asyncio
            output = await asyncio.wait_for(
                tool.execute(**params),
                timeout=self.timeout_s,
            )
            elapsed = (time.time() - start) * 1000
            result: dict[str, Any] = {
                "success": True,
                "output": output,
                "tool": name,
                "confirmed": not needs_confirm,
                "elapsed_ms": elapsed,
            }
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            result = {
                "success": False,
                "output": f"Tool '{name}' timed out after {self.timeout_s}s",
                "tool": name,
                "elapsed_ms": elapsed,
            }
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            result = {
                "success": False,
                "output": f"Error: {exc}",
                "tool": name,
                "elapsed_ms": elapsed,
            }

        # 4. audit: 记录日志
        self._log(tool, params, result)
        return result

    # -- 匹配 ---------------------------------------------------------

    def match(self, intent: str) -> list[Tool]:
        """根据意图关键词匹配工具。

        简单实现：按 name + description 做子串匹配。
        应用层可子类化实现更智能的匹配（LLM/embedding）。
        """
        q = intent.lower()
        results: list[Tool] = []
        for tool in self.tool_registry.list_all():
            score = 0
            if q in tool.name.lower():
                score += 10
            if q in tool.description.lower():
                score += 5
            if score > 0:
                results.append((score, tool))
        results.sort(key=lambda x: -x[0])
        return [r[1] for r in results]

    # -- 审计 ---------------------------------------------------------

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        """获取执行审计日志（只读副本）。"""
        return self._audit_log.copy()

    def _log(
        self, tool: Tool, params: dict[str, Any], result: dict[str, Any],
    ) -> None:
        """记录执行审计日志。"""
        entry = {
            "timestamp": time.time(),
            "tool": tool.name,
            "risk": tool.spec.risk.value,
            "params": {k: str(v)[:100] for k, v in params.items()},
            "success": result.get("success", False),
            "elapsed_ms": result.get("elapsed_ms", 0),
        }
        self._audit_log.append(entry)
        logger.info(
            "[PawsEngine] tool=%s success=%s elapsed=%.1fms",
            tool.name, entry["success"], entry["elapsed_ms"],
        )
