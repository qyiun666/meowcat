# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""ToolCall + TaskResult + built-in XML tool-call parser.

Usage::

    from meowcat.tools.tool_call import ToolCall, TaskResult, XmlToolCallParser

    parser = XmlToolCallParser()
    tc = parser.extract('<tool name="read_file"><param name="path">/tmp/x</param></tool>')
    # tc == ToolCall(name="read_file", params={"path": "/tmp/x"})
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


# -- Data types --------------------------------------------------------


@dataclass
class ToolCall:
    """A tool call extracted from cerebrum's output text.

    Args:
        name: Tool name (matches PawsEngine registry key).
        params: Tool parameters as key-value pairs.
    """

    name: str
    params: dict[str, object] = field(default_factory=dict)


@dataclass
class TaskResult:
    """The result of one ``cat.do_task()`` execution.

    Args:
        final_text: The final text output (from the last cerebrum round).
        rounds: Number of brain-tool rounds executed.
        tool_calls: All tool calls that were made during execution.
    """

    final_text: str
    rounds: int
    tool_calls: list[ToolCall] = field(default_factory=list)


# -- Protocol ----------------------------------------------------------


class ToolCallParser(Protocol):
    """Protocol: extract tool calls from cerebrum's text output.

    Built-in implementations:
    - :class:`XmlToolCallParser` — XML tag format
    - App-layer can provide custom parsers for JSON function-call,
      Anthropic tool-use blocks, etc.
    """

    def extract(self, text: str) -> ToolCall | None:
        """Extract a tool call from cerebrum output text.

        Args:
            text: The full text output from cerebrum.generate().

        Returns:
            A ToolCall if a tool invocation is detected, None otherwise.
        """
        ...


# -- Built-in XML parser -----------------------------------------------


class XmlToolCallParser:
    """Built-in parser: XML tag format.

    Expected cerebrum output format::

        <tool name="tool_name">
          <param name="param1">value1</param>
          <param name="param2">value2</param>
        </tool>

    Key features:
    - Case-insensitive tag matching (case-insensitive attribute matching).
    - Whitespace-tolerant (any whitespace between attributes, multiline params).
    - Multiple ``<param>`` elements extracted into a dict.
    - If no ``<tool>`` tag is found, returns None (no tool call).
    """

    _TOOL_PATTERN: re.Pattern[str] = re.compile(
        r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>',
        re.DOTALL | re.IGNORECASE,
    )
    _PARAM_PATTERN: re.Pattern[str] = re.compile(
        r'<param\s+name="([^"]+)"\s*>(.*?)</param>',
        re.DOTALL | re.IGNORECASE,
    )

    def extract(self, text: str) -> ToolCall | None:
        """Extract tool call from cerebrum output text.

        Args:
            text: Full text output from cerebrum.generate().

        Returns:
            ToolCall if found, None if no tool tag present.
        """
        m = self._TOOL_PATTERN.search(text)
        if not m:
            return None

        name = m.group(1).strip()
        params_body = m.group(2)

        params: dict[str, object] = {}
        for pm in self._PARAM_PATTERN.finditer(params_body):
            key = pm.group(1).strip()
            value = pm.group(2).strip()
            params[key] = value

        return ToolCall(name=name, params=params)


__all__ = [
    "ToolCall",
    "TaskResult",
    "ToolCallParser",
    "XmlToolCallParser",
]
