# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat assembly — do_task Mixin (v2.3.0: extracted from assembly.py).

Provides :class:`DoTaskMixin` which implements the brain-tool multi-round loop
for ``cat.do_task(...)``. Split from assembly.py per H-06 remediation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class DoTaskMixin:
    """Mixin that provides the brain-tool multi-round loop.

    Requires: ``self.path_registry`` and ``self.tool_registry`` (provided by CatBase).
    """

    async def do_task(
        self,
        task: str,
        *,
        max_rounds: int = 10,
        timeout: float | None = 120.0,
        parser: Any = None,
    ) -> Any:
        """Brain-tool multi-round loop — think → call tools → think → ... until done.

        Each round:
        1. Cerebrum thinks about the current context
        2. If cerebrum output contains a tool call → safety check → execute tool
        3. Tool result feeds back into context for next round
        4. If cerebrum says no more tools needed → final answer

        Args:
            task: Task description (e.g. "写一个用户登录函数").
            max_rounds: Maximum brain-tool rounds (prevents infinite loops).
            timeout: Total timeout in seconds. None = no timeout.
            parser: Tool-call parser. Defaults to ``XmlToolCallParser``.

        Returns:
            :class:`~meowcat.tools.tool_call.DoTaskResult` with final_text,
            rounds, and tool_calls list.
        """
        from meowcat.tools.tool_call import DoTaskResult, ToolCall, XmlToolCallParser

        if parser is None:
            parser = XmlToolCallParser()

        tool_calls: list[ToolCall] = []
        context: str = task
        final_text: str = ""
        rounds: int = 0

        for _ in range(max_rounds):
            rounds += 1
            # 1. Cerebrum thinks
            cerebrum_result: str = await self.path_registry.run(
                self, "deep_reason", prompt=context,
            )

            # 2. Try to extract a tool call
            tool_call = parser.extract(cerebrum_result)
            if tool_call is None:
                # No tool → this is the final answer
                final_text = cerebrum_result
                break

            # 3. Safety check
            safe = await self.path_registry.run(
                self, "assess_safety",
                user_input=str(tool_call.params),
            )
            if isinstance(safe, dict) and safe.get("risk") == "high":
                context = (
                    f"工具 {tool_call.name} 被安全策略拒绝（高风险操作）。"
                    f"请尝试其他方法完成原始任务: {task}"
                )
                continue

            # 4. Execute tool (bypass wiring — PawsEngine is the standard entry)
            from meowcat.tools.paws import PawsEngine

            paws = PawsEngine(self.tool_registry)
            raw_result = await paws.execute(
                name=tool_call.name, **tool_call.params,
            )
            # Extract meaningful output for LLM context (not raw dict repr)
            tool_result: str = raw_result.get("output", str(raw_result))
            tool_calls.append(tool_call)

            # 5. Feed result back as context for next round
            context = (
                f"原始任务: {task}\n\n"
                f"上一轮工具 {tool_call.name} 的执行结果:\n{tool_result}\n\n"
                f"请根据以上结果继续完成原始任务。如果任务已完成请输出最终答案，"
                f"如果还需要调用工具请使用 <tool name=\"...\"> 标签。"
            )
        else:
            # max_rounds exhausted — use last cerebrum output
            final_text = cerebrum_result or ""

        return DoTaskResult(
            final_text=final_text,
            rounds=rounds,
            tool_calls=tool_calls,
        )
