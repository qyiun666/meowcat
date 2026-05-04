"""meowcat plus builtin tools — pre-assembled tool set.

These are the concrete tool implementations every cat can use
out of the box.  Pure-framework abstractions live in ``meowcat.tools``.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from meowcat.tools.tool import Tool
from meowcat.plus.tools.file_ops import plus_read_file, plus_write_file
from meowcat.plus.tools.command import plus_run_command
from meowcat.plus.tools.http_client import plus_http_get

BUILTIN_TOOLS: list[Tool] = [
    plus_read_file,
    plus_write_file,
    plus_run_command,
    plus_http_get,
]

__all__ = ["BUILTIN_TOOLS"]
