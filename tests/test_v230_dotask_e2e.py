# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v2.3.0 — do_task end-to-end integration tests.

Coverage:
  * Safety rejection (high-risk tools blocked)
  * Tool not found → error response fed back to cerebrum
  * Multi-round tool chaining
  * max_rounds exhaustion
  * DoTaskResult structure verification
  * Tool parameter passing and custom parser
"""

from __future__ import annotations

from typing import Any

import pytest

from meowcat.defaults.factory import create_cat
from meowcat.testing import make_test_colony
from meowcat.tools.tool import Tool, ToolSpec
from meowcat.tools.tool_call import DoTaskResult

from tests.conftest import FakeToolHandler, MultiStepCerebrum, SimpleCerebrum


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


class _SafeAmygdala:
    """Amygdala that returns risk assessment."""

    def __init__(self, risk_level: str = "none") -> None:
        self.risk_level = risk_level

    async def assess_safety(self, user_input):
        return {"safe": self.risk_level != "high", "risk": self.risk_level}


# ═══════════════════════════════════════════════════════════════════════
# TestDoTaskE2E
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.anyio
class TestDoTaskE2E:
    """End-to-end do_task tests — safety, tool errors, multi-round."""

    def _cat_with_cerebrum(self, cerebrum, name: str = "test-cat", risk_level: str = "none"):
        col = make_test_colony(f"dotask_{name}")
        cat = create_cat(name=name, container=col, cerebrum=cerebrum)
        # Replace amygdala for controlled safety checks
        cat.mount("brain", "amygdala", _SafeAmygdala(risk_level))
        return cat

    @pytest.mark.asyncio
    async def test_safety_high_risk_tool_rejected(self) -> None:
        """工具被安全策略拒绝后，继续尝试其他方法。"""
        cerebrum = MultiStepCerebrum([
            '<tool name="dangerous"><param name="cmd">rm -rf /</param></tool>',
            '<tool name="safe_echo"><param name="msg">hello</param></tool>',
            "任务完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "safety", risk_level="high")

        handler = FakeToolHandler({"output": "echo: hello"})
        cat.tool_registry.register(
            Tool(ToolSpec(name="dangerous", description="危险工具"), handler=handler))
        cat.tool_registry.register(
            Tool(ToolSpec(name="safe_echo", description="安全工具"), handler=handler))

        result = await cat.do_task("做点危险的事", max_rounds=5)
        assert isinstance(result, DoTaskResult)
        assert result.rounds >= 2
        for tc in result.tool_calls:
            assert tc.name != "dangerous"

    @pytest.mark.asyncio
    async def test_tool_not_found_returns_error_response(self) -> None:
        """工具未注册时，do_task 将错误信息反馈给 cerebrum 重新推理。"""
        cerebrum = MultiStepCerebrum([
            '<tool name="unknown_tool"><param name="x">1</param></tool>',
            "无法使用工具，任务回退到手动完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "missing_tool")
        result = await cat.do_task("做某事", max_rounds=5)
        assert isinstance(result, DoTaskResult)
        assert result.rounds >= 2

    @pytest.mark.asyncio
    async def test_multi_round_multiple_different_tools(self) -> None:
        """多轮调用不同工具链。"""
        cerebrum = MultiStepCerebrum([
            '<tool name="step1"><param name="a">1</param></tool>',
            '<tool name="step2"><param name="b">2</param></tool>',
            '<tool name="step3"><param name="c">3</param></tool>',
            "全部完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "chain")
        for name in ["step1", "step2", "step3"]:
            cat.tool_registry.register(Tool(
                ToolSpec(name=name, description=f"step {name}"),
                handler=FakeToolHandler({"output": f"{name}_output"}),
            ))
        result = await cat.do_task("多步操作", max_rounds=10)
        assert result.rounds == 4
        assert len(result.tool_calls) == 3
        assert [tc.name for tc in result.tool_calls] == [
            "step1", "step2", "step3"]

    @pytest.mark.asyncio
    async def test_max_rounds_exhaustion_returns_last_output(self) -> None:
        """max_rounds 耗尽时返回最后一轮的 cerebrum 输出。"""
        cerebrum = MultiStepCerebrum(
            ['<tool name="loop"><param name="n">1</param></tool>'] * 20
        )
        cat = self._cat_with_cerebrum(cerebrum, "exhaust")
        cat.tool_registry.register(Tool(
            ToolSpec(name="loop", description="looping tool"),
            handler=FakeToolHandler({"output": "looped"}),
        ))
        result = await cat.do_task("无限循环任务", max_rounds=3)
        assert result.rounds == 3
        assert len(result.tool_calls) == 3
        assert result.final_text != ""

    @pytest.mark.asyncio
    async def test_do_task_result_shape(self) -> None:
        """DoTaskResult 结构验证。"""
        cerebrum = SimpleCerebrum()
        cerebrum._response = "没有工具调用，直接完成"  # type: ignore[attr-defined]
        cat = self._cat_with_cerebrum(cerebrum, "shape")
        result = await cat.do_task("简单任务")
        assert isinstance(result, DoTaskResult)
        assert result.final_text == "没有工具调用，直接完成"
        assert result.rounds == 1
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_tool_params_passed_correctly(self) -> None:
        """验证工具参数正确传递给 handler。"""
        cerebrum = MultiStepCerebrum([
            '<tool name="calculator"><param name="expr">2+3</param><param name="precision">2</param></tool>',
            "结果是 5",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "params")
        handler = FakeToolHandler({"output": "5.00"})
        cat.tool_registry.register(Tool(
            ToolSpec(name="calculator", description="计算器"), handler=handler,
        ))
        result = await cat.do_task("计算 2+3", max_rounds=5)
        assert result.rounds == 2
        tc = result.tool_calls[0]
        assert tc.name == "calculator"
        assert tc.params["expr"] == "2+3"
        assert tc.params["precision"] == "2"

    @pytest.mark.asyncio
    async def test_custom_parser(self) -> None:
        """自定义解析器的 do_task 测试。"""

        class _SimpleParser:
            def extract(self, text: str):
                if "TOOL:" in text:
                    parts = text.split("\n", 1)
                    name_line = parts[0].replace("TOOL:", "").strip()
                    params_str = parts[1] if len(parts) > 1 else ""
                    params = {}
                    for line in params_str.split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            params[k.strip()] = v.strip()
                    from meowcat.tools.tool_call import ToolCall
                    return ToolCall(name=name_line, params=params)
                return None

        cerebrum = MultiStepCerebrum([
            "TOOL:echo\nmsg: hello\nuser: test",
            "任务完成",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "custom_parser")
        cat.tool_registry.register(Tool(
            ToolSpec(name="echo", description="echo"),
            handler=FakeToolHandler({"output": "echo: hello"}),
        ))
        result = await cat.do_task("解析测试", max_rounds=5, parser=_SimpleParser())
        assert result.rounds == 2
        assert result.tool_calls[0].name == "echo"
        assert result.tool_calls[0].params["msg"] == "hello"

    @pytest.mark.asyncio
    async def test_safe_tool_allowed_when_risk_none(self) -> None:
        """低风险工具正常执行。"""
        cerebrum = MultiStepCerebrum([
            '<tool name="read"><param name="file">test.txt</param></tool>',
            "文件内容: hello world",
        ])
        cat = self._cat_with_cerebrum(cerebrum, "safe", risk_level="none")
        cat.tool_registry.register(Tool(
            ToolSpec(name="read", description="read file"),
            handler=FakeToolHandler({"output": "hello world"}),
        ))
        result = await cat.do_task("读取文件", max_rounds=5)
        assert result.rounds == 2
        assert result.tool_calls[0].name == "read"

    @pytest.mark.asyncio
    async def test_do_task_accepts_timeout_parameter(self) -> None:
        """do_task 接受 timeout 参数且不影响正常执行."""
        cerebrum = SimpleCerebrum()
        cerebrum._response = "直接完成，无需工具"  # type: ignore[attr-defined]
        cat = self._cat_with_cerebrum(cerebrum, "timeout_param")
        result = await cat.do_task("简单任务", timeout=1.0)
        assert isinstance(result, DoTaskResult)
        assert result.final_text == "直接完成，无需工具"
        result2 = await cat.do_task("简单任务", timeout=None)
        assert isinstance(result2, DoTaskResult)
        assert result2.final_text == "直接完成，无需工具"
