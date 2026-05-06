# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat Paws execution engine — match → security → execute → audit.

Standard tool execution flow for every cat's paws:
1. match — match tools by name/intent
2. security — security review (risk level, confirmation requirement)
3. execute — execute the tool
4. audit — record execution log

The framework layer defines this flow; the application layer can customize each stage via subclassing.
"""


from __future__ import annotations

import logging
import time
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolRegistry

logger = logging.getLogger(__name__)


class PawsEngine:
    """Paws execution engine — framework-layer standard tool execution flow.

    Execution flow::

        engine = PawsEngine(cat.tool_registry)
        result = await engine.execute("read_file", path="/tmp/hello.txt")
        # result = {"success": True, "output": "...", "tool": "read_file", ...}

    Args:
        tool_registry: Tool registry
        require_confirm: Whether to require confirmation for high-risk tools (default True)
        timeout_s: Tool execution timeout in seconds (default 30)
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
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    # -- Main entry point -----------------------------------------------

    async def execute(
        self,
        name: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Execute a tool: find → security review → execute → log.

        Returns:
            ``{"success": True/False, "output": str, "tool": name, ...}``
        """
        start = time.time()

        # 1. match: find tool by name
        tool = self.tool_registry.get(name)
        if tool is None:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "output": f"Tool '{name}' not found",
                "tool": name,
                "elapsed_ms": elapsed,
            }

        # 2. security: risk review
        if not tool.enabled:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "output": f"Tool '{name}' is disabled",
                "tool": name,
                "elapsed_ms": elapsed,
            }

        # High-risk tool + require_confirm → mark as needs confirmation
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

        # 4. audit: log
        self._log(tool, params, result)
        return result

    # -- Match --------------------------------------------------------

    def match(self, intent: str) -> list[Tool]:
        """Match tools by intent keywords.

        Simple implementation: substring match on name + description.
        Application layer can subclass for smarter matching (LLM/embedding).
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

    # -- Audit --------------------------------------------------------

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        """Get execution audit log (read-only copy)."""
        return self._audit_log.copy()

    def _log(
        self, tool: Tool, params: dict[str, Any], result: dict[str, Any],
    ) -> None:
        """Record execution audit log."""
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

